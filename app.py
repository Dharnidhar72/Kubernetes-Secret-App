from flask import Flask, request, render_template
from kubernetes import client, config
import base64
import os
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Ensure templates directory exists
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(templates_dir, exist_ok=True)

# Configure Kubernetes client
def setup_kubernetes_config():
    try:
        # Try local config first (for development)
        config.load_kube_config()
        app.logger.info("Loaded local Kubernetes configuration")
    except Exception as e:
        app.logger.warning(f"Failed to load local Kubernetes config: {e}")
        try:
            # Fallback to in-cluster config (when running in Kubernetes)
            config.load_incluster_config()
            app.logger.info("Loaded in-cluster Kubernetes configuration")
        except Exception as e2:
            app.logger.error(f"Failed to load any Kubernetes configuration: {e2}")
            raise RuntimeError("Could not configure Kubernetes client")

def create_deployment_with_secret(secret_name):
    """Create a deployment that mounts the given secret"""
    v1_apps = client.AppsV1Api()
    
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=f"app-{secret_name}"),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": f"app-{secret_name}"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": f"app-{secret_name}"}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="application",
                            image="nginx:latest",  # You can change this to your application image
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="secret-volume",
                                    mount_path="/mnt/secrets",
                                    read_only=True
                                )
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="secret-volume",
                            secret=client.V1SecretVolumeSource(
                                secret_name=secret_name
                            )
                        )
                    ]
                )
            )
        )
    )
    
    try:
        v1_apps.create_namespaced_deployment(
            namespace="default",
            body=deployment
        )
        return f"Deployment created with secret {secret_name} mounted"
    except client.exceptions.ApiException as e:
        if e.status == 409:
            # Deployment already exists, update it
            v1_apps.replace_namespaced_deployment(
                name=f"app-{secret_name}",
                namespace="default",
                body=deployment
            )
            return f"Deployment updated with secret {secret_name} mounted"
        raise

def get_deployment_status(secret_name):
    """Get the status of the deployment using the secret"""
    v1_apps = client.AppsV1Api()
    try:
        deployment = v1_apps.read_namespaced_deployment(
            name=f"app-{secret_name}",
            namespace="default"
        )
        return {
            'ready_replicas': deployment.status.ready_replicas or 0,
            'total_replicas': deployment.status.replicas or 0
        }
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return None
        raise

def create_or_update_secret(db_name, db_password):
    """Create or update a Kubernetes secret and create a deployment using it"""
    v1 = client.CoreV1Api()
    
    # Convert the database name to lowercase to comply with Kubernetes naming requirements
    safe_db_name = db_name.lower().replace('_', '-')
    secret_name = f"db-secret-{safe_db_name}"
    namespace = "default"

    # Prepare the data with proper Base64 encoding
    secret_data = {
        "DB_NAME": base64.b64encode(db_name.encode("utf-8")).decode("utf-8"),
        "DB_PASSWORD": base64.b64encode(db_password.encode("utf-8")).decode("utf-8")
    }

    try:
        # Try to read the existing secret
        existing_secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
        app.logger.info(f"Secret {secret_name} exists. Updating...")

        # Update the existing secret
        existing_secret.data = secret_data
        v1.replace_namespaced_secret(name=secret_name, namespace=namespace, body=existing_secret)
        
        # Create or update deployment with the secret
        deployment_message = create_deployment_with_secret(secret_name)
        return f"Secret '{secret_name}' successfully updated and {deployment_message}"
    
    except client.exceptions.ApiException as e:
        if e.status == 404:
            # Secret doesn't exist, create a new one
            app.logger.info(f"Secret {secret_name} not found. Creating a new one...")
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(name=secret_name),
                data=secret_data,
                type="Opaque"
            )
            v1.create_namespaced_secret(namespace=namespace, body=secret)
            
            # Create deployment with the new secret
            deployment_message = create_deployment_with_secret(secret_name)
            return f"Secret '{secret_name}' successfully created and {deployment_message}"
        else:
            # Handle other API errors
            error_msg = f"Kubernetes API error: {e.reason}"
            app.logger.error(error_msg)
            raise RuntimeError(error_msg)

@app.route("/", methods=["GET", "POST"])
def index():
    """Main route handler with comprehensive error handling"""
    message = ""
    status = "info"
    deployments = []
    
    # Get all secrets and their deployment status
    try:
        v1 = client.CoreV1Api()
        secrets = v1.list_namespaced_secret(namespace="default")
        for secret in secrets.items:
            if secret.metadata.name.startswith('db-secret-'):
                deployment_status = get_deployment_status(secret.metadata.name)
                if deployment_status:
                    deployments.append({
                        'name': secret.metadata.name,
                        'status': deployment_status
                    })
    except Exception as e:
        app.logger.error(f"Error getting deployments: {e}")
    
    if request.method == "POST":
        try:
            db_name = request.form.get("db_name", "").strip()
            db_password = request.form.get("db_password", "").strip()
            
            # Validate inputs
            if not db_name:
                raise ValueError("Database name cannot be empty")
            if not db_password:
                raise ValueError("Database password cannot be empty")
                
            # Create or update the secret and deployment
            message = create_or_update_secret(db_name, db_password)
            status = "success"
            
        except ValueError as ve:
            message = f"Validation error: {str(ve)}"
            status = "warning"
            app.logger.warning(message)
        except Exception as e:
            message = f"An unexpected error occurred: {str(e)}"
            status = "error"
            app.logger.error(f"Unexpected exception: {e}", exc_info=True)

    return render_template("index.html", 
                         message=message, 
                         status=status, 
                         deployments=deployments)

if __name__ == "__main__":
    # Setup Kubernetes config before starting the app
    try:
        setup_kubernetes_config()
        app.run(host="0.0.0.0", port=5001, debug=False)
    except Exception as e:
        print(f"Failed to start application: {e}")
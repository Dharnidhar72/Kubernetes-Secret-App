# Kubernetes Secret Management Application

This is a web-based application for managing Kubernetes secrets with automatic deployment capabilities. The application provides a user-friendly interface to create and manage Kubernetes secrets and automatically creates deployments with secrets mounted.

## Prerequisites

- Docker Desktop
- Kubernetes (kind cluster)
- Python 3.9+
- `kubectl` command-line tool

## Installation Steps

1. Clone the repository:
   ```bash
   git clone [your-repository-url]
   cd kubernetes-secrets-app
   ```

2. Create a kind cluster (if not already created):
   ```bash
   kind create cluster
   ```

3. Build the Docker image:
   ```bash
   docker build -t secret-manager:latest .
   ```

4. Load the image into the kind cluster:
   ```bash
   kind load docker-image secret-manager:latest
   ```

5. Deploy the application:
   ```bash
   kubectl apply -f deployment.yaml
   ```

6. Start port forwarding:
   ```bash
   kubectl port-forward svc/secret-manager 30001:80
   ```

7. Access the application:

   Open your browser and navigate to [localhost:30001](http://localhost:30001).

## Project Structure

```
kubernetes-secrets-app/
├── app.py                 # Main Flask application
├── Dockerfile             # Docker configuration  
├── requirements.txt       # Python dependencies
├── deployment.yaml        # Kubernetes deployment configuration
└── templates/
    └── index.html         # Web interface template
```

## Usage

1. Open the web interface at [localhost:30001](http://localhost:30001)
2. Enter database credentials:
   - **Database Name** (will be automatically converted to lowercase)
   - **Database Password**
     <img width="1434" alt="image" src="https://github.com/user-attachments/assets/abff5f02-a551-4518-a525-a6847071919e" />

3. Click **"Create / Update Secret"**  
   The application will:
   - Create a Kubernetes secret
   - Create a deployment with the secret mounted
   - Display the deployment status
     <img width="1003" alt="Screenshot 2025-02-19 at 11 44 56 PM" src="https://github.com/user-attachments/assets/c8d086b7-f885-4fba-91ba-c3528d026cba" />


## Verification Commands

Check created secrets:
```bash
kubectl get secrets
```

View secret details:
```bash
kubectl describe secret db-secret-<database-name>
```

Check deployments:
```bash
kubectl get deployments
```

Check pod status:
```bash
kubectl get pods
```
<img width="413" alt="image" src="https://github.com/user-attachments/assets/74d33070-f7d4-4574-8c13-1eb3693eebfc" />
<img width="279" alt="image" src="https://github.com/user-attachments/assets/304f7011-f5e8-4fe4-95b1-4bfa00878403" />





## Troubleshooting

### If pods are not starting:
```bash
# View pod logs
kubectl logs <pod-name>

# Describe pod for events  
kubectl describe pod <pod-name>
```

### If the web interface is not accessible:
```bash
# Verify service is running
kubectl get services

# Check port forwarding
kubectl port-forward svc/secret-manager 30001:80
```

## Key Files and Components

### `app.py`
- Main Flask application
- Handles Kubernetes configuration
- Manages secrets and deployments
- Processes web requests

### `deployment.yaml`
- Deployment configuration
- Service definition
- RBAC settings
- Volume mounts

### `index.html`
- Web interface
- Form for secret creation
- Status display
- Deployment monitoring

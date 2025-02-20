# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Copy requirements file first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ templates/

# Ensure templates directory exists (matches your app.py)
RUN mkdir -p templates

# Make port 5001 available (matches your app.py port)
EXPOSE 5001

# Command to run the application
CMD ["python3", "app.py"]
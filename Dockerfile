# Azure Container Apps Deployment Configuration
# This file configures deployment to Azure Container Apps with pay-as-you-go pricing

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory and ensure permissions
RUN mkdir -p /app/data && \
    chmod 755 /app/data

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/health', timeout=5)"

# Run the application with waitress (production WSGI server)
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=5001", "app:app"]
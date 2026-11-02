#!/bin/bash
# Automated Azure Container Apps Deployment Script for JobFlow
# This script deploys JobFlow to Azure with pay-as-you-go pricing

set -e

echo "🚀 Starting Azure Container Apps deployment for JobFlow..."

# Configuration
RESOURCE_GROUP="rg-jobflow"
LOCATION="eastus2"
CONTAINER_APP_ENV="jobflow-env"
CONTAINER_APP="jobflow-app"
ACR_NAME="crjobflow$(date +%s | tail -c 6)"  # Unique ACR name

echo "📋 Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Container App: $CONTAINER_APP"
echo "  Container Registry: $ACR_NAME"

# Check if logged into Azure CLI
echo "🔐 Checking Azure CLI login..."
if ! az account show > /dev/null 2>&1; then
    echo "❌ Not logged into Azure CLI. Please run: az login"
    exit 1
fi

echo "✅ Azure CLI authenticated"

# Get current subscription
SUBSCRIPTION=$(az account show --query id -o tsv)
echo "📊 Using subscription: $SUBSCRIPTION"

# Create resource group
echo "📦 Creating resource group: $RESOURCE_GROUP"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output table

# Create Azure Container Registry
echo "🏗️ Creating Azure Container Registry: $ACR_NAME"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --location $LOCATION \
    --output table

# Enable admin access for ACR
echo "🔑 Enabling ACR admin access..."
az acr update \
    --name $ACR_NAME \
    --resource-group $RESOURCE_GROUP \
    --admin-enabled true

# Build and push container image
echo "🔨 Building container image..."
az acr build \
    --registry $ACR_NAME \
    --resource-group $RESOURCE_GROUP \
    --image jobflow:latest \
    --file Dockerfile \
    .

# Create Container Apps environment
echo "🌍 Creating Container Apps environment: $CONTAINER_APP_ENV"
az containerapp env create \
    --name $CONTAINER_APP_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --output table

# Get ACR credentials
ACR_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query passwords[0].value -o tsv)

echo "🔧 ACR Details:"
echo "  Server: $ACR_SERVER"
echo "  Username: $ACR_USERNAME"

# Create Container App
echo "🚀 Creating Container App: $CONTAINER_APP"
az containerapp create \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_APP_ENV \
    --image $ACR_SERVER/jobflow:latest \
    --registry-server $ACR_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 5001 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 5 \
    --cpu 0.25 \
    --memory 0.5Gi \
    --env-vars FLASK_ENV=production PORT=5001 \
    --output table

# Get application URL
echo "🌐 Getting application URL..."
APP_URL=$(az containerapp show \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Deployment Summary:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Container App: $CONTAINER_APP"
echo "  Container Registry: $ACR_NAME"
echo "  Application URL: https://$APP_URL"
echo ""
echo "💰 Cost Information:"
echo "  Pricing Model: Pay-as-you-go (serverless)"
echo "  Idle Cost: $0 (scales to zero)"
echo "  Active Cost: ~$0.000012 per request"
echo "  Storage: Minimal cost for ACR (~$5/month for basic)"
echo ""
echo "🔧 Management:"
echo "  View logs: az containerapp logs show --name $CONTAINER_APP --resource-group $RESOURCE_GROUP --follow"
echo "  Scale app: az containerapp update --name $CONTAINER_APP --resource-group $RESOURCE_GROUP --min-replicas X --max-replicas Y"
echo "  Delete all: az group delete --name $RESOURCE_GROUP --yes"
echo ""
echo "✅ Your JobFlow app is now live at: https://$APP_URL"

# Test the deployment
echo "🧪 Testing deployment..."
sleep 30  # Wait for app to start
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$APP_URL/api/health" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Health check passed! Application is running correctly."
else
    echo "⚠️ Health check returned status: $HTTP_STATUS"
    echo "The app might need a few more minutes to start up."
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Visit your app: https://$APP_URL"
echo "2. Test the analytics: https://$APP_URL/api/followups/analytics"
echo "3. Monitor costs in Azure Portal"
echo "4. Set up custom domain (optional)"
echo ""
echo "Happy job hunting! 🚀"
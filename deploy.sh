#!/usr/bin/env bash
# Lightweight deployment script to provision resources and deploy the Nigella agent

set -e

# Load project ID from gcloud config if not set in environment
if [ -z "$GCP_PROJECT_ID" ]; then
    GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set and could not be read from gcloud."
    exit 1
fi

if [ -z "$GCP_REGION" ]; then
    export GCP_REGION="us-east1"
fi

echo "🚀 Starting lightweight deployment for project: $GCP_PROJECT_ID in region: $GCP_REGION"

# 1. Provision Infrastructure via Terraform
echo "🛠️  Applying Terraform configuration..."
terraform init
terraform apply -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION" -auto-approve

# 2. Deploy Agent definitions using the local python app
echo "🤖 Registering and deploying Nigella Agent..."
agents-cli deploy --auto-approve

echo "🎉 Deployment complete!"

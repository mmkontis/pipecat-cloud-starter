#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# Build the Docker image for ARM64
echo "Building Docker image..."
docker build --platform=linux/arm64 -t humanlike:latest .

# Tag the image
TAG="minasmarios/humanlike:0.1"
echo "Tagging image as $TAG..."
docker tag humanlike:latest $TAG

# Push the image to Docker Hub
echo "Pushing image to Docker Hub..."
docker push $TAG

# Deploy using pcc-deploy.toml configuration
echo "Deploying to Pipecat Cloud..."
pcc deploy

echo "Deployment sequence completed." 
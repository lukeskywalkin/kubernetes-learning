#!/bin/bash
# Build script for application Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building application Docker images...${NC}"

# Check if minikube docker-env is set
if ! docker info | grep -q "minikube"; then
    echo -e "${YELLOW}Warning: Docker may not be pointing to Minikube.${NC}"
    echo -e "${YELLOW}Run: eval \$(minikube docker-env)${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Build backend image
echo -e "${GREEN}Building backend image...${NC}"
cd "$ROOT_DIR/app/backend"
docker build -t task-backend:latest .
echo -e "${GREEN}✓ Backend image built${NC}"

# Build logger image
echo -e "${GREEN}Building logger image...${NC}"
cd "$ROOT_DIR/app/logger"
docker build -t task-logger:latest .
echo -e "${GREEN}✓ Logger image built${NC}"

# List built images
echo -e "\n${GREEN}Built images:${NC}"
docker images | grep -E "task-backend|task-logger"

echo -e "\n${GREEN}All images built successfully!${NC}"

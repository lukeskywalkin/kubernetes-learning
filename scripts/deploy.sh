#!/bin/bash
# Deployment script for Kubernetes resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying Kubernetes resources...${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
K8S_DIR="$ROOT_DIR/k8s"

# Check kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster.${NC}"
    echo -e "${YELLOW}Make sure minikube is running: minikube start${NC}"
    exit 1
fi

echo -e "${GREEN}Applying ConfigMaps...${NC}"
kubectl apply -f "$K8S_DIR/configmaps/"

echo -e "${GREEN}Applying Service Accounts and RBAC...${NC}"
kubectl apply -f "$K8S_DIR/serviceaccounts/"

echo -e "${GREEN}Applying Deployments...${NC}"
kubectl apply -f "$K8S_DIR/deployments/"

echo -e "${GREEN}Applying Services...${NC}"
kubectl apply -f "$K8S_DIR/services/"

echo -e "${GREEN}Applying Istio resources...${NC}"
kubectl apply -f "$K8S_DIR/istio/" 2>/dev/null || echo -e "${YELLOW}Istio resources skipped (Istio may not be installed)${NC}"

echo -e "\n${GREEN}Waiting for pods to be ready...${NC}"
kubectl wait --for=condition=ready pod --all --timeout=300s || true

echo -e "\n${GREEN}Deployment status:${NC}"
kubectl get pods

echo -e "\n${GREEN}Services:${NC}"
kubectl get services

echo -e "\n${GREEN}Deployment complete!${NC}"
echo -e "${YELLOW}To access the application:${NC}"
echo -e "  minikube service frontend-service --url"

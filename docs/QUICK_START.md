# Quick Start Guide

Get up and running with the Kubernetes learning environment in 5 minutes!

## Prerequisites

- Minikube installed and running
- kubectl configured
- Docker running

## 1. Start Minikube

```bash
minikube start --cpus=4 --memory=8192 --driver=docker
```

## 2. Build Images

```bash
# Point Docker to Minikube
eval $(minikube docker-env)

# Build images
cd kubernetes-learning
./scripts/build-images.sh
```

Or manually:

```bash
cd app/backend && docker build -t task-backend:latest .
cd ../logger && docker build -t task-logger:latest .
```

## 3. Deploy Application

```bash
# Apply all Kubernetes resources
./scripts/deploy.sh

# Or manually
kubectl apply -f k8s/
```

## 4. Access Application

```bash
# Get the frontend URL
minikube service frontend-service --url

# Or port forward
kubectl port-forward service/frontend-service 8080:80
# Visit http://localhost:8080
```

## 5. Verify Everything Works

```bash
# Check all pods are running
kubectl get pods

# Check services
kubectl get services

# Test backend health
kubectl run -it --rm test --image=curlimages/curl --restart=Never -- \
  curl http://backend-service:5000/health
```

## Next Steps

1. Read [SETUP.md](SETUP.md) for detailed setup instructions
2. Review [K8S_COMPONENTS.md](K8S_COMPONENTS.md) to understand Kubernetes architecture
3. Start working through [LEARNING_TASKS.md](LEARNING_TASKS.md) to learn by fixing bugs!

## Troubleshooting

If pods are not starting:

```bash
# Check pod status
kubectl get pods

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Describe a failing pod
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
```

For more detailed troubleshooting, see [SETUP.md](SETUP.md).

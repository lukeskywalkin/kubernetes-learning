# Setup Guide for Kubernetes Learning Environment

This guide will help you set up the Kubernetes learning environment using Minikube and Istio.

## Prerequisites

Before starting, ensure you have the following installed:

1. **Minikube** - [Installation Guide](https://minikube.sigs.k8s.io/docs/start/)
2. **kubectl** - [Installation Guide](https://kubernetes.io/docs/tasks/tools/)
3. **Docker** - Required for Minikube (usually comes with Docker Desktop)
4. **Istio CLI (istioctl)** - We'll install this during setup

## Step 1: Start Minikube

Start Minikube with sufficient resources:

```bash
# Start minikube with adequate CPU and memory
# Note: Use 4096-6144MB if Docker Desktop has limited memory (minimum 4GB recommended)
minikube start --cpus=4 --memory=6144 --driver=docker

# Verify cluster is running
kubectl cluster-info
kubectl get nodes
```

**Note**: If you encounter issues, you may need to increase Docker Desktop's resource allocation.

## Step 2: Enable Minikube Docker Registry

Since we'll be building images locally, configure Minikube to use the Docker daemon:

```bash
# Configure minikube to use local Docker daemon
eval $(minikube docker-env)

# Verify Docker is pointing to Minikube
docker ps
```

## Step 3: Build Application Images

Build the Docker images for the application services:

```bash
# Navigate to the repository root
cd kubernetes-learning

# Build backend image
cd app/backend
docker build -t task-backend:latest .
cd ../..

# Build logger image
cd app/logger
docker build -t task-logger:latest .
cd ../..

# Verify images were created
docker images | grep task-
```

## Step 4: Install Istio

Install Istio using istioctl:

```bash
# Download Istio (or use Homebrew: brew install istioctl)
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install Istio with default profile
istioctl install --set profile=default -y

# Verify installation
istioctl verify-install
kubectl get pods -n istio-system
```

**Alternative**: Install Istio using Homebrew (macOS) or download from [istio.io](https://istio.io/latest/docs/setup/getting-started/)

## Step 5: Enable Istio Sidecar Injection

Enable automatic Istio sidecar injection for the default namespace:

```bash
# Label default namespace for Istio injection
kubectl label namespace default istio-injection=enabled --overwrite

# Verify the label
kubectl get namespace default --show-labels
```

## Step 6: Deploy the Application

Deploy all Kubernetes resources:

```bash
# Apply all manifests (order matters for dependencies)
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/serviceaccounts/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/istio/

# Or apply everything at once (some resources might fail initially, that's okay)
kubectl apply -f k8s/

# Watch pods come up
kubectl get pods -w
```

Wait for all pods to be in `Running` state:

```bash
# Check pod status
kubectl get pods

# Check if all pods are ready
kubectl wait --for=condition=ready pod --all --timeout=300s
```

## Step 7: Verify Deployment

Check that all services are running:

```bash
# List all services
kubectl get services

# List all deployments
kubectl get deployments

# Check pod logs (example for backend)
kubectl logs -l app=backend --tail=50

# Check if Istio sidecars are injected
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'
```

You should see `istio-proxy` containers in each pod.

## Step 8: Access the Application

### Option 1: Using Minikube Service (Recommended)

```bash
# Get the frontend service URL
minikube service frontend-service --url

# Open in browser (or visit the URL manually)
minikube service frontend-service
```

### Option 2: Port Forward

```bash
# Forward frontend service port
kubectl port-forward service/frontend-service 8080:80

# Then visit http://localhost:8080 in your browser
```

### Option 3: Using Istio Ingress

```bash
# Get Istio ingress gateway address
kubectl get svc istio-ingressgateway -n istio-system

# Port forward Istio gateway
kubectl port-forward -n istio-system service/istio-ingressgateway 8080:80

# Visit http://localhost:8080
```

## Step 9: Test the Application

1. Open the frontend in your browser
2. Create a new task
3. Verify it appears in the task list
4. Try marking it as complete
5. Check logs using:

```bash
# Backend logs
kubectl logs -l app=backend --tail=20

# Logger service logs
kubectl logs -l app=logger --tail=20

# Check Istio metrics
istioctl proxy-config clusters $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') | grep backend
```

## Troubleshooting

### Issue: Pods stuck in Pending

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check node resources
kubectl top nodes
kubectl top pods
```

**Solution**: Minikube might not have enough resources. Try:
```bash
minikube stop
minikube start --cpus=4 --memory=8192
```

### Issue: Images not found

```bash
# Verify images exist in Minikube
minikube ssh
docker images | grep task-
exit

# If images don't exist, rebuild them
eval $(minikube docker-env)
# Then rebuild images as in Step 3
```

### Issue: Istio sidecar not injected

```bash
# Check namespace label
kubectl get namespace default --show-labels

# Re-enable injection
kubectl label namespace default istio-injection=enabled --overwrite

# Delete and recreate pods
kubectl delete pods --all
# Pods will be recreated with sidecars
```

### Issue: Services can't communicate

```bash
# Check service endpoints
kubectl get endpoints

# Check DNS resolution from within a pod
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup backend-service

# Check Istio service mesh connectivity
istioctl proxy-status
```

### Issue: Redis connection errors

```bash
# Check Redis pod status
kubectl get pods -l app=redis

# Check Redis service
kubectl get svc redis-service

# Test Redis connection from backend pod
kubectl exec -it $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- python -c "import redis; r = redis.Redis(host='redis-service', port=6379); print(r.ping())"
```

### Issue: ConfigMap not found

```bash
# Verify ConfigMaps exist
kubectl get configmaps

# Check ConfigMap contents
kubectl describe configmap backend-config

# Verify environment variables in pod
kubectl exec -it <pod-name> -- env | grep -i redis
```

## Clean Up

To remove everything and start fresh:

```bash
# Delete all resources
kubectl delete -f k8s/

# Or delete everything manually
kubectl delete deployments --all
kubectl delete services --all
kubectl delete configmaps --all
kubectl delete serviceaccounts --all
kubectl delete roles --all
kubectl delete rolebindings --all
kubectl delete virtualservices --all
kubectl delete destinationrules --all
kubectl delete gateways --all

# Stop minikube (optional)
minikube stop
```

## Next Steps

Once everything is running:

1. Review [K8S_COMPONENTS.md](K8S_COMPONENTS.md) to understand Kubernetes architecture
2. Read [ETCD.md](ETCD.md) to learn about etcd
3. Start working through [LEARNING_TASKS.md](LEARNING_TASKS.md) to fix bugs and add features

Good luck with your learning journey! 🚀

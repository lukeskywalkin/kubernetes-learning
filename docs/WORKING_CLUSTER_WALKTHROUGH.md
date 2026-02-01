# Working Cluster Walkthrough

A guided tour of the Kubernetes learning environment when everything is working. Use this to understand how each piece connects before we introduce problems.

## Overview

```
User → Frontend (nginx) → Backend (Flask) → Redis
                              ↓
                         Logger Service
```

## Step 1: Verify Everything is Running

```bash
# All pods should be Running and Ready
kubectl get pods

# All deployments should show desired replicas
kubectl get deployments

# Services should have endpoints
kubectl get services
kubectl get endpointslices
```

## Step 2: Understand the Request Flow

### When a user visits the frontend:

1. **Frontend Service** (NodePort) receives the request
   - Run: `kubectl get svc frontend-service`
   - Note the PORT(S) - e.g., `80:31234/TCP` means external port 31234 → internal 80

2. **kube-proxy** routes to a Frontend Pod
   - Service selector: `app: frontend`
   - Targets pods with that label
   - Load balances between them

3. **Frontend Pod** (nginx) serves the HTML
   - ConfigMap `frontend-config` mounted at `/usr/share/nginx/html`
   - ConfigMap `nginx-config` mounted at `/etc/nginx/conf.d`
   - Serves `index.html` which contains JavaScript

4. **Browser JavaScript** calls Backend API
   - Frontend JS fetches `http://backend-service:5000/api/tasks`
   - This works when accessed FROM WITHIN the cluster (or via port-forward)
   - When using `minikube service`, the browser runs locally - it needs the backend URL to be reachable (see frontend `index.html` - there's an API URL input)

### When the frontend calls the backend:

1. **Backend Service** (ClusterIP) receives the request
   - Name: `backend-service`
   - DNS: `backend-service.default.svc.cluster.local` (or just `backend-service` from same namespace)
   - Port: 5000

2. **Service** routes to a Backend Pod
   - Selector: `app: backend`
   - Load balances between 2 backend pods

3. **Backend Pod** (Flask) processes the request
   - Reads `REDIS_HOST` from ConfigMap `backend-config` → `redis-service`
   - Connects to Redis
   - Sends logs to Logger via `LOGGER_SERVICE_URL` → `http://logger-service:8080`

4. **Redis** stores/retrieves task data
   - Service: `redis-service` on port 6379
   - Backend connects using the service name

5. **Logger** receives log entries (optional, doesn't block main flow)
   - Service: `logger-service` on port 8080
   - Backend POSTs logs to `/log`

## Step 3: Trace the Configuration

### Backend Configuration Flow

```
ConfigMap: backend-config
  ├─ redis_host → REDIS_HOST env var in pod
  ├─ redis_port → REDIS_PORT env var
  ├─ redis_db → REDIS_DB env var
  └─ log_level → LOG_LEVEL env var

Backend pod reads these as environment variables at runtime.
```

Verify: `kubectl describe configmap backend-config`

### Frontend Configuration Flow

```
ConfigMap: frontend-config
  └─ index.html → mounted at /usr/share/nginx/html/index.html

ConfigMap: nginx-config
  └─ default.conf → mounted at /etc/nginx/conf.d/default.conf

Nginx reads these as files from the filesystem.
```

Verify: `kubectl describe configmap frontend-config`

## Step 4: Trace the Networking

### How does Backend find Redis?

```bash
# From inside a backend pod, Redis is reachable at:
# redis-service:6379

# DNS resolution happens automatically - CoreDNS resolves service names
# Run this to test from a pod:
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup redis-service
```

### Service → Pod connectivity

```bash
# See which pods a service routes to
kubectl get endpoints backend-service

# Output shows pod IPs - those are the backend pods
```

## Step 5: Key File Relationships

| Component | Defined In | Depends On |
|-----------|------------|------------|
| Backend Deployment | `k8s/deployments/backend-deployment.yaml` | backend-config ConfigMap, backend-service-account, redis-service (at runtime) |
| Frontend Deployment | `k8s/deployments/frontend-deployment.yaml` | frontend-config, nginx-config ConfigMaps |
| Logger Deployment | `k8s/deployments/logger-deployment.yaml` | logger-config ConfigMap, logger-service-account |
| Redis Deployment | `k8s/deployments/redis-deployment.yaml` | redis-config ConfigMap |
| Backend Service | `k8s/services/backend-service.yaml` | Pods with label app=backend |
| Frontend Service | `k8s/services/frontend-service.yaml` | Pods with label app=frontend |
| Redis Service | `k8s/services/redis-service.yaml` | Pods with label app=redis |
| Logger Service | `k8s/services/logger-service.yaml` | Pods with label app=logger |

## Step 6: Access Points

```bash
# Get frontend URL (for browser)
minikube service frontend-service --url

# Port-forward to backend (for testing API directly)
kubectl port-forward svc/backend-service 5000:5000
# Then: curl http://localhost:5000/health

# Port-forward to logger
kubectl port-forward svc/logger-service 8080:8080
# Then: curl http://localhost:8080/logs
```

## Step 7: Quick Verification Commands

```bash
# Is the backend healthy?
kubectl exec -it $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- curl -s localhost:5000/health

# Can backend reach Redis?
kubectl exec -it $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- python -c "import redis; r=redis.Redis(host='redis-service',port=6379); print('Redis:', r.ping())"

# What env vars does backend have?
kubectl exec -it $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- env | grep -E "REDIS|LOGGER"
```

**Note:** `kubectl exec` requires a shell in the container. Production images often omit shells. For safer debugging, use ephemeral debug containers (see below).

---

## Step 8: Debugging with Ephemeral Containers (Production-Safe)

Instead of `kubectl exec` (which needs a shell and can be a security risk), use `kubectl debug` to attach an ephemeral debug container to a pod. Since the debug container shares the pod's lifecycle, copy the pod first so you can delete the copy when done:

```bash
# 1. Create a copy of the faulty pod with an ephemeral debug container
#    Replace <faulty-pod-name> with the actual pod name (e.g. backend-deployment-abc123-xyz45)
#    Replace <container-name> with the container to debug (e.g. backend)
kubectl debug <faulty-pod-name> -it --copy-to=<pod-name>-debug --image=nicolaka/netshoot --target=<container-name>

# 2. You'll get a shell in the debug container, which shares the pod's network namespace.
#    Test connectivity: curl http://localhost:5000/health, nslookup redis-service, etc.

# 3. When done, delete the debug copy (original pod is unchanged)
kubectl delete pod <pod-name>-debug
```

**Example for backend pod:**
```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Create debug copy and attach
kubectl debug $BACKEND_POD -it --copy-to=backend-debug --image=nicolaka/netshoot --target=backend

# In the debug shell: curl localhost:5000/health, nslookup redis-service, etc.

# When done (Ctrl+D to exit), delete the copy
kubectl delete pod backend-debug
```

**Alternative with busybox** (smaller image, fewer tools):
```bash
kubectl debug $BACKEND_POD -it --copy-to=backend-debug --image=busybox --target=backend
# Then: wget -qO- http://localhost:5000/health, nslookup redis-service
```

---

## Summary: The Critical Paths

1. **Frontend → User**: NodePort service exposes nginx; ConfigMaps provide HTML and nginx config
2. **Frontend JS → Backend**: Service name `backend-service` resolves to backend pods
3. **Backend → Redis**: Service name `redis-service` resolves to Redis pod; ConfigMap provides host/port
4. **Backend → Logger**: Service name `logger-service` resolves to logger; URL in env var
5. **All pods**: Need correct labels for their Services to find them

When we introduce problems, we'll break one of these paths at a time. Use this walkthrough to trace where the break is.

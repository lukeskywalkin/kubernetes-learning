# DISCLAIMER: This repo is a bit of an incoherent mess. It was created so that I could learn Kubernetes interactively, and track my learning progress in the documentation. Please do not judge the contents of this repository as a reflection of my code quality 😊

# Kubernetes Learning Environment

A comprehensive Kubernetes cluster setup designed for learning DevOps and Kubernetes concepts through hands-on practice. This repository includes a multi-service application with intentional bugs and missing features that you'll fix to master Kubernetes.

## Learning Objectives

This repository covers:

- **IRSA (IAM Roles for Service Accounts)**: Service account patterns and RBAC
- **Deployments**: Rolling updates, rollbacks, replicas, health checks
- **ConfigMaps**: Configuration management and separation of concerns
- **etcd**: Understanding the Kubernetes backend key-value store
- **Kubernetes Components**: API server, kubelet, kube-proxy, scheduler, controller manager
- **Networking & CNI**: Istio service mesh, service discovery, load balancing

## Application Architecture

The application is a simple **Task Management API** with the following services:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  Database   │
│   (nginx)   │     │  (Python)   │     │  (Redis)    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Logger    │
                    │  (Python)   │
                    └─────────────┘
```

- **Frontend**: Nginx serving static HTML/JS
- **Backend API**: Python Flask application
- **Database**: Redis for data storage
- **Logger Service**: Python service for centralized logging

## Quick Start

### Prerequisites

- Minikube installed and running
- kubectl configured
- Istio installed (see [Setup Guide](docs/SETUP.md))

### Deploy the Application

```bash
# Start minikube with enough resources
# Note: Adjust memory (4096-6144) based on your Docker Desktop allocation
minikube start --cpus=4 --memory=6144 --driver=docker

# Install Istio (if not already installed)
istioctl install --set profile=default -y

# Enable Istio injection for default namespace
kubectl label namespace default istio-injection=enabled

# Deploy the application
kubectl apply -f k8s/

# Wait for pods to be ready
kubectl get pods -w

# Get service URLs
minikube service frontend-service --url
```

## Repository Structure

```
kubernetes-learning/
├── app/                    # Application source code
│   ├── frontend/          # Static HTML/JS frontend
│   ├── backend/           # Python Flask API
│   └── logger/            # Logging service
├── k8s/                   # Kubernetes manifests
│   ├── deployments/       # Deployment manifests
│   ├── services/          # Service manifests
│   ├── configmaps/        # ConfigMap manifests
│   ├── secrets/           # Secret manifests (examples)
│   ├── serviceaccounts/   # Service account & RBAC
│   └── istio/             # Istio configuration
├── docs/                  # Documentation
│   ├── SETUP.md          # Detailed setup guide
│   ├── LEARNING_TASKS.md # Tasks and bugs to fix
│   ├── ETCD.md           # etcd deep dive
│   └── K8S_COMPONENTS.md # Kubernetes components explained
└── scripts/              # Helper scripts
```

## Learning Path

1. **Start Here**: Read [SETUP.md](docs/SETUP.md) to get your environment ready
2. **Understand the Basics**: Review [K8S_COMPONENTS.md](docs/K8S_COMPONENTS.md) to learn about Kubernetes architecture
3. **Learn etcd**: Read [ETCD.md](docs/ETCD.md) to understand the data store
4. **Start Fixing**: Follow [LEARNING_TASKS.md](docs/LEARNING_TASKS.md) to fix bugs and add features
5. **Explore Istio**: Learn service mesh concepts through the Istio configurations

## Key Concepts Demonstrated

### Deployments
- Rolling updates and rollbacks
- Replica management
- Health checks (liveness and readiness probes)
- Resource limits and requests

### ConfigMaps
- Environment variable injection
- Configuration file mounting
- Separation of configuration from code

### Service Accounts & RBAC
- Service account creation and assignment
- Role-based access control
- IRSA-like patterns (service account token usage)
- Least privilege principles

### Networking (Istio)
- Service mesh architecture
- Traffic management (VirtualService, DestinationRule)
- Circuit breakers and retries
- Observability (metrics, tracing)

### etcd
- Understanding cluster state storage
- How Kubernetes uses etcd
- Backup and recovery concepts

## Troubleshooting

Common issues and solutions are documented in [SETUP.md](docs/SETUP.md).

## Next Steps

After completing the learning tasks, you'll have hands-on experience with:
- Debugging pod issues
- Configuring resource limits
- Setting up service mesh policies
- Managing configurations
- Understanding Kubernetes internals

Good luck with your interview! 🚀

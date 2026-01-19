# Kubernetes Concepts Overview

A comprehensive guide to understanding Kubernetes architecture and core concepts.

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Core Concepts](#core-concepts)
3. [Workload Resources](#workload-resources)
4. [Networking](#networking)
5. [Configuration](#configuration)
6. [Storage](#storage)
7. [Service Accounts & Security](#service-accounts--security)
8. [How Everything Connects](#how-everything-connects)

---

## High-Level Architecture

### The Big Picture

Kubernetes divides your cluster into two main parts:

```
┌─────────────────────────────────────────────────────┐
│                  CONTROL PLANE                      │
│  (The "Brain" - Manages and coordinates)            │
│                                                     │
│  • API Server    - Entry point for all operations  │
│  • etcd          - Cluster state database          │
│  • Scheduler     - Assigns pods to nodes           │
│  • Controller    - Maintains desired state         │
└─────────────────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
┌───────────▼──────┐      ┌────────▼────────┐
│     NODE 1       │      │     NODE 2      │
│  (Worker Node)   │      │  (Worker Node)  │
│                  │      │                 │
│  • Kubelet       │      │  • Kubelet      │
│  • kube-proxy    │      │  • kube-proxy   │
│  • Pods run here │      │  • Pods run here│
└──────────────────┘      └─────────────────┘
```

### Control Plane vs Nodes

| Control Plane | Nodes |
|--------------|-------|
| **Purpose**: Manages the cluster | **Purpose**: Runs your applications |
| **Components**: API Server, etcd, Scheduler, Controllers | **Components**: Kubelet, kube-proxy, Container Runtime |
| **What it does**: Makes decisions about what should run where | **What it does**: Actually runs containers |
| **Analogy**: The manager/boss | **Analogy**: The workers |

**Key Point**: You interact with the **Control Plane** (via `kubectl`), but your applications run on **Nodes**.

---

## Core Concepts

### 1. Containers

**What it is**: Your application packaged with dependencies (Docker image)

```
Container = Application + Runtime + Dependencies
Example: Python app + Python interpreter + libraries
```

### 2. Pods

**What it is**: The smallest deployable unit in Kubernetes. A pod contains one or more containers.

```
┌──────────────────┐
│      POD         │
│  ┌────────────┐  │
│  │ Container  │  │ ← Your app
│  │  (nginx)   │  │
│  └────────────┘  │
│                  │
│  • Shares IP     │
│  • Shares volumes│
│  • Lives/dies    │
│    together      │
└──────────────────┘
```

**Key Characteristics**:
- **Ephemeral**: Pods are created and destroyed as needed
- **Shared Resources**: Containers in a pod share:
  - IP address
  - Storage volumes
  - Network namespace
- **Lifecycle**: Pods are created, run, and deleted (not "restarted")

**Why Pods?**
- Pods allow multiple containers to work together closely
- Example: Main app container + sidecar (logging, monitoring)

**Real Example**:
```yaml
Pod: "backend-pod-abc123"
  └─ Container 1: Python Flask app
  └─ Container 2: Istio proxy (sidecar)
```

### 3. Nodes

**What it is**: A worker machine (physical or virtual) where pods run.

```
┌─────────────────────────────────────┐
│           NODE                      │
│                                     │
│  ┌──────┐  ┌──────┐  ┌──────┐     │
│  │ Pod  │  │ Pod  │  │ Pod  │     │
│  │  1   │  │  2   │  │  3   │     │
│  └──────┘  └──────┘  └──────┘     │
│                                     │
│  Kubelet (manages pods)             │
│  kube-proxy (networking)            │
│  Container Runtime (Docker)         │
└─────────────────────────────────────┘
```

**Key Point**: You typically don't create nodes directly. They're part of your cluster infrastructure.

---

## Workload Resources

These resources **manage pods** for you. You rarely create pods directly!

### 1. Deployment

**What it is**: Manages a set of identical pods (replicas) with rolling updates.

```
Deployment: "backend-deployment"
  └─ ReplicaSet (v1)
      ├─ Pod 1 (backend-abc123)
      ├─ Pod 2 (backend-def456)
      └─ Pod 3 (backend-ghi789)
```

**What it does**:
- Maintains desired number of replicas (e.g., 3 pods)
- Rolling updates (update pods one at a time)
- Rollbacks (revert to previous version)
- Self-healing (recreates failed pods)

**Example**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
spec:
  replicas: 3  # Want 3 identical pods
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: my-app:latest
```

**When to use**: 99% of the time! Use Deployments for stateless applications (web servers, APIs).

### 2. ReplicaSet

**What it is**: Ensures a specific number of pod replicas are running.

**Relationship**: Deployment **creates and manages** ReplicaSets.

```
User creates Deployment
  ↓
Deployment creates ReplicaSet
  ↓
ReplicaSet creates Pods
```

**Why it exists**: Deployments use ReplicaSets internally for pod management. You usually work with Deployments directly.

### 3. StatefulSet

**What it is**: Like Deployment, but for stateful applications (databases, queues).

**Differences from Deployment**:
- **Stable identity**: Pods have stable names (pod-0, pod-1, pod-2)
- **Stable storage**: Each pod gets its own persistent volume
- **Ordered deployment**: Pods start/stop in order

**Example**: Redis cluster, PostgreSQL, Kafka

**When to use**: Databases, stateful applications that need stable identities.

### 4. DaemonSet

**What it is**: Ensures every node runs one copy of a pod.

```
DaemonSet: "log-collector"
  ├─ Node 1 → log-collector-pod
  ├─ Node 2 → log-collector-pod
  └─ Node 3 → log-collector-pod
```

**When to use**: 
- Log collectors (one per node)
- Monitoring agents
- Network plugins

### 5. Job & CronJob

**Job**: Runs a pod until completion (one-time task)

**CronJob**: Runs Jobs on a schedule (like cron)

**Example**: Backup script, data migration, report generation

---

## Networking

### Services

**The Problem**: Pods are ephemeral. They get new IPs when recreated. How do other services find them?

**The Solution**: Services provide a stable IP/name that points to pods.

```
┌────────────────────────────────────────┐
│         SERVICE                        │
│  Name: backend-service                 │
│  IP: 10.96.0.10 (stable)              │
└────────────┬───────────────────────────┘
             │
      Load balances to
             │
  ┌──────────┴──────────┐
  │                     │
┌─▼─────┐  ┌─▼─────┐  ┌─▼─────┐
│ Pod 1 │  │ Pod 2 │  │ Pod 3 │
│(new IP)│  │(new IP)│  │(new IP)│
└───────┘  └───────┘  └───────┘
```

### Service Types

#### 1. ClusterIP (Default)

**What it is**: Internal service, only accessible within cluster.

```
Pod → Service (ClusterIP) → Other Pods
```

**Use case**: Communication between services in your cluster.

#### 2. NodePort

**What it is**: Exposes service on each node's IP at a static port.

```
External → NodeIP:30080 → Service → Pods
```

**Use case**: Expose service to external traffic (development/testing).

#### 3. LoadBalancer

**What it is**: Cloud provider creates an external load balancer.

```
Internet → Load Balancer → Service → Pods
```

**Use case**: Production external access (requires cloud provider).

#### 4. ExternalName

**What it is**: Maps service to external DNS name.

```
Pod → Service → external.example.com
```

**Use case**: Point to external services.

### Labels and Selectors

**How Services Find Pods**:

```yaml
# Service
spec:
  selector:
    app: backend  # Find pods with this label

# Pod (in Deployment)
metadata:
  labels:
    app: backend  # Has this label
```

**Labels** = Tags for organizing resources

**Selectors** = How resources find each other

---

## Configuration

### ConfigMaps

**What it is**: Stores non-sensitive configuration data.

```
ConfigMap: "backend-config"
  data:
    redis_host: "redis-service"
    log_level: "INFO"
```

**How it's used**:
```yaml
# In Deployment
containers:
- name: backend
  env:
  - name: REDIS_HOST
    valueFrom:
      configMapKeyRef:
        name: backend-config
        key: redis_host
```

**Key Point**: Separates configuration from code. Change config without rebuilding images.

### Secrets

**What it is**: Like ConfigMap, but for sensitive data (passwords, API keys).

```
Secret: "db-credentials"
  data:
    username: base64encoded
    password: base64encoded
```

**Important**: Base64 encoded, not encrypted! Use external secret management in production.

---

## Storage

### Volumes

**What it is**: Storage attached to a pod.

**Types**:
- **emptyDir**: Temporary storage (lost when pod deleted)
- **hostPath**: Mount directory from node (not portable)
- **PersistentVolume (PV)**: Persistent storage that survives pod deletion

### PersistentVolume & PersistentVolumeClaim

```
┌─────────────────────────────────────┐
│   PersistentVolume (PV)             │
│   (Storage resource in cluster)     │
└─────────────────────────────────────┘
              ▲
              │ Claim
              │
┌─────────────▼──────────────┐
│ PersistentVolumeClaim (PVC)│
│ (Pod requests storage)     │
└────────────────────────────┘
```

**Flow**:
1. Admin creates PersistentVolume (actual storage)
2. Pod requests storage via PersistentVolumeClaim
3. Kubernetes binds PVC to PV
4. Pod mounts the PVC

**Example**: Database data that needs to persist across pod restarts.

---

## Service Accounts & Security

### Service Accounts

**What it is**: Identity for pods (like a user account for applications).

```yaml
# Pod uses service account
spec:
  serviceAccountName: backend-service-account
```

**Why it matters**: 
- RBAC (permissions)
- IRSA (AWS IAM roles)
- Access control

### RBAC (Role-Based Access Control)

```
Service Account → Role → Permissions
   (who)         (what)    (can do)
```

**Example**:
- Service Account: `backend-service-account`
- Role: Can read `backend-config` ConfigMap
- Pod using this service account can read that ConfigMap

---

## How Everything Connects

### Complete Flow Example

Let's trace how a request flows through Kubernetes:

```
1. USER creates Deployment
   ↓
2. kubectl sends request to API Server
   ↓
3. API Server stores in etcd
   ↓
4. Controller Manager sees new Deployment
   ↓
5. Controller Manager creates ReplicaSet
   ↓
6. Scheduler assigns Pods to Nodes
   ↓
7. Kubelet (on node) creates Pods
   ↓
8. Pods are running
   ↓
9. Service points to Pods (using labels)
   ↓
10. Other Pods access via Service name
```

### Visual Relationship

```
┌──────────────────────────────────────────────────┐
│                    CLUSTER                       │
│                                                  │
│  ┌──────────────┐         ┌──────────────────┐ │
│  │  Deployment  │────────▶│   ReplicaSet     │ │
│  │  (manages)   │         │   (ensures pods) │ │
│  └──────────────┘         └──────────────────┘ │
│                           │                     │
│                           ▼                     │
│                  ┌──────────────────┐           │
│                  │       PODS       │           │
│                  │  ┌────────────┐  │           │
│                  │  │ Containers │  │           │
│                  │  └────────────┘  │           │
│                  └──────────────────┘           │
│                           ▲                     │
│                           │                     │
│  ┌──────────────────┐    │    ┌─────────────┐ │
│  │    Service       │────┘    │ ConfigMap   │ │
│  │  (discovers pods)│         │ (config)    │ │
│  └──────────────────┘         └─────────────┘ │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Real-World Example: Your Learning App

```
Deployment: backend-deployment
  ├─ ReplicaSet: backend-replicaset-abc123
  │    ├─ Pod: backend-pod-1
  │    │    └─ Container: Python Flask app
  │    │         ├─ Uses: ConfigMap (backend-config)
  │    │         ├─ Uses: Secret (if any)
  │    │         └─ Uses: ServiceAccount
  │    └─ Pod: backend-pod-2
  │         └─ Container: Python Flask app
  │
  └─ Service: backend-service
       └─ Selector: app=backend (points to all backend pods)

Pod connects to:
  ├─ ConfigMap: backend-config (environment variables)
  ├─ Secret: (if credentials needed)
  ├─ Service: redis-service (to find Redis)
  └─ PersistentVolumeClaim: (if storage needed)
```

---

## Key Relationships Summary

| Concept | Relates To | Relationship |
|---------|-----------|--------------|
| **Cluster** | Control Plane + Nodes | Contains everything |
| **Node** | Pods | Runs pods |
| **Pod** | Containers | Contains containers |
| **Deployment** | ReplicaSet | Creates/manages ReplicaSet |
| **ReplicaSet** | Pods | Creates/manages Pods |
| **Service** | Pods | Discovers and routes to pods |
| **ConfigMap** | Pods | Provides config to pods |
| **Secret** | Pods | Provides secrets to pods |
| **Label** | All resources | Tags for organization |
| **Selector** | Labels | Finds resources by label |
| **Namespace** | All resources | Organizes/clusters resources |

---

## Common Patterns

### Pattern 1: Web Application

```
Deployment → Pods (3 replicas)
Service (ClusterIP) → Routes to Pods
ConfigMap → App configuration
Secret → Database password
```

### Pattern 2: Database

```
StatefulSet → Database Pods (with stable names)
Service (ClusterIP) → Routes to database
PersistentVolumeClaim → Database storage
Secret → Database credentials
```

### Pattern 3: Monitoring

```
DaemonSet → One pod per node (log collector)
Deployment → Metrics collector
Service (NodePort) → Expose metrics
```

---

## Key Takeaways

1. **Pods are ephemeral** - Don't create them directly, use Deployments
2. **Services provide stable access** - Use Services to find pods
3. **Labels connect everything** - Services find pods via labels
4. **Deployments manage pods** - Most common workload resource
5. **ConfigMaps externalize config** - Change config without rebuilding
6. **Control Plane manages, Nodes run** - Understand the separation
7. **Everything is API-driven** - kubectl → API Server → etcd

---

## Next Steps

Now that you understand the concepts, you're ready to:

1. Work through [LEARNING_TASKS.md](LEARNING_TASKS.md)
2. See these concepts in action in your learning environment
3. Debug issues using `kubectl describe` and `kubectl get`
4. Understand how Istio fits into this architecture

Remember: **Kubernetes is about declarative management**. You describe what you want (3 replicas of my app), and Kubernetes makes it happen!

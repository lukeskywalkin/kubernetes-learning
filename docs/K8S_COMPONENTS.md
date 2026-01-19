# Kubernetes Components Deep Dive

This document explains the core components of Kubernetes and how they work together to orchestrate containers.

## Architecture Overview

Kubernetes follows a master-worker (control plane-node) architecture:

```
┌─────────────────────────────────────────────────┐
│           Control Plane (Master)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │   API    │  │Scheduler │  │Controller│     │
│  │  Server  │  │          │  │  Manager │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │              │            │
│       └─────────────┴──────────────┘            │
│                    │                             │
│                 ┌──▼──┐                         │
│                 │etcd │                         │
│                 └─────┘                         │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼──────┐       ┌───────▼──────┐
│    Node 1    │       │    Node 2    │
│  ┌────────┐  │       │  ┌────────┐  │
│  │ Kubelet│  │       │  │ Kubelet│  │
│  └───┬────┘  │       │  └───┬────┘  │
│      │       │       │      │       │
│  ┌───▼────┐  │       │  ┌───▼────┐  │
│  │kube-   │  │       │  │kube-   │  │
│  │proxy   │  │       │  │proxy   │  │
│  └────────┘  │       │  └────────┘  │
└──────────────┘       └──────────────┘
```

## Control Plane Components

### 1. API Server (kube-apiserver)

**Role**: The front-end for the Kubernetes control plane. All communication goes through the API Server.

**Responsibilities**:
- Exposes Kubernetes API (REST API)
- Validates and processes requests
- Updates etcd with cluster state
- Handles authentication and authorization
- Serves as the only component that communicates with etcd

**How it works**:
```
User/Component Request
    ↓
API Server (validates, authenticates, authorizes)
    ↓
Updates etcd
    ↓
Returns response
    ↓
Generates events for watchers
```

**Key Features**:
- **REST API**: All operations are API calls (kubectl converts commands to API calls)
- **Validation**: Ensures resource specifications are valid
- **Admission Controllers**: Can modify or reject requests (e.g., ResourceQuota, PodSecurityPolicy)
- **Watch API**: Allows components to watch for changes

**In Minikube**:
```bash
# View API Server pod
kubectl get pods -n kube-system | grep apiserver

# Check API Server logs
kubectl logs -n kube-system kube-apiserver-minikube
```

---

### 2. etcd

**Role**: Distributed key-value store that holds all cluster state.

**See [ETCD.md](ETCD.md) for detailed information.**

**Key Points**:
- Only API Server talks to etcd directly
- Stores all Kubernetes objects (pods, services, deployments, etc.)
- Provides watch API for change notifications
- Highly available in production (typically 3+ nodes)

---

### 3. Scheduler (kube-scheduler)

**Role**: Assigns pods to nodes based on resource requirements, constraints, and policies.

**Responsibilities**:
- Watches etcd for pods with `nodeName` not set
- Evaluates which node is best fit for each pod
- Binds pods to nodes (updates pod spec with nodeName)

**Scheduling Process**:
```
1. Pod created → etcd (nodeName not set)
   ↓
2. Scheduler watches etcd
   ↓
3. Scheduler evaluates nodes:
   - Resource availability (CPU, memory)
   - Node affinity/anti-affinity
   - Taints and tolerations
   - Pod affinity/anti-affinity
   ↓
4. Scheduler selects best node
   ↓
5. Scheduler binds pod to node (updates etcd)
   ↓
6. Kubelet on that node picks up the pod
```

**Scheduling Policies**:
- **Predicates**: Filter nodes (e.g., "has enough CPU")
- **Priorities**: Score nodes (e.g., "least CPU used")

**In Minikube**:
```bash
# View scheduler pod
kubectl get pods -n kube-system | grep scheduler

# View scheduler logs
kubectl logs -n kube-system kube-scheduler-minikube
```

---

### 4. Controller Manager (kube-controller-manager)

**Role**: Runs controller processes that reconcile desired state with actual state.

**Built-in Controllers**:

1. **Replication Controller**: Ensures correct number of pod replicas
2. **Deployment Controller**: Manages Deployment objects
3. **StatefulSet Controller**: Manages StatefulSet objects
4. **DaemonSet Controller**: Ensures all nodes run a pod
5. **Job Controller**: Manages Job objects
6. **Node Controller**: Monitors node health
7. **Service Controller**: Manages Service objects
8. **Endpoint Controller**: Updates Endpoints objects
9. **Namespace Controller**: Manages namespaces
10. **PersistentVolume Controller**: Binds PVCs to PVs

**How Controllers Work**:
```
1. Controller watches etcd for changes
   ↓
2. Compares desired state (spec) with actual state (status)
   ↓
3. Takes action to reconcile:
   - Create missing pods
   - Delete extra pods
   - Update resources
   ↓
4. Updates status in etcd
```

**Example: Replication Controller**
```
Desired: 3 replicas
Actual: 1 replica
Action: Create 2 more pods
```

**In Minikube**:
```bash
# View controller manager pod
kubectl get pods -n kube-system | grep controller-manager

# View logs
kubectl logs -n kube-system kube-controller-manager-minikube
```

---

### 5. Cloud Controller Manager (Optional)

**Role**: Integrates Kubernetes with cloud provider APIs.

**Responsibilities**:
- Node controller: Uses cloud APIs to manage nodes
- Route controller: Configures cloud load balancers
- Service controller: Manages cloud load balancers

**Note**: Not present in Minikube (local development).

---

## Node Components

### 1. Kubelet

**Role**: Agent that runs on each node and manages pods on that node.

**Responsibilities**:
- Registers node with API Server
- Watches etcd for pods assigned to its node
- Creates, updates, and destroys containers
- Reports pod and node status to API Server
- Runs liveness and readiness probes
- Mounts volumes
- Pulls container images

**Pod Lifecycle Management**:
```
1. Kubelet watches etcd for pods assigned to its node
   ↓
2. Kubelet creates pod:
   - Pulls container images
   - Creates container runtime (Docker/containerd)
   - Mounts volumes
   - Configures networking
   ↓
3. Kubelet monitors pod:
   - Runs health checks
   - Restarts failed containers
   - Reports status to API Server
```

**Container Runtime Interface (CRI)**:
- Kubelet doesn't directly manage containers
- Uses CRI to communicate with container runtime (containerd, Docker, CRI-O)

**In Minikube**:
```bash
# Kubelet runs on the minikube node
minikube ssh
# kubelet runs as a systemd service
```

---

### 2. kube-proxy

**Role**: Maintains network rules on nodes, enabling service communication.

**Responsibilities**:
- Watches API Server for Services and Endpoints
- Maintains iptables rules (or uses IPVS) for service routing
- Implements load balancing for ClusterIP services

**How Service Routing Works**:
```
Client → Service (ClusterIP: 10.96.0.1) 
         ↓
kube-proxy iptables rules route to:
         ├─→ Pod 1 (10.244.1.5)
         ├─→ Pod 2 (10.244.1.6)
         └─→ Pod 3 (10.244.2.3)
```

**Modes**:
- **iptables** (default): Uses Linux iptables for routing
- **IPVS**: Uses IP Virtual Server (more efficient for many services)
- **userspace**: Legacy mode (not recommended)

**Service Types**:
- **ClusterIP**: Internal service (handled by kube-proxy)
- **NodePort**: Exposes service on node IP
- **LoadBalancer**: Cloud provider load balancer
- **ExternalName**: DNS alias

**In Minikube**:
```bash
# View kube-proxy pod
kubectl get pods -n kube-system | grep kube-proxy

# View iptables rules (requires node access)
minikube ssh
sudo iptables -t nat -L | grep backend-service
```

---

### 3. Container Runtime

**Role**: Runs containers on the node.

**Examples**: Docker, containerd, CRI-O

**Responsibilities**:
- Pulling container images
- Creating and managing containers
- Managing container lifecycle

**Container Runtime Interface (CRI)**:
- Standard API for container runtimes
- Kubelet uses CRI to communicate with runtime
- Abstraction allows different runtimes

---

## Add-on Components

### DNS (CoreDNS)

**Role**: Provides DNS service discovery for pods and services.

**How it works**:
```
Pod requests: backend-service.default.svc.cluster.local
    ↓
CoreDNS resolves to Service ClusterIP
    ↓
kube-proxy routes to pod IPs
```

**Default DNS Names**:
- `<service>.<namespace>.svc.cluster.local`
- Short form: `<service>` (same namespace)
- Short form: `<service>.<namespace>` (different namespace)

---

### Network Plugin (CNI)

**Role**: Configures pod networking.

**Examples**: Calico, Flannel, Weave, Cilium

**Responsibilities**:
- Assigns IP addresses to pods
- Sets up network routes
- Implements network policies (if supported)

---

## Component Interaction Example

### Pod Creation Flow

```
1. User: kubectl create pod my-pod.yaml
         ↓
2. kubectl → API Server (POST /api/v1/namespaces/default/pods)
         ↓
3. API Server:
   - Validates request
   - Authenticates user
   - Authorizes action
   - Writes to etcd (/registry/pods/default/my-pod)
         ↓
4. Scheduler watches etcd:
   - Sees pod with no nodeName
   - Evaluates nodes
   - Selects best node
   - Updates etcd with nodeName
         ↓
5. Kubelet (on selected node) watches etcd:
   - Sees pod assigned to its node
   - Creates pod:
     * Pulls image
     * Creates container
     * Sets up networking
         ↓
6. Kubelet updates etcd with pod status
         ↓
7. API Server serves updated status
         ↓
8. User: kubectl get pods (sees Running status)
```

---

## Observing Components in Action

### View API Server Activity

```bash
# Enable verbose logging
kubectl get pods -v=8

# Watch API calls
kubectl proxy --port=8001
# Then use API directly
curl http://localhost:8001/api/v1/pods
```

### View Scheduler Decisions

```bash
# View scheduler logs
kubectl logs -n kube-system kube-scheduler-minikube

# Create pod and watch events
kubectl run test --image=nginx
kubectl get events --sort-by='.lastTimestamp'
```

### View Controller Actions

```bash
# Scale deployment (controller will create pods)
kubectl scale deployment backend-deployment --replicas=3

# Watch controller manager logs
kubectl logs -n kube-system kube-controller-manager-minikube | grep backend

# Watch pods being created
kubectl get pods -w
```

### View Kubelet Activity

```bash
# Check node status (kubelet reports this)
kubectl get nodes -o wide

# View pod status (kubelet updates this)
kubectl describe pod <pod-name>
```

---

## Component Health

### Check Control Plane Health

```bash
# Check all control plane components
kubectl get componentstatuses

# Or in newer versions
kubectl get --raw /healthz
```

### Check Node Health

```bash
# View node status
kubectl get nodes

# Detailed node info
kubectl describe node <node-name>

# Node conditions show health:
# - Ready: Node is healthy
# - MemoryPressure: Node low on memory
# - DiskPressure: Node low on disk
# - PIDPressure: Node has too many processes
```

---

## Key Takeaways

1. **API Server is the gateway**: All communication flows through it
2. **etcd is the source of truth**: All state is stored here
3. **Scheduler assigns pods**: Based on resources and policies
4. **Controllers maintain state**: They reconcile desired vs actual
5. **Kubelet manages pods**: On each node
6. **kube-proxy enables services**: Routes traffic to pods
7. **Components watch etcd**: React to changes asynchronously
8. **Everything is API-driven**: kubectl → API Server → etcd

---

## Further Learning

### Practical Exercises

1. **Trace pod creation**: Create a pod and follow events to see each component's role
2. **Observe scheduler**: Create pods with different resource requirements
3. **Watch controllers**: Scale deployments and watch controllers react
4. **Inspect networking**: Check kube-proxy rules and DNS resolution

### Debugging Tips

- **API Server issues**: Check authentication, authorization, etcd connectivity
- **Scheduling issues**: Check node resources, taints, affinity rules
- **Pod not starting**: Check kubelet logs, image pull issues, resource limits
- **Service not working**: Check kube-proxy, endpoints, DNS resolution

Understanding these components helps you debug issues and design robust Kubernetes applications!

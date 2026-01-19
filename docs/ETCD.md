# Understanding etcd in Kubernetes

## What is etcd?

**etcd** is a distributed, reliable key-value store that serves as the single source of truth for Kubernetes cluster state. Every piece of data in your Kubernetes cluster - pods, services, deployments, configurations, secrets - is stored in etcd.

## Key Characteristics

- **Consistent**: All nodes see the same data at the same time
- **Highly Available**: Designed to survive machine failures
- **Fast**: Optimized for read-heavy workloads
- **Secure**: Supports TLS encryption
- **Watch API**: Allows clients to watch for changes

## etcd's Role in Kubernetes

### 1. Cluster State Storage

Kubernetes uses etcd as its "database" to store:

- **Pods**: Current state of all pods
- **Services**: Service definitions and endpoints
- **Deployments**: Deployment configurations and replicas
- **ConfigMaps & Secrets**: Configuration data
- **Nodes**: Cluster node information
- **Namespaces**: Namespace definitions
- **RBAC**: Roles, RoleBindings, ServiceAccounts
- **Events**: Cluster events (with TTL)

### 2. API Server Backend

The Kubernetes API Server is the only component that directly communicates with etcd:

```
User/Component → API Server → etcd
                ↓
            Validates
            Updates State
            Generates Events
```

**Why only API Server?**
- Single point of truth
- Consistent data model
- Access control in one place
- Easier to maintain and backup

### 3. Watch Mechanism

etcd provides a **watch API** that allows Kubernetes components to be notified of changes:

```
1. Component subscribes to watch a key (e.g., /registry/pods/default)
2. etcd notifies component when data changes
3. Component reacts to the change (e.g., scheduler assigns pod to node)
```

## etcd Data Structure

### Key Naming Convention

etcd stores data with structured keys:

```
/registry/pods/<namespace>/<pod-name>
/registry/services/<namespace>/<service-name>
/registry/deployments/<namespace>/<deployment-name>
/registry/configmaps/<namespace>/<configmap-name>
/registry/secrets/<namespace>/<secret-name>
```

### Example: Pod Data

When you create a pod, etcd stores something like:

```
Key: /registry/pods/default/my-pod
Value: {
  "metadata": {
    "name": "my-pod",
    "namespace": "default",
    ...
  },
  "spec": {
    "containers": [...],
    ...
  },
  "status": {
    "phase": "Running",
    ...
  }
}
```

## etcd in Minikube

In Minikube, etcd runs as a container in the control plane:

```bash
# View etcd pod
kubectl get pods -n kube-system | grep etcd

# Access etcd (requires minikube ssh)
minikube ssh
docker ps | grep etcd

# etcd runs in the minikube VM's control plane
```

### Accessing etcd in Minikube

Since etcd is protected, accessing it directly requires:

```bash
# SSH into minikube
minikube ssh

# Find etcd container
docker ps | grep etcd

# Access etcd container
docker exec -it <etcd-container-id> sh

# Use etcdctl (etcd client)
etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/var/lib/minikube/certs/etcd/ca.crt \
  --cert=/var/lib/minikube/certs/etcd/server.crt \
  --key=/var/lib/minikube/certs/etcd/server.key \
  get --prefix /registry/pods/
```

**Note**: Direct etcd access is rarely needed. Use `kubectl` instead!

## How Kubernetes Uses etcd

### 1. Pod Creation Flow

```
User: kubectl create pod my-pod
  ↓
API Server: Validates request
  ↓
API Server: Writes to etcd (/registry/pods/default/my-pod)
  ↓
Scheduler: Watches etcd for unscheduled pods
  ↓
Scheduler: Assigns node, updates etcd
  ↓
Kubelet: Watches etcd for pods assigned to its node
  ↓
Kubelet: Creates pod, updates status in etcd
```

### 2. Service Discovery

```
Service created → API Server → etcd (/registry/services/...)
  ↓
kube-proxy: Watches etcd for services
  ↓
kube-proxy: Updates iptables/ipvs rules
  ↓
Service accessible via ClusterIP
```

### 3. ConfigMap Updates

```
ConfigMap updated → API Server → etcd
  ↓
Kubelet: Watches etcd for mounted ConfigMaps
  ↓
Kubelet: Updates volume mount (or restarts pod depending on config)
```

## etcd Performance Characteristics

### Read Operations
- **Very Fast**: etcd is optimized for reads
- **Consistent Reads**: Always returns latest committed data
- **Cached**: API Server caches etcd data for performance

### Write Operations
- **Consensus Required**: Writes require majority agreement (in HA setups)
- **Sequential**: Writes are serialized through Raft consensus
- **Transactional**: etcd supports transactions

### Watch Operations
- **Event-Based**: Components receive change notifications
- **Efficient**: Only sends deltas, not full data
- **Resumable**: Can resume from last known revision

## etcd Backup and Recovery

### Why Backup etcd?

**etcd contains your entire cluster state**. Losing etcd data means losing:
- All deployments, pods, services
- All configurations and secrets
- All RBAC rules
- Cluster metadata

### Backup Strategies

#### 1. Snapshot Backup

```bash
# Create etcd snapshot
etcdctl snapshot save /backup/etcd-snapshot.db

# Restore from snapshot
etcdctl snapshot restore /backup/etcd-snapshot.db
```

#### 2. Resource Export

While not a true etcd backup, exporting resources is practical:

```bash
# Export all resources
kubectl get all --all-namespaces -o yaml > backup.yaml

# Export specific resources
kubectl get deployments,services,configmaps -o yaml > backup.yaml
```

#### 3. Velero (Production Tool)

Velero backs up both etcd snapshots and persistent volumes.

## High Availability (HA) etcd

In production, etcd runs as a cluster:

### Raft Consensus

- **Leader**: Handles all write requests
- **Followers**: Replicate leader's data
- **Quorum**: Majority must agree (3 nodes = 2, 5 nodes = 3)

### Failure Scenarios

- **1 node fails (3-node cluster)**: Cluster continues (2/3 majority)
- **2 nodes fail (3-node cluster)**: Cluster unavailable (no majority)
- **Split-brain**: Can't occur with Raft (always maintains majority)

## etcd in Production

### Best Practices

1. **Run in HA Mode**: Minimum 3 nodes for production
2. **Separate etcd from Kubernetes**: Run etcd on dedicated machines
3. **Regular Backups**: Automated daily backups at minimum
4. **Monitor Performance**: Watch etcd latency and disk I/O
5. **Encrypt at Rest**: Use encryption for etcd data directory
6. **TLS Everywhere**: Secure etcd communication

### Performance Tuning

- **SSD Storage**: etcd is I/O intensive, use fast storage
- **Dedicated Network**: Low-latency network for etcd nodes
- **Resource Limits**: Ensure etcd has adequate CPU/memory
- **Compaction**: Regularly compact etcd history

## Common etcd Operations (for Learning)

### Query Pod Data (via kubectl)

```bash
# Get pod data as stored (YAML format)
kubectl get pod my-pod -o yaml

# This shows what etcd stores (after API Server processing)
```

### Watch for Changes

```bash
# Watch pods (similar to etcd watch)
kubectl get pods -w

# Watch events
kubectl get events -w
```

### Understand Data Flow

```bash
# Create a pod and watch events
kubectl run test-pod --image=nginx
kubectl get events --sort-by='.lastTimestamp'

# This shows the flow: API Server → etcd → Scheduler → Kubelet
```

## etcd vs. Other Databases

| Feature | etcd | Traditional DB |
|---------|------|----------------|
| Purpose | Distributed config store | General purpose |
| Consistency | Strong consistency | Configurable |
| API | REST/gRPC | SQL |
| Watch | Native support | Polling or triggers |
| Performance | Optimized for reads | Optimized for complex queries |
| Transactions | Simple | Complex ACID |

## Debugging etcd Issues

### Symptoms of etcd Problems

- API Server timeouts
- Unable to create/update resources
- Cluster becomes unresponsive
- Components can't communicate

### Diagnostic Commands

```bash
# Check API Server connectivity
kubectl cluster-info

# Check etcd pod status (in kube-system)
kubectl get pods -n kube-system | grep etcd

# Check etcd health (requires direct access)
etcdctl endpoint health

# View API Server logs (may show etcd connection issues)
kubectl logs -n kube-system kube-apiserver-minikube
```

## Learning Exercises

### Exercise 1: Understand Data Flow

1. Create a pod: `kubectl run test --image=nginx`
2. Watch events: `kubectl get events -w`
3. Trace the flow: API Server → etcd → Scheduler → Kubelet
4. Document each step

### Exercise 2: Observe etcd Updates

1. Create a ConfigMap
2. Update the ConfigMap
3. Watch pod events to see how kubelet reacts
4. Understand how etcd changes propagate

### Exercise 3: Backup Simulation

1. Export all resources: `kubectl get all -o yaml > backup.yaml`
2. Delete a namespace: `kubectl delete ns test`
3. Restore from YAML: `kubectl apply -f backup.yaml`
4. Understand what's preserved and what's not

## Key Takeaways

1. **etcd is Kubernetes' brain**: All cluster state lives here
2. **Only API Server talks to etcd**: This ensures consistency
3. **Watch API enables reactivity**: Components react to changes
4. **Backup etcd regularly**: It's critical for disaster recovery
5. **HA is essential**: Production needs 3+ etcd nodes
6. **Performance matters**: etcd bottlenecks affect entire cluster

## Further Reading

- [etcd Documentation](https://etcd.io/docs/)
- [Kubernetes Architecture](https://kubernetes.io/docs/concepts/architecture/)
- [etcd API](https://etcd.io/docs/latest/dev-guide/api_reference_v3/)
- [Raft Consensus Algorithm](https://raft.github.io/)

Remember: You rarely need to access etcd directly. Understanding how it works helps you understand Kubernetes behavior, but `kubectl` is your primary interface!

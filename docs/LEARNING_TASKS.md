# Learning Tasks and Exercises

This document contains a series of bugs, missing features, and improvements that you'll fix to master Kubernetes. Each task is designed to teach specific Kubernetes concepts.

## How to Use This Guide

1. **Read the task description** carefully
2. **Research** the Kubernetes concept if needed
3. **Fix the issue** or implement the feature
4. **Test** your changes
5. **Document** what you learned

## Task Categories

- 🔴 **Critical Bug**: App won't work without this fix
- 🟡 **Important Feature**: Missing functionality
- 🟢 **Enhancement**: Nice to have improvements
- 📚 **Learning Exercise**: Deep dive into concepts

---

## Section 1: Deployments & Replicas

### Task 1.1: Fix Replica Count (🔴 Critical)
**Issue**: Backend deployment is configured for 2 replicas, but only 1 is running.

**Steps**:
1. Check current replica count: `kubectl get deployment backend-deployment`
2. Investigate why replicas aren't scaling
3. Fix the deployment configuration
4. Verify all replicas are running

**Concepts**: Replicas, Deployment scaling, Pod scheduling

**Hint**: Check resource requests/limits and node capacity.

---

### Task 1.2: Add Rolling Update Strategy (🟡 Important)
**Issue**: The deployments don't have a rolling update strategy configured.

**Task**: Add `strategy` section to backend-deployment.yaml with:
- Type: RollingUpdate
- maxSurge: 1
- maxUnavailable: 0

**Concepts**: Rolling updates, Deployment strategies, Zero-downtime deployments

**Test**: Update the container image and watch the rolling update in action.

---

### Task 1.3: Implement Health Check Failures (🔴 Critical)
**Issue**: Backend health check endpoint returns 200 even when Redis is disconnected.

**Task**: The `/health` endpoint should return 503 when Redis is unavailable. Check if this is working correctly and fix if needed.

**Concepts**: Liveness probes, Readiness probes, Health checks

**Test**: 
1. Stop Redis pod: `kubectl delete pod -l app=redis`
2. Watch backend pods get restarted or marked as not ready
3. Verify frontend shows appropriate error

---

### Task 1.4: Add Resource Quotas (🟢 Enhancement)
**Task**: Create a ResourceQuota and LimitRange for the default namespace.

**Requirements**:
- ResourceQuota: Max 2 CPU, 4Gi memory, 10 pods
- LimitRange: Default requests 100m CPU, 128Mi memory; Default limits 500m CPU, 512Mi memory

**Concepts**: Resource quotas, Limit ranges, Resource management

---

## Section 2: ConfigMaps & Configuration

### Task 2.1: Fix ConfigMap Mount Issue (🔴 Critical)
**Issue**: Frontend ConfigMap contains HTML in a data key, but it's not being mounted correctly.

**Investigation**:
1. Check how frontend-deployment mounts the ConfigMap
2. Verify the ConfigMap structure
3. Fix the mount path or ConfigMap structure

**Concepts**: ConfigMap mounting, Volume mounting, File-based configuration

**Hint**: ConfigMaps can be mounted as files or used as environment variables.

---

### Task 2.2: Externalize Redis Configuration (🟡 Important)
**Issue**: Redis configuration is in a ConfigMap but not all settings are configurable.

**Task**: 
1. Add more Redis settings to the ConfigMap (e.g., maxmemory, timeout)
2. Update redis-deployment.yaml to use these settings
3. Test that changes to ConfigMap reflect in Redis

**Concepts**: ConfigMap updates, Configuration management, ConfigMap reload

**Note**: Some ConfigMap changes require pod restart.

---

### Task 2.3: Create Environment-Specific ConfigMaps (🟢 Enhancement)
**Task**: Create separate ConfigMaps for "dev" and "prod" environments using labels.

**Requirements**:
- Use labels to differentiate environments
- Create overlay structure: `k8s/configmaps/dev/` and `k8s/configmaps/prod/`
- Show how to select ConfigMaps using label selectors

**Concepts**: Environment management, Label selectors, Configuration patterns

---

## Section 3: Service Accounts & RBAC (IRSA Patterns)

### Task 3.1: Fix RBAC Permissions (🔴 Critical)
**Issue**: Backend service account doesn't have permission to read all ConfigMaps it needs.

**Investigation**:
1. Check what ConfigMaps the backend tries to read
2. Review backend-role.yaml permissions
3. Add necessary permissions

**Concepts**: RBAC, Roles, RoleBindings, Service accounts

**Test**: `kubectl auth can-i get configmaps --as=system:serviceaccount:default:backend-service-account`

---

### Task 3.2: Implement Least Privilege Principle (🟡 Important)
**Task**: Review and minimize RBAC permissions for all service accounts.

**Requirements**:
- Each service account should only have permissions it actually needs
- Remove unnecessary permissions
- Document why each permission is needed

**Concepts**: Least privilege, Security best practices, RBAC design

---

### Task 3.3: Add Pod Security Contexts (🟡 Important)
**Task**: Add security contexts to all deployments.

**Requirements**:
- Run containers as non-root users
- Set readOnlyRootFilesystem where possible
- Add security context at pod and container levels

**Concepts**: Pod security, Security contexts, Container security

**Hint**: You may need to update Dockerfiles to create non-root users.

---

## Section 4: Networking & Istio

### Task 4.1: Fix Service Discovery (🔴 Critical)
**Issue**: Backend can't reach Redis service using the service name.

**Investigation**:
1. Check service endpoints: `kubectl get endpoints redis-service`
2. Verify DNS resolution
3. Check Istio VirtualService configuration
4. Fix any misconfigurations

**Concepts**: Service discovery, DNS in Kubernetes, Service endpoints

---

### Task 4.2: Implement Traffic Splitting (🟡 Important)
**Task**: Configure Istio VirtualService to split traffic 80% to v1, 20% to v2.

**Requirements**:
1. Create a v2 version of the backend deployment
2. Update VirtualService with traffic splitting
3. Test traffic distribution

**Note**: You'll need to create a backend v2 deployment first (or simulate it).

**Concepts**: Traffic management, Canary deployments, Service mesh

---

### Task 4.3: Add Circuit Breaker Configuration (🟡 Important)
**Issue**: DestinationRule has circuit breaker settings but they're too permissive.

**Task**: Tighten circuit breaker settings and test behavior when backend fails.

**Test Scenario**:
1. Simulate backend failures
2. Verify circuit breaker trips
3. Check retry behavior

**Concepts**: Circuit breakers, Fault tolerance, Resilience patterns

---

### Task 4.4: Implement mTLS (🟢 Enhancement)
**Task**: Enable mutual TLS (mTLS) between services using Istio.

**Steps**:
1. Create a PeerAuthentication policy
2. Enable STRICT mTLS mode
3. Verify secure communication

**Concepts**: mTLS, Service mesh security, Encryption in transit

---

## Section 5: Observability & Debugging

### Task 5.1: Fix Log Aggregation (🔴 Critical)
**Issue**: Logger service receives logs but backend logs aren't appearing.

**Investigation**:
1. Check logger service connectivity
2. Verify LOGGER_SERVICE_URL environment variable
3. Test network policies (if any)
4. Fix configuration

**Concepts**: Service communication, Environment variables, Network debugging

---

### Task 5.2: Add Prometheus Metrics (🟢 Enhancement)
**Task**: Expose metrics endpoints and configure Istio to scrape them.

**Requirements**:
1. Add `/metrics` endpoint to backend
2. Configure Istio to enable metrics collection
3. Query metrics using `istioctl`

**Concepts**: Metrics, Observability, Prometheus integration

---

### Task 5.3: Implement Distributed Tracing (🟢 Enhancement)
**Task**: Set up Jaeger or Zipkin tracing with Istio.

**Requirements**:
1. Install Jaeger addon for Istio
2. Configure services to generate trace headers
3. View traces in Jaeger UI

**Concepts**: Distributed tracing, Observability, Service mesh tracing

---

## Section 6: etcd & Kubernetes Components

### Task 6.1: Explore etcd Data (📚 Learning)
**Task**: Examine etcd to understand what Kubernetes stores.

**Steps**:
1. Access etcd (if using external etcd) or use `kubectl proxy`
2. Query etcd for deployment data
3. Understand the data structure
4. Document findings

**Note**: In Minikube, etcd runs in the control plane. You may need to access it via `minikube ssh`.

**Concepts**: etcd, Kubernetes API, Cluster state

---

### Task 6.2: Understand Component Communication (📚 Learning)
**Task**: Trace how a pod creation request flows through Kubernetes components.

**Investigation**:
1. Create a pod and capture events: `kubectl get events -w`
2. Understand which components are involved
3. Document the flow: User → API Server → etcd → Scheduler → Kubelet

**Concepts**: Kubernetes architecture, Component interaction, API flow

---

### Task 6.3: Backup and Restore Simulation (📚 Learning)
**Task**: Simulate backing up etcd and restoring cluster state.

**Note**: In Minikube, you can simulate this by:
1. Exporting all resources to YAML
2. Deleting resources
3. Restoring from YAML

**Concepts**: etcd backup, Disaster recovery, Cluster state management

---

## Section 7: Advanced Scenarios

### Task 7.1: Implement Horizontal Pod Autoscaling (🟡 Important)
**Task**: Create an HPA for the backend deployment.

**Requirements**:
1. Install metrics-server (if not present)
2. Create HPA based on CPU utilization (target 70%)
3. Test scaling by generating load

**Concepts**: HPA, Autoscaling, Resource-based scaling

---

### Task 7.2: Add Init Containers (🟢 Enhancement)
**Task**: Add init container to backend to wait for Redis readiness.

**Requirements**:
1. Create init container that pings Redis
2. Configure it to run before main container
3. Verify initialization order

**Concepts**: Init containers, Startup dependencies, Initialization

---

### Task 7.3: Implement Pod Disruption Budget (🟡 Important)
**Task**: Create PDB to ensure at least 1 backend pod is always available.

**Concepts**: PDB, High availability, Voluntary disruptions

---

### Task 7.4: Add Network Policies (🟢 Enhancement)
**Task**: Restrict network traffic using NetworkPolicies.

**Requirements**:
1. Allow frontend → backend
2. Allow backend → Redis
3. Allow backend → logger
4. Deny all other traffic

**Concepts**: Network policies, Pod network security, Micro-segmentation

**Note**: Requires CNI that supports NetworkPolicies (not all Minikube drivers support this).

---

## Section 8: Real-World Scenarios

### Task 8.1: Fix Production Incident (🔴 Critical)
**Scenario**: Users report 503 errors. Backend pods are restarting.

**Investigation Steps**:
1. Check pod status: `kubectl get pods`
2. Check pod logs: `kubectl logs -l app=backend`
3. Check events: `kubectl get events --sort-by='.lastTimestamp'`
4. Check resource usage: `kubectl top pods`
5. Identify root cause and fix

**This is intentionally vague - you need to figure out what's wrong!**

---

### Task 8.2: Zero-Downtime Deployment (🟡 Important)
**Task**: Perform a rolling update of backend without service interruption.

**Requirements**:
1. Deploy new backend version
2. Verify zero downtime during update
3. Implement rollback strategy
4. Test rollback process

**Concepts**: Rolling updates, Zero-downtime deployments, Rollback strategies

---

### Task 8.3: Multi-Environment Setup (🟢 Enhancement)
**Task**: Use Kustomize or Helm to manage dev/staging/prod environments.

**Requirements**:
1. Create Kustomize overlays or Helm values files
2. Show how to deploy to different environments
3. Document differences between environments

**Concepts**: Configuration management, Kustomize, Helm, Multi-environment

---

## Testing Your Solutions

After completing each task:

```bash
# Verify deployments are healthy
kubectl get deployments
kubectl get pods

# Check service endpoints
kubectl get endpoints

# View logs
kubectl logs -l app=backend --tail=50

# Test service connectivity
kubectl run -it --rm test --image=curlimages/curl --restart=Never -- curl http://backend-service:5000/health
```

## Tips for Success

1. **Read Error Messages Carefully**: Kubernetes error messages are usually informative
2. **Use `kubectl describe`**: This shows detailed information about resources
3. **Check Events**: `kubectl get events` shows what's happening in the cluster
4. **Read Documentation**: kubernetes.io/docs is your friend
5. **Experiment Safely**: This is a learning environment - break things and fix them!

## Expected Outcomes

After completing these tasks, you should understand:

✅ How deployments manage pod lifecycles  
✅ How ConfigMaps externalize configuration  
✅ How Service Accounts and RBAC control access  
✅ How services enable service discovery  
✅ How Istio manages traffic and security  
✅ How etcd stores cluster state  
✅ How Kubernetes components interact  
✅ How to debug common issues  
✅ How to implement production best practices  

Good luck! 🚀

# General Notes:

## Taint and Tolerance

You can add a **taint** to a node so the scheduler avoids (or restricts) placing pods on it unless the pod has a matching **toleration**.

**Add a taint:**
```bash
kubectl taint nodes node1 key1=value1:NoSchedule
```

This prevents pods from being placed on the node unless the deployment or pod spec defines a toleration for the taint.

**Toleration in pod spec (e.g. in a Deployment):**
```yaml
tolerations:
- key: "key1"
  operator: "Exists"
  effect: "NoSchedule"
```

### What key / operator / effect mean

**key:** The taint’s label key. The toleration matches a taint that has this key (and optionally the same value). Example: `node-role.kubernetes.io/control-plane`, `dedicated`, `key1`.

**operator:** How the toleration matches the taint’s value.
- **`Equal`** (default): Key and value must both match. Use with `value: "value1"`.
- **`Exists`**: Only the key must exist on the taint; value is ignored. Use when you don’t care about the taint’s value.

**effect:** What the taint does when there’s no matching toleration.
- **`NoSchedule`**: Scheduler will not place new pods on the node (unless they tolerate it). Existing pods are unchanged.
- **`PreferNoSchedule`**: Scheduler tries to avoid the node but may still schedule there if needed.
- **`NoExecute`**: Same as NoSchedule, and **existing** pods that don’t tolerate it are evicted after a grace period (optional `tolerationSeconds`).

**Example with value (Equal):**
```yaml
tolerations:
- key: "key1"
  operator: "Equal"
  value: "value1"
  effect: "NoSchedule"
```

**Example for control-plane node (common in single-node/minikube):**
```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```

The above toleration means that the pod can be placed on nodes with the taint "node-role.kubernetes.io/control-plane" and the effect "NoSchedule"


## Common Debugging Scenarios

Scenarios engineers often face, with diagnostic commands and typical fixes.

---

### Scenario 1: Pods stuck in Pending

**Symptom:** `kubectl get pods` shows pods in `Pending` state.

**Diagnose:**
```bash
kubectl describe pod <pod-name>        # Look at "Events" section
kubectl get events --sort-by='.lastTimestamp'
kubectl top nodes                     # Check if nodes are out of resources
```

**Common causes:** Insufficient CPU/memory, node taints, no nodes available.

**Fix:** Increase node resources, add tolerations, or scale the cluster.

---

### Scenario 2: Pods stuck in ImagePullBackOff or ErrImagePull

**Symptom:** Pods never start; status shows `ImagePullBackOff` or `ErrImagePull`.

**Diagnose:**
```bash
kubectl describe pod <pod-name>        # Events show the image pull error
kubectl get events --sort-by='.lastTimestamp'
```

**Common causes:** Wrong image name, private registry without credentials, image doesn't exist.

**Fix:** Correct image name in deployment; add `imagePullSecrets` for private registries; ensure image exists (build/push for local images with `eval $(minikube docker-env)`).

---

### Scenario 3: Pods in CrashLoopBackOff

**Symptom:** Pods start, crash, restart, repeat.

**Diagnose:**
```bash
kubectl describe pod <pod-name>        # Events show exit reason
kubectl logs <pod-name>                # Current container logs
kubectl logs <pod-name> --previous     # Logs from crashed instance
```

**Common causes:** App crashes on startup (missing config, bad env var, can't connect to DB), failed health checks, OOMKill.

**Fix:** Fix the app or config; verify ConfigMaps/Secrets; check resource limits; adjust liveness/readiness probes.

---

### Scenario 4: Pods Running but not Ready (0/1 Ready)

**Symptom:** Pods show `Running` but `READY` column is `0/1`; Service doesn't route traffic to them.

**Diagnose:**
```bash
kubectl describe pod <pod-name>        # "Conditions" and "Events" show readiness probe failures
kubectl logs <pod-name>                # App may be failing health check
kubectl get endpoints <service-name>   # Empty = no ready pods
```

**Common causes:** Readiness probe failing (wrong path/port, app slow to start, dependency unavailable).

**Fix:** Correct probe path/port in deployment; increase `initialDelaySeconds`; fix the underlying dependency (e.g. Redis).

---

### Scenario 5: Service has no Endpoints

**Symptom:** `kubectl get endpoints <service-name>` shows empty or no addresses; traffic to Service fails.

**Diagnose:**
```bash
kubectl get endpoints <service-name>
kubectl get pods -l <label>            # Does the selector match? Do pods have that label?
kubectl describe service <service-name>   # Check selector
kubectl get pods -o wide               # Are pods Ready?
```

**Common causes:** Selector doesn't match pod labels; pods not Ready (readiness probe failing); no pods running.

**Fix:** Align Service selector with pod labels; fix pod readiness so they become Ready.

---

### Scenario 6: 503 or "connection refused" when hitting Service

**Symptom:** curl to Service returns 503 or connection refused.

**Diagnose:**
```bash
kubectl get endpoints <service-name>   # Are there endpoints?
kubectl get pods -l <label> -o wide    # Are pods Ready? What port do they use?
kubectl describe service <service-name>   # Is targetPort correct?
kubectl exec -it <pod-name> -- curl localhost:<port>/health   # Can the app respond inside the pod?
```

**Common causes:** Wrong `targetPort` (Service points to wrong container port); pods not Ready; app not listening on expected port.

**Fix:** Match Service `targetPort` to container `containerPort`; ensure pods are Ready and app is healthy.

---

### Scenario 7: ConfigMap/Secret changes not reflected in Pods

**Symptom:** Updated ConfigMap but pods still see old values.

**Diagnose:**
```bash
kubectl describe configmap <name>      # Verify ConfigMap content
kubectl exec <pod-name> -- env         # Or cat the mounted file; see current values
```

**Common cause:** ConfigMaps mounted as volumes are read at pod startup; updates don't propagate automatically.

**Fix:** Restart pods to pick up new ConfigMap: `kubectl rollout restart deployment <name>`

---

### Scenario 8: Pods can't reach other Services (DNS/network)

**Symptom:** App logs show "connection refused" or "unknown host" when calling another service.

**Diagnose:**
```bash
kubectl exec -it <pod-name> -- nslookup <service-name>   # Does DNS resolve?
kubectl exec -it <pod-name> -- curl http://<service-name>:<port>   # Can it reach the service?
kubectl get endpoints <service-name>   # Does target service have endpoints?
kubectl get svc                        # Is the service name/namespace correct?
```

**Common causes:** Wrong service name or namespace; target service has no endpoints; NetworkPolicy blocking traffic.

**Fix:** Use correct DNS (`<service>.<namespace>.svc.cluster.local`); ensure target pods are Ready; check NetworkPolicies.

---

### Scenario 9: High CPU/Memory usage, pods OOMKilled

**Symptom:** Pods restarted, `kubectl describe pod` shows OOMKilled; or `kubectl top pods` shows high usage.

**Diagnose:**
```bash
kubectl top pods
kubectl top nodes
kubectl describe pod <pod-name>        # "Last State" may show OOMKilled
kubectl get pod <pod-name> -o yaml     # Check resources.requests and resources.limits
```

**Common causes:** Memory limit too low; app leak; requests/limits misconfigured.

**Fix:** Increase memory limits; optimize app; set appropriate requests and limits.

---

### Scenario 10: Wrong cluster / "forbidden" or "context not found"

**Symptom:** Commands fail with "Forbidden" or "context not found"; changes don't appear where expected.

**Diagnose:**
```bash
kubectl config current-context         # Which cluster are you talking to?
kubectl config get-contexts            # List all contexts
kubectl cluster-info                   # Verify connectivity
```

**Common cause:** kubeconfig points to wrong cluster (e.g. production instead of dev).

**Fix:** `kubectl config use-context <correct-context>`

---

# Essential kubectl Commands Reference

Commands you'll use daily. **Bold** = most critical.

## Cluster & Context

| Command | Description |
|---------|-------------|
| **`kubectl cluster-info`** | Check cluster connectivity; shows API server URL |
| **`kubectl config current-context`** | Which cluster/context you're talking to |
| `kubectl config get-contexts` | List all contexts |
| `kubectl config use-context <name>` | Switch cluster (e.g. minikube vs production) |

## Viewing Resources (get)

| Command | Description |
|---------|-------------|
| **`kubectl get pods`** | List pods (default namespace) |
| **`kubectl get pods -o wide`** | List pods with node, IP |
| **`kubectl get pods -l app=backend`** | Filter by label |
| **`kubectl get pods -A`** or **`-n kube-system`** | All namespaces or specific |
| `kubectl get deployments` | List deployments |
| `kubectl get services` | List services |
| `kubectl get configmaps` | List ConfigMaps |
| **`kubectl get endpoints`** | See which pod IPs a Service routes to |
| `kubectl get all` | Pods, services, deployments in namespace |

## Inspecting Resources (describe)

| Command | Description |
|---------|-------------|
| **`kubectl describe pod <name>`** | Full pod details: events, conditions, why it failed |
| **`kubectl describe deployment <name>`** | Deployment status, rollout history |
| `kubectl describe service <name>` | Service endpoints, selector |
| **`kubectl describe node <name>`** | Node capacity, conditions, resource usage |

## Logs & Debugging

| Command | Description |
|---------|-------------|
| **`kubectl logs <pod-name>`** | Container logs |
| **`kubectl logs -l app=backend`** | Logs from all pods with label |
| **`kubectl logs -f <pod-name>`** | Stream logs (follow) |
| **`kubectl logs <pod-name> --previous`** | Logs from crashed/restarted container |
| **`kubectl logs <pod-name> -c <container>`** | Specific container in multi-container pod |
| **`kubectl exec -it <pod-name> -- sh`** | Shell into pod (requires shell in image) |
| `kubectl exec <pod-name> -- <cmd>` | Run one-off command in pod |

## Events & Troubleshooting

| Command | Description |
|---------|-------------|
| **`kubectl get events --sort-by='.lastTimestamp'`** | Cluster events; often shows why things failed |
| **`kubectl get events -w`** | Watch events in real time |
| `kubectl top pods` | CPU/memory usage (needs metrics-server) |
| `kubectl top nodes` | Node resource usage |

## Applying & Managing

| Command | Description |
|---------|-------------|
| **`kubectl apply -f <file>`** | Create/update resources from YAML |
| **`kubectl apply -f <directory>`** | Apply all YAML in directory |
| **`kubectl delete -f <file>`** | Delete resources defined in YAML |
| `kubectl rollout restart deployment <name>` | Restart all pods (pick up new ConfigMaps/images) |
| `kubectl rollout status deployment <name>` | Watch rollout progress |
| `kubectl scale deployment <name> --replicas=3` | Change replica count |
| **`kubectl port-forward svc/<name> 8080:80`** | Forward local port to Service |

## Minikube-Specific

| Command | Description |
|---------|-------------|
| **`minikube start`** | Start cluster |
| **`minikube service <svc-name> --url`** | Get URL to access Service from browser |
| `eval $(minikube docker-env)` | Build images into Minikube's Docker |
| `minikube ssh` | SSH into Minikube node |
| `minikube addons enable metrics-server` | Enable `kubectl top` |

## Quick Reference: Most Used

```bash
# Daily workflow
kubectl get pods                    # What's running?
kubectl get pods -o wide            # With IPs and nodes
kubectl describe pod <name>         # Why is it broken?
kubectl logs <pod-name>             # What did it log?
kubectl logs -f -l app=backend      # Stream backend logs
kubectl get events --sort-by='.lastTimestamp'   # What happened?
kubectl apply -f k8s/               # Deploy changes
kubectl rollout restart deployment <name>       # Restart after ConfigMap change
```

---

## Questions:
1. What is an external vs internal port? For example, in working cluster walkthrough, you write that `80:31234/TCP` means external port 31234 → internal 80.

**Answer:** The format is `port:nodePort/protocol`. For `80:31234/TCP`:
- **Internal port 80**: The container listens on port 80 (what nginx expects). This is `targetPort` in the Service.
- **External port 31234**: The *node* (machine) exposes port 31234. Traffic to `node-ip:31234` gets forwarded to a pod's port 80.

So: User → `minikube-ip:31234` → Service → Pod's port 80. The "external" side is what clients hit; the "internal" side is what the container receives.

---

2. Can you explain kube-proxy to me? I don't really know anything about it

**Answer:** kube-proxy is a daemon that runs on every node. Its job: **implement Services** by maintaining network rules that route traffic to pods.

When you create a Service:
1. kube-proxy watches the API for Services and Endpoints (pod IPs).
2. It updates iptables (or IPVS) rules on the node: "traffic to ClusterIP X:5000 → forward to these pod IPs."
3. When a pod on that node sends traffic to `backend-service:5000`, the rules redirect it to an actual pod IP.

kube-proxy doesn't forward traffic itself; it programs the kernel (via iptables/IPVS) to do the routing. So every node knows how to route Service traffic to the right pods.

---

3. I see you can use configmaps as a volume and then mount them (i.e. in frontend) but you can also just kind of read from them like a config file (i.e. in backend). I'm confused about how volume mounting a configmap works, the other use case seems intuitive to me though.

**Answer:** Two ways to use ConfigMaps:

**A. Environment variables** (backend): ConfigMap keys become env vars. The container sees `REDIS_HOST=redis-service` as an environment variable. No files—the app reads `os.getenv("REDIS_HOST")`.

**B. Volume mount** (frontend): ConfigMap keys become *files* in a directory. Each key becomes a filename; the value becomes the file content. So `frontend-config` with key `index.html` creates a file at `/usr/share/nginx/html/index.html`. Nginx reads it from disk like any file.

Both pull data from the ConfigMap; the difference is *how* the app consumes it—env vars vs files. Nginx expects files on disk, so we mount. Python can use env vars, so we inject those.

---

4. Relating (kind of) to the previous problem, why is index.html not just built into the frontend container? Is there any reason why we choose to mount it into the configmap mount?

**Answer:** Both approaches work; it's a tradeoff.

**Build into image:** Simpler, single artifact. To change the UI, you rebuild and redeploy the image.

**Mount via ConfigMap:** Change the HTML without rebuilding the image. Update the ConfigMap, restart pods (or wait for sync), and the new content is served. Better for:
- Config that changes often
- Same image, different content per environment
- Separation of "code" (nginx image) from "content" (HTML)

In production, you might build the frontend into the image for performance and versioning. Using ConfigMaps is more flexible for learning and rapid iteration.

---

5. Where is the dns for the backend service defined? I'm guessing that it's just <service_name>.<namespace>.svc.cluster.local, is that correct? Is it always .svc.cluster.local?

**Answer:** Yes. The full DNS name is:
```
<service-name>.<namespace>.svc.cluster.local
```

`cluster.local` is the default cluster domain; it can be changed via kubelet's `--cluster-domain` flag. Most clusters keep it as `cluster.local`.

Shortcuts (from the same namespace):
- `backend-service` (just the name)
- `backend-service.default` (name + namespace)

CoreDNS (or kube-dns) resolves these names automatically—you don't define them in the Service file. Creating a Service with name `backend-service` in namespace `default` automatically makes `backend-service.default.svc.cluster.local` resolve to that Service's ClusterIP.

---

6. In what situation would you define services to be in separate namespaces?

**Answer:** Namespaces isolate resources. Use separate namespaces when:

- **Environments**: `dev`, `staging`, `prod`—same app, different config and lifecycles.
- **Teams**: `team-a`, `team-b`—separate quotas, RBAC, and visibility.
- **Multi-tenancy**: Different customers or projects in the same cluster.
- **System vs app**: `kube-system` for cluster components; `default` or custom namespaces for apps.
- **Resource quotas**: Limit CPU/memory per namespace.
- **Network policies**: Restrict traffic between namespaces.

Services in different namespaces use the full DNS name: `backend-service.production.svc.cluster.local`.

---

7. In the service files, is the selector referring to the label on the deployment or on the pods?

**Answer:** The Service selector refers to **pod labels**, not Deployment labels.

Deployments don't receive traffic. They create Pods, and Pods get the labels from the Deployment's `spec.template.metadata.labels`. The Service's selector matches those pod labels. So: Deployment → creates Pods with labels → Service finds Pods by selector.

The Deployment has its own labels (e.g. `app: backend`) for identifying the Deployment. The Pod template has labels that must match what the Service selects. They're often the same value, but the selector targets Pods, not the Deployment.

---

8. Are the service files meant to define how the services network with each other? How does the frontend service find the backend service and vice versa?

**Answer:** Service files define a **stable endpoint** (name + ClusterIP + port) that other pods use to reach your app. They don't define "connections between" services; each Service is independent.

**How frontend finds backend:**
1. Frontend pod (or its JS, when run server-side) needs to call the backend API.
2. It uses the DNS name `backend-service` (or the full form).
3. CoreDNS resolves `backend-service` → ClusterIP of backend-service.
4. kube-proxy routes traffic to that ClusterIP → actual backend pod IPs.

**How backend finds frontend:**
- Usually it doesn't. Frontend (browser) calls backend. Backend calls Redis, Logger, etc.—each via *their* Service names.

**The key:** Pods don't "register" with each other. They just use Service names. CoreDNS + kube-proxy handle resolution and routing. Each Service file defines one stable endpoint; anything in the cluster can reach it by name.

9. How come the frontend service files defines the internal and external ports as port 80 but when I run minikube service frontend-service --url it comes back as localhost:63058? Shouldn't it be running on port 80?

**Answer:** Port 80 is the *container* port (what nginx listens on). The Service type NodePort assigns a *random high port* (30000–32767) on the node for external access. So:

- **Port 80**: The Service's `port` (and `targetPort`)—what clients use when they hit `frontend-service:80` from inside the cluster, and what the pods listen on. In our setup they're the same.
- **Port 63058** (or similar): The NodePort—a high port on the *node* itself. Traffic to `node-ip:63058` is forwarded through the Service to a pod's port 80.

**When would `port` and `targetPort` differ?** Sometimes the container listens on a different port than you want the Service to expose. Example: your app listens on 8080, but you want clients to hit the standard HTTP port 80. Then you'd set `port: 80` (what clients connect to) and `targetPort: 8080` (what the container actually listens on). In our services they're the same because nginx listens on 80 and the backend listens on 5000.

`minikube service --url` returns the URL to reach the Service *from your laptop*—it uses the node’s NodePort and a tunnel so `localhost:63058` reaches the minikube node. You’re not inside the cluster, so you need that tunnel and the NodePort, not port 80. Port 80 only exists inside the pod.

---

10. How does the port forwarding commands work?

**Answer:** `kubectl port-forward` creates a tunnel from a port on your machine to a port on a Pod, Service, or Deployment.

**Example:** `kubectl port-forward svc/backend-service 5000:5000`
- **Left (5000)**: Port on your local machine.
- **Right (5000)**: Port on the backend-service (or its pods).
- Effect: `localhost:5000` on your laptop forwards to the backend service inside the cluster.

**Example:** `kubectl port-forward pod/my-pod 8080:80`
- Local port 8080 → pod’s port 80.

**How it works:** kubectl talks to the API server, which talks to the kubelet on the node where the pod runs. kubectl keeps a connection open and forwards data between your local port and the pod’s port. The tunnel stops when you Ctrl+C.

**Use case:** Quick local access to cluster services without NodePort or Ingress.

---

11. I read online that kubectl exec is actually a bad habit: shells shouldn't be installed in containers as they pose security risks. Instead, if we want to debug what's going inside a container, we should use --debug to attach a debugging container to the faulty container, and copy the faulty pod first since debug containers can't be deleted without deleting the pod. Can you put the command for how to do that in the working cluster walkthrough?

**Answer:** You’re right: production images often omit shells, and `kubectl exec` can be a security concern.

**Ephemeral debug container approach:**

**Recommended workflow:**
```bash
kubectl debug -it <faulty-pod-name> --copy-to=<pod-name>-debug --image=nicolaka/netshoot --target=<container-name>

# When done, delete the copy
kubectl delete pod debug-<pod-name>
```

This creates a copy of the pod, adds a debug container (`netshoot` or `busybox`), and lets you attach. Delete the copy when finished: `kubectl delete pod <pod-name>-debug`.

12. What is busybox/netshoot? I assume they're just debug containers that you attach to the container you are debugging?

**Answer:** Yes. They're small, general-purpose images that include tools useful for debugging. You run them as ephemeral or sidecar containers in the same pod as the container you're debugging, so they share the same network (and optionally PID) namespace.

**BusyBox:** Very small (~5MB) image with common Unix tools: `sh`, `wget`, `curl`, `nslookup`, `ping`, `telnet`, `netstat`, `ps`, etc. Good for basic connectivity checks (ping, curl, nslookup) when the app image has no shell.

**Netshoot:** Larger image with a full network troubleshooting toolkit: `curl`, `dig`, `tcpdump`, `netstat`, `iptables`, `iperf`, `nmap`, `mtr`, and more. Better when you need deeper network debugging (e.g. packet capture, DNS inspection).

You don't attach *to* the app container; you add one of these as a separate container in the pod. Because they share the pod network namespace, you can reach `localhost:5000` or `redis-service:6379` from inside the debug container.

---

13. What is the difference between ClusterIP/NodePort? Are there more types?

**Answer:** Yes. There are four Service types:

**ClusterIP (default):** Internal-only. Gets a stable virtual IP (e.g. 10.96.0.10) reachable only from inside the cluster. Use for app-to-app traffic (backend, database, internal APIs).

**NodePort:** Exposes the service on a high port (30000–32767) on *every node*. Traffic to `node-ip:31234` is forwarded to the Service, then to a pod. Use for dev/testing or when you need external access without a load balancer. ClusterIP is still created; NodePort adds an extra external port.

**LoadBalancer:** Cloud-provider creates an external load balancer (AWS ELB, GCP LB, etc.) that forwards to the Service. Use for production external access. On bare metal/minikube, often implemented via MetalLB or similar, or behaves like NodePort.

**ExternalName:** Maps the Service to an external DNS name (e.g. `external-db.example.com`). No proxying; it's a DNS alias. Use when pointing to services outside the cluster.

**Summary:**

| Type         | Reachable from         | Use case                          |
|--------------|------------------------|-----------------------------------|
| ClusterIP    | Inside cluster only    | Internal services                 |
| NodePort     | Node IP + high port    | Dev/testing, simple external access |
| LoadBalancer | External load balancer | Production external access        |
| ExternalName | DNS alias only         | Point to external services        |

14. How does load balancer work? Assuming I'm using AWS, does it automatically provision the load balancer for me or do I need to create it myself and provide the arn? 

**Answer:** With AWS EKS, the cloud controller **provisions the load balancer for you**. You don't create it manually or provide an ARN.

**Flow:**
1. You create a Service with `type: LoadBalancer`.
2. The **AWS cloud controller** (running in the cluster) watches for LoadBalancer Services.
3. It creates an Elastic Load Balancer (ELB/ALB/NLB) in your AWS account.
4. It configures the load balancer to route traffic to your Service's NodePort (or directly to pods, depending on setup).
5. It writes the load balancer's hostname or IP into the Service's `status.loadBalancer.ingress`.

You just apply the Service YAML; AWS handles the rest. The load balancer is created in the same region as your cluster, in your AWS account. You pay for it like any other ELB.

**Annotations** (optional) let you customize: e.g. `service.beta.kubernetes.io/aws-load-balancer-type: nlb` for Network Load Balancer, or annotations for SSL certificates, internal vs internet-facing, etc.

---

15. How does ExternalName work? How does it even know I own the domain?

**Answer:** ExternalName **doesn't verify or care** that you own the domain. It's just a DNS alias—a CNAME record that says "when someone looks up this Service name, return this other hostname instead."

**How it works:**
1. You create a Service with `type: ExternalName` and `externalName: external-db.example.com`.
2. CoreDNS creates a CNAME record: `my-service.default.svc.cluster.local` → `external-db.example.com`.
3. When a pod does `nslookup my-service`, it gets back `external-db.example.com`.
4. The pod then connects to `external-db.example.com` directly. Kubernetes doesn't proxy the traffic; it only does DNS translation.

**Ownership:** Kubernetes doesn't validate that you control the domain. It just stores and returns the hostname. If you point it at a domain you don't control, pods will resolve it, try to connect, and either succeed (if the host is reachable) or fail (if it's not). There's no "ownership check"—it's just DNS.

**Use case:** Your app expects to connect to `database.internal`. You create an ExternalName Service `database` that points to `my-rds-instance.region.rds.amazonaws.com`. Your app code doesn't need to change; it still calls `database`, and DNS resolves it to the RDS hostname.

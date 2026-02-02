# Istio configuration in this repo

Suggested **reading order** and how the files relate.

## Reading order

1. **`gateway.yaml`** – Defines the *edge*: what the Istio ingress gateway listens on (HTTP port 80). Does not route traffic by itself.
2. **`virtualservice-frontend.yaml`** – Routes traffic that *enters* through the Gateway to `frontend-service`. References the Gateway; without this, traffic hitting the Gateway would have no route (404).
3. **`destinationrule-backend.yaml`** – Defines *what* the backend destination is (subsets, connection pool, circuit breaker). The backend VirtualService refers to subsets like `v1` and `v2`; the DestinationRule defines those subsets.
4. **`virtualservice-backend.yaml`** – Defines *how* mesh-internal traffic to `backend-service` is routed (by header to subset v2, otherwise v1). Does **not** reference the Gateway—it applies when pods inside the mesh (e.g. frontend) call backend-service.

## How they relate

**External traffic (user → Gateway → frontend):**
```
  User → gateway.yaml (listen 80) → virtualservice-frontend.yaml (route to frontend-service) → frontend pod
```

**Mesh-internal traffic (frontend pod → backend):**
```
  Frontend pod → virtualservice-backend.yaml (route by header to v1/v2) → destinationrule-backend.yaml (subsets, circuit breaker) → backend pod
```

| File | Role | Depends on |
|------|------|------------|
| **gateway.yaml** | Configures the **ingress gateway** (listen on port 80). Entry point for external traffic. | Nothing in this folder. |
| **virtualservice-frontend.yaml** | Routes traffic that **entered through the Gateway** to `frontend-service`. Binds to the Gateway. | Gateway (task-manager-gateway). |
| **virtualservice-backend.yaml** | **Mesh-internal** routing for `backend-service`: which subset (v1/v2) based on headers. Does *not* reference the Gateway. | DestinationRule (for subset names v1, v2). |
| **destinationrule-backend.yaml** | **Destination config** for `backend-service`: subsets (v1 by label), connection pool, circuit breaker. | Nothing in this folder. |

**Note:** The VirtualService references subset `v2`, but the DestinationRule only defines subset `v1`. That’s intentional: v2 would be used when you add a canary deployment with `version: v2`. Until then, routing to v2 would have no matching pods.

## Apply order

Apply in any order; Istio doesn’t care. A common order is:

```bash
kubectl apply -f k8s/istio/
```

To perform a canary deployment with Istio:

1. **Deploy the canary version**: Create a new Deployment for your service with pods labeled `version: v2` (the canary). The existing (stable) pods should have `version: v1`.
   
2. **Update the DestinationRule**: The provided `destinationrule-backend.yaml` defines subset `v1`, but to do a canary, add a subset for `v2`:
   ```yaml
   subsets:
   - name: v1
     labels:
       version: v1
   - name: v2
     labels:
       version: v2
   ```
   This lets Istio route to both versions by label.

3. **Control routing in the VirtualService**: The `virtualservice-backend.yaml` already has a rule that routes traffic with header `x-canary: true` to subset `v2` (the canary), and otherwise to `v1`. To start the canary, you can direct a small portion of traffic (e.g., by only sending the header from test clients) or use weights to split traffic gradually, e.g.:
   ```yaml
   - route:
     - destination:
         host: backend-service
         subset: v1
       weight: 90
     - destination:
         host: backend-service
         subset: v2
       weight: 10
   ```

**Summary of required changes:**
- Deploy a v2 Deployment with `version: v2` label
- Add `v2` subset to your DestinationRule
- Adjust VirtualService to send a portion of traffic to v2 (by header or by weight)

This lets you introduce v2 without disrupting all users, test with limited traffic, and gradually promote v2 to full production.

QUESTION: In our current setup, destinationrule-backend does not contain a definition for a subset v2. In virtualservice-backend, we say that if we receive a header called x-canary set to true, then we forward to v2. Thus, if we were to send a request in our current setup through the istio gateway, would it just fail because there is no destination rule defined to match the subset we are sending traffic to?
No, the request to subset `v2` will **not immediately fail** solely because there’s no `v2` subset defined in the `DestinationRule`. Istio’s behavior in this case is as follows:

- If the `DestinationRule` does not define a subset that matches the requested `subset` (e.g., `v2`), Istio **routes the traffic to any backing pod** for the specified `host` *that matches no subset label selector*, i.e., as if no subset was selected.


QUESTION: Then given our current setup, any traffic with x-canary not set to true would go to the service called 
backend-service with the label version: v1 right? But since in backend-service.yaml we don't define that label, 
there would be no service that matches the subset so it would just send it to the host backend-service right?

ANSWER: Not exactly. Here’s what happens in your current setup:

- Your `VirtualService` rules say:  
  - If `x-canary: true`, route to subset `v2`  
  - Otherwise, route to subset `v1`
- Your `DestinationRule` defines only subset `v1` (matching pods with label `version: v1`).  
- But your `backend-service.yaml` Service does **not** have any label or selector for `version: v1`, just `app: backend`.

What this means:
- If your Deployment **pods** have `version: v1` labels, the subset rule works (traffic with no `x-canary` goes only to v1 pods).
- However, if your pods **don’t** actually have `version: v1` as a label, the subset will match nothing, and Istio will fall back to sending to any pod for `backend-service`—effectively acting as if no subsets are defined.
- The Service itself doesn’t filter traffic by version label; selector is for `app: backend`, so it targets all pods with that label.

**In summary:**  
If your pods aren’t labeled with `version: v1`, then subset-based routing in the DestinationRule does nothing, and traffic without `x-canary` just gets sent to all `backend-service` endpoints (ignoring subset rules). The key piece is the pod labels: if those don’t match the subset definitions, Istio falls back to sending traffic to any healthy instance behind the Service.

To get true canary behavior, you must:
- Label your stable pods with `version: v1`
- Add `version: v2` for your canary pods
- Make sure your `DestinationRule` subsets match those labels

Otherwise, VirtualService routing by subset will not work as intended.


QUESTION: How would I label a pod with version: v1 in this case? Would I add the label to the deployment file 
and then apply the deployment or would I manually label existing pods? I actually have a similar question 
regarding taints: how do you add a taint to a node? Is it something you do in a file or manually via command to a 
running node?

# ANSWER: 

**1. How to label pods with `version: v1`:**

You should add the label (`version: v1`) to your **Deployment** specification, not manually label pods after they are created. Labels defined in the Pod template of a Deployment will be automatically applied to all pods managed by that Deployment.

For example, in your `Deployment` YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-v1
spec:
  selector:
    matchLabels:
      app: backend
      version: v1           # <--- add version label to selector
  template:
    metadata:
      labels:
        app: backend
        version: v1         # <--- add version label here
    spec:
      containers:
      - name: backend
        image: your-backend:v1
```

When you apply this Deployment, all pods created will have both `app: backend` and `version: v1` labels. This is the correct way to ensure Istio subset routing works.

You can manually label an existing pod (for testing), for example:
```bash
kubectl label pod <pod-name> version=v1
```
But **for production and automation**, always add labels to the Deployment pod template, so new pods get the right labels.

---

**2. How to add a taint to a node:**

Adding taints to nodes is NOT done in any manifest file (there’s no "node manifest" in Kubernetes). It’s done **manually via kubectl** to a running node.

To add a taint, use:
```bash
kubectl taint nodes <node-name> key=value:taint-effect
```
Example:
```bash
kubectl taint nodes node1 dedicated=backend:NoSchedule
```
This mark prevents pods without the corresponding toleration from being scheduled onto the node.

You can view existing taints with:
```bash
kubectl describe node <node-name>
```
And you can remove a taint with:
```bash
kubectl taint nodes <node-name> dedicated-
```

**Summary:**
- Pod labels like `version: v1` are set in your Deployment YAML (recommended) or can be manually added to existing pods (`kubectl label pod ...`).
- Node taints are always set or removed dynamically via the `kubectl taint` command, not via manifests.


QUESTION: So if I wanted to do a canary deployment on the backend service that I have right now in the repo: 
1. I would first add the v1 label to the existing deployment file
2. I would apply that deployment so the label gets picked up by the pods
3. I would then create a new deployment file that is a copy of the current backend deployment file but add the v2 label instead of the v1 label, and then apply the deployment to create pods with the v2 label
4. I would modify the destination rule file to create a subset for v2, matching the pods of backend-service matching the v2 label
Is this correct?

Yes, your understanding is correct!

Let me elaborate step-by-step:

1. **Label the current deployment pods with `version: v1`**  
   Add the `version: v1` label to your backend Deployment’s pod template (in the `metadata.labels` section under `spec.template`). Apply the updated Deployment so that all running/recreated pods get this label.

2. **Create a new deployment for canary (`version: v2`)**  
   Duplicate your backend Deployment manifest. Change the pod template `version` label to `v2` and update the container image (if needed) to your canary version. Apply this new Deployment. Now, you’ll have two sets of pods—one with `version: v1` and one with `version: v2`.

3. **Update the DestinationRule**  
   In your Istio `DestinationRule` for the backend service, add (or make sure you have) `subsets` for both `v1` and `v2`, each matching the respective `version` label.

   ```yaml
   subsets:
   - name: v1
     labels:
       version: v1
   - name: v2
     labels:
       version: v2
   ```

4. **Control traffic with a VirtualService**  
   Your `VirtualService` can now define which percentage or request pattern goes to each subset. For example, you can start with 100% to `v1`, then shift some percentage (or matching headers, e.g. `x-canary`) to `v2` as desired.

In summary:  
- Pod labels (`version`) identify deployment versions for traffic splitting.
- Multiple Deployments for the same app, but different labels/images, enable canary/blue-green rollout.
- The Istio DestinationRule/VirtualService use those labels to control routing.

This is the standard workflow for canary deployments in Kubernetes with Istio. Good work!
# What a Sidecar Container Is and How It Works

This document explains the sidecar pattern in Kubernetes: what it is, how it works, and how Istio uses it.

## What is a sidecar container?

A **sidecar** is an extra container that runs in the **same pod** as your main application container. The pod has two (or more) containers that share the same lifecycle and some resources (network, sometimes storage). The “main” container does the primary work (e.g. serve API); the “sidecar” does supporting work (e.g. proxy traffic, collect logs, export metrics).

```
┌─────────────────────────────────────────┐
│  Pod                                     │
│  ┌─────────────────┐  ┌─────────────────┐
│  │  Main container │  │  Sidecar         │
│  │  (your app)     │  │  (helper)        │
│  │                 │  │                  │
│  │  e.g. backend   │  │  e.g. Envoy      │
│  │  on port 5000   │  │  proxy           │
│  └────────┬────────┘  └────────┬────────┘
│           │                     │
│           └──────────┬──────────┘
│                      │
│           Shared network namespace
│           (same IP, same localhost)
└─────────────────────────────────────────┘
```

So: **one pod, multiple containers, one of them is the “sidecar” that assists the main app.**

## How pods with multiple containers work

- **Containers in a pod** share:
  - **Network namespace:** Same IP address, same `localhost`. So the app can call `localhost:15001` and reach the sidecar on that port.
  - **Optional: volumes.** You can mount the same volume into both containers to share files (e.g. logs, secrets).
- They **do not** share:
  - PID namespace by default (separate process trees).
  - Filesystem (unless you use a shared volume).
- **Lifecycle:** All containers in the pod start together. If the pod is deleted, all containers stop. If the main container exits, the whole pod can be considered failed (depending on restart policy), so the sidecar stops too.

So the sidecar is “next to” the app in the same pod and can communicate over `localhost` and shared volumes.

## How a sidecar is used: traffic interception (e.g. Istio)

A common use is a **proxy sidecar** that all traffic goes through:

1. **Outbound:** Your app is configured to send HTTP to `localhost:15001` (or the proxy listens on the app’s outbound port and the app uses localhost). The sidecar receives the request, then forwards it to the real destination (e.g. `backend-service:5000`). On the way it can add headers, retries, metrics, mTLS.
2. **Inbound:** Traffic from other pods arrives at the pod’s IP and port. The **sidecar** listens on that port (or a dedicated port and the Service targets it). The sidecar accepts the connection (e.g. terminates mTLS), then forwards to the app on `localhost:5000`.

So the sidecar sits in the middle of all traffic to and from the app. The app code still talks to “normal” addresses; the mesh just configures the app or the proxy so that traffic goes through the sidecar. In Istio, the Envoy proxy is that sidecar.

```
  Other pod                    This pod
       │                            │
       │   request to pod-ip:5000   │
       └───────────────────────────►│
                                   │  Envoy (sidecar) receives
                                   │  on port 5000 (or redirect)
                                   │  forwards to localhost:5000
                                   │  ┌─────────────────────┐
                                   │  │ App container       │
                                   │  │ listens 127.0.0.1:5000
                                   │  └─────────────────────┘
```

## Sidecar vs main container: who listens on which port

- **Without sidecar:** The app listens on port 5000; the Service’s `targetPort: 5000` sends traffic to the app.
- **With Istio:** The pod has two containers. Istio can set **redirect rules** so that:
  - Inbound: Traffic to the pod on 5000 is captured by Envoy, which then forwards to the app on `localhost:5000`.
  - Outbound: App traffic is redirected (e.g. via iptables) to Envoy, which then forwards to the real destination.

So the “who listens where” is configured by the mesh (and optionally pod spec); the app often doesn’t change ports.

## Other sidecar use cases

- **Log shipper:** Main app writes logs to a shared volume; sidecar reads them and ships to Elasticsearch or S3.
- **Metrics exporter:** Sidecar scrapes the app’s metrics endpoint (on localhost) and exposes them in Prometheus format.
- **Secrets fetcher:** Sidecar fetches secrets from an external store and writes files to a shared volume; main app reads them.
- **Network proxy:** Any proxy (e.g. Envoy, NGINX) that handles encryption, auth, or routing is a classic sidecar.

In all cases, the sidecar shares the pod’s network (and often a volume) with the main container.

## How Istio injects the sidecar

When **automatic sidecar injection** is enabled for a namespace:

```bash
kubectl label namespace default istio-injection=enabled
```
QUESTION: Do all sidecar containers work like this (specifically, that they have some label that you set to have them be automatically injected into pods)?
No, not all sidecar containers work like Istio’s automatic injection mechanism. The approach where you label a namespace (e.g. `istio-injection=enabled`) and a webhook injects a sidecar is specific to service meshes like **Istio** (and similar tools such as Linkerd, which use their own injection methods).

**How do other sidecars get injected if not via label?**

For most common Kubernetes use cases—like a log shipper, metrics exporter, or a secrets-fetching helper—the sidecar pattern is implemented *manually* in your pod definition:

1. **Manual Declaration in the Pod Spec:**  
   You specify the sidecar as an additional entry in the `containers:` list in your pod YAML or Deployment resource. For example:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: my-app-with-sidecar
   spec:
     containers:
       - name: main-app
         image: my-app:latest
       - name: log-shipper
         image: fluentd:latest
   ```
   Both containers run in the same pod. The sidecar is not injected or added automatically by Kubernetes.

2. **Templates and Custom Tools:**  
   Some CI/CD or GitOps pipelines (e.g. Helm, Kustomize, ArgoCD) might give you a way to *template* or *patch* in sidecar containers. These are platform-specific workflows, not part of Kubernetes itself.

3. **Admission Webhooks (Custom):**  
   It’s possible to write a *custom* mutating admission webhook that will inject containers based on your organization’s needs, but this is advanced usage and generally limited to specialized platforms rather than common open-source tools.

**Summary:**
- Service meshes and similar tools give you auto-injection via labels/annotations and webhooks.
- All other sidecars are added by explicitly listing both containers in the pod/deployment YAML.
- There is no Kubernetes-native mechanism (label, annotation, or otherwise) for injecting arbitrary sidecars for regular workloads.
- If you don’t see a webhook-based service mesh (like Istio) involved, assume that you must declare the sidecar container directly in your resource manifests.



the **Istio admission webhook** runs when a pod is created:

1. It sees the pod is in a namespace with `istio-injection=enabled`.
2. It **mutates** the pod spec: adds the `istio-proxy` container (Envoy) and an init container that sets up iptables (or similar) to redirect traffic to the proxy.
3. The pod is then created with two containers (and the init container); the Envoy container is the Istio sidecar.

So you don’t add the sidecar manually; Istio adds it for every pod in labeled namespaces. You can confirm with:

```bash
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].name}'
# e.g. output: backend istio-proxy
```

## Summary

| Concept | Explanation |
|--------|--------------|
| **Sidecar** | Extra container in the same pod as the main app, doing a supporting role (proxy, logging, metrics, etc.). |
| **Shared network** | All containers in the pod share one IP and localhost, so the app can talk to the sidecar on `localhost:<port>`. |
| **Lifecycle** | Sidecar starts and stops with the pod; no separate scaling. |
| **Istio** | Uses an Envoy proxy as a sidecar to handle traffic, mTLS, and observability without changing app code. |

Understanding sidecars helps you understand why each pod in the mesh has two containers and how traffic actually flows through the proxy.

## References

- [Kubernetes: Pods with multiple containers](https://kubernetes.io/docs/concepts/workloads/pods/#workload-resources-for-managing-pods)
- [Istio: Sidecar injection](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)

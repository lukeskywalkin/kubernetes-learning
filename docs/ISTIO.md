# How Istio Works

This document explains what Istio is, how it fits into Kubernetes, and how it manages traffic, security, and observability.

## What is Istio?

**Istio** is a **service mesh**: an infrastructure layer that sits between your application services and the network. It gives you traffic management (routing, retries, timeouts), security (mTLS, authorization), and observability (metrics, tracing) without changing your application code.

```
Without Istio:  Pod A  ──────────────►  Pod B
                     (direct TCP/HTTP)

With Istio:     Pod A  ──► proxy ──► proxy ──►  Pod B
                     (sidecar)    (sidecar)
                     ↑                ↑
                     └── Control plane configures both
```

Your app still sends requests to `backend-service:5000`. Istio’s proxy (Envoy) runs next to each pod, intercepts traffic, and applies routing, retries, mTLS, and metrics. The control plane (Istiod) configures all proxies from a central place.

## Architecture: Control Plane and Data Plane

### Data plane: the proxies

- **Envoy proxy** runs as a **sidecar container** in every pod that has Istio injection enabled.
- All traffic to and from the app goes through this proxy (inbound and outbound).
- The proxy does: load balancing, retries, timeouts, mTLS, and reports metrics/traces to the control plane.

So the “data plane” is the set of all Envoy sidecars handling real traffic.

### Control plane: Istiod

- **Istiod** (single binary in recent Istio versions) runs in the cluster (e.g. `istio-system` namespace).
- It takes your configuration (VirtualServices, DestinationRules, PeerAuthentication, etc.) and converts it into **Envoy configuration**.
- It pushes that config to each Envoy sidecar (via xDS APIs).
- It also issues certificates for mTLS between proxies.

So the “control plane” is Istiod; the “data plane” is the Envoy sidecars.

```
┌─────────────────────────────────────────────────────────┐
│  Control plane (istio-system)                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Istiod                                         │    │
│  │  - Watches Kubernetes API (Services, Pods)      │    │
│  │  - Reads Istio config (VirtualService, etc.)   │    │
│  │  - Pushes config to Envoy sidecars (xDS)        │    │
│  │  - Issues certs for mTLS                        │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Pod (app)   │  │  Pod (app)   │  │  Pod (app)   │
│  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │
│  │  App   │  │  │  │  App   │  │  │  │  App   │  │
│  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │
│      │       │  │      │       │  │      │       │
│  ┌───▼────┐  │  │  ┌───▼────┐  │  │  ┌───▼────┐  │
│  │ Envoy  │  │  │  │ Envoy  │  │  │  │ Envoy  │  │
│  │sidecar │  │  │  │sidecar │  │  │  │sidecar │  │
│  └────────┘  │  │  └────────┘  │  │  └────────┘  │
└──────────────┘  └──────────────┘  └──────────────┘
       Data plane (all Envoy sidecars)
```

## How traffic flows with Istio

1. **Outbound:** App in Pod A calls `http://backend-service:5000/api/tasks`. The call goes to **localhost** (or the same pod); the Envoy sidecar in Pod A is configured to listen on the app’s outbound port and forwards to the backend-service.
2. **Envoy resolves** `backend-service` to the list of pod IPs (from Kubernetes), applies DestinationRule (e.g. subsets, load balancing, circuit breaker) and VirtualService (e.g. route to subset, retries).
3. **Request is sent** to a backend pod. It first hits the **Envoy sidecar** of Pod B (inbound), which can terminate mTLS and then forward to the app container on localhost.
4. **Response** goes back through the same path (app → sidecar → network → sidecar → app).

So every request passes through two Envoy proxies (caller’s and callee’s). The app code does not change; it still uses normal Kubernetes Service DNS and ports.

## Key Istio resources (used in this repo)

### 1. Enabling the mesh: sidecar injection

Pods get an Envoy sidecar only if they are in a namespace with **automatic injection** enabled:

```bash
kubectl label namespace default istio-injection=enabled
```

New pods in `default` will then get two containers: your app and `istio-proxy`. Existing pods need a restart (e.g. `kubectl rollout restart deployment/backend-deployment`).

### 2. Gateway

**Gateway** configures how traffic **enters** the mesh at the edge (e.g. Istio ingress gateway).
QUESTION: What do you mean at the edge? Do you mean inbound traffic into the cluster from the internet?
Yes, “edge” here means inbound traffic entering **the Kubernetes cluster** from outside—typically from the internet, a company intranet, or another network.

Here’s how it fits together:

- **Istio ingress gateway** (controlled via the Gateway resource) acts as the mesh’s entry point at the “edge” of the cluster.
- It is deployed as a special pod (commonly `istio-ingressgateway`) that has a public ClusterIP, NodePort, LoadBalancer, or Ingress IP.
- The Gateway resource configures *which ports/protocols/hosts* this gateway will listen for (e.g. HTTP port 80 for all hosts, as in the provided `gateway.yaml`).
- **External traffic** (from outside the cluster) first hits this ingress gateway pod on a NodePort or LoadBalancer IP.
- After entering through the gateway, Istio routes the request to internal services (via VirtualService rules).

**Summary:**  
“At the edge” means the traffic enters the Kubernetes cluster boundary—usually from outside the cluster (the internet or another network). The Istio ingress gateway (with its Gateway resource) is the managed entry point for such traffic.

QUESTION: How does this relate to the NodePort we configure in the frontend service file?
The NodePort that you configure in the frontend service file (`k8s/services/frontend-service.yaml`) allows traffic from *outside* the Kubernetes cluster to reach the frontend pod(s) by exposing a specific port on each node’s IP. In a standard setup (without Istio), you’d access the service using `<node IP>:<nodePort>` and traffic is sent directly to a frontend pod behind the service.

**When Istio is enabled and you use an Istio ingress gateway:**

- The **frontend NodePort** is not typically exposed directly to users anymore.
- Instead, *external* clients send requests to the **NodePort (or LoadBalancer IP) of the Istio ingress gateway**. This is configured by the Gateway resource.
- The Istio ingress gateway then receives the outside traffic and, using VirtualService routing, forwards it to internal services—such as your frontend-service—**inside the mesh**.

**So, in relation:**
- The NodePort in the frontend service allows old-style access (direct node port access), but with Istio, the standard approach is to expose the ingress gateway’s NodePort or LoadBalancer IP, and not access backend/frontend pod NodePorts directly.
- The Gateway resource and ingress gateway *replace* direct Service NodePort exposure for most use cases.
- The frontend Service still needs a ClusterIP or NodePort type for internal routing (so that the ingress gateway can forward traffic to it), but you do not need to access the frontend NodePort directly from outside the cluster.

**Summary Table:**

| Scenario          | How traffic enters | Typical use case with Istio |
|-------------------|-------------------|----------------------------|
| NodePort Service  | Node IP:NodePort  | Legacy, not recommended    |
| Istio Ingress GW  | Node IP:IGW Port / LB IP | Preferred; expose only gateway, route internally via Istio |

**Best practice:**  
*Expose only the ingress gateway; do not rely on individual service NodePorts for public traffic when using Istio. Internal Service types (ClusterIP/NodePort) just make the services discoverable and routable inside the cluster.*

This repo demonstrates both, but with Istio in place, you’d guide users to use only the ingress gateway’s endpoint for external access.



- In this repo: `k8s/istio/gateway.yaml` selects the pod with label `istio: ingressgateway` and exposes HTTP on port 80 for all hosts.
- The Gateway only defines “what port/protocol”; it does not define which internal service handles the request. That is done by a **VirtualService** bound to the Gateway.

### 3. VirtualService

**VirtualService** defines **routing rules** for one or more hosts (e.g. Kubernetes Service names).

- You can route by path, header, or other criteria.
- You can split traffic by weight (e.g. 90% v1, 10% v2).
- You can set retries, timeouts, and fault injection.

In this repo, `k8s/istio/virtualservice-backend.yaml`:

- For host `backend-service`: if header `x-canary: true` is present, send 100% of traffic to subset `v2`; otherwise 100% to subset `v1`.
- Subsets (v1, v2) are defined in a **DestinationRule**.

### 4. DestinationRule

**DestinationRule** defines **what happens after** routing: subsets (e.g. by version labels), load balancing policy, connection pool limits, and **circuit breaker** settings.

In this repo, `k8s/istio/destinationrule-backend.yaml`:

- Defines subset `v1` for pods with label `version: v1`.
- Sets connection pool limits (max connections, pending requests, etc.) and circuit breaker (eject after 3 consecutive errors, etc.).

So: **VirtualService** = “where to send traffic”; **DestinationRule** = “how to treat that destination (subsets, LB, resilience).”

## Security: mutual TLS (mTLS)

Istio can encrypt and authenticate traffic between pods:

- **Istiod** issues certificates to each Envoy sidecar.
- Envoy can enforce **strict mTLS**: only accept encrypted traffic from other Envoy proxies (and optionally verify identity).
- You configure this with **PeerAuthentication** (e.g. `strict` for a namespace). When enabled, app-to-app traffic is TLS-encrypted and authenticated without any changes in your app code.

## Observability

- **Metrics:** Envoy exposes metrics (request count, latency, etc.); Prometheus can scrape them. Istio also adds metrics and dashboards.
- **Tracing:** Istio can add trace headers and send spans to Jaeger/Zipkin so you see request flow across services.
- **Access logs:** Envoy can log every request; you can configure this via Telemetry / EnvoyFilter.

## How this repo uses Istio

| Resource              | File                          | Purpose |
|-----------------------|--------------------------------|---------|
| Namespace label       | `kubectl label namespace ...`  | Enable sidecar injection in `default`. |
| Gateway               | `k8s/istio/gateway.yaml`       | HTTP port 80 on Istio ingress gateway. |
| VirtualService        | `k8s/istio/virtualservice-backend.yaml` | Route to backend; canary by `x-canary: true` to subset v2. |
| DestinationRule       | `k8s/istio/destinationrule-backend.yaml` | Subset v1, connection pool, circuit breaker. |

After applying `k8s/istio/` and having injection enabled, you can use the Istio ingress gateway (e.g. `kubectl port-forward -n istio-system svc/istio-ingressgateway 8080:80`) and hit your app through the mesh. Traffic to `backend-service` from other pods will go through Envoy and respect VirtualService and DestinationRule.

## Quick reference

- **Install (e.g. Minikube):** `istioctl install --set profile=default -y`
- **Enable injection:** `kubectl label namespace default istio-injection=enabled`
- **Check sidecars:** `kubectl get pods` — pods should show 2/2 containers (app + istio-proxy)
- **Check proxy config:** `istioctl proxy-status` or `istioctl proxy-config clusters <pod-name>`

## References

- [Istio Documentation](https://istio.io/latest/docs/)
- [Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
- [Security](https://istio.io/latest/docs/concepts/security/)


QUESTION: I'm confused as to why the istio destination rule points to the backend service right now instead of the frontend service

The Istio DestinationRule in this setup points to the `backend-service` (and not the frontend service) because it is intended to control the traffic policy and resilience settings (like subsets, connection pooling, and circuit breakers) *for the backend service specifically*. 

A DestinationRule is always applied to the **destination** of traffic (i.e., the service being called)—not the origin or the client. In this repo, traffic is routed to the backend via the VirtualService, so the DestinationRule ensures that all requests hitting `backend-service` have the configured load balancing and circuit breaking policies applied.
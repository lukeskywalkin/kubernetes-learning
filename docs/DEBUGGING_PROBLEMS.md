# Debugging Problems

Problems to introduce one by one. Each problem breaks something specific. Your job: find it and fix it.

**How to use**: We'll introduce one problem at a time. You diagnose (using `kubectl get`, `kubectl describe`, `kubectl logs`, etc.) and fix it. Then we move to the next.

---

## Problem 1: Wrong Redis Host

**What we break**: Backend can't connect to Redis.

**Symptom**: Backend pods may fail readiness probe, or API returns 503.

**Fix**: Correct the `redis_host` value in ConfigMap `backend-config`.

---

## Problem 2: Missing Environment Variable

**What we break**: Backend doesn't know where Redis is.

**Symptom**: Backend logs show connection to localhost or wrong host.

**Fix**: Restore the REDIS_HOST environment variable in backend-deployment.

---

## Problem 3: Service Port Mismatch

**What we break**: Backend service points to wrong container port.

**Symptom**: curl to backend-service times out or connection refused.

**Fix**: Align Service's targetPort with container's containerPort.

---

## Problem 4: Wrong Service Selector

**What we break**: Backend service has no endpoints (can't find pods).

**Symptom**: `kubectl get endpoints backend-service` shows empty or no addresses.

**Fix**: Change Service selector to match pod labels (app: backend).

---

## Problem 5: Broken ConfigMap Mount

**What we break**: Frontend can't serve HTML (wrong path or missing key).

**Symptom**: Frontend returns 404 or blank page.

**Fix**: Correct the ConfigMap volume mount path or ConfigMap key name.

---

## Problem 6: Readiness Probe Too Strict

**What we break**: Backend never becomes "Ready" (probe fails).

**Symptom**: Pods stuck in 0/1 Ready, never receive traffic.

**Fix**: Adjust readiness probe (path, port, or timing).

---

## Problem 7: Replicas Scaled to Zero

**What we break**: No backend pods running.

**Symptom**: Backend service has no endpoints, API unreachable.

**Fix**: Scale deployment back up.

---

## Problem 8: Logger URL Wrong

**What we break**: Backend can't send logs to logger (wrong URL).

**Symptom**: Logger receives no logs; backend may log connection errors.

**Fix**: Correct LOGGER_SERVICE_URL in backend deployment.

---

## Problem 9: RBAC Permission Missing

**What we break**: Backend can't read its ConfigMap (if we add code that does).

**Symptom**: Backend fails to start or logs "Forbidden" when accessing API.

**Fix**: Add ConfigMap get permission to backend Role.

---

## Problem 10: Image Pull Fails

**What we break**: Use wrong image name or one that doesn't exist.

**Symptom**: Pods in ImagePullBackOff or ErrImagePull.

**Fix**: Correct image name or build/push the image.

---

## Diagnostic Commands Reference

When something's broken, run these:

```bash
kubectl get pods
kubectl get pods -o wide
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl logs <pod-name> --previous
kubectl get events --sort-by='.lastTimestamp'
kubectl get endpoints
kubectl describe service <service-name>
kubectl describe configmap <configmap-name>
kubectl get configmap
```

Ready to start? Say when you've gone through the walkthrough and we'll introduce Problem 1.

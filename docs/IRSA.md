# Understanding IRSA (IAM Roles for Service Accounts)

## What is IRSA?

**IRSA (IAM Roles for Service Accounts)** is an AWS EKS feature that allows Kubernetes service accounts to assume IAM roles. This enables pods to access AWS services (S3, DynamoDB, etc.) without hardcoding credentials.

## IRSA Concept (AWS EKS)

In AWS EKS, IRSA works like this:

```
Pod → Service Account → IAM Role → AWS Services
```

**Key Components**:
1. **Service Account**: Kubernetes service account with IAM role annotation
2. **IAM Role**: AWS IAM role with necessary permissions
3. **OIDC Provider**: Connects Kubernetes service accounts to IAM roles
4. **Token Mounting**: Pod receives AWS credentials via mounted token

### IRSA in AWS EKS

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend-service-account
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/backend-role
```

When a pod uses this service account:
1. AWS SDK in the pod reads the mounted token
2. AWS SDK assumes the IAM role
3. Pod can access AWS services (S3, DynamoDB, etc.)

## IRSA Patterns in This Repository

Since we're using Minikube (not AWS EKS), we demonstrate IRSA **patterns** and **concepts**:

### 1. Service Accounts

Service accounts are created for each service:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend-service-account
  annotations:
    # In AWS EKS, this would be the IAM role ARN
    # eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/backend-role
    description: "Service account for backend service (IRSA pattern)"
```

**Learning**: Service accounts are the foundation of IRSA.

### 2. RBAC (Role-Based Access Control)

Service accounts are bound to Kubernetes roles:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: backend-role
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["backend-config"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: backend-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: backend-role
subjects:
- kind: ServiceAccount
  name: backend-service-account
  namespace: default
```

**Learning**: RBAC controls what service accounts can access in Kubernetes (similar to how IRSA controls AWS access).

### 3. Pod Assignment

Pods use service accounts:

```yaml
spec:
  serviceAccountName: backend-service-account
  containers:
  - name: backend
    # ...
```

**Learning**: Pods reference service accounts, which determine their permissions.

## IRSA Concepts Explained

### Least Privilege

**IRSA Pattern**: Each service account should have **minimal required permissions**.

**In Our Repo**: RBAC roles grant only necessary permissions:
- Backend can read `backend-config` ConfigMap
- Logger can read `logger-config` ConfigMap
- Neither can modify secrets or delete pods

### Token Mounting

**IRSA Pattern**: Tokens are automatically mounted at `/var/run/secrets/eks.amazonaws.com/serviceaccount/token.json`

**In Our Repo**: Service account tokens are mounted at `/var/run/secrets/kubernetes.io/serviceaccount/token`

You can verify:

```bash
# Get a pod using the service account
kubectl exec -it <pod-name> -- ls /var/run/secrets/kubernetes.io/serviceaccount/

# View the token (it's a JWT)
kubectl exec -it <pod-name> -- cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

### Separation of Concerns

**IRSA Pattern**: Each service has its own IAM role with specific permissions.

**In Our Repo**: Each service has its own service account with specific RBAC permissions:
- `backend-service-account`: Can read backend ConfigMap
- `logger-service-account`: Can read logger ConfigMap
- Different permissions for different services

## Real-World IRSA Usage (AWS EKS)

### Example: Accessing S3

```yaml
# Service account with IAM role
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-service-account
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/s3-reader-role
---
# Pod using the service account
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: s3-access-service-account
  containers:
  - name: app
    image: my-app:latest
    # App can now access S3 using AWS SDK
    # No credentials needed!
```

The AWS SDK automatically discovers and uses the IAM role credentials.

### IAM Role Trust Policy (AWS)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B716D3041E"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B716D3041E:sub": "system:serviceaccount:default:s3-access-service-account",
          "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B716D3041E:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

This trust policy allows the Kubernetes service account to assume the IAM role.

## IRSA vs. Traditional Methods

### Without IRSA (Old Way)

```yaml
# BAD: Hardcoded credentials
env:
- name: AWS_ACCESS_KEY_ID
  value: "AKIAIOSFODNN7EXAMPLE"
- name: AWS_SECRET_ACCESS_KEY
  value: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**Problems**:
- Credentials in manifests (security risk)
- Hard to rotate credentials
- Same credentials for all pods
- Cannot audit who used what credentials

### With IRSA (Best Practice)

```yaml
# GOOD: Service account with IAM role
spec:
  serviceAccountName: s3-access-service-account
```

**Benefits**:
- No hardcoded credentials
- Automatic credential rotation
- Per-service IAM roles
- Audit trail via CloudTrail

## Learning Exercises

### Exercise 1: Understand Service Account Tokens

```bash
# Check service account token mount
kubectl exec -it $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- \
  ls -la /var/run/secrets/kubernetes.io/serviceaccount/

# View token
kubectl exec -it $(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- \
  cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

### Exercise 2: Test RBAC Permissions

```bash
# Test what backend service account can do
kubectl auth can-i get configmaps --as=system:serviceaccount:default:backend-service-account

# Try accessing something not allowed
kubectl auth can-i delete pods --as=system:serviceaccount:default:backend-service-account
```

### Exercise 3: Verify Service Account Usage

```bash
# Check which service account a pod is using
kubectl get pod <pod-name> -o jsonpath='{.spec.serviceAccountName}'

# List all service accounts
kubectl get serviceaccounts

# Describe service account
kubectl describe serviceaccount backend-service-account
```

## Key Takeaways

1. **Service Accounts**: Foundation of IRSA - identify pods
2. **RBAC**: Controls Kubernetes permissions (similar to IAM for AWS)
3. **Least Privilege**: Each service gets minimal required permissions
4. **Token Mounting**: Automatic credential injection
5. **Separation**: Each service has its own account/permissions
6. **Security**: No hardcoded credentials

## IRSA Interview Topics

### Common Questions

1. **What is IRSA?**
   - IAM Roles for Service Accounts
   - Allows pods to assume IAM roles in AWS EKS
   - Eliminates need for hardcoded credentials

2. **How does IRSA work?**
   - Service account annotated with IAM role ARN
   - OIDC provider links Kubernetes to AWS
   - Token mounted in pod at specific path
   - AWS SDK automatically discovers and uses token

3. **What are the benefits?**
   - No hardcoded credentials
   - Automatic credential rotation
   - Per-service permissions
   - Audit trail

4. **How do you implement IRSA?**
   - Create IAM role with trust policy
   - Annotate service account with role ARN
   - Assign service account to pods
   - IAM role needs proper permissions

5. **What's the difference between IRSA and instance profiles?**
   - IRSA: Per-pod IAM roles (granular)
   - Instance profiles: Per-node IAM roles (coarse-grained)
   - IRSA is more secure and flexible

## Further Reading

- [AWS EKS IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Kubernetes Service Accounts](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

Understanding IRSA patterns prepares you for AWS EKS environments and demonstrates security best practices in Kubernetes!

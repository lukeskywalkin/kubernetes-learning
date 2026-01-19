.PHONY: help build deploy clean status logs

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	@echo "Building Docker images..."
	@./scripts/build-images.sh

deploy: ## Deploy application to Kubernetes
	@echo "Deploying application..."
	@./scripts/deploy.sh

clean: ## Remove all Kubernetes resources
	@echo "Cleaning up resources..."
	@kubectl delete -f k8s/ --ignore-not-found=true
	@echo "Cleanup complete!"

status: ## Show deployment status
	@echo "=== Pods ==="
	@kubectl get pods
	@echo ""
	@echo "=== Services ==="
	@kubectl get services
	@echo ""
	@echo "=== Deployments ==="
	@kubectl get deployments

logs-backend: ## View backend logs
	@kubectl logs -l app=backend --tail=50 -f

logs-frontend: ## View frontend logs
	@kubectl logs -l app=frontend --tail=50 -f

logs-logger: ## View logger logs
	@kubectl logs -l app=logger --tail=50 -f

logs-redis: ## View Redis logs
	@kubectl logs -l app=redis --tail=50 -f

shell-backend: ## Get shell in backend pod
	@kubectl exec -it $$(kubectl get pod -l app=backend -o jsonpath='{.items[0].metadata.name}') -- /bin/sh

shell-redis: ## Get shell in Redis pod
	@kubectl exec -it $$(kubectl get pod -l app=redis -o jsonpath='{.items[0].metadata.name}') -- /bin/sh

url: ## Get frontend service URL
	@minikube service frontend-service --url

all: build deploy ## Build and deploy everything

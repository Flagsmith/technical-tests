# Flagsmith Interview Challenge

## Your Task
Debug and fix the broken Flagsmith deployment in this Kubernetes cluster.

**Important:** This is a production environment scenario. You must diagnose and fix the issue using kubectl and standard debugging techniques. Redeploying the entire application from scratch is not an option.

## Available Tools
- `kubectl` - Kubernetes CLI
- `helm` - Helm package manager
- `curl` - HTTP testing
- Standard Unix tools (grep, awk, sed, etc.)

## Quick Start Commands
```bash
# Check overall status
kubectl get pods -n flagsmith
kubectl get svc -n flagsmith

# View pod logs
kubectl logs <pod-name> -n flagsmith

# Check health endpoint
kubectl port-forward svc/flagsmith-api 8000:8000 -n flagsmith
curl http://localhost:8000/health/liveness/

# Manual exploration
kubectl get pods -n flagsmith
kubectl describe pod <pod-name> -n flagsmith
helm list -A
```

## Key Files
- `~/challenge-guide.md` - This guide (you're reading it now)
- `~/kubectl-cheatsheet.md` - Kubernetes debugging commands reference

## Success Criteria
The Flagsmith API should respond with HTTP 200 on the `/health/liveness/` endpoint.

Good luck! 🚀

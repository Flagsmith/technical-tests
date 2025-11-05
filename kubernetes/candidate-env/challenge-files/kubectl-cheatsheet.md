# Kubernetes Debugging Cheatsheet

## Pod Investigation
```bash
kubectl get pods -n flagsmith                    # List pods
kubectl describe pod <name> -n flagsmith        # Pod details
kubectl logs <name> -n flagsmith                 # Current logs
kubectl logs <name> -n flagsmith --previous      # Previous container logs
kubectl logs <name> -n flagsmith --tail=50       # Last 50 lines
kubectl exec -it <name> -n flagsmith -- /bin/sh # Shell into pod
```

## Service & Networking
```bash
kubectl get svc -n flagsmith                     # List services
kubectl describe svc <name> -n flagsmith        # Service details
kubectl get endpoints -n flagsmith              # Service endpoints
kubectl port-forward svc/<name> 8080:8000 -n flagsmith  # Port forward
```

## Helm Operations
```bash
helm list -A                              # All releases
helm status flagsmith -n flagsmith        # Release status
helm get values flagsmith -n flagsmith    # Current values
helm get manifest flagsmith -n flagsmith  # Generated manifests
```

## Resource Investigation
```bash
kubectl get events -n flagsmith --sort-by='.lastTimestamp'  # Recent events
kubectl top pods -n flagsmith                   # Resource usage
kubectl get pvc -n flagsmith                    # Persistent volumes
kubectl get configmaps -n flagsmith             # Config maps
kubectl get secrets -n flagsmith                # Secrets
```

## Troubleshooting Common Issues
```bash
# Check resource limits
kubectl describe pod <name> -n flagsmith | grep -A 5 "Limits\|Requests"

# Check if image can be pulled
kubectl describe pod <name> -n flagsmith | grep -A 5 "Events"

# Check service selector matches pod labels
kubectl get pods -n flagsmith --show-labels
kubectl describe svc <name> -n flagsmith

# Test connectivity between pods
kubectl run debug --image=busybox --rm -it --restart=Never -- nslookup <service>.<namespace>
```

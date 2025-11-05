# Challenge 002: Resource Configuration Issue - Solution

## Problem Description
The Flagsmith API pods are failing to start due to insufficient memory resources. There's a misconfiguration in the resource limits that causes pods to be killed by the OOMKiller during startup.

## Step-by-Step Solution

### Step 1: Identify the Problem
Check the overall pod status to see what's broken:
```bash
kubectl get pods -n flagsmith
```

You should see the API pod in `CrashLoopBackOff` or `OOMKilled` status.

### Step 2: Examine Pod Events and Status
Get detailed information about why the pod is failing:
```bash
# Get the failing pod name
BROKEN_POD=$(kubectl get pods -n flagsmith | grep -E "(CrashLoop|OOMKilled|Error)" | awk '{print $1}')

# Check pod events
kubectl describe pod $BROKEN_POD -n flagsmith | grep -A 10 'Events:'
```

**Key Error Messages to Look For:**
- `OOMKilled` status
- `Last State: Terminated (Reason: OOMKilled)`
- Memory limit exceeded events

### Step 3: Check Resource Configuration
Examine the deployment's resource configuration:
```bash
kubectl describe deployment flagsmith-api -n flagsmith | grep -A 10 'Limits:'
```

Or get the full resource configuration:
```bash
kubectl get deployment flagsmith-api -n flagsmith -o yaml | grep -A 10 'resources:'
```

You'll find the memory limit is set too low:
```yaml
resources:
  limits:
    cpu: 500m
    memory: "64Mi"  # This is too low!
  requests:
    cpu: 300m
    memory: "32Mi"  # Request too low for startup
```

### Step 4: Identify the Root Cause
The issue is that:
1. Memory limit (64Mi) is extremely low for a Django application
2. Memory request (32Mi) is too low for startup - the pod can be scheduled but will immediately crash
3. Flagsmith API typically needs at least 256Mi-512Mi to start properly

### Step 5: Apply the Fix
Edit the deployment to fix the memory configuration:

```bash
kubectl edit deployment flagsmith-api -n flagsmith
```

This opens the deployment YAML in your editor. Find the `resources:` section under `spec.template.spec.containers[0]` and update it:

```yaml
resources:
  limits:
    cpu: 500m
    memory: "512Mi"    # Increase from 64Mi
  requests:
    cpu: 300m
    memory: "256Mi"    # Reduce from 300Mi to be less than limit
```

Save and exit the editor.

**Alternative: Remove resource limits entirely** (for development):
Delete the entire `resources:` section in the editor.

### Step 6: Verify the Fix
Wait for the deployment to roll out:
```bash
kubectl rollout status deployment/flagsmith-api -n flagsmith --timeout=120s
```

Check that all pods are running and ready:
```bash
kubectl get pods -n flagsmith
```

Monitor resource usage to ensure it's within acceptable limits:
```bash
kubectl top pods -n flagsmith
```

Test the health endpoint:
```bash
kubectl port-forward svc/flagsmith-api 8080:8000 -n flagsmith &
curl http://localhost:8080/health/liveness/
kill %1
```

Expected response: `{"status": "ok"}`

## Key Learning Points

1. **Resource Limits vs Requests**: 
   - Requests: Guaranteed resources Kubernetes will allocate
   - Limits: Maximum resources the container can use
   - Limits must be >= requests

2. **OOMKiller Behavior**: When a container exceeds its memory limit, the Linux OOMKiller terminates it with status `OOMKilled`.

3. **Sizing Guidelines for Django Apps**:
   - Minimum: 256Mi memory
   - Recommended: 512Mi-1Gi for production
   - Monitor actual usage and adjust accordingly

4. **Debugging Memory Issues**:
   - Check pod events for OOMKilled messages
   - Use `kubectl top pods` to monitor actual usage
   - Look at historical resource usage patterns

## Prevention

- **Capacity Planning**: Profile your application's memory usage under load
- **Monitoring**: Set up alerts for high memory usage (>80% of limits)
- **Testing**: Test resource changes in development first
- **Resource Quotas**: Use namespace resource quotas to prevent resource exhaustion
- **Horizontal Pod Autoscaling**: Scale pods based on resource utilization rather than just increasing limits

## Additional Commands for Investigation

Check cluster resource availability:
```bash
kubectl describe nodes | grep -A 5 "Allocated resources"
```

View resource usage across all pods:
```bash
kubectl top pods -A --sort-by=memory
```

Check if there are resource quotas limiting the namespace:
```bash
kubectl describe resourcequota -n flagsmith
```

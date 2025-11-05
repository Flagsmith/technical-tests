# Challenge 004: Performance Degradation Issue - Solution

## Problem Description
The Flagsmith API is experiencing severe performance issues with response times over 10 seconds. There are resource constraints and a CPU-intensive sidecar container consuming system resources unnecessarily.

## Step-by-Step Solution

### Step 1: Identify the Problem
Check the overall pod status and resource usage:
```bash
kubectl get pods -n flagsmith
kubectl top pods -n flagsmith
```

You should see high CPU usage on the API pods and potentially slow response times.

### Step 2: Examine Pod Resource Usage
Get detailed resource information:
```bash
# Check current resource limits and requests
kubectl describe pod <api-pod-name> -n flagsmith | grep -A 10 'Limits:\|Requests:'

# Monitor real-time resource usage
kubectl top pods -n flagsmith --containers
```

**Key Issues to Look For:**
- Very low CPU limits (100m) for the main application
- High CPU usage approaching or exceeding limits
- Additional containers consuming resources unnecessarily

### Step 3: Investigate Container Configuration
Examine the deployment configuration:
```bash
kubectl get deployment flagsmith-api -n flagsmith -o yaml | grep -A 20 'containers:'
```

You'll discover:
1. **Insufficient CPU limits**: 100m CPU limit is too low for a web application under load
2. **CPU-intensive sidecar**: A "cpu-hog" container running unnecessary CPU-intensive operations
3. **No horizontal scaling**: Single replica handling all traffic

### Step 4: Identify the Root Causes
The performance issues are caused by:
1. **Resource starvation**: CPU limits too restrictive for application needs
2. **Resource competition**: Sidecar container consuming available CPU
3. **Lack of scaling**: Single pod handling all requests without autoscaling

### Step 5: Apply the Fixes

**Fix 1: Edit the deployment to remove the sidecar and fix resources**
```bash
kubectl edit deployment flagsmith-api -n flagsmith
```

This opens the deployment YAML. You'll see two containers in the `containers:` section:

1. The main `flagsmith-api` container (first)
2. A `cpu-hog` container (second) - **delete this entire container block**

In the main container's `resources:` section, update:
```yaml
resources:
  limits:
    cpu: 500m        # Increase from 100m
    memory: "256Mi"
  requests:
    cpu: 250m        # Increase from 50m  
    memory: "128Mi"
```

Save and exit the editor.

**Fix 3: Scale up replicas for better load distribution**
```bash
kubectl scale deployment flagsmith-api -n flagsmith --replicas=2
```

### Step 6: Verify the Fix
Wait for the deployment to roll out and test performance:
```bash
# Wait for rollout to complete
kubectl rollout status deployment/flagsmith-api -n flagsmith --timeout=120s

# Check resource usage after fix
kubectl top pods -n flagsmith

# Test response time
kubectl port-forward svc/flagsmith-api 8080:8000 -n flagsmith &
time curl http://localhost:8080/health/liveness/
kill %1
```

Expected results:
- Response time should drop to under 1 second
- CPU usage should be more reasonable and stable
- Multiple pods should be handling traffic

### Step 7: Monitor Stability
```bash
# Watch pods for stability
kubectl get pods -n flagsmith -w

# Monitor resource usage over time
watch kubectl top pods -n flagsmith
```

## Key Learning Points

1. **Resource Right-sizing**: Web applications typically need 250m-1000m CPU for reasonable performance
2. **Container Efficiency**: Remove unnecessary sidecar containers that consume resources without adding value
3. **Horizontal Scaling**: Multiple replicas distribute load and improve resilience
4. **Performance Monitoring**: Use `kubectl top` to identify resource bottlenecks
5. **Systematic Approach**: Check resource usage before making assumptions about performance issues

## Prevention

- **Resource Planning**: Profile applications under expected load to set appropriate limits
- **Monitoring**: Set up alerts for high resource utilization (>80% of limits)
- **Horizontal Pod Autoscaling**: Configure HPA to automatically scale based on CPU/memory usage
- **Load Testing**: Regular performance testing to identify bottlenecks before they reach production
- **Resource Reviews**: Periodic review of resource allocation vs. actual usage

## Production Considerations

- **Gradual Scaling**: In production, scale replicas gradually and monitor impact
- **Resource Quotas**: Ensure namespace has sufficient CPU/memory quotas for increased allocation
- **Monitoring Integration**: Set up proper APM tools for ongoing performance monitoring
- **SLA Impact**: Document how resource changes affect application SLAs
- **Change Management**: Test resource changes carefully and monitor impact

## Additional Debugging Commands

Check cluster resource availability:
```bash
kubectl describe nodes | grep -A 5 "Allocated resources"
```

View historical resource usage (if metrics-server is available):
```bash
kubectl top pods -n flagsmith --sort-by=cpu
kubectl top nodes
```

Test application performance:
```bash
# Simple load test
for i in {1..10}; do curl -w "%{time_total}s\n" -o /dev/null -s http://localhost:8080/health/liveness/; done
```

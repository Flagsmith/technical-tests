# Challenge 006: Network Connectivity Issue - Solution

## Problem Description
The Flagsmith API cannot connect to the PostgreSQL database due to network configuration problems. DNS resolution is failing because of incorrect service names and broken service selectors that prevent proper endpoint discovery.

## Step-by-Step Solution

### Step 1: Identify the Problem
Check the overall pod status to see what's broken:
```bash
kubectl get pods -n flagsmith
```

You should see API pods in `CrashLoopBackOff` or `Init:CrashLoopBackOff` status while the PostgreSQL pod is running fine.

### Step 2: Examine Connection Errors
Get the logs from the failing pod to understand the error:
```bash
# Get the failing pod name
BROKEN_POD=$(kubectl get pods -n flagsmith | grep -E "(CrashLoop|Init)" | awk '{print $1}')

# Check init container logs for database connection errors
kubectl logs $BROKEN_POD -n flagsmith -c migrate-db --tail=20
```

**Key Error Messages:**
```
could not translate host name "flagsmith-postgresql" to address: Name or service not known
connection to server at "flagsmith-postgresql" (x.x.x.x), port 5432 failed: Connection timed out
```

### Step 3: Investigate DNS and Service Configuration
Check if the database service exists and is properly configured:
```bash
# Check all services in the namespace
kubectl get svc -n flagsmith

# Check if the service the app is trying to connect to exists
kubectl get svc flagsmith-postgresql -n flagsmith 2>/dev/null || echo "Service not found"

# Check the correct service name
kubectl get svc -n flagsmith | grep postgresql
```

You'll discover:
1. The app is trying to connect to `flagsmith-postgresql`
2. But the actual service is named `flagsmith-dev-postgresql`
3. The service selector may be broken

### Step 4: Check Service Endpoints
Verify if the service has healthy endpoints:
```bash
# Check the correct service
kubectl describe svc flagsmith-dev-postgresql -n flagsmith

# Check service endpoints
kubectl get endpoints flagsmith-dev-postgresql -n flagsmith

# Check what the service selector is looking for vs what pods have
kubectl get pods -n flagsmith --show-labels | grep postgresql
```

**Key Issues to Look For:**
- Service selector doesn't match pod labels
- No endpoints listed for the service
- Incorrect service name in DATABASE_URL

### Step 5: Identify the Root Causes
The network issues are caused by:
1. **Wrong service name**: DATABASE_URL references `flagsmith-postgresql` instead of `flagsmith-dev-postgresql`
2. **Broken service selector**: Service selector has wrong label value preventing endpoint discovery
3. **DNS configuration**: Aggressive DNS timeout settings causing premature failures

### Step 6: Apply the Fixes

**Fix 1: Fix the PostgreSQL service selector**
```bash
kubectl edit svc flagsmith-dev-postgresql -n flagsmith
```

This opens the service YAML in your editor. Find the `selector:` section and fix the broken label:

```yaml
selector:
  app.kubernetes.io/name: postgresql-wrong  # Change this
```

Change `postgresql-wrong` to `postgresql` to match the actual pod labels.

**Fix 2: Remove the incorrect DATABASE_URL override**
```bash
kubectl edit deployment flagsmith-api -n flagsmith
```

This opens the deployment YAML. Find the `env:` section under `spec.template.spec.containers[0]` and look for the hardcoded DATABASE_URL at the bottom:

```yaml
- name: DATABASE_URL
  value: postgresql://postgres:flagsmith@flagsmith-postgresql:5432/flagsmith
```

Delete these two lines entirely. Also remove any `dnsConfig:` section if present.

Save and exit the editor for both files.

### Step 7: Verify Service Connectivity
Check that the service now has proper endpoints:
```bash
# Verify service endpoints are populated
kubectl get endpoints flagsmith-dev-postgresql -n flagsmith

# Test DNS resolution from a pod
kubectl run dns-test --image=busybox --rm -it --restart=Never -n flagsmith -- nslookup flagsmith-dev-postgresql

# Test connectivity to the database
kubectl run netcat-test --image=busybox --rm -it --restart=Never -n flagsmith -- nc -zv flagsmith-dev-postgresql 5432
```

### Step 8: Verify the Fix
Wait for the deployment to roll out and test connectivity:
```bash
# Wait for rollout to complete
kubectl rollout status deployment/flagsmith-api -n flagsmith --timeout=120s

# Check that all pods are running
kubectl get pods -n flagsmith

# Test the health endpoint
kubectl port-forward svc/flagsmith-api 8080:8000 -n flagsmith &
curl http://localhost:8080/health/liveness/
kill %1
```

Expected response: `{"status": "ok"}`

### Step 9: Test End-to-End Connectivity
Verify database connectivity is working:
```bash
# Check that the API can connect to the database
API_POD=$(kubectl get pods -n flagsmith -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}')

# Test database connection from the API pod
kubectl exec -it $API_POD -n flagsmith -- python manage.py dbshell --command="SELECT 1;"
```

## Key Learning Points

1. **Service Discovery**: Kubernetes uses DNS for service discovery - service names must match exactly
2. **Service Selectors**: Services must have correct selectors to discover and route to pods
3. **DNS Debugging**: Use `nslookup` and `dig` to debug DNS resolution issues
4. **Network Connectivity**: Test both DNS resolution AND actual connectivity (ports, firewalls, etc.)
5. **Endpoint Verification**: Always check service endpoints to ensure pods are being discovered

## Common Network Issues in Kubernetes

- **Wrong service names**: Typos in service names cause DNS resolution failures
- **Broken selectors**: Service selectors that don't match pod labels result in no endpoints
- **Namespace issues**: Services in different namespaces require FQDN (service.namespace.svc.cluster.local)
- **Port mismatches**: Service ports don't match container ports
- **Network policies**: Restrictive network policies blocking traffic

## Prevention

- **Service Validation**: Always verify service selectors match pod labels
- **DNS Testing**: Test service DNS resolution during deployment
- **Connectivity Monitoring**: Monitor service endpoint health and connectivity
- **Network Policies**: Document and test network policy impacts
- **Service Mesh**: Consider using service mesh for advanced traffic management and observability

## Production Considerations

- **Testing**: Test network changes in staging before production
- **Monitoring**: Set up alerts for DNS resolution failures and connection timeouts
- **Circuit Breakers**: Implement connection retry logic with backoff
- **Network Observability**: Use tools like Istio or Linkerd for network insights
- **Disaster Recovery**: Document network dependencies for incident response

## Additional Debugging Commands

Test service connectivity from different contexts:
```bash
# Test from within the cluster
kubectl run debug-pod --image=busybox --rm -it --restart=Never -n flagsmith

# Check service discovery across namespaces
kubectl get svc --all-namespaces | grep postgresql

# Test basic connectivity
kubectl run test-pod --image=busybox --rm -it --restart=Never -n flagsmith -- ping flagsmith-dev-postgresql
```

Check DNS configuration:
```bash
# View DNS configuration in pods
kubectl exec -it <pod-name> -n flagsmith -- cat /etc/resolv.conf

# Test different DNS queries
kubectl run dns-debug --image=busybox --rm -it --restart=Never -n flagsmith -- nslookup flagsmith-dev-postgresql
```

Debug service mesh issues (if applicable):
```bash
# Check for service mesh sidecars
kubectl get pods -n flagsmith -o jsonpath='{.items[*].spec.containers[*].name}'

# Check network policies
kubectl get networkpolicies -n flagsmith
kubectl describe networkpolicy <policy-name> -n flagsmith
```

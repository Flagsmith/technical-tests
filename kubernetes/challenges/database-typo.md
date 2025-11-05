# Challenge 001: Database Connection Issue - Solution

## Problem Description
The Flagsmith API pods are crashing with database connection errors. There's a subtle typo in the PostgreSQL service name that prevents the API from connecting to the database.

## Step-by-Step Solution

### Step 1: Identify the Problem
Check the overall pod status to see what's broken:
```bash
kubectl get pods -n flagsmith
```

You should see a new API pod in `CrashLoopBackOff` or `Error` status, while an older pod may still be running.

### Step 2: Examine Pod Logs
Get the logs from the failing pod to understand the error:
```bash
# Get the failing pod name (look for CrashLoopBackOff or Error status)
BROKEN_POD=$(kubectl get pods -n flagsmith | grep -E 'CrashLoop|Error' | awk '{print $1}')

# Check the logs
kubectl logs $BROKEN_POD -n flagsmith --tail=20
```

**Key Error Message:**
```
OperationalError: could not translate host name "dev-postgresl" to address: Name or service not known
```

### Step 3: Investigate the Configuration
Check the deployment configuration to find the source of the wrong hostname:
```bash
kubectl describe pod $BROKEN_POD -n flagsmith | grep -A 20 'Environment:'
```

Look for the `DATABASE_URL` environment variable. You'll find it set to a hardcoded value with a typo:
```
DATABASE_URL: postgresql://postgres:flagsmith@dev-postgresl:5432/flagsmith
```

This hardcoded value overrides the correct DATABASE_URL that would normally come from a secret, and contains the typo `dev-postgresl` instead of `dev-postgresql`.

### Step 4: Identify the Root Cause
The hostname `dev-postgresl` is missing the letter 'q' - it should be `dev-postgresql`.

Verify the correct service name exists:
```bash
kubectl get services -n flagsmith | grep postgresql
```

You should see `flagsmith-dev-postgresql`.

### Step 5: Apply the Fix
Open the deployment in an editor to remove the incorrect environment variable:

```bash
kubectl edit deployment flagsmith-api -n flagsmith
```

This will open the deployment configuration in your default editor. Look for the `env:` section under `spec.template.spec.containers[0]` and find the hardcoded `DATABASE_URL` environment variable at the bottom of the list:

```yaml
- name: DATABASE_URL
  value: postgresql://postgres:flagsmith@dev-postgresl:5432/flagsmith
```

Delete these two lines entirely, then save and exit the editor. This removes the hardcoded DATABASE_URL that overrides the correct one from the secret.



### Step 6: Verify the Fix
Wait for the deployment to roll out:
```bash
kubectl rollout status deployment/flagsmith-api -n flagsmith --timeout=120s
```

Check that all pods are running:
```bash
kubectl get pods -n flagsmith
```

Test the health endpoint:
```bash
kubectl port-forward svc/flagsmith-api 8080:8000 -n flagsmith &
curl http://localhost:8080/health/liveness/
kill %1
```

Expected response: `{"status": "ok"}`



## Key Learning Points

1. **DNS Resolution Errors**: When you see "could not translate host name" errors, it usually means a typo in service names or the service doesn't exist.

2. **Environment Variable Priority**: Later environment variables can override earlier ones. The broken `DATABASE_URL` was added after the correct one from the secret, causing the application to use the incorrect value.

3. **Service Discovery**: Kubernetes services are accessible via DNS using the format `<service-name>.<namespace>.svc.cluster.local` or just `<service-name>` within the same namespace.

4. **Debugging Strategy**: Always start with pod logs, then examine configuration, and verify the resources that the application is trying to connect to actually exist.

5. **JSON Patch Operations**: The `kubectl patch` command with `--type json` allows precise modifications using operations like `add`, `remove`, and `replace` on specific paths in the resource structure.

## Prevention
- Use proper naming conventions and double-check service names
- Validate connectivity between services before deployment
- Use health checks and monitoring to catch issues early
- Consider using tools like `nslookup` or `dig` from within pods to test DNS resolution

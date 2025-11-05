#!/bin/bash
# This script runs as root initially to do system setup, then switches to candidate user
set -e

echo "🚀 Starting Flagsmith Interview Challenge System..."

# ==============================================================================
# ROOT SETUP - Runtime system configuration
# ==============================================================================

echo "📁 Setting up tmate info directory..."
mkdir -p /tmp/tmate-info
chown candidate:candidate /tmp/tmate-info

echo "🔧 Setting up kubeconfig..."

# Setup kubectl config for candidate user
mkdir -p /home/candidate/.kube

# Find and copy kubeconfig
if [ -f "/home/candidate/.kube-shared/kubeconfig.yaml" ]; then
    # Use shared kubeconfig from k3s
    cp /home/candidate/.kube-shared/kubeconfig.yaml /home/candidate/.kube/config
elif [ -f "/etc/rancher/k3s/k3s.yaml" ]; then
    # Fallback to direct k3s config
    cp /etc/rancher/k3s/k3s.yaml /home/candidate/.kube/config
else
    echo "❌ Kubeconfig not found in expected locations"
    exit 1
fi

# Set proper ownership and permissions
chown candidate:candidate /home/candidate/.kube/config
chmod 600 /home/candidate/.kube/config

# Update server address to point to k3s-server container
sed -i 's/127.0.0.1:6443/k3s-server:6443/g' /home/candidate/.kube/config
sed -i 's/localhost:6443/k3s-server:6443/g' /home/candidate/.kube/config
sed -i 's|server: https://k3s:6443|server: https://k3s-server:6443|g' /home/candidate/.kube/config

# Verify the replacement worked
echo "📋 Kubeconfig server URL: $(grep 'server:' /home/candidate/.kube/config)"

echo "✅ Kubeconfig setup complete"

# Quick connectivity test (should work since k3s is healthy)
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Kubernetes cluster connectivity verified"
else
    echo "⚠️  Kubernetes cluster not immediately ready (may need a moment)"
fi

# ==============================================================================
# CANDIDATE SESSION - Switch to candidate user and start tmate
# ==============================================================================

# Switch to candidate user for the actual tmate session
echo "👤 Starting tmate session as candidate user..."

# Create a temporary script to avoid nested quote issues
cat > /tmp/tmate_session.sh << 'SCRIPT_EOF'
#!/bin/bash
set -e

echo "🚀 Starting tmate session..."

# Initialize status
echo "starting" > /tmp/tmate-info/status

# Quick connectivity verification (should work since k3s is healthy)
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ Kubernetes cluster is ready!"
else
    echo "⚠️  Kubernetes cluster not immediately ready, continuing anyway..."
fi
echo "🔗 Starting tmate session (this may take a moment)..."

# Define socket path
TMATE_SOCKET="/tmp/tmate-$USER.sock"

# Start tmate with socket
echo "🔧 Starting tmate with socket: $TMATE_SOCKET"
/usr/local/bin/tmate -S "$TMATE_SOCKET" new-session -d
echo "📊 Tmate session created"

# Wait for tmate to be ready
echo "⏳ Waiting for tmate to be ready..."
if ! /usr/local/bin/tmate -S "$TMATE_SOCKET" wait tmate-ready; then
    echo "❌ Tmate failed to become ready"
    echo "failed" > /tmp/tmate-info/status
    exit 1
fi

echo "✅ Tmate is ready!"

# Get the tmate session URLs
TMATE_SSH=$(/usr/local/bin/tmate -S "$TMATE_SOCKET" display -p '#{tmate_ssh}' 2>/dev/null || echo "")
TMATE_WEB=$(/usr/local/bin/tmate -S "$TMATE_SOCKET" display -p '#{tmate_web}' 2>/dev/null || echo "")

if [ -n "$TMATE_SSH" ]; then
    echo ""
    echo "🎯 CANDIDATE CONNECTION INFO:"
    echo "================================================"
    echo "SSH: $TMATE_SSH"
    if [ -n "$TMATE_WEB" ]; then
        echo "Web: $TMATE_WEB"
    fi
    echo "================================================"
    echo ""
    echo "✨ Session is ready! Candidate can now connect."
    
    # Write connection info directly to shared volume for CLI to read
    echo "$TMATE_SSH" > /tmp/tmate-info/ssh
    if [ -n "$TMATE_WEB" ]; then
        echo "$TMATE_WEB" > /tmp/tmate-info/web
    fi
    echo "ready" > /tmp/tmate-info/status
else
    echo "⚠️  Could not retrieve tmate session info after 30 seconds"
    echo "timeout" > /tmp/tmate-info/status
    exit 1
fi

# Set up cleanup on exit
cleanup() {
    echo "🧹 Cleaning up tmate session..."
    echo "stopped" > /tmp/tmate-info/status 2>/dev/null || true
    /usr/local/bin/tmate -S "$TMATE_SOCKET" kill-session 2>/dev/null || true
}
trap cleanup EXIT

# Keep the session alive - just sleep to maintain container
echo "🔄 Tmate session is now available. Container will stay alive."

exec sleep infinity
SCRIPT_EOF

chmod +x /tmp/tmate_session.sh
exec su - candidate -c '/tmp/tmate_session.sh'
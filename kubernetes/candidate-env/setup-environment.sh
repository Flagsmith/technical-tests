#!/bin/bash
# Setup minimal environment for the candidate debugging session

# Set up minimal environment
cat >> ~/.bashrc << 'EOF'
# Set default namespace for convenience
export KUBECONFIG=~/.kube/config

# Set editor
export EDITOR=nano
EOF

# Create a simple .nanorc for better editing experience
cat > ~/.nanorc << 'EOF'
set tabsize 2
set autoindent
set linenumbers
set mouse
EOF

echo "✅ Candidate environment setup completed"
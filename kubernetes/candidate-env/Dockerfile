FROM alpine:3.21

# ==============================================================================
# ROOT OPERATIONS - Install packages and system setup
# ==============================================================================

# Install system dependencies and tools from Alpine repos
RUN apk add --no-cache \
    bash \
    curl \
    wget \
    git \
    vim \
    nano \
    jq \
    netcat-openbsd \
    bind-tools \
    iputils \
    tree \
    htop \
    less \
    openssh-client \
    ca-certificates \
    kubectl \
    helm \
    sudo \
    shadow

# TODO: Use OS repos when tmate becomes available in stable Alpine packages
# Install tmate (currently only available in testing, so use direct download)
RUN curl -L https://github.com/tmate-io/tmate/releases/download/2.4.0/tmate-2.4.0-static-linux-amd64.tar.xz \
    | tar -xJ -C /tmp \
    && mv /tmp/tmate-2.4.0-static-linux-amd64/tmate /usr/local/bin/tmate \
    && rm -rf /tmp/tmate-* \
    && chmod +x /usr/local/bin/tmate

# Create candidate user and configure sudo access
RUN adduser -D -s /bin/bash candidate \
    && echo 'candidate ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Copy system scripts and make them executable
COPY --chown=root:root start-session.sh /opt/
RUN chmod +x /opt/start-session.sh

# ==============================================================================
# CANDIDATE USER OPERATIONS - User environment and files
# ==============================================================================

# Switch to candidate user for all remaining operations
USER candidate
WORKDIR /home/candidate

# Generate SSH key for tmate
RUN mkdir -p ~/.ssh \
    && ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N "" \
    && chmod 700 ~/.ssh \
    && chmod 600 ~/.ssh/id_rsa*

# Copy challenge files directly to home directory
COPY --chown=candidate:candidate challenge-files/ ./

# Copy and run candidate environment setup
COPY --chown=candidate:candidate setup-environment.sh /tmp/
RUN chmod +x /tmp/setup-environment.sh && /tmp/setup-environment.sh && rm /tmp/setup-environment.sh

# Start the candidate session - this is the main purpose of this container
CMD ["/opt/start-session.sh"]
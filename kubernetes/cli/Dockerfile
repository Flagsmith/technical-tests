FROM python:3.14-alpine

# Install system dependencies and tools from Alpine repos
RUN apk add --no-cache \
    curl \
    git \
    patch \
    wget \
    bash \
    ca-certificates \
    docker-cli \
    docker-compose \
    helm \
    kubectl

# Upgrade pip to latest version for pyproject.toml support
RUN pip install --upgrade pip

# Set working directory
WORKDIR /app

# Copy Python project files
COPY pyproject.toml ./
COPY cli/ ./cli/

# Install Python dependencies
RUN pip install -e .

# Create challenges directory
RUN mkdir -p /app/challenges

# Default command
CMD ["python", "-m", "cli.main"]

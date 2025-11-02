# TheAppApp Python Execution Environment
# Golden image for Python code execution by AI agents

FROM python:3.11-slim

# Set labels for identification
LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="python"
LABEL version="3.11"

# Install common build tools and utilities
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \
    requests \
    numpy \
    pandas \
    pytest \
    black \
    flake8 \
    mypy

# Create workspace directory
WORKDIR /workspace

# Set Python to run in unbuffered mode (better for logs)
ENV PYTHONUNBUFFERED=1

# Default command (will be overridden by ContainerManager)
CMD ["tail", "-f", "/dev/null"]

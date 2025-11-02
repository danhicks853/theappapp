# TheAppApp Node.js Execution Environment
# Golden image for Node.js/JavaScript code execution by AI agents

FROM node:20-slim

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="node"
LABEL version="20"

# Install common build tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    python3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install common npm packages globally
RUN npm install -g \
    typescript \
    ts-node \
    eslint \
    prettier \
    jest \
    nodemon

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

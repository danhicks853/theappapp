# TheAppApp PowerShell Execution Environment
# Golden image for PowerShell code execution by AI agents

FROM mcr.microsoft.com/powershell:lts-alpine-3.17

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="powershell"
LABEL version="7"

# Install common tools and Python (for TAS file operations)
RUN apk add --no-cache \
    git \
    curl \
    wget \
    python3 \
    py3-pip

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

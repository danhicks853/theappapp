# TheAppApp .NET Execution Environment
# Golden image for .NET/C# code execution by AI agents

FROM mcr.microsoft.com/dotnet/sdk:8.0

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="dotnet"
LABEL version="8.0"

# Install common tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

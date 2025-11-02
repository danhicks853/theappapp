# TheAppApp Java Execution Environment
# Golden image for Java code execution by AI agents

FROM openjdk:17-slim

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="java"
LABEL version="17"

# Install common build tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    maven \
    gradle \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

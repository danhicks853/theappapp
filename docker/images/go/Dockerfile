# TheAppApp Go Execution Environment
# Golden image for Go code execution by AI agents

FROM golang:1.21-alpine

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="go"
LABEL version="1.21"

# Install common tools
RUN apk add --no-cache \
    git \
    curl \
    wget \
    make

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

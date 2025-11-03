# TheAppApp PHP Execution Environment
# Golden image for PHP code execution by AI agents

FROM php:8.2-cli

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="php"
LABEL version="8.2"

# Install common tools, extensions, and Python (for TAS file operations)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    zip \
    unzip \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

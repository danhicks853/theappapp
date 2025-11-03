# TheAppApp Ruby Execution Environment
# Golden image for Ruby code execution by AI agents

FROM ruby:3.2-slim

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="ruby"
LABEL version="3.2"

# Install common build tools and Python (for TAS file operations)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install common gems
RUN gem install \
    bundler \
    rails \
    rspec \
    rubocop

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]

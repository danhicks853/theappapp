# TheAppApp Ruby Execution Environment
# Golden image for Ruby code execution by AI agents

FROM ruby:3.2-slim

LABEL maintainer="TheAppApp"
LABEL purpose="code-execution-sandbox"
LABEL language="ruby"
LABEL version="3.2"

# Install common build tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
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

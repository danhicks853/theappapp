#!/bin/bash
# Build all TheAppApp golden images for code execution

set -e  # Exit on error

echo "Building TheAppApp Golden Images..."
echo "==================================="

# Array of languages
languages=("python" "node" "java" "go" "ruby" "php" "dotnet" "powershell")

# Build each image
for lang in "${languages[@]}"; do
    echo ""
    echo "Building $lang image..."
    docker build \
        -t "theappapp-$lang:latest" \
        -f "images/$lang/Dockerfile" \
        "images/$lang/"
    echo "✓ $lang image built successfully"
done

echo ""
echo "==================================="
echo "All images built successfully!"
echo ""
echo "Built images:"
docker images | grep "theappapp-"

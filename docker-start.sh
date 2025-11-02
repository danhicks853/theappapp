#!/bin/bash

# TheAppApp Docker Startup Script

echo "🐳 Starting TheAppApp with Docker..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Please edit .env and add your OPENAI_API_KEY"
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start all services
echo "🏗️  Building containers..."
docker-compose build

echo "🚀 Starting all services..."
docker-compose up -d

echo ""
echo "✅ TheAppApp is starting up!"
echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  PostgreSQL: localhost:55432"
echo "  Qdrant:    localhost:6333"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop:      docker-compose down"

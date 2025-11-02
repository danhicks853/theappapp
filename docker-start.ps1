# TheAppApp Docker Startup Script (PowerShell)

Write-Host "🐳 Starting TheAppApp with Docker..." -ForegroundColor Cyan

# Check if .env exists
if (-Not (Test-Path .env)) {
    Write-Host "⚠️  No .env file found." -ForegroundColor Yellow
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "✅ Created .env from template" -ForegroundColor Green
    }
    Write-Host "Please edit .env and add your OPENAI_API_KEY" -ForegroundColor Yellow
    exit 1
}

# Stop any existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Yellow
docker-compose down

# Build and start all services
Write-Host "🏗️  Building containers..." -ForegroundColor Cyan
docker-compose build

Write-Host "🚀 Starting all services..." -ForegroundColor Green
docker-compose up -d

Write-Host ""
Write-Host "✅ TheAppApp is starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:55432" -ForegroundColor White
Write-Host "  Qdrant:    localhost:6333" -ForegroundColor White
Write-Host ""
Write-Host "To view logs: docker-compose logs -f" -ForegroundColor Yellow
Write-Host "To stop:      docker-compose down" -ForegroundColor Yellow

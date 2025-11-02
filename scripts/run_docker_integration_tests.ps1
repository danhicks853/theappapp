# Docker Integration Test Runner
# Tests against real Docker services with full rebuild

Write-Host "🐳 Docker Integration Test Suite" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker
Write-Host "1️⃣  Checking Docker..." -ForegroundColor Yellow
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker not running" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker running" -ForegroundColor Green
Write-Host ""

# 2. Stop existing containers
Write-Host "2️⃣  Stopping existing containers..." -ForegroundColor Yellow
docker-compose down -v
Write-Host "✅ Containers stopped" -ForegroundColor Green
Write-Host ""

# 3. Rebuild images
Write-Host "3️⃣  Rebuilding Docker images..." -ForegroundColor Yellow
docker-compose build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Images rebuilt" -ForegroundColor Green
Write-Host ""

# 4. Start all services
Write-Host "4️⃣  Starting all services..." -ForegroundColor Yellow
docker-compose up -d
Start-Sleep -Seconds 15
Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# 5. Wait for PostgreSQL
Write-Host "5️⃣  Waiting for PostgreSQL..." -ForegroundColor Yellow
$retries = 30
while ($retries -gt 0) {
    docker exec theappapp-postgres pg_isready -U postgres > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        break
    }
    $retries--
    Start-Sleep -Seconds 1
}
if ($retries -eq 0) {
    Write-Host "❌ PostgreSQL not ready" -ForegroundColor Red
    docker-compose logs postgres
    exit 1
}
Write-Host "✅ PostgreSQL ready" -ForegroundColor Green
Write-Host ""

# 6. Run migrations
Write-Host "6️⃣  Running migrations..." -ForegroundColor Yellow
docker-compose exec -T backend alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migrations failed" -ForegroundColor Red
    docker-compose logs backend
    exit 1
}
Write-Host "✅ Migrations complete" -ForegroundColor Green
Write-Host ""

# 7. Seed test data (if script exists)
Write-Host "7️⃣  Seeding test data..." -ForegroundColor Yellow
if (Test-Path "scripts/seed_test_data.py") {
    docker-compose exec -T backend python scripts/seed_test_data.py
    Write-Host "✅ Test data seeded" -ForegroundColor Green
} else {
    Write-Host "⚠️  seed_test_data.py not found, skipping" -ForegroundColor Yellow
}
Write-Host ""

# 8. Run integration tests
Write-Host "8️⃣  Running integration tests..." -ForegroundColor Yellow
Write-Host ""

docker-compose exec -T backend pytest backend/tests/integration/ -v --tb=short

$test_exit_code = $LASTEXITCODE

Write-Host ""
if ($test_exit_code -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed" -ForegroundColor Red
}
Write-Host ""

# 9. Cleanup
Write-Host "9️⃣  Cleanup..." -ForegroundColor Yellow
Write-Host "Keep services running? (Y/n)" -ForegroundColor Cyan
$response = Read-Host
if ($response -eq 'n' -or $response -eq 'N') {
    docker-compose down
    Write-Host "✅ Services stopped" -ForegroundColor Green
} else {
    Write-Host "✅ Services still running" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Service URLs:" -ForegroundColor Cyan
    Write-Host "  Backend: http://localhost:8000" -ForegroundColor White
    Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
    Write-Host "  PostgreSQL: localhost:55432" -ForegroundColor White
    Write-Host "  Qdrant: http://localhost:6333" -ForegroundColor White
}
Write-Host ""

exit $test_exit_code

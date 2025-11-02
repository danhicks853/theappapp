# Phase 1 Test Runner
# Runs all Phase 1 tests with proper setup

Write-Host "🧪 Phase 1 Test Suite" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if Docker is running
Write-Host "1️⃣  Checking Docker services..." -ForegroundColor Yellow
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# 2. Start required services
Write-Host "2️⃣  Starting PostgreSQL and Qdrant..." -ForegroundColor Yellow
docker-compose up -d postgres qdrant
Start-Sleep -Seconds 5
Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# 3. Prepare test database
Write-Host "3️⃣  Preparing test database..." -ForegroundColor Yellow
python scripts/prepare_test_database.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to prepare test database" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Test database ready" -ForegroundColor Green
Write-Host ""

# 4. Run tests
Write-Host "4️⃣  Running tests..." -ForegroundColor Yellow
Write-Host ""

# Set environment
$env:TESTING = "true"
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:55432/theappapp_test"
$env:QDRANT_URL = "http://localhost:6333"
$env:OPENAI_API_KEY = "test_key_for_mocking"

# Run pytest with coverage
pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term --tb=short

$test_exit_code = $LASTEXITCODE

Write-Host ""
if ($test_exit_code -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "📊 Coverage report: backend/htmlcov/index.html" -ForegroundColor Cyan
Write-Host ""

# 5. Summary
Write-Host "📋 Test Summary" -ForegroundColor Cyan
Write-Host "===============" -ForegroundColor Cyan
Write-Host "Unit Tests: backend/tests/unit/" -ForegroundColor White
Write-Host "Integration Tests: backend/tests/integration/" -ForegroundColor White
Write-Host "Coverage Report: backend/htmlcov/index.html" -ForegroundColor White
Write-Host ""

exit $test_exit_code

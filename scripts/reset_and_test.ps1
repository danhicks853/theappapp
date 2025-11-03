# Reset and Test Script
# Completely resets the environment and prepares for E2E test
# Run from project root: .\scripts\reset_and_test.ps1

Write-Host "`n" -NoNewline
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "COMPLETE ENVIRONMENT RESET FOR E2E TESTING" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop and remove all containers
Write-Host "Step 1: Stopping and removing all containers..." -ForegroundColor Yellow
docker-compose down -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: docker-compose down had errors (may be expected if not running)" -ForegroundColor Yellow
}
Write-Host "✓ Containers stopped and removed" -ForegroundColor Green
Write-Host ""

# Step 2: Remove dangling volumes
Write-Host "Step 2: Cleaning up Docker volumes..." -ForegroundColor Yellow
docker volume prune -f
Write-Host "✓ Volumes cleaned" -ForegroundColor Green
Write-Host ""

# Step 3: Verify API key is set
Write-Host "Step 3: Checking environment variables..." -ForegroundColor Yellow
if (-not $env:OPENAI_API_KEY) {
    Write-Host "ERROR: OPENAI_API_KEY not set!" -ForegroundColor Red
    Write-Host "Please set it: `$env:OPENAI_API_KEY = 'your-key-here'" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ OPENAI_API_KEY is set" -ForegroundColor Green
Write-Host ""

# Step 4: Start PostgreSQL and Qdrant
Write-Host "Step 4: Starting database services..." -ForegroundColor Yellow
docker-compose up -d postgres qdrant
Start-Sleep -Seconds 5
Write-Host "✓ Database services started" -ForegroundColor Green
Write-Host ""

# Step 5: Wait for PostgreSQL to be ready
Write-Host "Step 5: Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    Write-Host "  Attempt $attempt/$maxAttempts..." -NoNewline
    
    docker exec theappapp-postgres pg_isready -U postgres 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        Write-Host " Ready!" -ForegroundColor Green
    } else {
        Write-Host " Not ready yet..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host "ERROR: PostgreSQL did not become ready in time" -ForegroundColor Red
    exit 1
}
Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
Write-Host ""

# Step 6: Run Alembic migrations
Write-Host "Step 6: Running Alembic migrations..." -ForegroundColor Yellow

# Check if alembic is installed
try {
    alembic --version | Out-Null
    Write-Host "  Alembic found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Alembic not found. Install it: pip install alembic" -ForegroundColor Red
    exit 1
}

# Run migrations from backend directory with DATABASE_URL set
Push-Location backend
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:55432/theappapp"
Write-Host "  Using DATABASE_URL: $env:DATABASE_URL" -ForegroundColor Cyan
alembic upgrade head
$migrateExitCode = $LASTEXITCODE
Pop-Location

if ($migrateExitCode -ne 0) {
    Write-Host "ERROR: Alembic migrations failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Migrations complete" -ForegroundColor Green
Write-Host ""

# Step 7: Verify database schema
Write-Host "Step 7: Verifying database schema..." -ForegroundColor Yellow
$tables = docker exec theappapp-postgres psql -U postgres -d theappapp -t -c "\dt" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Database tables:" -ForegroundColor Cyan
    Write-Host $tables
    Write-Host "✓ Database schema verified" -ForegroundColor Green
} else {
    Write-Host "Warning: Could not verify schema" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Check connectivity
Write-Host "Step 8: Testing database connectivity..." -ForegroundColor Yellow
$testQuery = "SELECT 1"
docker exec theappapp-postgres psql -U postgres -d theappapp -c "$testQuery" | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database connectivity OK" -ForegroundColor Green
} else {
    Write-Host "ERROR: Cannot connect to database" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Summary
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "ENVIRONMENT READY FOR TESTING" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running:" -ForegroundColor Yellow
Write-Host "  ✓ PostgreSQL: localhost:55432" -ForegroundColor Green
Write-Host "  ✓ Qdrant:     localhost:6333" -ForegroundColor Green
Write-Host ""
Write-Host "Database:" -ForegroundColor Yellow
Write-Host "  Name:     theappapp" -ForegroundColor Cyan
Write-Host "  User:     postgres" -ForegroundColor Cyan
Write-Host "  Password: postgres" -ForegroundColor Cyan
Write-Host "  URL:      postgresql://postgres:postgres@localhost:55432/theappapp" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ready to run E2E test:" -ForegroundColor Yellow
Write-Host "  pytest backend/tests/test_e2e_real_hello_world.py -v -s --tb=short" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan

# Build all TheAppApp golden images for code execution
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "Building TheAppApp Golden Images..." -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Array of languages
$languages = @("python", "node", "java", "go", "ruby", "php", "dotnet", "powershell")

# Build each image
foreach ($lang in $languages) {
    Write-Host ""
    Write-Host "Building $lang image..." -ForegroundColor Yellow
    
    docker build -t "theappapp-$lang`:latest" -f "images/$lang/Dockerfile" "images/$lang/"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $lang image built successfully" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $lang image build failed" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "All images built successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Built images:" -ForegroundColor Cyan
docker images | findstr theappapp

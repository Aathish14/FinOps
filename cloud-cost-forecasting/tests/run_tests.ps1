# tests/run_tests.ps1
# PowerShell script to set up and execute the PyTest test suite locally.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tests\run_tests.ps1

$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Cloud Cost Forecasting - PyTest Runner" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Navigate to the repository root
$repoRoot = "D:\FinOps\cloud-cost-forecasting"
Set-Location -Path $repoRoot
Write-Host "`n==> Working directory: $(Get-Location)" -ForegroundColor Cyan

# 2. Ensure the tests/ directory exists
$testsDir = Join-Path $repoRoot "tests"
if (!(Test-Path -Path $testsDir)) {
    Write-Host "==> Creating tests/ directory ..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $testsDir -Force | Out-Null
}
Write-Host "==> tests/ directory exists: $(Test-Path -Path $testsDir)" -ForegroundColor Green

# 3. Confirm PyTest is installed
Write-Host "`n==> Checking PyTest installation ..." -ForegroundColor Cyan
try {
    $pytestVersion = python -m pytest --version 2>&1
    Write-Host "    $pytestVersion" -ForegroundColor Green
} catch {
    Write-Host "==> PyTest not found. Installing pytest ..." -ForegroundColor Yellow
    python -m pip install pytest
    Write-Host "==> PyTest installed." -ForegroundColor Green
}

# 4. Execute the test suite with verbose output
Write-Host "`n==> Running PyTest suite (tests/ -v --tb=short) ..." -ForegroundColor Cyan
python -m pytest tests/ -v --tb=short

$exitCode = $LASTEXITCODE

# 5. Print summary
Write-Host "`n==============================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  TEST SUITE: ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "  TEST SUITE: FAILURES DETECTED (exit code $exitCode)" -ForegroundColor Red
}
Write-Host "==============================================" -ForegroundColor Cyan

exit $exitCode

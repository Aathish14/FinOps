# scripts/run-tests.ps1
# Convenience wrapper that runs all test suites in the repository.
# Delegates to cloud-cost-forecasting/tests/run_tests.ps1 for app tests,
# then runs the shared root tests/ directory.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\run-tests.ps1

$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  FinOps Test Runner" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$repoRoot = Get-Location
$exitCode = 0

# 1. Run application tests (existing runner in cloud-cost-forecasting/tests/)
Write-Host "`n==> Running application tests (cloud-cost-forecasting/tests/) ..." -ForegroundColor Cyan
Set-Location -Path (Join-Path $repoRoot "cloud-cost-forecasting")
try {
    & python -m pytest tests/ -v --tb=short
    $appExitCode = $LASTEXITCODE
    if ($appExitCode -ne 0) {
        Write-Host "    Application tests FAILED (exit code $appExitCode)" -ForegroundColor Red
        $exitCode = $appExitCode
    } else {
        Write-Host "    Application tests: ALL PASSED" -ForegroundColor Green
    }
} catch {
    Write-Host "    ERROR: Could not run application tests" -ForegroundColor Red
    $exitCode = 1
}

# 2. Run shared root tests
Write-Host "`n==> Running shared tests (tests/) ..." -ForegroundColor Cyan
Set-Location -Path $repoRoot
try {
    & python -m pytest tests/ -v --tb=short
    $sharedExitCode = $LASTEXITCODE
    if ($sharedExitCode -ne 0) {
        Write-Host "    Shared tests FAILED (exit code $sharedExitCode)" -ForegroundColor Red
        $exitCode = $sharedExitCode
    } else {
        Write-Host "    Shared tests: ALL PASSED" -ForegroundColor Green
    }
} catch {
    Write-Host "    ERROR: Could not run shared tests" -ForegroundColor Red
    $exitCode = 1
}

# Summary
Write-Host "`n==============================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "  TEST FAILURES DETECTED (exit code $exitCode)" -ForegroundColor Red
}
Write-Host "==============================================" -ForegroundColor Cyan

exit $exitCode

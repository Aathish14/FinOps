# scripts/validate.ps1
# Validates the FinOps repository structure, configuration, and tests.
# Returns nonzero exit code on any failure.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\validate.ps1

$ErrorActionPreference = "Stop"
$exitCode = 0

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  FinOps Repository Validation" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Verify repository root
$repoRoot = Get-Location
Write-Host "`n==> Repository root: $repoRoot" -ForegroundColor Cyan

# 2. Verify git repository
Write-Host "`n==> Checking git repository ..." -ForegroundColor Cyan
try {
    $branch = git branch --show-current
    Write-Host "    Active branch: $branch" -ForegroundColor Green
} catch {
    Write-Host "    ERROR: Not a git repository or git not available" -ForegroundColor Red
    $exitCode = 1
}

# 3. Verify entry point exists
Write-Host "`n==> Verifying Streamlit entry point ..." -ForegroundColor Cyan
$entryPoint = Join-Path $repoRoot "cloud-cost-forecasting\app.py"
if (Test-Path -Path $entryPoint) {
    Write-Host "    Found: cloud-cost-forecasting/app.py" -ForegroundColor Green
} else {
    Write-Host "    ERROR: cloud-cost-forecasting/app.py not found" -ForegroundColor Red
    $exitCode = 1
}

# 4. Verify requirements.txt exists
Write-Host "`n==> Verifying requirements.txt ..." -ForegroundColor Cyan
$reqFile = Join-Path $repoRoot "cloud-cost-forecasting\requirements.txt"
if (Test-Path -Path $reqFile) {
    Write-Host "    Found: cloud-cost-forecasting/requirements.txt" -ForegroundColor Green
} else {
    Write-Host "    ERROR: cloud-cost-forecasting/requirements.txt not found" -ForegroundColor Red
    $exitCode = 1
}

# 5. Verify runtime.txt exists
Write-Host "`n==> Verifying runtime.txt ..." -ForegroundColor Cyan
$runtimeFile = Join-Path $repoRoot "runtime.txt"
if (Test-Path -Path $runtimeFile) {
    $content = Get-Content -Path $runtimeFile
    Write-Host "    Found: runtime.txt ($content)" -ForegroundColor Green
} else {
    Write-Host "    ERROR: runtime.txt not found" -ForegroundColor Red
    $exitCode = 1
}

# 6. Verify sample data files
Write-Host "`n==> Verifying sample data files ..." -ForegroundColor Cyan
$sampleAws = Join-Path $repoRoot "cloud-cost-forecasting\data\samples\sample_aws_billing.csv"
$sampleGcp = Join-Path $repoRoot "cloud-cost-forecasting\data\samples\sample_gcp_billing.csv"
if (Test-Path -Path $sampleAws) {
    Write-Host "    Found: sample_aws_billing.csv" -ForegroundColor Green
} else {
    Write-Host "    ERROR: sample_aws_billing.csv not found" -ForegroundColor Red
    $exitCode = 1
}
if (Test-Path -Path $sampleGcp) {
    Write-Host "    Found: sample_gcp_billing.csv" -ForegroundColor Green
} else {
    Write-Host "    ERROR: sample_gcp_billing.csv not found" -ForegroundColor Red
    $exitCode = 1
}

# 7. Verify Python imports
Write-Host "`n==> Verifying Python imports ..." -ForegroundColor Cyan
try {
    Set-Location -Path (Join-Path $repoRoot "cloud-cost-forecasting")
    $importResult = python -c "import streamlit; import pandas; import numpy; import plotly; from app.ingest.ingestor import ingest_billing_data, normalize_file_inputs; from app.forecasting.prophet_model import create_forecasting_model; from app.anomaly.isolation_forest import create_anomaly_detector; print('All imports OK')"
    Write-Host "    $importResult" -ForegroundColor Green
} catch {
    Write-Host "    ERROR: Import check failed" -ForegroundColor Red
    $exitCode = 1
}

# 8. Run application tests
Write-Host "`n==> Running application tests ..." -ForegroundColor Cyan
Set-Location -Path (Join-Path $repoRoot "cloud-cost-forecasting")
try {
    $appTestResult = python -m pytest tests/ -v --tb=short 2>&1
    Write-Host $appTestResult
    $appExitCode = $LASTEXITCODE
    if ($appExitCode -ne 0) {
        Write-Host "    ERROR: Application tests failed (exit code $appExitCode)" -ForegroundColor Red
        $exitCode = $appExitCode
    } else {
        Write-Host "    Application tests: ALL PASSED" -ForegroundColor Green
    }
} catch {
    Write-Host "    ERROR: Could not run application tests" -ForegroundColor Red
    $exitCode = 1
}

# 9. Run shared tests
Write-Host "`n==> Running shared tests ..." -ForegroundColor Cyan
Set-Location -Path $repoRoot
try {
    $sharedTestResult = python -m pytest tests/ -v --tb=short 2>&1
    Write-Host $sharedTestResult
    $sharedExitCode = $LASTEXITCODE
    if ($sharedExitCode -ne 0) {
        Write-Host "    ERROR: Shared tests failed (exit code $sharedExitCode)" -ForegroundColor Red
        $exitCode = $sharedExitCode
    } else {
        Write-Host "    Shared tests: ALL PASSED" -ForegroundColor Green
    }
} catch {
    Write-Host "    ERROR: Could not run shared tests" -ForegroundColor Red
    $exitCode = 1
}

# 10. Summary
Write-Host "`n==============================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  VALIDATION: ALL CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "  VALIDATION: FAILURES DETECTED (exit code $exitCode)" -ForegroundColor Red
}
Write-Host "==============================================" -ForegroundColor Cyan

exit $exitCode

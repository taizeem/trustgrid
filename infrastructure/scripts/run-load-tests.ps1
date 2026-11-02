param(
    [int]$Users = 50,
    [int]$SpawnRate = 10,
    [string]$RunTime = "45s",
    [string]$HostUrl = "http://localhost:8088"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " TrustGrid Distributed Multi-Tenant Load Testing Suite   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target Host : $HostUrl"
Write-Host "Users       : $Users"
Write-Host "Spawn Rate  : $SpawnRate users/sec"
Write-Host "Duration    : $RunTime"

# Verify locust is installed
$locustCheck = Get-Command locust -ErrorAction SilentlyContinue
if (-not $locustCheck) {
    Write-Host "[INFO] Installing locust into virtual environment..." -ForegroundColor Yellow
    uv pip install --system locust pyjwt
}

# Run headless load test and output CSV statistics
$csvPrefix = "infrastructure/monitoring/load_test_results"
locust -f tests/load/locustfile.py `
       --headless `
       --users $Users `
       --spawn-rate $SpawnRate `
       --run-time $RunTime `
       --host $HostUrl `
       --csv $csvPrefix

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Load test run completed successfully!" -ForegroundColor Green
    Write-Host "Results saved to $csvPrefix`_stats.csv" -ForegroundColor Green
} else {
    Write-Host "`n[ERROR] Load test failed or terminated abnormally." -ForegroundColor Red
}
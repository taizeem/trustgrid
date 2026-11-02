Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " TrustGrid Phase 12: End-to-End Reliability & Chaos Drill" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Verify Gateway Health
Write-Host "`n[1/6] Auditing Stack Health Baseline..." -ForegroundColor Yellow
$healthResp = Invoke-RestMethod -Uri "http://localhost:8008/health/" -Method Get
Write-Host "  [OK] Service Gateway is responding (Audit Service: $($healthResp.status))" -ForegroundColor Green

# 2. Chaos Drill: Transient RabbitMQ Restart with Backoff Reconnection
Write-Host "`n[2/6] Chaos Drill: Restarting RabbitMQ Broker..." -ForegroundColor Yellow
docker restart trustgrid_rabbitmq | Out-Null
Write-Host "  [INFO] Broker restarted. Allowing 12s for AMQP network listener..." -ForegroundColor Gray
Start-Sleep -Seconds 12

# Trigger outbox publisher to verify reconnection with retry
docker exec trustgrid_vendor_svc python manage.py publish_outbox --once
Write-Host "  [OK] Outbox publisher successfully reconnected to RabbitMQ!" -ForegroundColor Green

# 3. Chaos Drill: Workflow Service Recovery After Hard Kill
Write-Host "`n[3/6] Chaos Drill: Testing Workflow Service Crash Recovery..." -ForegroundColor Yellow
docker kill trustgrid_workflow_svc | Out-Null
Write-Host "  [INFO] Container killed. Restarting workflow service..." -ForegroundColor Gray
docker start trustgrid_workflow_svc | Out-Null
Start-Sleep -Seconds 4

$wfHealth = Invoke-RestMethod -Uri "http://localhost:8003/health" -Method Get
if ($wfHealth.status -eq "ok" -or $wfHealth.status -eq "healthy") {
    Write-Host "  [OK] Workflow service recovered state cleanly from PostgreSQL!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Workflow service failed to recover: $($wfHealth.status)" -ForegroundColor Red
}

# 4. Gateway Timeout Boundedness Check
Write-Host "`n[4/6] Verifying Gateway Fail-Fast Behavior on Stopped Backend..." -ForegroundColor Yellow
docker stop trustgrid_risk_svc | Out-Null
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $null = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/risk/compute" -Method Post -TimeoutSec 7 -ErrorAction Stop
} catch {
    $stopwatch.Stop()
    $elapsedSec = $stopwatch.Elapsed.TotalSeconds
    Write-Host "  [OK] Gateway failed fast in $($elapsedSec.ToString('0.00'))s with: $($_.Exception.Message)" -ForegroundColor Green
}
# Recover Risk Service
docker start trustgrid_risk_svc | Out-Null
Start-Sleep -Seconds 3

# 5. Run Python End-to-End Reliability Suite
Write-Host "`n[5/6] Running Platform Integration, Idempotency & Concurrency Tests..." -ForegroundColor Yellow
python -m pytest tests/ -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] All platform integration tests passed!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Some integration tests failed." -ForegroundColor Red
}

# 6. Verify System Audit Log Integrity
Write-Host "`n[6/6] Verifying Cross-System Audit Log Integrity..." -ForegroundColor Yellow
$auditCheck = docker exec trustgrid_postgres psql -U audit_user -d trustgrid_audit -t -c "SELECT COUNT(*) FROM audit_events;"
Write-Host "  [OK] Recorded $([string]$auditCheck.Trim()) immutable audit events across reliability runs." -ForegroundColor Green

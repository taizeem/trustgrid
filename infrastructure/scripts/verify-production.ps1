
$gatewayUrl = "http://localhost:8088"

# 1. Gateway Security Headers Audit
Write-Host "`n[1/5] Auditing API Gateway Security Headers..." -ForegroundColor Yellow
$headers = $null
try {
    $resp = Invoke-WebRequest -Uri "$gatewayUrl/api/v1/auth/token/" -Method Post -Body "{}" -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
    $headers = $resp.Headers
} catch {
    if ($_.Exception.Response) {
        $headers = $_.Exception.Response.Headers
    }
}

if ($headers) {
    $frameOptions = $headers["X-Frame-Options"]
    $hsts = $headers["Strict-Transport-Security"]
    $csp = $headers["Content-Security-Policy"]
    if ($frameOptions -eq "DENY" -or $hsts -or $csp) {
        Write-Host "  [OK] Gateway enforces Security Headers (FrameDeny: '$frameOptions', HSTS: '$hsts')!" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Headers received but expected security flags were not present." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [FAIL] Gateway was unreachable at $gatewayUrl" -ForegroundColor Red
}

# 2. All Microservices Health Verification
Write-Host "`n[2/5] Auditing Microservices Health & Liveness..." -ForegroundColor Yellow
$services = @(
    @{ Name = "Identity Service"; Url = "http://localhost:8001/health/" },
    @{ Name = "Vendor Service"; Url = "http://localhost:8002/health/" },
    @{ Name = "Workflow Service"; Url = "http://localhost:8003/health" },
    @{ Name = "Document Service"; Url = "http://localhost:8004/health" },
    @{ Name = "Risk Service"; Url = "http://localhost:8005/health" },
    @{ Name = "Integrations Service"; Url = "http://localhost:8006/health" },
    @{ Name = "Billing Service"; Url = "http://localhost:8007/health/" },
    @{ Name = "Audit Service"; Url = "http://localhost:8008/health/" }
)

foreach ($svc in $services) {
    try {
        $res = Invoke-RestMethod -Uri $svc.Url -Method Get -TimeoutSec 5
        Write-Host "  [OK] $($svc.Name) is healthy (Status: $($res.status))" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($svc.Name) failed health check: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 3. Observability & Telemetry Audit
Write-Host "`n[3/5] Auditing Prometheus & Grafana Telemetry..." -ForegroundColor Yellow
try {
    $promTargets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" -TimeoutSec 5
    $activeTargets = @($promTargets.data.activeTargets | Where-Object { $_.health -eq "up" }).Count
    Write-Host "  [OK] Prometheus is scraping $activeTargets active service targets!" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Prometheus query failed (Container may be initializing)." -ForegroundColor Yellow
}

# 4. Multi-Database Decoupled Backup Drill
Write-Host "`n[4/5] Executing Automated Database Backup Drill..." -ForegroundColor Yellow
.\infrastructure\scripts\backup-databases.ps1

# 5. Full CI / Platform Integration Test Suite
Write-Host "`n[5/5] Running Platform Integration & Isolation Suite..." -ForegroundColor Yellow
python -m pytest tests/ -v
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] All platform integration tests passed!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Some tests failed." -ForegroundColor Red
}
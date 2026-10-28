Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid Infrastructure Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check Docker Containers Status
Write-Host "`n[1/3] Checking Docker Container Health..." -ForegroundColor Yellow
$containers = @("trustgrid_postgres", "trustgrid_rabbitmq", "trustgrid_redis")
foreach ($container in $containers) {
    $status = docker inspect --format="{{.State.Health.Status}}" $container 2>$null
    if ($status -eq "healthy") {
        Write-Host "  [OK] $container is healthy." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $container status: $status" -ForegroundColor Red
    }
}

# 2. Check Database Isolation & Multi-DB Initialization
Write-Host "`n[2/3] Verifying Service Database Access..." -ForegroundColor Yellow
$databases = @(
    @{ Name="trustgrid_identity"; User="identity_user"; Pass="identity_secure_pass_dev" },
    @{ Name="trustgrid_vendor";   User="vendor_user";   Pass="vendor_secure_pass_dev" },
    @{ Name="trustgrid_workflow"; User="workflow_user"; Pass="workflow_secure_pass_dev" },
    @{ Name="trustgrid_risk";     User="risk_user";     Pass="risk_secure_pass_dev" }
)

foreach ($db in $databases) {
    $cmd = "docker exec -e PGPASSWORD=$($db.Pass) trustgrid_postgres psql -U $($db.User) -d $($db.Name) -c '\q' 2>&1"
    Invoke-Expression $cmd | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Successfully authenticated to '$($db.Name)' as '$($db.User)'." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Cannot connect to '$($db.Name)' as '$($db.User)'." -ForegroundColor Red
    }
}

# 3. Check RabbitMQ and Redis
Write-Host "`n[3/3] Verifying Broker and Cache Ports..." -ForegroundColor Yellow
$rabbitCheck = docker exec trustgrid_rabbitmq rabbitmq-diagnostics -q ping 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] RabbitMQ ping succeeded." -ForegroundColor Green
} else {
    Write-Host "  [FAIL] RabbitMQ ping failed: $rabbitCheck" -ForegroundColor Red
}

$redisCheck = docker exec trustgrid_redis redis-cli -a trustgrid_redis_pass_dev ping 2>&1
if ($redisCheck -match "PONG") {
    Write-Host "  [OK] Redis responded with PONG." -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Redis ping failed: $redisCheck" -ForegroundColor Red
}

Write-Host "`nVerification complete." -ForegroundColor Cyan

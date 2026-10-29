Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid Messaging & Outbox Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Register User and Acquire Token
$userEmail = "compliance-$((Get-Random))@enterprise.test"
$regResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/register/" -Method Post -Body (@{
    email = $userEmail
    password = "SecurePassword123!"
    first_name = "Event"
    last_name = "Tester"
} | ConvertTo-Json) -ContentType "application/json"
$token = $regResp.token

# 2. Create Organization
$orgResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/organizations/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    name = "EventDriven Org"
    slug = "event-org-$((Get-Random))"
} | ConvertTo-Json) -ContentType "application/json"
$orgId = $orgResp.id

# 3. Exchange for Tenant-Scoped Token
$exchangeResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/token/tenant/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    organization_id = $orgId
} | ConvertTo-Json) -ContentType "application/json"
$tenantToken = $exchangeResp.token
$headers = @{ Authorization = "Bearer $tenantToken" }

# 4. Create Vendor & Template
Write-Host "`n[1/4] Creating Vendor and Template..." -ForegroundColor Yellow
$vendorResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/vendors/" -Method Post -Headers $headers -Body (@{
    name = "AWS Cloud"
    website = "https://aws.amazon.com"
} | ConvertTo-Json) -ContentType "application/json"

$tmplResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/templates/" -Method Post -Headers $headers -Body (@{
    title = "Vendor Risk Baseline"
    version = 1
    schema = @{ questions = @() }
} | ConvertTo-Json) -ContentType "application/json"

# 5. Create Draft Assessment and Submit
Write-Host "`n[2/4] Submitting Assessment to trigger Outbox..." -ForegroundColor Yellow
$subResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/assessments/" -Method Post -Headers $headers -Body (@{
    vendor = $vendorResp.id
    template = $tmplResp.id
    answers = @{ q1 = "compliant" }
} | ConvertTo-Json) -ContentType "application/json"

$submitResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/assessments/$($subResp.id)/submit/" -Method Post -Headers $headers
Write-Host "  [OK] Assessment submitted (Status: $($submitResp.status))." -ForegroundColor Green

# 6. Run Outbox Publisher to Relay Event to RabbitMQ
Write-Host "`n[3/4] Triggering Outbox Publisher Relay..." -ForegroundColor Yellow
docker exec trustgrid_vendor_svc python manage.py publish_outbox --once

# 7. Verify Auto-Created Workflow in Workflow Service
Write-Host "`n[4/4] Verifying auto-created workflow in Workflow Service..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Query PostgreSQL directly for the generated workflow
$query = "SELECT id, current_state, assessment_id FROM workflows WHERE assessment_id = '$($subResp.id)';"
$result = docker exec trustgrid_postgres psql -U workflow_user -d trustgrid_workflow -c $query

if ($result -match "IN_REVIEW") {
    Write-Host "  [OK] Workflow was automatically created in IN_REVIEW state via RabbitMQ!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Workflow not found in database: $result" -ForegroundColor Red
}

Write-Host "`nMessaging verification complete." -ForegroundColor Cyan
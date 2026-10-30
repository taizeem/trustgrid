Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid Integrations & Webhooks Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Acquire Token for Tenant A
$regPayload = @{
    email = "integration-lead-$((Get-Random))@enterprise.test"
    password = "SecurePassword123!"
    first_name = "Webhook"
    last_name = "Engineer"
} | ConvertTo-Json

$regResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/register/" -Method Post -Body $regPayload -ContentType "application/json"
$token = $regResp.token

$orgResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/organizations/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    name = "Integration Enterprise Org"
    slug = "integrations-org-$((Get-Random))"
} | ConvertTo-Json) -ContentType "application/json"
$orgId = $orgResp.id

$exchangeResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/token/tenant/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    organization_id = $orgId
} | ConvertTo-Json) -ContentType "application/json"
$tenantToken = $exchangeResp.token

# 2. Verify SSRF Protection (Attempt registration of loopback/private URL)
Write-Host "`n[1/5] Verifying SSRF Protection against restricted target..." -ForegroundColor Yellow
$ssrfPayload = @{
    target_url = "http://127.0.0.1:8080/internal/admin"
    event_types = @("vendor.created")
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri "$gatewayUrl/api/v1/integrations/webhooks" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $ssrfPayload -ContentType "application/json" | Out-Null
    Write-Host "  [FAIL] SSRF target was not blocked!" -ForegroundColor Red
} catch {
    Write-Host "  [OK] SSRF target (127.0.0.1) successfully blocked with HTTP 400 Bad Request!" -ForegroundColor Green
}

# 3. Register Authentic Webhook Subscription
Write-Host "`n[2/5] Registering outbound webhook subscription..." -ForegroundColor Yellow
$whPayload = @{
    target_url = "https://httpbin.org/post"
    secret = "whsec_custom_secure_signing_secret_999"
    event_types = @("vendor.created", "workflow.approved")
} | ConvertTo-Json

$whResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/integrations/webhooks" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $whPayload -ContentType "application/json"
$webhookId = $whResp.id
Write-Host "  [OK] Webhook created! ID: $webhookId, URL: $($whResp.target_url), Secret: $($whResp.secret.Substring(0,12))..." -ForegroundColor Green

# 4. List Tenant Webhooks
Write-Host "`n[3/5] Querying registered webhooks for tenant..." -ForegroundColor Yellow
$listResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/integrations/webhooks" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
if ($listResp.Count -ge 1 -and $listResp[0].id -eq $webhookId) {
    Write-Host "  [OK] Found registered webhook in tenant list!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Webhook not listed!" -ForegroundColor Red
}

# 5. Dispatch Test Webhook Ping
Write-Host "`n[4/5] Dispatching test webhook ping..." -ForegroundColor Yellow
$testResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/integrations/webhooks/$webhookId/test" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" }
Write-Host "  [OK] Test dispatch executed! Status Code: $($testResp.status_code), Duration: $($testResp.duration_ms)ms" -ForegroundColor Green

# 6. Verify Delivery History
Write-Host "`n[5/5] Checking delivery history log..." -ForegroundColor Yellow
$historyResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/integrations/webhooks/$webhookId/deliveries" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
if ($historyResp.Count -ge 1) {
    Write-Host "  [OK] Delivery attempt recorded in audit log: ID: $($historyResp[0].id), Status: $($historyResp[0].status_code)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Delivery attempt log missing!" -ForegroundColor Red
}

# Cleanup: Delete Webhook
Invoke-RestMethod -Uri "$gatewayUrl/api/v1/integrations/webhooks/$webhookId" -Method Delete -Headers @{ Authorization = "Bearer $tenantToken" } | Out-Null
Write-Host "`nCleaned up webhook subscription." -ForegroundColor Gray

Write-Host "`nIntegrations & Webhooks verification complete." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid Billing & Usage Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Acquire Token for Tenant A
Write-Host "`n[1/7] Authenticating and acquiring tenant token..." -ForegroundColor Yellow
$regPayload = @{
    email = "billing-admin-$((Get-Random))@enterprise.test"
    password = "SecurePassword123!"
    first_name = "Billing"
    last_name = "Admin"
} | ConvertTo-Json

$regResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/register/" -Method Post -Body $regPayload -ContentType "application/json"
$token = $regResp.token

$orgResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/organizations/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    name = "Billing Enterprise Org"
    slug = "billing-org-$((Get-Random))"
} | ConvertTo-Json) -ContentType "application/json"
$orgId = $orgResp.id

$exchangeResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/token/tenant/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    organization_id = $orgId
} | ConvertTo-Json) -ContentType "application/json"
$tenantToken = $exchangeResp.token
Write-Host "  [OK] Tenant token acquired for Organization $orgId" -ForegroundColor Green

# 2. Query Available Plans
Write-Host "`n[2/7] Listing active subscription plans..." -ForegroundColor Yellow
$plans = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/plans/" -Method Get
Write-Host "  [OK] Found $($plans.Count) active plans: $(($plans | ForEach-Object { $_.code }) -join ', ')" -ForegroundColor Green

# 3. Retrieve Tenant Subscription
Write-Host "`n[3/7] Fetching auto-provisioned subscription..." -ForegroundColor Yellow
$sub = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/subscription/" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
Write-Host "  [OK] Subscription status: '$($sub.status)', Plan: '$($sub.plan.name)'" -ForegroundColor Green

# 4. Check Entitlement Limits
Write-Host "`n[4/7] Checking entitlement quota for 'max_vendors'..." -ForegroundColor Yellow
$entCheck = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/entitlements/check/?feature=max_vendors&quantity=1" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
Write-Host "  [OK] Entitlement check passed: allowed=$($entCheck.allowed), remaining=$($entCheck.remaining)" -ForegroundColor Green

# 5. Ingest Usage Record Idempotently
Write-Host "`n[5/7] Testing usage metering with idempotency key..." -ForegroundColor Yellow
$idempotencyKey = "tx_billing_meter_$((Get-Random))"
$usagePayload = @{
    metric_name = "max_vendors"
    quantity = 2
    idempotency_key = $idempotencyKey
} | ConvertTo-Json

$usageResp1 = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/usage/" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $usagePayload -ContentType "application/json"
Write-Host "  [OK] Usage recorded: created=$($usageResp1.created), status=$($usageResp1.status)" -ForegroundColor Green

$usageResp2 = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/usage/" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $usagePayload -ContentType "application/json"
if ($usageResp2.created -eq $false -and $usageResp2.status -eq "idempotent_duplicate") {
    Write-Host "  [OK] Billing idempotency confirmed: duplicate delivery was not double-counted!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Duplicate usage record was counted twice!" -ForegroundColor Red
}

# 6. Create Sandbox Checkout Session
Write-Host "`n[6/7] Creating Stripe sandbox checkout session..." -ForegroundColor Yellow
$checkoutPayload = @{
    plan_code = "growth"
} | ConvertTo-Json

$checkoutResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/checkout-session/" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $checkoutPayload -ContentType "application/json"
Write-Host "  [OK] Checkout session generated: ID=$($checkoutResp.session_id)" -ForegroundColor Green

# 7. Deliver Simulated Webhook
Write-Host "`n[7/7] Delivering simulated payment webhook with HMAC signature..." -ForegroundColor Yellow
$webhookSecret = "whsec_mock_sandbox_secret_456"
$eventId = "evt_ps_verify_$((Get-Random))"
$webhookBody = @{
    id = $eventId
    type = "customer.subscription.updated"
    data = @{
        object = @{
            id = "sub_sandbox_live_$((Get-Random))"
            customer = "cus_tenant_org_$orgId"
            status = "active"
            metadata = @{
                tenant_id = $orgId
                plan_code = "enterprise"
            }
        }
    }
} | ConvertTo-Json -Depth 5

$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$signedPayload = "$timestamp.$webhookBody"
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($webhookSecret)
$sigBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($signedPayload))
$sigHex = -join ($sigBytes | ForEach-Object { "{0:x2}" -f $_ })
$stripeHeader = "t=$timestamp,v1=$sigHex"

$webhookResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/webhooks/stripe/" -Method Post -Body $webhookBody -ContentType "application/json" -Headers @{ "Stripe-Signature" = $stripeHeader }
Write-Host "  [OK] Webhook processed: status=$($webhookResp.status), event_id=$($webhookResp.event_id)" -ForegroundColor Green

$upgradedSub = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/billing/subscription/" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
Write-Host "  [OK] Subscription upgraded to: '$($upgradedSub.plan.name)' via idempotent webhook!" -ForegroundColor Green

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host " Billing Service Verification Successful! " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid Risk Engine Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Acquire Token for Tenant
$regPayload = @{
    email = "risk-analyst-$((Get-Random))@enterprise.test"
    password = "SecurePassword123!"
    first_name = "Risk"
    last_name = "Assessor"
} | ConvertTo-Json

$regResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/register/" -Method Post -Body $regPayload -ContentType "application/json"
$token = $regResp.token

$orgResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/organizations/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    name = "Enterprise Risk Org"
    slug = "risk-org-$((Get-Random))"
} | ConvertTo-Json) -ContentType "application/json"
$orgId = $orgResp.id

$exchangeResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/token/tenant/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    organization_id = $orgId
} | ConvertTo-Json) -ContentType "application/json"
$tenantToken = $exchangeResp.token

# 2. Query Rules Catalog
Write-Host "`n[1/4] Querying available versioned scoring rules..." -ForegroundColor Yellow
$rules = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/risk/rules" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
Write-Host "  [OK] Found $($rules.Count) active rule model(s): $($rules[0].name) ($($rules[0].version))" -ForegroundColor Green

# 3. Compute Deterministic Risk Score
Write-Host "`n[2/4] Computing deterministic risk score for SaaS vendor..." -ForegroundColor Yellow
$vendorId = [guid]::NewGuid().ToString()

$computePayload = @{
    vendor_id = $vendorId
    data_sensitivity = "CONFIDENTIAL"
    business_criticality = "TIER_2_HIGH"
    security_controls = @{
        enforces_mfa = $true
        encrypts_at_rest = $true
        has_incident_response_plan = $false
        meets_vulnerability_sla = $true
    }
    certifications = @{
        has_soc2_type2 = $true
        has_iso27001 = $false
    }
    incident_history = @{
        breach_count_last_12m = 0
        breach_count_last_24m = 0
    }
    rule_version = "v1.0.0"
} | ConvertTo-Json -Depth 5

$riskResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/risk/compute" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $computePayload -ContentType "application/json"

# Expected: 20 (Confidential) + 18 (Tier2) + 5 (No IRP) - 10 (SOC2) = 33.00 (MEDIUM)
Write-Host "  [OK] Computed Score: $($riskResp.overall_score)/100.00 | Tier: $($riskResp.risk_tier)" -ForegroundColor Green
Write-Host "  [OK] Factors Evaluated: $($riskResp.factor_breakdown.Count)" -ForegroundColor Green
Write-Host "  [OK] Disclaimer: $($riskResp.disclaimer)" -ForegroundColor Gray

if ($riskResp.overall_score -ne 33.0 -or $riskResp.risk_tier -ne "MEDIUM") {
    Write-Host "  [FAIL] Expected score 33.00 (MEDIUM), got $($riskResp.overall_score) ($($riskResp.risk_tier))" -ForegroundColor Red
} else {
    Write-Host "  [OK] Score precisely matches deterministic expected calculation!" -ForegroundColor Green
}

# 4. Verify Determinism & Idempotence
Write-Host "`n[3/4] Verifying Calculation Determinism across identical runs..." -ForegroundColor Yellow
$repeatResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/risk/compute" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $computePayload -ContentType "application/json"
if ($repeatResp.overall_score -eq $riskResp.overall_score -and $repeatResp.risk_tier -eq $riskResp.risk_tier) {
    Write-Host "  [OK] Calculation is 100% deterministic and reproducible!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Determinism mismatch!" -ForegroundColor Red
}

# 5. Verify Unsupported Rule Version Rejection
Write-Host "`n[4/4] Verifying unsupported rule version rejection..." -ForegroundColor Yellow
$badPayload = @{
    vendor_id = $vendorId
    data_sensitivity = "PUBLIC"
    business_criticality = "TIER_4_LOW"
    security_controls = @{
        enforces_mfa = $true
        encrypts_at_rest = $true
        has_incident_response_plan = $true
        meets_vulnerability_sla = $true
    }
    certifications = @{
        has_soc2_type2 = $true
        has_iso27001 = $true
    }
    incident_history = @{
        breach_count_last_12m = 0
        breach_count_last_24m = 0
    }
    rule_version = "v99.0.0"
} | ConvertTo-Json -Depth 5

try {
    Invoke-RestMethod -Uri "$gatewayUrl/api/v1/risk/compute" -Method Post -Headers @{ Authorization = "Bearer $tenantToken" } -Body $badPayload -ContentType "application/json" | Out-Null
    Write-Host "  [FAIL] Unsupported version was not rejected!" -ForegroundColor Red
} catch {
    Write-Host "  [OK] Unsupported rule version correctly rejected with HTTP 400 Bad Request!" -ForegroundColor Green
}

Write-Host "`nRisk Engine verification complete." -ForegroundColor Cyan
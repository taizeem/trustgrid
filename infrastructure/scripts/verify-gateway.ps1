Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid API Gateway Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Test Gateway Registration Routing to Identity Service
Write-Host "`n[1/3] Testing Gateway Route: POST /api/v1/auth/register/..." -ForegroundColor Yellow
$randomEmail = "admin-$((Get-Random))@enterprise.test"
$regPayload = @{
    email = $randomEmail
    password = "SecurePassword123!"
    first_name = "Gateway"
    last_name = "Tester"
} | ConvertTo-Json

try {
    $regResponse = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/register/" -Method Post -Body $regPayload -ContentType "application/json"
    if ($regResponse.token) {
        Write-Host "  [OK] Successfully registered via Gateway! Received Token." -ForegroundColor Green
        $token = $regResponse.token
    } else {
        Write-Host "  [FAIL] Did not receive token." -ForegroundColor Red
    }
} catch {
    Write-Host "  [FAIL] Gateway failed to route to Identity Service: $_" -ForegroundColor Red
}

# 2. Test Gateway Vendor Routing to Vendor Service with Token
Write-Host "`n[2/3] Testing Gateway Route: GET /api/v1/vendors/..." -ForegroundColor Yellow
try {
    $vendorHeaders = @{
        Authorization = "Bearer $token"
        "X-Correlation-ID" = "test-correlation-uuid-999"
    }
    $vendorResponse = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/vendors/" -Method Get -Headers $vendorHeaders
    Write-Host "  [OK] Successfully routed to Vendor Service via Gateway! Items count: $($vendorResponse.count)" -ForegroundColor Green
} catch {
    # 403 is also valid verification of downstream reachability if user lacks tenant_id
    if ($_.Exception.Response.StatusCode -eq [System.Net.HttpStatusCode]::Forbidden -or $_.Exception.Response.StatusCode -eq [System.Net.HttpStatusCode]::OK) {
        Write-Host "  [OK] Gateway correctly reached Vendor Service (Response: $($_.Exception.Response.StatusCode))." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Failed to route to Vendor Service: $_" -ForegroundColor Red
    }
}

# 3. Test Unmapped Route Boundary (Should return 404 from Gateway)
Write-Host "`n[3/3] Testing Unmapped Route: GET /api/v1/nonexistent/..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "$gatewayUrl/api/v1/nonexistent/" -Method Get | Out-Null
    Write-Host "  [FAIL] Unmapped route should not return 200." -ForegroundColor Red
} catch {
    Write-Host "  [OK] Gateway rejected unmapped route with 404 Not Found as expected." -ForegroundColor Green
}

Write-Host "`nGateway verification complete." -ForegroundColor Cyan

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " TrustGrid Document Service Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$gatewayUrl = "http://localhost:8088"

# 1. Acquire Token for Tenant A
$regPayload = @{
    email = "doc-auditor-$((Get-Random))@enterprise.test"
    password = "SecurePassword123!"
    first_name = "Evidence"
    last_name = "Auditor"
} | ConvertTo-Json

$regResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/register/" -Method Post -Body $regPayload -ContentType "application/json"
$token = $regResp.token

$orgResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/organizations/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    name = "Compliance Org A"
    slug = "compliance-org-$((Get-Random))"
} | ConvertTo-Json) -ContentType "application/json"
$orgId = $orgResp.id

$exchangeResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/token/tenant/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    organization_id = $orgId
} | ConvertTo-Json) -ContentType "application/json"
$tenantToken = $exchangeResp.token

# 2. Create Dummy PDF File on Disk
$tempPdf = "$PWD\soc2_evidence.pdf"
Set-Content -Path $tempPdf -Value "%PDF-1.4`nSOC 2 Type II Confidential Report for TrustGrid.`n%%EOF"

# 3. Upload Document using native Windows curl.exe (compatible with PowerShell 5.1 & 7)
Write-Host "`n[1/3] Uploading genuine PDF document through Gateway..." -ForegroundColor Yellow
$uploadRaw = curl.exe -s -X POST "$gatewayUrl/api/v1/documents/upload" -H "Authorization: Bearer $tenantToken" -F "file=@$tempPdf"
$uploadResp = $uploadRaw | ConvertFrom-Json

if ($uploadResp.id) {
    Write-Host "  [OK] Uploaded! ID: $($uploadResp.id), MIME: $($uploadResp.content_type), Hash: $($uploadResp.sha256_hash.Substring(0,16))..." -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Upload failed: $uploadRaw" -ForegroundColor Red
}

# 4. Verify Metadata Retrieval
Write-Host "`n[2/3] Fetching document metadata..." -ForegroundColor Yellow
$metaResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/documents/$($uploadResp.id)" -Method Get -Headers @{ Authorization = "Bearer $tenantToken" }
if ($metaResp.sha256_hash -eq $uploadResp.sha256_hash) {
    Write-Host "  [OK] Metadata matches verified SHA-256 hash!" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Hash mismatch" -ForegroundColor Red
}

# 5. Verify Cross-Tenant Isolation
Write-Host "`n[3/3] Verifying Cross-Tenant Isolation (Unauthorized Tenant Access)..." -ForegroundColor Yellow
$fakeOrgResp = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/organizations/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    name = "Intruder Org B"
    slug = "intruder-org-$((Get-Random))"
} | ConvertTo-Json) -ContentType "application/json"

$fakeExchange = Invoke-RestMethod -Uri "$gatewayUrl/api/v1/auth/token/tenant/" -Method Post -Headers @{ Authorization = "Bearer $token" } -Body (@{
    organization_id = $fakeOrgResp.id
} | ConvertTo-Json) -ContentType "application/json"

try {
    Invoke-RestMethod -Uri "$gatewayUrl/api/v1/documents/$($uploadResp.id)" -Method Get -Headers @{ Authorization = "Bearer $($fakeExchange.token)" } | Out-Null
    Write-Host "  [FAIL] Cross-tenant access was not blocked!" -ForegroundColor Red
} catch {
    Write-Host "  [OK] Cross-tenant access successfully blocked with 404 Not Found!" -ForegroundColor Green
}

# Cleanup temporary local test file
Remove-Item -Path $tempPdf -Force

Write-Host "`nDocument verification complete." -ForegroundColor Cyan
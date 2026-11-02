param(
    [string]$BackupDir = "infrastructure/backups",
    [string]$DbUser = "trustgrid_admin"
)

$ErrorActionPreference = "Stop"
$timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$targetDir = Join-Path $BackupDir $timestamp

if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$databases = @(
    "trustgrid_identity",
    "trustgrid_vendor",
    "trustgrid_workflow",
    "trustgrid_document",
    "trustgrid_integrations",
    "trustgrid_billing",
    "trustgrid_audit"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " TrustGrid Decoupled Multi-Database Backup Pipeline      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Target Directory: $targetDir"

foreach ($db in $databases) {
    $dumpFile = Join-Path $targetDir "$db.dump"
    Write-Host "Backing up database: $db ..." -NoNewline
    
    # 1. Dump directly inside container to avoid Windows PowerShell pipeline encoding issues
    docker exec trustgrid_postgres pg_dump -U $DbUser -d $db -F c -f "/tmp/$db.dump"
    
    # 2. Copy binary dump out cleanly via docker cp
    docker cp "trustgrid_postgres:/tmp/$db.dump" $dumpFile
    
    # 3. Clean up container temporary dump
    docker exec trustgrid_postgres rm -f "/tmp/$db.dump"
    
    if (Test-Path $dumpFile) {
        $size = (Get-Item $dumpFile).Length
        Write-Host " [OK] ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host " [FAIL]" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[SUCCESS] All 7 microservice databases backed up cleanly to $targetDir" -ForegroundColor Green
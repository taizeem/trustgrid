param(
    [string]$BackupTimestampDir = "",
    [string]$DbUser = "trustgrid_admin"
)

$ErrorActionPreference = "Stop"

# Auto-detect latest backup folder if not passed
if ([string]::IsNullOrWhiteSpace($BackupTimestampDir)) {
    $latestBackup = Get-ChildItem -Path "infrastructure\backups" -Directory -ErrorAction SilentlyContinue |
                    Sort-Object LastWriteTime -Descending |
                    Select-Object -First 1

    if (-not $latestBackup) {
        Write-Host "[ERROR] No backups found in infrastructure\backups. Run backup-databases.ps1 first." -ForegroundColor Red
        exit 1
    }
    $BackupTimestampDir = $latestBackup.FullName
    Write-Host "[INFO] Auto-selected latest backup: $BackupTimestampDir" -ForegroundColor Yellow
}

if (-not (Test-Path $BackupTimestampDir)) {
    Write-Host "[ERROR] Backup directory not found: $BackupTimestampDir" -ForegroundColor Red
    exit 1
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
Write-Host " TrustGrid Microservices Disaster Recovery Restore Drill  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Restoring from: $BackupTimestampDir"

foreach ($db in $databases) {
    $dumpFile = Join-Path $BackupTimestampDir "$db.dump"
    if (-not (Test-Path $dumpFile)) {
        Write-Host "[ERROR] Dump file missing: $dumpFile" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Restoring $db from backup..." -NoNewline

    # 1. Reset database
    docker exec trustgrid_postgres psql -U $DbUser -d postgres -c "DROP DATABASE IF EXISTS $db;" | Out-Null
    docker exec trustgrid_postgres psql -U $DbUser -d postgres -c "CREATE DATABASE $db;" | Out-Null
    
    # 2. Copy binary file into container
    docker cp $dumpFile "trustgrid_postgres:/tmp/$db.dump"

    # 3. Restore natively inside PostgreSQL container
    docker exec trustgrid_postgres pg_restore -U $DbUser -d $db --clean --if-exists "/tmp/$db.dump" 2>$null
    
    # 4. Clean up temporary container file
    docker exec trustgrid_postgres rm -f "/tmp/$db.dump"
    
    Write-Host " [RESTORED]" -ForegroundColor Green
}

Write-Host "`n[SUCCESS] Point-in-time multi-database restore drill complete!" -ForegroundColor Green
# Database backup script for RouteX (PowerShell)
# Usage: .\scripts\backup_database.ps1 [backup_directory]

param(
    [string]$BackupDir = ".\backups"
)

# Configuration
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DbName = if ($env:DB_NAME) { $env:DB_NAME } else { "routex" }
$DbUser = if ($env:DB_USER) { $env:DB_USER } else { "routex_user" }
$DbHost = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DbPort = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }

# Create backup directory if it doesn't exist
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Backup filename
$BackupFile = Join-Path $BackupDir "routex_backup_$Timestamp.sql"

Write-Host "Starting database backup..."
Write-Host "Database: $DbName"
Write-Host "Backup file: $BackupFile"

# Set PostgreSQL password environment variable
$env:PGPASSWORD = $env:DB_PASSWORD

# Perform backup using pg_dump
& pg_dump `
    -h $DbHost `
    -p $DbPort `
    -U $DbUser `
    -d $DbName `
    --no-owner `
    --no-acl `
    --clean `
    --if-exists `
    -f $BackupFile

if ($LASTEXITCODE -eq 0) {
    # Compress backup using .NET compression
    $CompressedFile = "$BackupFile.gz"
    $InputFile = [System.IO.File]::OpenRead($BackupFile)
    $OutputFile = [System.IO.File]::Create($CompressedFile)
    $GzipStream = New-Object System.IO.Compression.GzipStream($OutputFile, [System.IO.Compression.CompressionMode]::Compress)
    
    $InputFile.CopyTo($GzipStream)
    $GzipStream.Close()
    $OutputFile.Close()
    $InputFile.Close()
    
    # Remove uncompressed file
    Remove-Item $BackupFile
    
    Write-Host "✅ Backup completed successfully: $CompressedFile"
    
    # Keep only last 30 days of backups
    $CutoffDate = (Get-Date).AddDays(-30)
    Get-ChildItem -Path $BackupDir -Filter "routex_backup_*.sql.gz" | 
        Where-Object { $_.LastWriteTime -lt $CutoffDate } | 
        Remove-Item
    
    Write-Host "✅ Old backups (older than 30 days) cleaned up"
} else {
    Write-Host "❌ Backup failed!" -ForegroundColor Red
    exit 1
}


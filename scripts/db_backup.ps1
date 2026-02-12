# Backup local PostgreSQL database for migration to VPS
# Запуск: .\scripts\db_backup.ps1 [output.sql]
# Требует: .env в корне проекта (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
# Для загрузки .env: Get-Content .env | ForEach-Object { if ($_ -match '^([^#][^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process') } }

param(
    [string]$OutputFile = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
)

$rootDir = Split-Path $PSScriptRoot -Parent
if (Test-Path "$rootDir\.env") {
    Get-Content "$rootDir\.env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, 'Process')
            Set-Item -Path "Env:$key" -Value $val
        }
    }
}

$env:PGPASSWORD = $env:DB_PASSWORD
$outputPath = Join-Path $rootDir $OutputFile

Write-Host "Backing up database $($env:DB_NAME) to $outputPath..."
pg_dump -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -F p -f $outputPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backup completed: $outputPath"
    Write-Host "File size: $((Get-Item $outputPath).Length / 1MB) MB"
} else {
    Write-Host "Backup failed!" -ForegroundColor Red
    exit 1
}

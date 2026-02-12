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

# Поиск pg_dump (может быть не в PATH)
$pgDump = $null
if (Get-Command pg_dump -ErrorAction SilentlyContinue) {
    $pgDump = "pg_dump"
} else {
    $pgPaths = @(
        "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"
    )
    foreach ($p in $pgPaths) {
        if (Test-Path $p) {
            $pgDump = $p
            break
        }
    }
}

if (-not $pgDump) {
    Write-Host "pg_dump не найден. Установите PostgreSQL клиент или добавьте bin в PATH:" -ForegroundColor Red
    Write-Host "  https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "  Или: C:\Program Files\PostgreSQL\16\bin\ - в переменную PATH"
    exit 1
}

Write-Host "Backing up database $($env:DB_NAME) to $outputPath..."
& $pgDump -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -F p -f $outputPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backup completed: $outputPath"
    Write-Host "File size: $((Get-Item $outputPath).Length / 1MB) MB"
} else {
    Write-Host "Backup failed!" -ForegroundColor Red
    exit 1
}

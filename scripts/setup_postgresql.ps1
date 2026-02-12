# PowerShell script для помощи с удалением PostgreSQL

Write-Host "=== PostgreSQL Removal Helper ===" -ForegroundColor Cyan
Write-Host ""

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  ВНИМАНИЕ: Скрипт должен быть запущен от имени администратора!" -ForegroundColor Yellow
    Write-Host "Нажмите правой кнопкой на PowerShell и выберите 'Запуск от имени администратора'" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Поиск установленных версий PostgreSQL
Write-Host "Поиск установленных версий PostgreSQL..." -ForegroundColor Green
$postgresVersions = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | 
    Where-Object {$_.DisplayName -like "*PostgreSQL*"} | 
    Select-Object DisplayName, DisplayVersion, UninstallString

if ($postgresVersions.Count -eq 0) {
    Write-Host "❌ PostgreSQL не найден в списке установленных программ" -ForegroundColor Red
    Write-Host "Возможно, он установлен в другом месте или уже удален" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Найдены следующие версии PostgreSQL:" -ForegroundColor Cyan
$index = 1
foreach ($version in $postgresVersions) {
    Write-Host "$index. $($version.DisplayName) (версия $($version.DisplayVersion))" -ForegroundColor White
    $index++
}

Write-Host ""
$choice = Read-Host "Выберите номер версии для удаления (или 'q' для выхода)"

if ($choice -eq 'q' -or $choice -eq 'Q') {
    Write-Host "Отменено пользователем" -ForegroundColor Yellow
    exit 0
}

$selectedVersion = $postgresVersions[$choice - 1]

if (-not $selectedVersion) {
    Write-Host "❌ Неверный выбор" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Выбрано: $($selectedVersion.DisplayName)" -ForegroundColor Cyan
Write-Host ""

# Остановка служб PostgreSQL
Write-Host "Остановка служб PostgreSQL..." -ForegroundColor Green
$services = Get-Service | Where-Object {$_.Name -like "*postgres*"}
if ($services) {
    foreach ($service in $services) {
        if ($service.Status -eq 'Running') {
            Write-Host "  Остановка службы: $($service.Name)" -ForegroundColor Yellow
            Stop-Service -Name $service.Name -Force
        }
    }
} else {
    Write-Host "  Службы PostgreSQL не найдены" -ForegroundColor Yellow
}

Write-Host ""
$confirm = Read-Host "Вы уверены, что хотите удалить $($selectedVersion.DisplayName)? (yes/no)"

if ($confirm -ne 'yes' -and $confirm -ne 'y' -and $confirm -ne 'да') {
    Write-Host "Отменено пользователем" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Запуск удаления..." -ForegroundColor Green

# Извлечение пути к uninstaller
$uninstallString = $selectedVersion.UninstallString
if ($uninstallString -match '^"(.*?)"') {
    $uninstaller = $matches[1]
    $args = $uninstallString.Substring($matches[0].Length).Trim()
} else {
    $parts = $uninstallString -split ' ', 2
    $uninstaller = $parts[0]
    $args = if ($parts.Count -gt 1) { $parts[1] } else { "" }
}

# Добавление флага тихой установки, если его нет
if ($args -notmatch '/S') {
    $args = "$args /S"
}

Write-Host "Выполняется: $uninstaller $args" -ForegroundColor Cyan
Start-Process -FilePath $uninstaller -ArgumentList $args -Wait -NoNewWindow

Write-Host ""
Write-Host "✅ Удаление завершено!" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Скачайте PostgreSQL 18.1 с: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads" -ForegroundColor White
Write-Host "2. Установите PostgreSQL 18.1" -ForegroundColor White
Write-Host "3. Обновите .env файл с новым паролем" -ForegroundColor White

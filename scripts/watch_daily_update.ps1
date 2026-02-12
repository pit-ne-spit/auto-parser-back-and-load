# PowerShell script to watch daily update progress in real-time
$processId = 20552  # Current PID
$logFile = "logs\app.log"

Write-Host "=== Monitoring Daily Update Progress ===" -ForegroundColor Cyan
Write-Host "Process ID: $processId" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$lastLine = ""

while ($true) {
    # Check if process is still running
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "`n[INFO] Process $processId is no longer running" -ForegroundColor Yellow
        break
    }
    
    # Read last lines from log file
    if (Test-Path $logFile) {
        $logTail = Get-Content $logFile -Tail 5 -ErrorAction SilentlyContinue
        
        foreach ($line in $logTail) {
            # Show progress lines
            if ($line -match "Daily update: Page \d+.*Records:") {
                $progress = $line -replace '.*\[INFO\] ', ''
                if ($progress -ne $lastLine) {
                    Write-Host "`r$progress" -NoNewline -ForegroundColor Green
                    $lastLine = $progress
                }
            }
            # Show important messages
            elseif ($line -match "ERROR|completed|Finished|Retrying") {
                Write-Host "`n$line" -ForegroundColor $(if ($line -match "ERROR") { "Red" } elseif ($line -match "completed|Finished") { "Green" } else { "Yellow" })
            }
        }
    }
    
    Start-Sleep -Seconds 1
}

Write-Host "`n`nMonitoring stopped." -ForegroundColor Cyan

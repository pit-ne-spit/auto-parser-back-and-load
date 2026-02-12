# PowerShell script to watch progress in real-time
$terminalFile = "C:\Users\parap\.cursor\projects\c-Users-parap-PycharmProjects-auto-parser-back-and-load\terminals\697811.txt"
$logFile = "logs\app.log"

Write-Host "=== Monitoring Initial Load Progress ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$lastProgress = ""

while ($true) {
    # Try to read from terminal file
    if (Test-Path $terminalFile) {
        $content = Get-Content $terminalFile -Tail 1 -ErrorAction SilentlyContinue
        if ($content -match "Page \d+.*Records loaded.*Skipped.*Errors") {
            $progress = $matches[0]
            if ($progress -ne $lastProgress) {
                Write-Host "`r$progress" -NoNewline -ForegroundColor Green
                $lastProgress = $progress
            }
        }
    }
    
    # Also check logs for errors or completion
    if (Test-Path $logFile) {
        $logTail = Get-Content $logFile -Tail 3 -ErrorAction SilentlyContinue
        foreach ($line in $logTail) {
            if ($line -match "ERROR|completed|Retrying") {
                Write-Host "`n$line" -ForegroundColor $(if ($line -match "ERROR") { "Red" } elseif ($line -match "completed") { "Green" } else { "Yellow" })
            }
        }
    }
    
    Start-Sleep -Seconds 2
}

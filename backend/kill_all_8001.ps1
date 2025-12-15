$processIds = @(31684, 6208)
foreach ($procId in $processIds) {
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "Killed PID $procId"
    } catch {
        Write-Host "PID $procId not found or already stopped"
    }
}
Start-Sleep -Seconds 2
$remaining = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Still processes on 8001:"
    $remaining | ForEach-Object { Write-Host "  PID: $($_.OwningProcess)" }
} else {
    Write-Host "Port 8001 is now free"
}

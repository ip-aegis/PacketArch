$conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($conn) {
    $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Write-Host "Killed process on port 8001"
} else {
    Write-Host "No process on port 8001"
}

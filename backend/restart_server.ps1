# Kill all processes on port 8001
$conns = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($conns) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess | Where-Object { $_ -gt 0 } | Sort-Object -Unique
    foreach ($p in $pids) {
        Write-Host "Killing PID $p"
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 3
}

# Verify port is free
$remaining = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "ERROR: Port 8001 still in use"
    exit 1
}

Write-Host "Port 8001 is free"

# Clear pycache
Get-ChildItem -Path "D:\Dev\PacketArch\backend" -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cache cleared"

# Start the server with poetry
Set-Location "D:\Dev\PacketArch\backend"
Write-Host "Starting server..."
python -m poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

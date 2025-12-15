# Kill everything on port 8001
$conns = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($conns) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique
    foreach ($p in $pids) {
        Write-Host "Killing PID $p"
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 3
}

# Clear pycache
Get-ChildItem -Path "D:\Dev\PacketArch\backend" -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Cache cleared"

# Start the server
Set-Location "D:\Dev\PacketArch\backend"
python -m poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

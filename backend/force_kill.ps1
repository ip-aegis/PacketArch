Stop-Process -Id 6208 -Force -ErrorAction SilentlyContinue
Stop-Process -Id 31684 -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
netstat -ano | Select-String ':8001'

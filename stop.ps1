$ErrorActionPreference = "Stop"
docker compose down
Write-Host "GrantCurrent v0.7 Classic stopped. The named data volume was kept." -ForegroundColor Green

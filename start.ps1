$ErrorActionPreference = "Stop"
Write-Host "Starting GrantCurrent v0.7 Classic..." -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker was not found. Install/open Docker Desktop first."
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example" -ForegroundColor DarkGray
}

$old5173 = docker ps --filter "publish=5173" --format "{{.Names}}"
$old8000 = docker ps --filter "publish=8000" --format "{{.Names}}"
$blocking = @($old5173; $old8000) | Where-Object { $_ -and ($_ -notlike "grantcurrent_v7_classic-*") } | Select-Object -Unique
if ($blocking.Count -gt 0) {
  Write-Host "Ports 5173/8000 are currently used by: $($blocking -join ', ')" -ForegroundColor Yellow
  Write-Host "Stop the old GrantCurrent containers first, for example: docker stop <container-name>" -ForegroundColor Yellow
  throw "Required ports are already in use."
}

docker compose up --build -d
Start-Sleep -Seconds 2
docker compose ps

try {
  $health = Invoke-RestMethod http://localhost:8000/health
  Write-Host "Backend health: $($health.status) · version $($health.version)" -ForegroundColor Green
} catch {
  Write-Host "Backend did not answer health check yet. Run: docker compose logs backend --tail 100" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "GrantCurrent: http://localhost:5173" -ForegroundColor Green
Write-Host "API health:   http://localhost:8000/health" -ForegroundColor Green
Write-Host "API docs:     http://localhost:8000/docs" -ForegroundColor Green

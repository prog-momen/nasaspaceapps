# Starts the Python AI service (if its venv exists) and the Next.js dev server.
# Usage: powershell -File scripts/dev-all.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$rag = Join-Path $root "nasa-challenge-API\earthtrend_rag"
$py = Join-Path $rag ".venv\Scripts\python.exe"
$health = "http://127.0.0.1:8000/api/rag/health"
$aiProc = $null

function Test-Health {
  try { return Invoke-RestMethod -Uri $health -TimeoutSec 3 } catch { return $null }
}

if (Test-Path $py) {
  if (Test-Health) {
    Write-Host "AI service already running on :8000, reusing it."
  } else {
    Write-Host "Starting AI service..."
    $aiProc = Start-Process -FilePath $py -WorkingDirectory $rag -PassThru -WindowStyle Minimized `
      -ArgumentList @("-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000")
    $h = $null
    for ($i = 0; $i -lt 60 -and -not $h; $i++) { Start-Sleep -Seconds 2; $h = Test-Health }
    if (-not $h) { Write-Warning "AI service did not answer within 2 minutes; continuing without it." }
  }
  $h = Test-Health
  if ($h) {
    $text = $h | ConvertTo-Json -Depth 5 -Compress
    $ready = $text -match '"(indexed_chunks|chunks|points_count|count)":\s*[1-9]'
    Write-Host "AI service: http://127.0.0.1:8000/"
    if ($ready) { Write-Host "Knowledge index: ready" }
    else {
      Write-Host "Knowledge index: NOT ready (or not detected). Build it once (about 3-4 min):"
      Write-Host "  Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/rag/ingest -ContentType application/json -Body '{`"reset`":true,`"force`":true,`"include_resources`":true}'"
    }
  }
} else {
  Write-Host "No Python venv at $py - skipping AI service (chat will use offline mode)."
}

Write-Host "Web app: http://localhost:3000"
try {
  Set-Location $root
  npm run dev
} finally {
  if ($aiProc -and -not $aiProc.HasExited) {
    Write-Host "Stopping the AI service started by this script..."
    Stop-Process -Id $aiProc.Id -ErrorAction SilentlyContinue
  }
}

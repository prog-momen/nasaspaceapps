<#
  EarthTrend Explorer - start the local test prototype (Windows PowerShell).
  - uses the project virtual environment (.venv); installs declared dependencies on first run
  - binds ONLY to 127.0.0.1 (no firewall change, not reachable from other machines)
  - picks the first free port from 8000 (override: $env:EARTHTREND_PORT), waits until the backend answers, opens the browser
  Usage:  powershell -ExecutionPolicy Bypass -File start_prototype.ps1 [-NoBrowser] [-Install]
#>
param([switch]$NoBrowser, [switch]$Install)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Data = Join-Path $Root "data"; New-Item -ItemType Directory -Force $Data | Out-Null
$PidFile = Join-Path $Data "server.pid"; $PortFile = Join-Path $Data "server.port"
$Log = Join-Path $Data "server.log"; $ErrLog = Join-Path $Data "server.err.log"
$Py = Join-Path $Root ".venv\Scripts\python.exe"

# 1) environment
if (-not (Test-Path $Py)) {
  Write-Host "First run: creating the virtual environment (.venv) ..."
  $sys = (Get-Command python -ErrorAction SilentlyContinue)
  if (-not $sys) { Write-Host "ERROR: Python 3.11+ not found on PATH. Install it from https://www.python.org/downloads/ and re-run." -ForegroundColor Red; exit 1 }
  & python -m venv .venv; $Install = $true
}
if ($Install) { Write-Host "Installing declared dependencies (requirements.txt) - this can take several minutes the first time ..."; & $Py -m pip install -r requirements.txt; if ($LASTEXITCODE) { Write-Host "ERROR: pip install failed." -ForegroundColor Red; exit 1 } }
& $Py -c "import fastapi, uvicorn, qdrant_client, sentence_transformers, google.genai, scipy" 2>$null
if ($LASTEXITCODE) { Write-Host "ERROR: dependencies are missing. Run:  powershell -ExecutionPolicy Bypass -File start_prototype.ps1 -Install" -ForegroundColor Red; exit 1 }

# 2) already running?
if (Test-Path $PidFile) {
  $old = Get-Content $PidFile -ErrorAction SilentlyContinue
  if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
    $p = Get-Content $PortFile -ErrorAction SilentlyContinue
    Write-Host "Already running (PID $old) at http://127.0.0.1:$p/  - use stop_prototype.ps1 to stop it."; if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$p/" }; exit 0
  }
  Remove-Item $PidFile -ErrorAction SilentlyContinue
}

# 3) configuration notes (never prints secret values)
$envFiles = @((Join-Path $Root ".env"), (Join-Path (Split-Path $Root -Parent) ".env"))
$envFiles += Get-ChildItem -LiteralPath (Join-Path (Split-Path $Root -Parent) ([string][char[]](0x627,0x644,0x628,0x631,0x648,0x62A,0x648,0x62A,0x627,0x64A,0x628))) -Force -Filter "*.env" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
$found = $envFiles | Where-Object { Test-Path -LiteralPath $_ }
if (-not $found) { Write-Host "NOTE: no .env file found - Gemini and key-based providers are disabled (the rest works). See .env.example." -ForegroundColor Yellow }

# 4) port
$start = if ($env:EARTHTREND_PORT) { [int]$env:EARTHTREND_PORT } else { 8000 }
$port = $null
foreach ($c in $start..($start + 10)) {
  $busy = Get-NetTCPConnection -State Listen -LocalPort $c -ErrorAction SilentlyContinue
  if (-not $busy) { $port = $c; break } else { Write-Host "Port $c is in use by another program - trying the next one." -ForegroundColor Yellow }
}
if (-not $port) { Write-Host "ERROR: no free port in $start..$($start + 10). Set EARTHTREND_PORT to a free port." -ForegroundColor Red; exit 1 }

# 5) launch (hidden, local only)
$args = @("-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "$port", "--log-level", "info")
$proc = Start-Process -FilePath $Py -ArgumentList $args -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $Log -RedirectStandardError $ErrLog
$proc.Id | Set-Content $PidFile; "$port" | Set-Content $PortFile
Write-Host "Starting backend (PID $($proc.Id)) on http://127.0.0.1:$port/ - loading the embedding model (can take ~30-60 s the first time) ..."

# 6) readiness
$ready = $false
foreach ($i in 1..120) {
  if ($proc.HasExited) { Write-Host "ERROR: the backend exited. Last log lines:" -ForegroundColor Red; Get-Content $ErrLog -Tail 15; Remove-Item $PidFile -ErrorAction SilentlyContinue; exit 1 }
  try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/api/rag/health" -TimeoutSec 3; if ($r.StatusCode -eq 200) { $ready = $true; break } } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { Write-Host "ERROR: backend did not become ready in 120 s. See $ErrLog" -ForegroundColor Red; exit 1 }
Write-Host "READY:  http://127.0.0.1:$port/   (stop with: powershell -ExecutionPolicy Bypass -File stop_prototype.ps1)" -ForegroundColor Green
Write-Host "Logs:   $Log  |  $ErrLog"
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$port/" }

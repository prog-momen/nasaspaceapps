<# Stops the local prototype started by start_prototype.ps1 (kills only the PID recorded in data\server.pid and its children). #>
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $Root "data\server.pid"
if (-not (Test-Path $PidFile)) { Write-Host "Not running (no data\server.pid)."; exit 0 }
$id = Get-Content $PidFile
$p = Get-Process -Id $id -ErrorAction SilentlyContinue
if ($p -and $p.ProcessName -like "python*") { taskkill /PID $id /T /F | Out-Null; Write-Host "Stopped backend PID $id." } else { Write-Host "Process $id is not the prototype backend (already stopped)." }
Remove-Item $PidFile, (Join-Path $Root "data\server.port") -ErrorAction SilentlyContinue

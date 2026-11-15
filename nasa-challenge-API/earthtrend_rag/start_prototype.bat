@echo off
rem Double-click launcher: starts the local EarthTrend Explorer prototype (127.0.0.1 only).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_prototype.ps1" %*
pause

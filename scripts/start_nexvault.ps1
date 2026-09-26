# ==============================================================================
# NEXVAULT — Unified Hackathon Launcher
# Launches the 6 Storage Nodes, Control Plane Coordinator, and React Frontend
# ==============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "                    NEXVAULT UNIFIED LAUNCHER                     " -ForegroundColor Cyan
Write-Host "                  Storage that survives failure.                  " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

# 1. Start Storage Nodes & Coordinator
Write-Host "`n[1/2] Starting Storage Nodes (Ports 5001-5006) & Coordinator (Port 8000)..." -ForegroundColor Yellow
python scripts/start_cluster.py

# 2. Start Frontend Dev Server
Write-Host "`n[2/2] Starting React Frontend Dev Server (Port 5173)..." -ForegroundColor Yellow
Set-Location "$RootDir\frontend"

Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "$RootDir\frontend"

Start-Sleep -Seconds 2

Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host "       NEXVAULT SYSTEM SUCCESSFULLY LAUNCHED AND RUNNING!         " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "🖥️  React Frontend Dashboard : http://localhost:5173" -ForegroundColor White
Write-Host "📡 Control Plane API        : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "📖 Interactive Swagger Docs : http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "⚡ Storage Nodes (Zone A)   : Ports 5001, 5002, 5003" -ForegroundColor White
Write-Host "⚡ Storage Nodes (Zone B)   : Ports 5004, 5005, 5006" -ForegroundColor White
Write-Host "`nDemo Accounts:" -ForegroundColor Magenta
Write-Host "  Admin: admin@nexvault.io / admin123" -ForegroundColor Magenta
Write-Host "  User:  demo@nexvault.io  / demo123" -ForegroundColor Magenta
Write-Host "`nTo check health: python scripts/demo_preflight.py" -ForegroundColor Cyan
Write-Host "To reset state:  python scripts/demo_reset.py" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# ============================================
# SIH Project – Ollama Setup Script (Windows)
# ============================================
# Run this script in PowerShell to set up Ollama
# Usage: .\scripts\setup_ollama.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SIH Project – Ollama Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is installed
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaPath) {
    Write-Host "[!] Ollama is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please download and install Ollama from:" -ForegroundColor Yellow
    Write-Host "  https://ollama.com/download" -ForegroundColor Green
    Write-Host ""
    Write-Host "After installing, re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Ollama is installed: $($ollamaPath.Source)" -ForegroundColor Green

# Check if Ollama is running
Write-Host ""
Write-Host "Checking if Ollama server is running..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[OK] Ollama server is running." -ForegroundColor Green
} catch {
    Write-Host "[!] Ollama server is not running. Starting it..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "[OK] Ollama server started." -ForegroundColor Green
}

# Pull the model
$model = "qwen3:8b"
Write-Host ""
Write-Host "Pulling model: $model ..." -ForegroundColor Yellow
Write-Host "(This may take a while on first download)" -ForegroundColor DarkGray
Write-Host ""

& ollama pull $model

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] Model '$model' is ready!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[!] Failed to pull model '$model'." -ForegroundColor Red
    exit 1
}

# Final status
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. pip install -r requirements.txt" -ForegroundColor White
Write-Host "  2. uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  3. Open http://localhost:8000" -ForegroundColor White
Write-Host ""

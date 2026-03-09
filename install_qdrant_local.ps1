# Qdrant Local Installation Script for Windows
# This script downloads and sets up Qdrant to run locally without Docker

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "QDRANT LOCAL INSTALLATION FOR WINDOWS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$QdrantVersion = "v1.7.4"
$DownloadUrl = "https://github.com/qdrant/qdrant/releases/download/$QdrantVersion/qdrant-x86_64-pc-windows-msvc.zip"
$InstallDir = "$PSScriptRoot\qdrant"
$ZipFile = "$PSScriptRoot\qdrant.zip"

Write-Host "Step 1: Creating installation directory..." -ForegroundColor Yellow
if (Test-Path $InstallDir) {
    Write-Host "  Directory already exists: $InstallDir" -ForegroundColor Green
} else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Host "  Created directory: $InstallDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Downloading Qdrant $QdrantVersion..." -ForegroundColor Yellow
Write-Host "  URL: $DownloadUrl" -ForegroundColor Gray

try {
    # Download with progress
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipFile -UseBasicParsing
    Write-Host "  Download complete!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to download Qdrant" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Extracting Qdrant..." -ForegroundColor Yellow

try {
    Expand-Archive -Path $ZipFile -DestinationPath $InstallDir -Force
    Write-Host "  Extraction complete!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Failed to extract Qdrant" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 4: Cleaning up..." -ForegroundColor Yellow
Remove-Item $ZipFile -Force
Write-Host "  Removed temporary zip file" -ForegroundColor Green

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Qdrant has been installed to: $InstallDir" -ForegroundColor White
Write-Host ""
Write-Host "To start Qdrant, run:" -ForegroundColor Yellow
Write-Host "  .\qdrant\qdrant.exe" -ForegroundColor White
Write-Host ""
Write-Host "Or use the provided start script:" -ForegroundColor Yellow
Write-Host "  .\start_qdrant.ps1" -ForegroundColor White
Write-Host ""

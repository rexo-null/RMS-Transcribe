# RMS Transcribe - Interactive Release Builder
# This script interactively creates a new release with specified version

param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   RMS Transcribe - Release Builder" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Get version from user if not provided
if (-not $Version) {
    $defaultVersion = "1.0.0"
    Write-Host "Enter version number (default: $defaultVersion)" -ForegroundColor Yellow
    Write-Host "Format: X.Y.Z (e.g., 1.0.0, 1.1.0, 2.0.0)" -ForegroundColor Gray
    $userInput = Read-Host "Version"
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        $Version = $defaultVersion
    } else {
        $Version = $userInput.Trim()
    }
}

# Validate version format
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Error "Invalid version format! Use X.Y.Z (e.g., 1.0.0)"
    exit 1
}

Write-Host ""
Write-Host "Building release version: $Version" -ForegroundColor Green
Write-Host ""

# Confirmation
Write-Host "This will create:" -ForegroundColor Yellow
Write-Host "  - RMS-Transcribe-Windows-v$Version.zip" -ForegroundColor White
Write-Host "  - RMS-Transcribe-Setup-v$Version.exe (if Inno Setup installed)" -ForegroundColor White
Write-Host ""
$confirm = Read-Host "Continue? (Y/n)"

if ($confirm -and $confirm.ToLower() -eq 'n') {
    Write-Host "Build cancelled." -ForegroundColor Red
    exit 0
}

# Check prerequisites
Write-Host ""
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found! Install from https://python.org"
    exit 1
}
Write-Host "  Python: OK" -ForegroundColor Green

# Check project root
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$projectRoot\src\main.py")) {
    Write-Error "Project structure invalid! main.py not found in src/"
    exit 1
}
Write-Host "  Project: OK" -ForegroundColor Green

# Check icon exists
$iconPath = "$projectRoot\assets\icon.ico"
if (-not (Test-Path $iconPath)) {
    Write-Warning "Icon not found at assets\icon.ico"
    Write-Host "  Installer will use default icon" -ForegroundColor Yellow
} else {
    Write-Host "  Icon: OK" -ForegroundColor Green
}

# Clean previous release files with same version
Write-Host ""
Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
$artifacts = @(
    "RMS-Transcribe-Windows-v$Version.zip",
    "RMS-Transcribe-Setup-v$Version.exe",
    "RMS-Transcribe-Windows-v$Version"
)

foreach ($artifact in $artifacts) {
    if (Test-Path $artifact) {
        Remove-Item -Path $artifact -Recurse -Force
        Write-Host "  Removed: $artifact" -ForegroundColor Gray
    }
}

# Run the build script
Write-Host ""
Write-Host "Starting build process..." -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\build_windows.ps1" -Version $Version

# Check results
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Build Results" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$zipPath = "RMS-Transcribe-Windows-v$Version.zip"
$exePath = "RMS-Transcribe-Setup-v$Version.exe"

$success = $true

if (Test-Path $zipPath) {
    $zipSize = (Get-Item $zipPath).Length / 1MB
    Write-Host "  ZIP: $zipPath ($([math]::Round($zipSize, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "  ZIP: NOT FOUND" -ForegroundColor Red
    $success = $false
}

if (Test-Path $exePath) {
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Host "  EXE: $exePath ($([math]::Round($exeSize, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "  EXE: NOT FOUND (Inno Setup may not be installed)" -ForegroundColor Yellow
}

Write-Host ""

if ($success) {
    Write-Host "  Release v$Version built successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Test the portable version: RMS-Transcribe-Windows-v$Version\app\RMS-Transcribe.exe" -ForegroundColor White
    Write-Host "  2. Test the installer: RMS-Transcribe-Setup-v$Version.exe" -ForegroundColor White
    Write-Host "  3. Create GitHub release and upload these files" -ForegroundColor White
    Write-Host "     URL: https://github.com/rexo-null/transcribe/releases/new?tag=v$Version" -ForegroundColor White
} else {
    Write-Host "  Build failed! Check errors above." -ForegroundColor Red
    exit 1
}

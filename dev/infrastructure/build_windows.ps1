# RMS Transcribe - Windows Build Script
param(
    [string]$Version = "1.0.1",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

Write-Host "=== RMS Transcribe Windows Builder v$Version ===" -ForegroundColor Cyan

# Paths
$infraRoot = $PSScriptRoot
$devRoot = Split-Path -Parent $infraRoot
$projectRoot = Split-Path -Parent $devRoot
$sourceRoot = Join-Path $projectRoot "source"
$outputRoot = Join-Path $devRoot "output"
$releasesDir = Join-Path $outputRoot "releases"

Write-Host "Source: $sourceRoot" -ForegroundColor Gray
Write-Host "Output: $releasesDir" -ForegroundColor Gray

# Check Python
Write-Host "`n[1/6] Checking Python..." -ForegroundColor Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { Write-Error "Python not found!" ; exit 1 }

# Check PyInstaller
Write-Host "`n[2/6] Checking PyInstaller..." -ForegroundColor Yellow
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) { pip install pyinstaller }

# Install requirements
Write-Host "`n[3/6] Installing dependencies..." -ForegroundColor Yellow
pip install -r "$sourceRoot\requirements.txt"

# Clean previous builds
Write-Host "`n[4/6] Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item -Path "$outputRoot\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$outputRoot\dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$releasesDir\RMS-Transcribe-Windows-v$Version" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$releasesDir\*.zip" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$releasesDir\*.exe" -Force -ErrorAction SilentlyContinue

# Build executable
Write-Host "`n[5/6] Building Windows executable..." -ForegroundColor Yellow
$mainPy = Join-Path $sourceRoot "src\main.py"

# Get lightning_fabric path for version.info
$lfPath = python -c "import lightning_fabric; import os; print(os.path.dirname(lightning_fabric.__file__))" 2>$null
$addData = ""
if ($lfPath -and (Test-Path "$lfPath\version.info")) {
    Write-Host "Found lightning_fabric version.info" -ForegroundColor Green
    $addData = "--add-data `"$lfPath\version.info;lightning_fabric`""
}

$pyinstallerCmd = "pyinstaller --noconfirm --clean --windowed --name `"RMS-Transcribe`" --icon `"$sourceRoot\assets\icon.ico`" --distpath `"$outputRoot\dist`" --workpath `"$outputRoot\build`" --specpath `"$outputRoot\build`" $addData `"$mainPy`""
Invoke-Expression $pyinstallerCmd

$exePath = "$outputRoot\dist\RMS-Transcribe\RMS-Transcribe.exe"
if (-not (Test-Path $exePath)) { Write-Error "Build failed!" ; exit 1 }
Write-Host "Executable built!" -ForegroundColor Green

# Create release package
Write-Host "`n[6/6] Creating release package..." -ForegroundColor Yellow
$releaseDir = "$releasesDir\RMS-Transcribe-Windows-v$Version"
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\app" -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\models" -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\results" -Force | Out-Null

Copy-Item -Path "$outputRoot\dist\RMS-Transcribe\*" -Destination "$releaseDir\app\" -Recurse -Force
Copy-Item -Path "$sourceRoot\requirements.txt" -Destination "$releaseDir\"
Copy-Item -Path "$sourceRoot\assets\icon.ico" -Destination "$releaseDir\app\" -Force

# Create SETUP.bat
$setupContent = @"
@echo off
echo ===================================
echo RMS Transcribe Desktop v$Version
echo Windows Setup
echo ===================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.
echo Setup complete! Run: app\RMS-Transcribe.exe
pause
"@
$setupContent | Out-File -FilePath "$releaseDir\SETUP.bat" -Encoding ASCII

# Create ZIP archive
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow
Compress-Archive -Path $releaseDir -DestinationPath "$releasesDir\RMS-Transcribe-Windows-v$Version.zip" -Force

# Build Inno Setup installer
if (-not $SkipInstaller) {
    $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $iscc) {
        Write-Host "`nBuilding Windows installer..." -ForegroundColor Yellow
        
        # Copy ISS to releases folder (where source files are) and update version
        $issContent = Get-Content "$infraRoot\installer.iss" -Raw
        $issContent = $issContent -replace '#define MyAppVersion "[\d.]+"', "#define MyAppVersion `"$Version`""
        $issContent | Out-File -FilePath "$releasesDir\installer.iss" -Encoding ASCII
        
        # Run ISCC from releases folder so relative paths work
        Push-Location $releasesDir
        & $iscc "installer.iss"
        Pop-Location
        
        if (Test-Path "$releasesDir\RMS-Transcribe-Setup-v$Version.exe") {
            Write-Host "`n✅ Installer created" -ForegroundColor Green
        }
    } else {
        Write-Warning "Inno Setup not found"
    }
}

Write-Host "`n✅ Build complete!" -ForegroundColor Green
Write-Host "`nFiles in: $releasesDir" -ForegroundColor Cyan
Get-ChildItem -Path "$releasesDir\RMS-Transcribe-*" | ForEach-Object { Write-Host "  - $($_.Name)" }

Pop-Location

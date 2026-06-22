# Build storage_system desktop release (Windows).
# Run from repo root or app/:  .\build.ps1

$ErrorActionPreference = 'Stop'
$AppRoot = $PSScriptRoot
Set-Location $AppRoot

$config = Get-Content (Join-Path $AppRoot 'config.json') -Raw | ConvertFrom-Json
$appName = 'storage_system'
$version = $config.appVersion
$distDir = Join-Path $AppRoot "dist\$appName"
$archive = Join-Path $AppRoot "dist\storage_system-$version-win64.zip"

Write-Host "Syncing dependencies..."
uv sync

Write-Host "Building $appName $version..."
uv run nicegui-pack `
    --name $appName `
    --onedir `
    --windowed `
    --icon dashboard.ico `
    --add-data "assets;assets" `
    --add-data "config.json;." `
    --add-data "dashboard.ico;." `
    --clean `
    --noconfirm `
    main.py

if (-not (Test-Path $distDir)) {
    throw "Build failed: $distDir not found"
}

Write-Host "Creating archive $archive..."
if (Test-Path $archive) { Remove-Item $archive -Force }
Compress-Archive -Path $distDir -DestinationPath $archive

Write-Host ""
Write-Host "Done."
Write-Host "  Run:  $distDir\$appName.exe"
Write-Host "  Zip:  $archive"
Write-Host ""
Write-Host "Note: objects.db is created next to the exe on first run."
Write-Host "      Copy an existing objects.db into dist\$appName\ to ship pre-filled data."

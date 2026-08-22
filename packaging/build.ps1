#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "=== Сборка Тренажёра вестибулярного аппарата ==="

python -m pip install -r requirements.txt -r requirements-build.txt
python packaging\make_icon.py
python -m PyInstaller VestibularTrainer.spec --noconfirm --clean

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "PyInstaller готов: dist\VestibularTrainer\VestibularTrainer.exe"
    Write-Host "Для установщика установите Inno Setup 6 и снова запустите этот скрипт."
    Write-Host "https://jrsoftware.org/isinfo.php"
    exit 0
}

New-Item -ItemType Directory -Force -Path packaging\output | Out-Null
& $iscc packaging\installer.iss
Write-Host "Установщик: packaging\output\RehabTrainerSetup-1.0.0.exe"

param(
    [string]$RunDirectory = "runs\e00\canonical-seed-17",
    [string]$OutputPath = "runs\e00\canonical-seed-17\verification.json"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\scripts\00-setup.ps1 first."
}

& $Python -m relate.verification.e00 $RunDirectory --output $OutputPath

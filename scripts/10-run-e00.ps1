param(
    [string]$OutputDirectory = "runs\e00\canonical-seed-17",
    [int]$Seed = 17,
    [int]$Samples = 4096,
    [int]$Dimensions = 64
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\scripts\00-setup.ps1 first."
}

& $Python -m relate.experiments.e00 `
    --output $OutputDirectory `
    --seed $Seed `
    --samples $Samples `
    --dimensions $Dimensions

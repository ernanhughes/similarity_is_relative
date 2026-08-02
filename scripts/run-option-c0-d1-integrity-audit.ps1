param(
    [string]$Identity = "artifacts/canonical/option-b/option-b-external-identity-v1.json",
    [string]$FirewallDir = "artifacts/canonical/option-c0/data-firewall-v1",
    [string]$Output = "runs/option-c0/d1-integrity-audit-v1/option-c0-d1-integrity-audit-v1.json",
    [string]$Cache = ".writer/option-c0/cache/option-c0-d1-integrity-v1.sqlite3",
    [string]$V1ExecutionRef = "07cf6fc5ea9c261b10df272215a8afb404612e76",
    [int]$NearHamming = 3,
    [int]$NearMaxBucket = 250,
    [int]$NearMaxPairs = 50000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (Test-Path $Output) {
    throw "D1 audit output already exists: $Output"
}

$OutputDirectory = Split-Path -Parent $Output
$LogDirectory = Join-Path $OutputDirectory "logs"
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$LogPath = Join-Path $LogDirectory "option-c0-d1-integrity-audit.log"

Write-Host "=================================================="
Write-Host "Option C0-D1 visible-role integrity audit"
Write-Host "=================================================="
Write-Host "SQLite cache: $Cache"
Write-Host "Output:       $Output"
Write-Host "Log:          $LogPath"
Write-Host ""
Write-Host "Hidden C0-selection and C1 row contents remain inaccessible."
Write-Host "Repository-family diagnostics use only the published allocation names."
Write-Host ""

$Arguments = @(
    "--identity", $Identity,
    "--firewall-dir", $FirewallDir,
    "--output", $Output,
    "--cache", $Cache,
    "--repo-root", $RepoRoot,
    "--v1-execution-ref", $V1ExecutionRef,
    "--near-hamming", $NearHamming,
    "--near-max-bucket", $NearMaxBucket,
    "--near-max-pairs", $NearMaxPairs
)

& relate-option-c0-audit-d1 @Arguments 2>&1 | Tee-Object -FilePath $LogPath
$ExitCode = $LASTEXITCODE
if ($ExitCode -ne 0) {
    throw "Option C0-D1 audit failed with exit code $ExitCode. See $LogPath"
}

Write-Host ""
Write-Host "=================================================="
Write-Host "Option C0-D1 audit completed"
Write-Host "=================================================="
Write-Host "Result: $Output"
Write-Host "Cache retained for exact resume: $Cache"
Write-Host "Next action: review D1 findings before implementing D2."

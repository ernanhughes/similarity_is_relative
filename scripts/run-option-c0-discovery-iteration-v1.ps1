param(
    [string] $ResultsBranch = "agent/option-c0-iteration-results-v1",
    [string] $Device = "cuda"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-NativeExit {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Step,
        [Parameter(Mandatory = $true)]
        [int] $ExitCode
    )
    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Step,
        [Parameter(Mandatory = $true)]
        [string] $Executable,
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments,
        [Parameter(Mandatory = $true)]
        [string] $StdoutPath,
        [Parameter(Mandatory = $true)]
        [string] $StderrPath
    )
    Remove-Item $StdoutPath -Force -ErrorAction SilentlyContinue
    Remove-Item $StderrPath -Force -ErrorAction SilentlyContinue
    $Process = Start-Process `
        -FilePath $Executable `
        -ArgumentList $Arguments `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath
    if ($Process.ExitCode -ne 0) {
        if (Test-Path $StderrPath) {
            Write-Host ""
            Write-Host "=== $Step stderr ==="
            Get-Content -LiteralPath $StderrPath |
                Select-Object -Last 120 |
                ForEach-Object { Write-Host $_ }
        }
        throw "$Step failed with exit code $($Process.ExitCode)."
    }
}

$RepoRoot = (Get-Location).Path
$HarnessMergeCommit = "784353e4d2400e570d29c5b75ac611bd04e6664e"
$ImplementationCommit = "d36436209d95eca555215a83856f042d241a90f4"
$ExpectedPlanFileSha256 = "5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d"
$ExpectedPlanCanonicalSha256 = "f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94"
$ExpectedRegistryFileSha256 = "a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282"

$Plan = "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-initial-candidate-plan-v1.json"
$Registry = "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-candidate-registry-v1.jsonl"
$Identity = "artifacts/canonical/option-b/option-b-external-identity-v1.json"
$Firewall = "artifacts/canonical/option-c0/data-firewall-v1"
$RunDir = "runs/option-c0/discovery-v1"
$CanonicalDir = "artifacts/canonical/option-c0/discovery-v1"
$Stdout = "runs/option-c0/discovery-v1.stdout.log"
$Stderr = "runs/option-c0/discovery-v1.stderr.log"

if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "Run this script from the similarity_is_relative repository root."
}

Write-Host ""
Write-Host "=== Synchronizing reviewed main ==="
git fetch origin
Assert-NativeExit -Step "git fetch" -ExitCode $LASTEXITCODE

git switch main
Assert-NativeExit -Step "switch main" -ExitCode $LASTEXITCODE

git pull --ff-only origin main
Assert-NativeExit -Step "fast-forward main" -ExitCode $LASTEXITCODE

git merge-base --is-ancestor $HarnessMergeCommit HEAD
Assert-NativeExit -Step "verify harness ancestry" -ExitCode $LASTEXITCODE

git merge-base --is-ancestor $ImplementationCommit HEAD
if ($LASTEXITCODE -ne 0) {
    throw (
        "Registered implementation commit is not in main ancestry. " +
        "The candidate-plan PR must be merged with a regular merge commit, not squash."
    )
}

$Dirty = @(git status --porcelain)
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "The Git worktree must be clean before C0 iteration execution."
}

$RemoteBranch = git ls-remote --heads origin $ResultsBranch
if ($RemoteBranch) {
    throw "Remote results branch already exists: $ResultsBranch"
}
$LocalBranch = git branch --list $ResultsBranch
if ($LocalBranch) {
    throw "Local results branch already exists: $ResultsBranch"
}

foreach ($Path in @($RunDir, $CanonicalDir)) {
    if (Test-Path $Path) {
        throw "C0 discovery output already exists: $Path. Do not overwrite or rerun."
    }
}
foreach ($Path in @($Plan, $Registry, $Identity, $Firewall)) {
    if (-not (Test-Path $Path)) {
        throw "Required frozen input is missing: $Path"
    }
}

$ObservedPlanFile = (Get-FileHash $Plan -Algorithm SHA256).Hash.ToLowerInvariant()
$ObservedRegistryFile = (Get-FileHash $Registry -Algorithm SHA256).Hash.ToLowerInvariant()
$ObservedPlanCanonical = @'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
payload = json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode()
print(hashlib.sha256(payload).hexdigest())
'@ | python - $Plan
Assert-NativeExit -Step "canonical candidate-plan hashing" -ExitCode $LASTEXITCODE
$ObservedPlanCanonical = ([string]$ObservedPlanCanonical).Trim().ToLowerInvariant()

if ($ObservedPlanFile -ne $ExpectedPlanFileSha256) {
    throw "Candidate-plan file hash mismatch: $ObservedPlanFile"
}
if ($ObservedPlanCanonical -ne $ExpectedPlanCanonicalSha256) {
    throw "Candidate-plan canonical JSON hash mismatch: $ObservedPlanCanonical"
}
if ($ObservedRegistryFile -ne $ExpectedRegistryFileSha256) {
    throw "Candidate-registry file hash mismatch: $ObservedRegistryFile"
}

Write-Host "Candidate plan and registry identities verified."
Write-Host "  plan file:      $ObservedPlanFile"
Write-Host "  plan canonical: $ObservedPlanCanonical"
Write-Host "  registry file:  $ObservedRegistryFile"

Write-Host ""
Write-Host "=== Validating the reviewed implementation ==="
python -m pip install -e ".[dev,option-b]"
Assert-NativeExit -Step "editable installation" -ExitCode $LASTEXITCODE

ruff check .
Assert-NativeExit -Step "Ruff" -ExitCode $LASTEXITCODE

python -m pytest -q tests/test_option_c0_discovery_runner.py
Assert-NativeExit -Step "focused discovery tests" -ExitCode $LASTEXITCODE

python -m pytest -q
Assert-NativeExit -Step "full test suite" -ExitCode $LASTEXITCODE

git diff --check
Assert-NativeExit -Step "whitespace validation" -ExitCode $LASTEXITCODE

$Dirty = @(git status --porcelain)
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "Validation changed the worktree. Stop before scientific execution."
}

Write-Host ""
Write-Host "=== Creating the result branch ==="
git switch -c $ResultsBranch
Assert-NativeExit -Step "create results branch" -ExitCode $LASTEXITCODE

$env:PYTHONHASHSEED = "0"
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:VECLIB_MAXIMUM_THREADS = "1"
$env:BLIS_NUM_THREADS = "1"

$Command = Get-Command "relate-option-c0-discover" -ErrorAction Stop

Write-Host ""
Write-Host "=== Validating candidate plan and registry ==="
& $Command.Source `
    --plan $Plan `
    --registry $Registry `
    --canonical-firewall-dir $Firewall `
    --validate-only
Assert-NativeExit -Step "candidate-plan validation" -ExitCode $LASTEXITCODE

Write-Host ""
Write-Host "=== Running the one-time C0 iteration experiment ==="
Write-Host "This is exploratory. C0 selection and C1 evidence remain inaccessible."

$Arguments = @(
    "--plan", "`"$Plan`"",
    "--registry", "`"$Registry`"",
    "--identity", "`"$Identity`"",
    "--canonical-firewall-dir", "`"$Firewall`"",
    "--output-dir", "`"$RunDir`"",
    "--device", $Device
)
Invoke-LoggedProcess `
    -Step "C0 iteration experiment" `
    -Executable $Command.Source `
    -Arguments $Arguments `
    -StdoutPath $Stdout `
    -StderrPath $Stderr

Write-Host ""
Write-Host "=== Appending evaluated events and packaging evidence ==="

$env:OPTION_C0_RUN_DIR = $RunDir
$env:OPTION_C0_CANONICAL_DIR = $CanonicalDir
$env:OPTION_C0_PLAN = $Plan
$env:OPTION_C0_REGISTRY = $Registry

@'
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from relate.experiments.option_c0_data_firewall import (
    append_discovery,
    read_candidate_registry,
    record_candidate_evaluation,
)

run_dir = Path(os.environ["OPTION_C0_RUN_DIR"])
canonical_dir = Path(os.environ["OPTION_C0_CANONICAL_DIR"])
plan_path = Path(os.environ["OPTION_C0_PLAN"])
registry_seed = Path(os.environ["OPTION_C0_REGISTRY"])
result_path = run_dir / "option-c0-discovery-iteration-v1.json"
registry_path = run_dir / "option-c0-candidate-registry-v1.jsonl"
discovery_path = run_dir / "option-c0-discovery-ledger-v1.jsonl"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


result = json.loads(result_path.read_text(encoding="utf-8"))
if result["status"] != "C0_ITERATION_EXPLORATORY_RESULTS_PENDING_LEDGER_PUBLICATION":
    raise RuntimeError("unexpected C0 iteration status")
for field in ("scientific_result_observed", "c0_selection_accessed", "c1_rows_selected"):
    if result[field] is not False:
        raise RuntimeError(f"forbidden result state: {field}")
if result["mechanism_result_observed"] is not True:
    raise RuntimeError("iteration mechanism result was not recorded")
if registry_path.read_bytes() != registry_seed.read_bytes():
    raise RuntimeError("runner changed the registered candidate seed")

result_sha = sha256(result_path)
registrations = [
    event
    for event in read_candidate_registry(registry_path)
    if event["event_type"] == "REGISTERED"
]
for event in registrations:
    record_candidate_evaluation(
        registry_path,
        candidate_id=event["candidate_id"],
        version=event["version"],
        commit_sha=event["commit_sha"],
        timestamp="2026-08-02T16:00:00Z",
        artifact_hashes={"iteration_result": result_sha},
    )

# No discovery interpretation is fabricated automatically. The empty ledger
# proves that interpretation has not yet been added by the review stage.
discovery_path.write_bytes(b"")

canonical_dir.mkdir(parents=True, exist_ok=False)
for source in (result_path, registry_path, discovery_path):
    shutil.copyfile(source, canonical_dir / source.name)

publication = {
    "checkpoint_id": "option-c0-discovery-iteration-publication-v1",
    "status": "C0_ITERATION_RESULTS_PUBLISHED_PENDING_REVIEW",
    "scientific_result_observed": False,
    "mechanism_result_observed": True,
    "c0_selection_accessed": False,
    "c1_rows_selected": False,
    "candidate_registry_entries": len(read_candidate_registry(registry_path)),
    "candidate_registrations": len(registrations),
    "candidate_evaluations": len(registrations),
    "discovery_ledger_entries": 0,
    "artifacts": {
        path.name: {
            "file_sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in (
            canonical_dir / result_path.name,
            canonical_dir / registry_path.name,
            canonical_dir / discovery_path.name,
            plan_path,
        )
    },
    "next_allowed_action": "C0_ITERATION_RESULT_AND_DISCOVERY_REVIEW",
    "prohibited_actions": [
        "C0 selection access before registry closure",
        "C1 reserve access",
        "C1 row selection",
        "Option C scientific decision",
    ],
}
publication_path = canonical_dir / "option-c0-discovery-iteration-publication-v1.json"
publication_path.write_text(
    json.dumps(publication, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps(publication, indent=2, sort_keys=True))
'@ | python -
Assert-NativeExit -Step "package exploratory C0 evidence" -ExitCode $LASTEXITCODE

Write-Host ""
Write-Host "=== Committing the exploratory result checkpoint ==="
git add -- $CanonicalDir
Assert-NativeExit -Step "stage C0 iteration evidence" -ExitCode $LASTEXITCODE

git diff --cached --check
Assert-NativeExit -Step "staged whitespace validation" -ExitCode $LASTEXITCODE

git commit -m "Publish exploratory Option C0 iteration results"
Assert-NativeExit -Step "commit C0 iteration evidence" -ExitCode $LASTEXITCODE

git push -u origin $ResultsBranch
Assert-NativeExit -Step "push C0 iteration result branch" -ExitCode $LASTEXITCODE

Write-Host ""
Write-Host "=================================================="
Write-Host "Exploratory Option C0 iteration results pushed."
Write-Host "=================================================="
Write-Host "Branch: $ResultsBranch"
Write-Host "Next action: review results and append genuine discovery-ledger observations."
Write-Host "Do not access C0 selection yet."

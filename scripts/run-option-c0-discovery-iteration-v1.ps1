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
$CandidatePlanMergeCommit = "59cb6232ec9813742216536397ebe1bdeaf1f05c"

$ExpectedPlanFileSha256 = "5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d"
$ExpectedPlanCanonicalSha256 = "7de70669553f180ea0507c68b28dc790e896019d664055fbaa0a535b550c10c6"
$ExpectedRegistryFileSha256 = "a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282"
$ExpectedErratumFileSha256 = "c1fa786fc5932bd5157ac2659ef8e6c58eb421d0d3200f339b6a096f362dc3dc"
$StalePublishedDigest = "f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94"

$PlanDir = "artifacts/canonical/option-c0/candidate-plan-v1"
$Plan = "$PlanDir/option-c0-initial-candidate-plan-v1.json"
$Registry = "$PlanDir/option-c0-candidate-registry-v1.jsonl"
$Erratum = "$PlanDir/option-c0-candidate-plan-identity-erratum-v1.json"
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

foreach ($Commit in @($HarnessMergeCommit, $ImplementationCommit, $CandidatePlanMergeCommit)) {
    git merge-base --is-ancestor $Commit HEAD
    Assert-NativeExit -Step "verify reviewed ancestry $Commit" -ExitCode $LASTEXITCODE
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
foreach ($Path in @($Plan, $Registry, $Erratum, $Identity, $Firewall)) {
    if (-not (Test-Path $Path)) {
        throw "Required frozen input is missing: $Path"
    }
}

Write-Host ""
Write-Host "=== Verifying candidate-plan identities and pre-execution erratum ==="
@'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

(
    plan_path,
    registry_path,
    erratum_path,
    expected_plan_file,
    expected_plan_canonical,
    expected_registry_file,
    expected_erratum_file,
    stale_digest,
) = sys.argv[1:]


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


plan_bytes = Path(plan_path).read_bytes()
if sha256(plan_bytes) != expected_plan_file:
    raise RuntimeError("candidate-plan exact file identity mismatch")

plan = json.loads(plan_bytes)
canonical = json.dumps(
    plan,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode()
if sha256(canonical) != expected_plan_canonical:
    raise RuntimeError("candidate-plan canonical JSON identity mismatch")

registry_bytes = Path(registry_path).read_bytes()
if sha256(registry_bytes) != expected_registry_file:
    raise RuntimeError("candidate-registry exact file identity mismatch")

erratum_bytes = Path(erratum_path).read_bytes()
if sha256(erratum_bytes) != expected_erratum_file:
    raise RuntimeError("candidate-plan identity erratum file mismatch")
erratum = json.loads(erratum_bytes)

registrations = [
    json.loads(line)["payload"]
    for line in registry_bytes.decode().splitlines()
    if line.strip()
]
if len(registrations) != 6:
    raise RuntimeError("expected exactly six pre-execution registrations")
if any(event.get("event_type") != "REGISTERED" for event in registrations):
    raise RuntimeError("pre-execution registry contains a non-registration event")
if any(
    event.get("artifact_hashes", {}).get("candidate_plan") != stale_digest
    for event in registrations
):
    raise RuntimeError("registry stale digest does not match the reviewed erratum")

expected_identities = {
    "exact_file_sha256": expected_plan_file,
    "canonical_json_sha256": expected_plan_canonical,
    "candidate_registry_file_sha256": expected_registry_file,
}
if erratum.get("correct_identities") != expected_identities:
    raise RuntimeError("erratum does not bind the corrected identities")
if erratum.get("stale_published_digest") != stale_digest:
    raise RuntimeError("erratum stale digest mismatch")
for field in (
    "scientific_result_observed",
    "mechanism_result_observed",
    "c0_selection_accessed",
    "c1_rows_selected",
    "result_branch_created",
):
    if erratum.get(field) is not False:
        raise RuntimeError(f"erratum must keep {field}=false")
if erratum.get("observed_before_execution") is not True:
    raise RuntimeError("erratum must be explicitly pre-execution")

print("Candidate plan, registry, and erratum identities verified.")
print(f"  plan file:      {expected_plan_file}")
print(f"  plan canonical: {expected_plan_canonical}")
print(f"  registry file:  {expected_registry_file}")
print(f"  erratum file:   {expected_erratum_file}")
'@ | python - `
    $Plan `
    $Registry `
    $Erratum `
    $ExpectedPlanFileSha256 `
    $ExpectedPlanCanonicalSha256 `
    $ExpectedRegistryFileSha256 `
    $ExpectedErratumFileSha256 `
    $StalePublishedDigest
Assert-NativeExit -Step "candidate-plan identity and erratum verification" -ExitCode $LASTEXITCODE

Write-Host ""
Write-Host "=== Validating the reviewed implementation ==="
python -m pip install -e ".[dev,option-b]"
Assert-NativeExit -Step "editable installation" -ExitCode $LASTEXITCODE

ruff check .
Assert-NativeExit -Step "Ruff" -ExitCode $LASTEXITCODE

python -m pytest -q tests/test_option_c0_candidate_plan_identities.py
Assert-NativeExit -Step "candidate-plan identity tests" -ExitCode $LASTEXITCODE

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
$env:OPTION_C0_ERRATUM = $Erratum
$env:OPTION_C0_EVALUATION_TIMESTAMP = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

@'
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from relate.experiments.option_c0_data_firewall import (
    read_candidate_registry,
    record_candidate_evaluation,
)

run_dir = Path(os.environ["OPTION_C0_RUN_DIR"])
canonical_dir = Path(os.environ["OPTION_C0_CANONICAL_DIR"])
plan_path = Path(os.environ["OPTION_C0_PLAN"])
registry_seed = Path(os.environ["OPTION_C0_REGISTRY"])
erratum_path = Path(os.environ["OPTION_C0_ERRATUM"])
evaluation_timestamp = os.environ["OPTION_C0_EVALUATION_TIMESTAMP"]

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
if len(registrations) != 6:
    raise RuntimeError("expected six registered candidates")
for event in registrations:
    record_candidate_evaluation(
        registry_path,
        candidate_id=event["candidate_id"],
        version=event["version"],
        commit_sha=event["commit_sha"],
        timestamp=evaluation_timestamp,
        artifact_hashes={"iteration_result": result_sha},
    )

# Interpretation remains a separate human review step.
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
    "candidate_plan_identity_erratum_sha256": sha256(erratum_path),
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
            erratum_path,
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

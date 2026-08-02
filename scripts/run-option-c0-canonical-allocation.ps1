param(
    [string] $BranchName = "agent/option-c0-canonical-allocation-v1"
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
$ImplementationMergeCommit = "d401dd01f66ca328d3b4d7ee92f53986eb1f636a"
$ReviewedSetupCommit = "b5f523271de3bafb5ce9922ae772d06dbd8524d4"
$ExpectedConfigSha256 = (
    "09190fedbe9623af8307382f781da77598da38bf7546bd6e9b9f0ca703acef20"
)

if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "Run this script from the similarity_is_relative repository root."
}

$Identity = "artifacts/canonical/option-b/option-b-external-identity-v1.json"
$OptionBSelection = "artifacts/canonical/option-b/selection"
$AllocationConfig = (
    "artifacts/canonical/option-c0/option-c0-allocation-config-v1.json"
)
$RunDir = "runs/option-c0/canonical-data-firewall-v1"
$CanonicalDir = "artifacts/canonical/option-c0/data-firewall-v1"
$CheckpointDoc = (
    "docs/results/option-c0-canonical-repository-allocation-checkpoint-v1.md"
)
$AllocatorStdout = "runs/option-c0/canonical-data-firewall-v1.stdout.log"
$AllocatorStderr = "runs/option-c0/canonical-data-firewall-v1.stderr.log"
$VerifierStdout = "runs/option-c0/canonical-data-firewall-independent-v1.stdout.log"
$VerifierStderr = "runs/option-c0/canonical-data-firewall-independent-v1.stderr.log"

Write-Host ""
Write-Host "=== Synchronizing the reviewed allocation branch ==="

git fetch origin
Assert-NativeExit -Step "git fetch" -ExitCode $LASTEXITCODE

git switch $BranchName
Assert-NativeExit -Step "switch allocation branch" -ExitCode $LASTEXITCODE

git pull --ff-only origin $BranchName
Assert-NativeExit -Step "fast-forward allocation branch" -ExitCode $LASTEXITCODE

git merge-base --is-ancestor $ImplementationMergeCommit HEAD
Assert-NativeExit `
    -Step "verify data-firewall implementation ancestry" `
    -ExitCode $LASTEXITCODE

git merge-base --is-ancestor $ReviewedSetupCommit HEAD
Assert-NativeExit `
    -Step "verify reviewed allocation setup ancestry" `
    -ExitCode $LASTEXITCODE

$Dirty = @(git status --porcelain)
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "The Git worktree must be clean before canonical allocation."
}

foreach ($Path in @($RunDir, $CanonicalDir, $CheckpointDoc)) {
    if (Test-Path $Path) {
        throw (
            "Canonical allocation output already exists: $Path. " +
            "Do not overwrite or rerun the allocation."
        )
    }
}

foreach ($Path in @($Identity, $OptionBSelection, $AllocationConfig)) {
    if (-not (Test-Path $Path)) {
        throw "Required frozen input is missing: $Path"
    }
}

$ObservedConfigSha256 = (
    Get-FileHash -LiteralPath $AllocationConfig -Algorithm SHA256
).Hash.ToLowerInvariant()

if ($ObservedConfigSha256 -ne $ExpectedConfigSha256) {
    throw (
        "Allocation configuration hash mismatch. Expected " +
        "$ExpectedConfigSha256 but observed $ObservedConfigSha256."
    )
}

New-Item -ItemType Directory -Force "runs/option-c0" | Out-Null

$env:PYTHONHASHSEED = "0"
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:VECLIB_MAXIMUM_THREADS = "1"
$env:BLIS_NUM_THREADS = "1"

Write-Host ""
Write-Host "=== Installing reviewed Option C0 allocation code ==="

python -m pip install -e ".[dev,option-b]"
Assert-NativeExit -Step "editable installation" -ExitCode $LASTEXITCODE

$Allocator = Get-Command "relate-option-c0-prepare-firewall" -ErrorAction Stop
$Verifier = Get-Command "relate-option-c0-verify-firewall" -ErrorAction Stop

Write-Host ""
Write-Host "=== Generating the one-time canonical repository allocation ==="
Write-Host "No mechanism, metric, or scientific result is evaluated in this stage."

$AllocatorArguments = @(
    "--identity", "`"$Identity`"",
    "--option-b-selection-dir", "`"$OptionBSelection`"",
    "--allocation-config", "`"$AllocationConfig`"",
    "--output-dir", "`"$RunDir`""
)

Invoke-LoggedProcess `
    -Step "canonical C0 repository allocation" `
    -Executable $Allocator.Source `
    -Arguments $AllocatorArguments `
    -StdoutPath $AllocatorStdout `
    -StderrPath $AllocatorStderr

$CandidateRegistry = Join-Path `
    $RunDir `
    "option-c0-candidate-registry-v1.jsonl"
$DiscoveryLedger = Join-Path `
    $RunDir `
    "option-c0-discovery-ledger-v1.jsonl"

[System.IO.File]::WriteAllBytes($CandidateRegistry, [byte[]]@())
[System.IO.File]::WriteAllBytes($DiscoveryLedger, [byte[]]@())

Write-Host ""
Write-Host "=== Independently reconstructing and verifying the allocation ==="

$VerifierArguments = @(
    "--identity", "`"$Identity`"",
    "--option-b-selection-dir", "`"$OptionBSelection`"",
    "--allocation-config", "`"$AllocationConfig`"",
    "--result-dir", "`"$RunDir`""
)

Invoke-LoggedProcess `
    -Step "independent C0 allocation recomputation" `
    -Executable $Verifier.Source `
    -Arguments $VerifierArguments `
    -StdoutPath $VerifierStdout `
    -StderrPath $VerifierStderr

Write-Host ""
Write-Host "=== Packaging verified canonical allocation evidence ==="

$env:OPTION_C0_RUN_DIR = $RunDir
$env:OPTION_C0_CANONICAL_DIR = $CanonicalDir
$env:OPTION_C0_CONFIG = $AllocationConfig
$env:OPTION_C0_CHECKPOINT_DOC = $CheckpointDoc
$env:OPTION_C0_IMPLEMENTATION_MERGE = $ImplementationMergeCommit
$env:OPTION_C0_SETUP_COMMIT = $ReviewedSetupCommit

@'
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

run_dir = Path(os.environ["OPTION_C0_RUN_DIR"])
canonical_dir = Path(os.environ["OPTION_C0_CANONICAL_DIR"])
config_path = Path(os.environ["OPTION_C0_CONFIG"])
checkpoint_path = Path(os.environ["OPTION_C0_CHECKPOINT_DOC"])
implementation_merge = os.environ["OPTION_C0_IMPLEMENTATION_MERGE"]
setup_commit = os.environ["OPTION_C0_SETUP_COMMIT"]

REPORT = "option-c0-data-firewall-v1.json"
ALLOCATION = "option-c0-repository-allocation-v1.jsonl"
EXCLUSIONS = "option-c0-option-b-excluded-repositories-v1.jsonl"
CANDIDATES = "option-c0-candidate-registry-v1.jsonl"
DISCOVERIES = "option-c0-discovery-ledger-v1.jsonl"
INDEPENDENT = "option-c0-data-firewall-independent-v1.json"
PUBLICATION = "option-c0-data-firewall-publication-v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


report = json.loads((run_dir / REPORT).read_text(encoding="utf-8"))
independent = json.loads(
    (run_dir / INDEPENDENT).read_text(encoding="utf-8")
)

if report["status"] != (
    "C0_REPOSITORY_ALLOCATION_GENERATED_PENDING_INDEPENDENT_VERIFICATION"
):
    raise RuntimeError("allocation report status is incomplete")
if independent["status"] != (
    "C0_CANONICAL_REPOSITORY_ALLOCATION_INDEPENDENTLY_RECOMPUTED"
):
    raise RuntimeError("independent verification status is incomplete")
if independent["runner_imported"] is not False:
    raise RuntimeError("independent verifier imported the allocation runner")

for field in (
    "scientific_result_observed",
    "mechanism_result_observed",
    "c1_rows_selected",
):
    if report[field] is not False or independent[field] is not False:
        raise RuntimeError(f"forbidden result state: {field}")

required_checks = (
    "eligible_pool_recomputed",
    "option_b_exclusion_recomputed",
    "allocation_exactly_equal",
    "role_counts_exactly_equal",
    "pairwise_role_disjointness",
    "option_b_repositories_excluded",
    "c1_reserve_undivided",
    "candidate_registry_empty",
    "discovery_ledger_empty",
)
for check in required_checks:
    if independent["checks"].get(check) is not True:
        raise RuntimeError(f"independent check failed: {check}")

for name in (CANDIDATES, DISCOVERIES):
    if (run_dir / name).read_bytes() != b"":
        raise RuntimeError(f"append-only ledger is not empty: {name}")

canonical_dir.mkdir(parents=True, exist_ok=False)
for name in (
    REPORT,
    ALLOCATION,
    EXCLUSIONS,
    CANDIDATES,
    DISCOVERIES,
    INDEPENDENT,
):
    shutil.copyfile(run_dir / name, canonical_dir / name)
    if sha256(run_dir / name) != sha256(canonical_dir / name):
        raise RuntimeError(f"canonical packaging changed bytes: {name}")

artifacts = {
    name: {
        "path": str((canonical_dir / name)).replace("\\", "/"),
        "file_sha256": sha256(canonical_dir / name),
        "bytes": (canonical_dir / name).stat().st_size,
    }
    for name in (
        REPORT,
        ALLOCATION,
        EXCLUSIONS,
        CANDIDATES,
        DISCOVERIES,
        INDEPENDENT,
    )
}
artifacts["allocation_config"] = {
    "path": str(config_path).replace("\\", "/"),
    "file_sha256": sha256(config_path),
    "bytes": config_path.stat().st_size,
}

publication = {
    "checkpoint_id": "option-c0-data-firewall-publication-v1",
    "status": "C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED_PENDING_REVIEW",
    "scientific_result_observed": False,
    "mechanism_result_observed": False,
    "c1_rows_selected": False,
    "candidate_registry_entries": 0,
    "discovery_ledger_entries": 0,
    "implementation_merge_commit": implementation_merge,
    "reviewed_setup_commit": setup_commit,
    "allocation_context_sha256": report["allocation_context_sha256"],
    "config_sha256": report["config_sha256"],
    "counts": independent["counts"],
    "role_counts": independent["role_counts"],
    "commitments": independent["commitments"],
    "independent_verification": {
        "verification_id": independent["verification_id"],
        "status": independent["status"],
        "runner_imported": independent["runner_imported"],
        "checks": independent["checks"],
    },
    "artifacts": artifacts,
    "next_allowed_action": "C0_MECHANISM_IMPLEMENTATION_REVIEW",
    "prohibited_actions": [
        "C0 mechanism execution before this checkpoint merges",
        "C0 selection access before candidate-registry closure",
        "C1 calibration row selection",
        "C1 test row selection",
        "Option C scientific decision",
    ],
}

publication_path = canonical_dir / PUBLICATION
publication_path.write_text(
    json.dumps(publication, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
    newline="\n",
)

roles = independent["role_counts"]
lines = [
    "# Option C0 Canonical Repository Allocation Checkpoint",
    "",
    "Date: 2026-08-02",
    "",
    "## Status",
    "",
    "```text",
    publication["status"],
    "scientific_result_observed = false",
    "mechanism_result_observed = false",
    "c1_rows_selected = false",
    "candidate_registry_entries = 0",
    "discovery_ledger_entries = 0",
    "```",
    "",
    "The complete eligible CodeSearchNet Python pool was reconstructed under "
    "the frozen Option B eligibility rules. Every repository represented in "
    "the canonical Option B selected manifests was excluded before whole-"
    "repository allocation.",
    "",
    "## Counts",
    "",
    "| Quantity | Count |",
    "|---|---:|",
    f"| Eligible rows | `{independent['counts']['eligible_rows']}` |",
    f"| Eligible repositories | `{independent['counts']['eligible_repositories']}` |",
    f"| Option B repositories excluded | "
    f"`{independent['counts']['option_b_excluded_repositories']}` |",
    f"| Repositories allocated | "
    f"`{independent['counts']['allocated_repositories']}` |",
    "",
    "## Role allocation",
    "",
    "| Role | Repositories | Eligible rows |",
    "|---|---:|---:|",
]
for role in ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve"):
    lines.append(
        f"| `{role}` | `{roles[role]['repositories']}` | "
        f"`{roles[role]['rows']}` |"
    )
lines.extend(
    [
        "",
        "The `c1_reserve` remains undivided. No final C1 calibration or test "
        "row identity exists.",
        "",
        "## Independent verification",
        "",
        "A standalone implementation that does not import the allocator "
        "independently reconstructed the eligible pool, Option B repository "
        "set, role quotas, repository order, complete allocation manifest, "
        "role counts and all commitments. Exact equality was required.",
        "",
        "All verification checks passed:",
        "",
    ]
)
for check in required_checks:
    lines.append(f"- `{check}`")
lines.extend(
    [
        "",
        "## Commitments",
        "",
        "```text",
        f"allocation context: {publication['allocation_context_sha256']}",
        f"eligible pool: {publication['commitments']['eligible_pool_sha256']}",
        "Option B repository set: "
        f"{publication['commitments']['option_b_repository_set_sha256']}",
        f"configuration: {publication['config_sha256']}",
        "```",
        "",
        "## Boundary",
        "",
        "This checkpoint contains no mechanism candidate, discovery "
        "observation, conformal threshold, risk–coverage metric, C1 row "
        "selection or Option C scientific result.",
        "",
        "After review and merge, the next permitted stage is a separate C0 "
        "mechanism-implementation PR. C0 mechanism execution remains blocked "
        "until that implementation is reviewed.",
        "",
    ]
)
checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
checkpoint_path.write_text(
    "\n".join(lines),
    encoding="utf-8",
    newline="\n",
)

print("C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED")
print("eligible_rows:", independent["counts"]["eligible_rows"])
print("eligible_repositories:", independent["counts"]["eligible_repositories"])
print(
    "option_b_excluded_repositories:",
    independent["counts"]["option_b_excluded_repositories"],
)
for role in ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve"):
    print(
        role + ":",
        roles[role]["repositories"],
        "repositories,",
        roles[role]["rows"],
        "rows",
    )
print("allocation_context_sha256:", publication["allocation_context_sha256"])
print("publication_sha256:", sha256(publication_path))
'@ | python -

Assert-NativeExit -Step "package canonical allocation" -ExitCode $LASTEXITCODE

Write-Host ""
Write-Host "=== Staging the verified allocation checkpoint ==="

git add -- `
    $CanonicalDir `
    $CheckpointDoc

Assert-NativeExit -Step "stage allocation evidence" -ExitCode $LASTEXITCODE

git diff --cached --check
Assert-NativeExit -Step "staged whitespace validation" -ExitCode $LASTEXITCODE

git diff --cached --stat

git commit -m "Publish canonical Option C0 repository allocation"
Assert-NativeExit -Step "commit allocation checkpoint" -ExitCode $LASTEXITCODE

git push origin $BranchName
Assert-NativeExit -Step "push allocation checkpoint" -ExitCode $LASTEXITCODE

Write-Host ""
Write-Host "=================================================="
Write-Host "Canonical Option C0 repository allocation pushed."
Write-Host "=================================================="
Write-Host ""
Write-Host "Branch:"
Write-Host "  $BranchName"
Write-Host ""
Write-Host "Next action:"
Write-Host "  Review the updated canonical allocation PR."
Write-Host ""
Write-Host "Do not register a mechanism candidate before that PR merges."

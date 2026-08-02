param(
    [string] $BranchName = "agent/option-b-probe-artifacts-v1"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-NativeExit {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Step,
        [int] $ExitCode = $LASTEXITCODE
    )

    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$RepoRoot = (Get-Location).Path

if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "Run this script from the similarity_is_relative repository root."
}

$MergedProbeRunnerCommit = "35d90fc7182d29bbbb93b2e3e34c5cc484e65a72"
$OutputDir = Join-Path $RepoRoot "runs/option-b/probes-v1"
$OutputLog = Join-Path $RepoRoot "runs/option-b/probes-v1.log"
$TargetDir = Join-Path $RepoRoot "artifacts/canonical/option-b/probes-v1"

$EmbeddingDir = Join-Path `
    $RepoRoot `
    "runs/option-b/gpu-fixed-batch-10/embeddings-a"

$ExpectedEmbeddingFiles = @(
    "option-b-embeddings-train-v2.npy",
    "option-b-embeddings-validation-v2.npy",
    "option-b-embeddings-test-v2.npy"
)

$PredictionFiles = @(
    "option-b-predicted-train-candidates-v1.npy",
    "option-b-predicted-validation-rows-v1.npy",
    "option-b-predicted-test-queries-v1.npy"
)

$ReportName = "option-b-primitive-probe-bundle-v1.json"
$PublicationName = "option-b-primitive-probe-publication-v1.json"

Write-Host ""
Write-Host "=== Synchronizing authoritative main ==="

git fetch origin
Assert-NativeExit "git fetch"

git switch main
Assert-NativeExit "switch to main"

git pull --ff-only origin main
Assert-NativeExit "fast-forward main"

git merge-base --is-ancestor $MergedProbeRunnerCommit HEAD
Assert-NativeExit "verify merged probe-runner ancestry"

$Dirty = @(git status --porcelain)
if ($Dirty.Count -ne 0) {
    $Dirty | ForEach-Object { Write-Host $_ }
    throw "The Git worktree must be clean before the one-time canonical fit."
}

$ExistingLocalBranch = git show-ref --verify --quiet "refs/heads/$BranchName"
if ($LASTEXITCODE -eq 0) {
    throw "Local branch already exists: $BranchName"
}

$ExistingRemoteBranch = git ls-remote --heads origin $BranchName
Assert-NativeExit "check remote artifact branch"
if ($ExistingRemoteBranch) {
    throw "Remote branch already exists: $BranchName"
}

if (Test-Path $TargetDir) {
    throw "Canonical probe target already exists: $TargetDir"
}

foreach ($Name in $ExpectedEmbeddingFiles) {
    $Path = Join-Path $EmbeddingDir $Name
    if (-not (Test-Path $Path)) {
        throw "Required reproduced embedding matrix is missing: $Path"
    }
}

Write-Host ""
Write-Host "=== Installing the merged runner ==="

python -m pip install -e ".[dev,option-b]"
Assert-NativeExit "editable installation"

# Freeze CPU linear-algebra execution before importing NumPy, SciPy, or scikit-learn.
$env:PYTHONHASHSEED = "0"
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:VECLIB_MAXIMUM_THREADS = "1"
$env:BLIS_NUM_THREADS = "1"

Write-Host ""
Write-Host "=== Running the one-time canonical primitive-probe fit ==="
Write-Host "Linear-algebra threads are frozen to 1."
Write-Host "Test primitive labels remain unopened."

Remove-Item $OutputDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $OutputLog -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path (Split-Path $OutputLog) | Out-Null

# Windows PowerShell 5.1 wraps any native stderr as NativeCommandError.
# Permit diagnostic stderr during the process, then enforce the real exit code.
$PreviousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

try {
    & relate-option-b-fit-probes `
        --embedding-dir $EmbeddingDir `
        --output-dir $OutputDir 2>&1 |
        Tee-Object -FilePath $OutputLog

    $FitExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $PreviousErrorActionPreference
}

Assert-NativeExit -Step "canonical primitive-probe fit" -ExitCode $FitExitCode

$ReportPath = Join-Path $OutputDir $ReportName
if (-not (Test-Path $ReportPath)) {
    throw "Probe report was not written: $ReportPath"
}

Write-Host ""
Write-Host "=== Independently validating fit outputs ==="

$env:OPTION_B_PROBE_OUTPUT = $OutputDir

@'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from relate.experiments.option_b_real_code import ALPHAS, PRIMITIVES, array_hash


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


root = Path(os.environ["OPTION_B_PROBE_OUTPUT"])
report_path = root / "option-b-primitive-probe-bundle-v1.json"
report = json.loads(report_path.read_text(encoding="utf-8"))

if report.get("probe_bundle_id") != "option-b-primitive-probe-bundle-v1":
    raise RuntimeError("Unexpected probe bundle ID")

if report.get("status") != "PRIMITIVE_PROBE_FIT_COMPLETE_PENDING_PUBLICATION_REVIEW":
    raise RuntimeError("Probe fit is not complete")

if report.get("scientific_result_observed") is not False:
    raise RuntimeError("Scientific-result boundary was crossed")

if report.get("next_allowed_action") != "CANONICAL_PROBE_ARTIFACT_PUBLICATION":
    raise RuntimeError("Unexpected next action")

if report.get("inputs", {}).get("test_primitive_labels_loaded") is not False:
    raise RuntimeError("Test primitive labels were loaded")

contract = report.get("contract", {})
if contract.get("status") != "PREDICTED_EXECUTOR_CONTRACT_COMPLETE":
    raise RuntimeError("Predicted-executor contract is incomplete")

if contract.get("folds") != 5:
    raise RuntimeError("Canonical fold count changed")

if tuple(sorted(float(value) for value in ALPHAS)) != (0.01, 0.1, 1.0, 10.0, 100.0):
    raise RuntimeError("Registered alpha grid changed")

if contract.get("prediction_rounding") != "forbidden":
    raise RuntimeError("Prediction rounding contract changed")

expected = {
    "train_candidates": (
        "option-b-predicted-train-candidates-v1.npy",
        20_000,
    ),
    "validation_rows": (
        "option-b-predicted-validation-rows-v1.npy",
        4_000,
    ),
    "test_queries": (
        "option-b-predicted-test-queries-v1.npy",
        4_000,
    ),
}

for role, (filename, rows) in expected.items():
    metadata = report["predictions"][role]
    path = root / filename
    values = np.load(path, allow_pickle=False)

    if values.shape != (rows, len(PRIMITIVES)):
        raise RuntimeError(f"{role}: invalid shape {values.shape}")

    if values.dtype != np.float64:
        raise RuntimeError(f"{role}: invalid dtype {values.dtype}")

    if not np.isfinite(values).all():
        raise RuntimeError(f"{role}: non-finite predictions")

    if metadata.get("array_sha256") != array_hash(values):
        raise RuntimeError(f"{role}: logical array hash mismatch")

    if metadata.get("file_sha256") != file_sha256(path):
        raise RuntimeError(f"{role}: file hash mismatch")

    if contract["prediction_sha256"][role] != array_hash(values):
        raise RuntimeError(f"{role}: contract prediction hash mismatch")

print("PRIMITIVE_PROBE_OUTPUTS_INDEPENDENTLY_VERIFIED")
print("bundle_sha256:", contract["bundle_sha256"])
print("report_file_sha256:", file_sha256(report_path))

for role, (filename, _) in expected.items():
    path = root / filename
    values = np.load(path, allow_pickle=False)
    print(role, values.shape, values.dtype, array_hash(values), file_sha256(path))
'@ | python -

Assert-NativeExit "independent probe-output validation"

Write-Host ""
Write-Host "=== Creating dedicated probe-artifact branch ==="

git switch -c $BranchName
Assert-NativeExit "create artifact branch"

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

$FilesToPromote = @($ReportName) + $PredictionFiles

foreach ($Name in $FilesToPromote) {
    $Source = Join-Path $OutputDir $Name
    $Target = Join-Path $TargetDir $Name

    if (-not (Test-Path $Source)) {
        throw "Missing probe artifact: $Source"
    }

    Copy-Item -LiteralPath $Source -Destination $Target -Force

    $SourceHash = Get-Sha256 $Source
    $TargetHash = Get-Sha256 $Target

    if ($SourceHash -ne $TargetHash) {
        throw "Promotion changed bytes for $Name"
    }

    Write-Host "$Name"
    Write-Host "  SHA256: $TargetHash"
}

Write-Host ""
Write-Host "=== Writing publication checkpoint ==="

$env:OPTION_B_PROBE_SOURCE = $OutputDir
$env:OPTION_B_PROBE_TARGET = $TargetDir

@'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from relate.experiments.option_b_real_code import array_hash


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


source = Path(os.environ["OPTION_B_PROBE_SOURCE"])
target = Path(os.environ["OPTION_B_PROBE_TARGET"])

report_name = "option-b-primitive-probe-bundle-v1.json"
report_path = target / report_name
report = json.loads(report_path.read_text(encoding="utf-8"))

files = {
    "train_candidates": "option-b-predicted-train-candidates-v1.npy",
    "validation_rows": "option-b-predicted-validation-rows-v1.npy",
    "test_queries": "option-b-predicted-test-queries-v1.npy",
}

predictions: dict[str, object] = {}

for role, filename in files.items():
    canonical_path = target / filename
    source_path = source / filename

    if canonical_path.read_bytes() != source_path.read_bytes():
        raise RuntimeError(f"{role}: promotion is not byte-identical")

    values = np.load(canonical_path, allow_pickle=False)
    predictions[role] = {
        "path": str(canonical_path).replace("\\", "/"),
        "rows": int(values.shape[0]),
        "columns": int(values.shape[1]),
        "dtype": str(values.dtype),
        "array_sha256": array_hash(values),
        "file_sha256": file_sha256(canonical_path),
        "row_order_sha256": report["contract"]["row_order_sha256"][role],
    }

checkpoint = {
    "checkpoint_id": "option-b-primitive-probe-publication-v1",
    "status": "PRIMITIVE_PROBE_ARTIFACTS_PUBLISHED_PENDING_REVIEW",
    "scientific_result_observed": False,
    "source_fit": {
        "path": str(report_path).replace("\\", "/"),
        "file_sha256": file_sha256(report_path),
        "probe_bundle_id": report["probe_bundle_id"],
        "bundle_sha256": report["contract"]["bundle_sha256"],
        "folds": report["contract"]["folds"],
        "alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0],
        "test_primitive_labels_loaded": report["inputs"][
            "test_primitive_labels_loaded"
        ],
    },
    "predictions": predictions,
    "fit_scope": report["fit_scope"],
    "next_allowed_action": "HARD_NEGATIVE_MANIFEST_IMPLEMENTATION_REVIEW",
    "prohibited_actions": [
        "hard-negative generation before this publication checkpoint merges",
        "scientific metric evaluation before the hard-negative checkpoint",
        "test-label use in preprocessing, fitting, or model selection",
        "prediction rounding",
        "threshold, query, model, language, or canonical-row changes",
    ],
}

checkpoint_path = target / "option-b-primitive-probe-publication-v1.json"
checkpoint_path.write_text(
    json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
    newline="\n",
)

print("Publication checkpoint:", checkpoint_path)
print("Status:", checkpoint["status"])
print("Bundle:", checkpoint["source_fit"]["bundle_sha256"])
print("File SHA256:", file_sha256(checkpoint_path))
'@ | python -

Assert-NativeExit "write probe publication checkpoint"

$PublicationPath = Join-Path $TargetDir $PublicationName
if (-not (Test-Path $PublicationPath)) {
    throw "Publication checkpoint was not written."
}

Write-Host ""
Write-Host "=== Committing and pushing probe artifacts ==="

git add -- `
    "artifacts/canonical/option-b/probes-v1"

Assert-NativeExit "stage probe artifacts"

git diff --cached --check
Assert-NativeExit "staged whitespace validation"

git diff --cached --stat

git commit -m "Publish canonical Option B primitive probes"
Assert-NativeExit "commit probe artifacts"

git push -u origin $BranchName
Assert-NativeExit "push probe artifact branch"

Write-Host ""
Write-Host "=================================================="
Write-Host "Canonical primitive-probe artifacts are pushed."
Write-Host "=================================================="
Write-Host ""
Write-Host "Branch:"
Write-Host "  $BranchName"
Write-Host ""
Write-Host "Canonical directory:"
Write-Host "  $TargetDir"
Write-Host ""
Write-Host "Scientific result observed:"
Write-Host "  false"
Write-Host ""
Write-Host "Next action:"
Write-Host "  Open and review the dedicated probe-artifact checkpoint PR."
Write-Host ""
Write-Host "Do not generate hard negatives or evaluate metrics yet."

param(
    [ValidateRange(1, 128)]
    [int] $BatchSize = 32,

    [string] $Device = "cuda"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExitCode {
    param([string] $Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

$RepoRoot = (Get-Location).Path

if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "Run this script from the similarity_is_relative repository root."
}

$SelectionDir = Join-Path `
    $RepoRoot `
    "artifacts/canonical/option-b/selection"

$CpuIdentity = Join-Path `
    $RepoRoot `
    "artifacts/canonical/option-b/option-b-embedding-identity-v2.json"

$GpuRoot = Join-Path `
    $RepoRoot `
    "runs/option-b/gpu-amended"

$GpuIdentity = Join-Path `
    $GpuRoot `
    "identity/option-b-embedding-identity-v2-gpu-amended.json"

$RunA = Join-Path $GpuRoot "embeddings-a"
$RunB = Join-Path $GpuRoot "embeddings-b"

$CacheA = Join-Path `
    $RepoRoot `
    ".writer/option-b/cache/gpu-amended-a.sqlite3"

$CacheB = Join-Path `
    $RepoRoot `
    ".writer/option-b/cache/gpu-amended-b.sqlite3"

$RawCheckpoint = Join-Path `
    $GpuRoot `
    "reproduction/option-b-gpu-amended-verifier-output.json"

$AmendedCheckpoint = Join-Path `
    $GpuRoot `
    "reproduction/option-b-gpu-amended-reproduction-checkpoint.json"

$RunALog = Join-Path $GpuRoot "embeddings-a.log"
$RunBLog = Join-Path $GpuRoot "embeddings-b.log"
$PreflightLog = Join-Path $GpuRoot "gpu-preflight.log"
$VerificationLog = Join-Path $GpuRoot "gpu-verification.log"

if (-not (Test-Path $CpuIdentity)) {
    throw "Frozen CPU identity not found: $CpuIdentity"
}

Write-Host ""
Write-Host "=== Installing current Option B tooling ==="

# python -m pip install -e ".[dev,option-b]"
# Assert-LastExitCode "Editable package installation"

Write-Host ""
Write-Host "=== Checking CUDA ==="

@'
import torch

print("Torch:", torch.__version__)
print("Torch CUDA runtime:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())

if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available")

print("GPU:", torch.cuda.get_device_name(0))
print(
    "VRAM GB:",
    round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
)
'@ | python -

Assert-LastExitCode "CUDA validation"

New-Item `
    -ItemType Directory `
    -Force `
    -Path (Split-Path $GpuIdentity) |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path (Split-Path $RawCheckpoint) |
    Out-Null

$env:OPTION_B_CPU_IDENTITY = $CpuIdentity
$env:OPTION_B_GPU_IDENTITY = $GpuIdentity

Write-Host ""
Write-Host "=== Creating separate GPU execution identity ==="

@'
from __future__ import annotations

import hashlib
import json
import os
import platform
from copy import deepcopy
from importlib import metadata
from pathlib import Path

import numpy as np
import torch

from relate.experiments.option_b_embedding import (
    canonical_embed_loaded,
    embedding_implementation_sha256,
    load_canonical_backend,
    tokenization_config,
    tokenization_config_sha256,
)
from relate.experiments.option_b_identity import FIXTURE_CODES
from relate.experiments.option_b_real_code import MODEL_ID, array_hash


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


cpu_path = Path(os.environ["OPTION_B_CPU_IDENTITY"])
gpu_path = Path(os.environ["OPTION_B_GPU_IDENTITY"])

cpu_identity = json.loads(cpu_path.read_text(encoding="utf-8"))

if cpu_identity.get("identity_id") != "option-b-embedding-identity-v2":
    raise RuntimeError("Unexpected frozen CPU identity ID")

if cpu_identity.get("status") != "EMBEDDING_IDENTITY_V2_COMPLETE":
    raise RuntimeError("Frozen CPU identity is incomplete")

if not torch.cuda.is_available():
    raise RuntimeError("CUDA is not available")

revision = cpu_identity["model"]["revision"]

tokenizer, model, torch_module = load_canonical_backend(
    model_id=MODEL_ID,
    revision=revision,
    device="cuda",
)

batch_sizes = (len(FIXTURE_CODES), 5, 1)

matrices = {
    batch_size: canonical_embed_loaded(
        FIXTURE_CODES,
        tokenizer,
        model,
        batch_size=batch_size,
        device="cuda",
        torch_module=torch_module,
    )
    for batch_size in batch_sizes
}

canonical = matrices[5].astype(np.float32, copy=False)

batch_invariance = {
    str(batch_size): {
        "array_sha256": array_hash(matrix),
        "exactly_equal_to_canonical": bool(
            np.array_equal(matrix, canonical)
        ),
    }
    for batch_size, matrix in matrices.items()
}

if not all(
    result["exactly_equal_to_canonical"]
    for result in batch_invariance.values()
):
    raise RuntimeError(
        "GPU fixture is not exact across GPU batch partitions"
    )

fixture_rows = [
    {
        "index": index,
        "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "embedding_array_sha256": array_hash(embedding),
    }
    for index, (code, embedding) in enumerate(
        zip(FIXTURE_CODES, canonical, strict=True)
    )
]

gpu_identity = deepcopy(cpu_identity)

# The existing extractor currently requires the v2 schema ID.
# This separate file is explicitly labelled as an amendment and must
# never overwrite the merged CPU identity.
gpu_identity["identity_id"] = "option-b-embedding-identity-v2"
gpu_identity["identity_variant"] = "gpu-amended-local-v1"
gpu_identity["status"] = "EMBEDDING_IDENTITY_V2_COMPLETE"
gpu_identity["scientific_result_observed"] = False

gpu_identity["protocol_amendment"] = {
    "status": "LOCAL_GPU_EXECUTION_AMENDMENT_NOT_YET_CANONICAL",
    "reason": (
        "CUDA failed exact equality against the frozen CPU fixture "
        "before canonical embeddings or scientific metrics were observed."
    ),
    "frozen_cpu_identity_path": str(cpu_path).replace("\\", "/"),
    "frozen_cpu_identity_file_sha256": file_sha256(cpu_path),
    "changes": [
        "execution device changed from cpu to cuda",
        "fixture hashes regenerated on the declared CUDA environment",
    ],
    "unchanged": [
        "dataset revision",
        "model revision",
        "canonical selected rows",
        "tokenization configuration",
        "pooling implementation",
        "query",
        "threshold",
        "outcomes",
    ],
    "promotion_requires_explicit_review": True,
}

gpu_identity["tokenization_config"] = tokenization_config()
gpu_identity["tokenization_config_sha256"] = (
    tokenization_config_sha256()
)
gpu_identity["embedding_implementation_sha256"] = (
    embedding_implementation_sha256()
)

gpu_identity["fixture"] = {
    "count": len(FIXTURE_CODES),
    "embedding_shape": list(canonical.shape),
    "embedding_dtype": str(canonical.dtype),
    "matrix_array_sha256": array_hash(canonical),
    "preflight_batch_size": 5,
    "batch_invariance": batch_invariance,
    "rows": fixture_rows,
}

gpu_identity["environment"] = {
    "canonical_device": "cuda",
    "python": platform.python_version(),
    "platform": platform.platform(),
    "numpy": np.__version__,
    "torch": torch.__version__,
    "transformers": package_version("transformers"),
    "tokenizers": package_version("tokenizers"),
    "datasets": package_version("datasets"),
    "huggingface_hub": package_version("huggingface-hub"),
    "cuda_runtime": torch.version.cuda,
    "gpu_name": torch.cuda.get_device_name(0),
}

gpu_identity["fixture_preflight_required"] = True
gpu_identity["next_allowed_action"] = (
    "INDEPENDENT_GPU_EMBEDDING_REPRODUCTION"
)
gpu_identity["prohibited_actions"] = [
    "promotion as canonical evidence without protocol-amendment review",
    "primitive probe fitting before independent A/B agreement",
    "hard-negative generation before independent A/B agreement",
    "scientific metric evaluation before checkpoint review",
]

payload = json.dumps(
    gpu_identity,
    indent=2,
    sort_keys=True,
) + "\n"

gpu_path.parent.mkdir(parents=True, exist_ok=True)
gpu_path.write_text(payload, encoding="utf-8", newline="\n")

print("GPU identity written:", gpu_path)
print("GPU identity file SHA256:", file_sha256(gpu_path))
print(
    "GPU fixture array SHA256:",
    gpu_identity["fixture"]["matrix_array_sha256"],
)
print("GPU:", gpu_identity["environment"]["gpu_name"])
print("CUDA runtime:", gpu_identity["environment"]["cuda_runtime"])
'@ | python -

Assert-LastExitCode "GPU identity creation"

Write-Host ""
Write-Host "=== Verifying GPU identity preflight ==="

& relate-option-b-embed-preflight `
    --identity $GpuIdentity `
    --device $Device 2>&1 |
    Tee-Object -FilePath $PreflightLog

Assert-LastExitCode "GPU identity preflight"

Write-Host ""
Write-Host "=== Removing prior GPU-amended Run A and Run B ==="

Remove-Item $RunA -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $RunB -Recurse -Force -ErrorAction SilentlyContinue

foreach ($Cache in @($CacheA, $CacheB)) {
    Remove-Item $Cache -Force -ErrorAction SilentlyContinue
    Remove-Item "$Cache-shm" -Force -ErrorAction SilentlyContinue
    Remove-Item "$Cache-wal" -Force -ErrorAction SilentlyContinue
}

Remove-Item $RunALog -Force -ErrorAction SilentlyContinue
Remove-Item $RunBLog -Force -ErrorAction SilentlyContinue
Remove-Item $RawCheckpoint -Force -ErrorAction SilentlyContinue
Remove-Item $AmendedCheckpoint -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== GPU Run A ==="
Write-Host "Batch size: $BatchSize"

& relate-option-b-embed `
    --identity $GpuIdentity `
    --selection-dir $SelectionDir `
    --output-dir $RunA `
    --cache-db $CacheA `
    --cache-mode refresh `
    --batch-size $BatchSize `
    --device $Device 2>&1 |
    Tee-Object -FilePath $RunALog

Assert-LastExitCode "GPU Run A"

Write-Host ""
Write-Host "=== GPU Run B ==="
Write-Host "Batch size: $BatchSize"

& relate-option-b-embed `
    --identity $GpuIdentity `
    --selection-dir $SelectionDir `
    --output-dir $RunB `
    --cache-db $CacheB `
    --cache-mode refresh `
    --batch-size $BatchSize `
    --device $Device 2>&1 |
    Tee-Object -FilePath $RunBLog

Assert-LastExitCode "GPU Run B"

$RunAReport = Join-Path `
    $RunA `
    "option-b-canonical-embeddings-v2.json"

$RunBReport = Join-Path `
    $RunB `
    "option-b-canonical-embeddings-v2.json"

Write-Host ""
Write-Host "=== Independent A/B verification ==="

& relate-option-b-verify-embeddings `
    --run-a-report $RunAReport `
    --run-b-report $RunBReport `
    --identity $GpuIdentity `
    --selection-dir $SelectionDir `
    --required-device cuda `
    --output $RawCheckpoint 2>&1 |
    Tee-Object -FilePath $VerificationLog

Assert-LastExitCode "Independent GPU A/B verification"

$env:OPTION_B_RAW_GPU_CHECKPOINT = $RawCheckpoint
$env:OPTION_B_AMENDED_GPU_CHECKPOINT = $AmendedCheckpoint
$env:OPTION_B_GPU_IDENTITY = $GpuIdentity

@'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


raw_path = Path(os.environ["OPTION_B_RAW_GPU_CHECKPOINT"])
output_path = Path(os.environ["OPTION_B_AMENDED_GPU_CHECKPOINT"])
identity_path = Path(os.environ["OPTION_B_GPU_IDENTITY"])

raw = json.loads(raw_path.read_text(encoding="utf-8"))
identity = json.loads(identity_path.read_text(encoding="utf-8"))

if raw.get("status") != "CANONICAL_EMBEDDINGS_V2_REPRODUCED":
    raise RuntimeError(
        f"Unexpected verifier status: {raw.get('status')}"
    )

amended = {
    "checkpoint_id": "option-b-gpu-amended-reproduction-v1",
    "status": "GPU_AMENDED_EMBEDDINGS_REPRODUCED_NOT_YET_CANONICAL",
    "scientific_result_observed": False,
    "protocol_amendment": identity["protocol_amendment"],
    "gpu_identity": {
        "path": str(identity_path).replace("\\", "/"),
        "file_sha256": hashlib.sha256(
            identity_path.read_bytes()
        ).hexdigest(),
        "fixture_matrix_array_sha256": identity[
            "fixture"
        ]["matrix_array_sha256"],
    },
    "independent_verifier": {
        "path": str(raw_path).replace("\\", "/"),
        "file_sha256": hashlib.sha256(
            raw_path.read_bytes()
        ).hexdigest(),
        "original_status": raw["status"],
    },
    "splits": raw["splits"],
    "next_required_action": (
        "REVIEW_AND_MERGE_EXPLICIT_GPU_PROTOCOL_AMENDMENT"
    ),
    "prohibited_actions": [
        "claiming this as the frozen CPU canonical checkpoint",
        "scientific metric evaluation before amendment review",
        "silently replacing the merged CPU identity",
    ],
}

payload = json.dumps(amended, indent=2, sort_keys=True) + "\n"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(payload, encoding="utf-8", newline="\n")

print("GPU-amended checkpoint:", output_path)
print("Status:", amended["status"])

for split, value in amended["splits"].items():
    print(
        split,
        value["array_sha256"],
        value["arrays_exactly_equal"],
    )
'@ | python -

Assert-LastExitCode "GPU-amended checkpoint creation"

Write-Host ""
Write-Host "=============================================="
Write-Host "GPU A/B reproduction completed successfully."
Write-Host "=============================================="
Write-Host ""
Write-Host "GPU identity:"
Write-Host "  $GpuIdentity"
Write-Host ""
Write-Host "Run A report:"
Write-Host "  $RunAReport"
Write-Host ""
Write-Host "Run B report:"
Write-Host "  $RunBReport"
Write-Host ""
Write-Host "GPU-amended checkpoint:"
Write-Host "  $AmendedCheckpoint"
Write-Host ""
Write-Host "These results are independently reproduced but"
Write-Host "are not canonical until an explicit amendment PR"
Write-Host "is reviewed and merged."

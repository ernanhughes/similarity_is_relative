param(
    [string] $Device = "cuda"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# The GPU identity is intentionally frozen to the ten-row fixture batch shape.
# All canonical Option B split sizes are divisible by 10:
# train=20,000; validation=4,000; test=4,000.
$BatchSize = 10

function Assert-ExitCode {
    param(
        [string] $Step,
        [int] $ExitCode = $LASTEXITCODE
    )
    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

function Invoke-NativePipeline {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command,

        [Parameter(Mandatory = $true)]
        [string] $Step,

        [string] $LogPath
    )

    # Windows PowerShell 5.1 wraps native stderr as NativeCommandError.
    # Transformers and Hugging Face legitimately write progress bars to
    # stderr, so temporarily prevent those records from terminating the
    # script while still preserving the native process exit code.
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    try {
        if ($LogPath) {
            & $Command 2>&1 | Tee-Object -FilePath $LogPath
        }
        else {
            & $Command 2>&1
        }

        $NativeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousPreference
    }

    Assert-ExitCode -Step $Step -ExitCode $NativeExitCode
}

$RepoRoot = (Get-Location).Path
if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "Run this script from the similarity_is_relative repository root."
}

$SelectionDir = Join-Path $RepoRoot "artifacts/canonical/option-b/selection"
$CpuIdentity = Join-Path $RepoRoot "artifacts/canonical/option-b/option-b-embedding-identity-v2.json"

$GpuRoot = Join-Path $RepoRoot "runs/option-b/gpu-fixed-batch-10"
$GpuIdentity = Join-Path $GpuRoot "identity/option-b-embedding-identity-v2-gpu-batch10.json"

$RunA = Join-Path $GpuRoot "embeddings-a"
$RunB = Join-Path $GpuRoot "embeddings-b"
$CacheA = Join-Path $RepoRoot ".writer/option-b/cache/gpu-batch10-a.sqlite3"
$CacheB = Join-Path $RepoRoot ".writer/option-b/cache/gpu-batch10-b.sqlite3"

$RunAReport = Join-Path $RunA "option-b-canonical-embeddings-v2.json"
$RunBReport = Join-Path $RunB "option-b-canonical-embeddings-v2.json"

$RawCheckpoint = Join-Path `
    $GpuRoot `
    "reproduction/option-b-independent-embedding-reproduction-v2.json"

$AmendedCheckpoint = Join-Path `
    $GpuRoot `
    "reproduction/option-b-gpu-batch10-amendment-checkpoint.json"

$RunALog = Join-Path $GpuRoot "embeddings-a.log"
$RunBLog = Join-Path $GpuRoot "embeddings-b.log"
$PreflightLog = Join-Path $GpuRoot "gpu-preflight.log"
$VerificationLog = Join-Path $GpuRoot "gpu-verification.log"

if (-not (Test-Path $CpuIdentity)) {
    throw "Frozen CPU identity not found: $CpuIdentity"
}

# Required by deterministic CUDA matrix multiplication on supported CUDA builds.
$env:CUBLAS_WORKSPACE_CONFIG = ":4096:8"
$env:CUDA_LAUNCH_BLOCKING = "0"
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"
$env:TRANSFORMERS_NO_ADVISORY_WARNINGS = "1"
$env:OPTION_B_CPU_IDENTITY = $CpuIdentity
$env:OPTION_B_GPU_IDENTITY = $GpuIdentity
$env:OPTION_B_GPU_BATCH_SIZE = "$BatchSize"

Write-Host ""
Write-Host "=== Installing current Option B tooling ==="
python -m pip install -e ".[dev,option-b]"
Assert-ExitCode "Editable package installation"

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
Assert-ExitCode "CUDA validation"

New-Item -ItemType Directory -Force -Path (Split-Path $GpuIdentity) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $RawCheckpoint) | Out-Null

Write-Host ""
Write-Host "=== Creating GPU execution identity at fixed batch size $BatchSize ==="

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

# Freeze deterministic CUDA behaviour before model execution.
torch.use_deterministic_algorithms(True)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

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
batch_size = int(os.environ["OPTION_B_GPU_BATCH_SIZE"])

if batch_size != len(FIXTURE_CODES):
    raise RuntimeError(
        "GPU amendment requires batch size equal to the ten-row fixture count"
    )

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

canonical = canonical_embed_loaded(
    FIXTURE_CODES,
    tokenizer,
    model,
    batch_size=batch_size,
    device="cuda",
    torch_module=torch_module,
).astype(np.float32, copy=False)

if canonical.shape != (len(FIXTURE_CODES), 768):
    raise RuntimeError(f"Unexpected GPU fixture shape: {canonical.shape}")

if not np.isfinite(canonical).all():
    raise RuntimeError("GPU fixture contains non-finite values")

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

# Keep the schema ID required by the existing verifier, but label the
# execution identity and amendment explicitly.
gpu_identity["identity_id"] = "option-b-embedding-identity-v2"
gpu_identity["identity_variant"] = "gpu-fixed-batch10-amendment-v1"
gpu_identity["status"] = "EMBEDDING_IDENTITY_V2_COMPLETE"
gpu_identity["scientific_result_observed"] = False

gpu_identity["protocol_amendment"] = {
    "status": "LOCAL_GPU_EXECUTION_AMENDMENT_NOT_YET_CANONICAL",
    "reason": (
        "CUDA was not bit-identical to the frozen CPU fixture and was not "
        "invariant across GPU batch shapes. The amended execution identity "
        "therefore freezes device=cuda and batch_size=10 before any probes, "
        "hard negatives, retrieval metrics, or scientific result."
    ),
    "frozen_cpu_identity_path": str(cpu_path).replace("\\", "/"),
    "frozen_cpu_identity_file_sha256": file_sha256(cpu_path),
    "frozen_execution": {
        "device": "cuda",
        "batch_size": batch_size,
        "deterministic_algorithms": True,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "allow_tf32": False,
    },
    "unchanged": [
        "dataset revision",
        "model revision",
        "canonical selected rows and order",
        "tokenization configuration",
        "pooling implementation",
        "query",
        "threshold",
        "registered outcomes",
    ],
    "promotion_requires_explicit_review": True,
}

gpu_identity["tokenization_config"] = tokenization_config()
gpu_identity["tokenization_config_sha256"] = tokenization_config_sha256()
gpu_identity["embedding_implementation_sha256"] = (
    embedding_implementation_sha256()
)

gpu_identity["fixture"] = {
    "count": len(FIXTURE_CODES),
    "embedding_shape": list(canonical.shape),
    "embedding_dtype": str(canonical.dtype),
    "matrix_array_sha256": array_hash(canonical),
    "preflight_batch_size": batch_size,
    "fixed_batch_identity": {
        "batch_size": batch_size,
        "cross_batch_invariance_required": False,
        "reason": "GPU execution is batch-shape specific.",
    },
    # Retained for compatibility and made truthful: only the frozen
    # execution batch shape is certified.
    "batch_invariance": {
        str(batch_size): {
            "array_sha256": array_hash(canonical),
            "exactly_equal_to_canonical": True,
        }
    },
    "rows": fixture_rows,
}

gpu_identity["environment"] = {
    "canonical_device": "cuda",
    "canonical_batch_size": batch_size,
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
    "deterministic_algorithms": True,
    "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    "allow_tf32": False,
}

gpu_identity["fixture_preflight_required"] = True
gpu_identity["next_allowed_action"] = (
    "INDEPENDENT_GPU_EMBEDDING_REPRODUCTION"
)
gpu_identity["prohibited_actions"] = [
    "promotion as canonical evidence without protocol-amendment review",
    "changing GPU batch size after identity capture",
    "primitive probe fitting before independent A/B agreement",
    "hard-negative generation before independent A/B agreement",
    "scientific metric evaluation before checkpoint review",
]

payload = json.dumps(gpu_identity, indent=2, sort_keys=True) + "\n"
gpu_path.parent.mkdir(parents=True, exist_ok=True)
gpu_path.write_text(payload, encoding="utf-8", newline="\n")

print("GPU identity written:", gpu_path)
print("GPU identity file SHA256:", file_sha256(gpu_path))
print("GPU fixture array SHA256:", array_hash(canonical))
print("Frozen GPU batch size:", batch_size)
print("GPU:", gpu_identity["environment"]["gpu_name"])
print("CUDA runtime:", gpu_identity["environment"]["cuda_runtime"])
'@ | python -
Assert-ExitCode "GPU identity creation"

Write-Host ""
Write-Host "=== Verifying GPU identity in a fresh process ==="

$PreflightPython = @'
from __future__ import annotations

import json
import os
from pathlib import Path

import torch

torch.use_deterministic_algorithms(True)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

from relate.experiments.option_b_embedding_preflight import run_preflight

identity = Path(os.environ["OPTION_B_GPU_IDENTITY"])
result = run_preflight(identity, device="cuda")
print(json.dumps(result, indent=2, sort_keys=True))
'@

Invoke-NativePipeline `
    -Step "GPU identity preflight" `
    -LogPath $PreflightLog `
    -Command {
        $PreflightPython | python -
    }

Write-Host ""
Write-Host "=== Removing prior fixed-batch GPU runs ==="

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

function Invoke-GpuExtraction {
    param(
        [string] $OutputDir,
        [string] $CacheDb,
        [string] $LogPath,
        [string] $RunLabel
    )

    $env:OPTION_B_RUN_OUTPUT = $OutputDir
    $env:OPTION_B_RUN_CACHE = $CacheDb
    $env:OPTION_B_SELECTION_DIR = $SelectionDir
    $env:OPTION_B_GPU_IDENTITY = $GpuIdentity
    $env:OPTION_B_GPU_BATCH_SIZE = "$BatchSize"

    Write-Host ""
    Write-Host "=== $RunLabel ==="

    $ExtractionPython = @'
from __future__ import annotations

import json
import os
from pathlib import Path

import torch

torch.use_deterministic_algorithms(True)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

from relate.experiments.option_b_embeddings_hardened import run_extraction

report = run_extraction(
    Path(os.environ["OPTION_B_GPU_IDENTITY"]),
    Path(os.environ["OPTION_B_SELECTION_DIR"]),
    Path(os.environ["OPTION_B_RUN_OUTPUT"]),
    batch_size=int(os.environ["OPTION_B_GPU_BATCH_SIZE"]),
    device="cuda",
    cache_db=Path(os.environ["OPTION_B_RUN_CACHE"]),
    cache_mode="refresh",
)

print(json.dumps(report, indent=2, sort_keys=True))
'@

    Invoke-NativePipeline `
        -Step $RunLabel `
        -LogPath $LogPath `
        -Command {
            $ExtractionPython | python -
        }
}

Invoke-GpuExtraction `
    -OutputDir $RunA `
    -CacheDb $CacheA `
    -LogPath $RunALog `
    -RunLabel "GPU Run A"

Invoke-GpuExtraction `
    -OutputDir $RunB `
    -CacheDb $CacheB `
    -LogPath $RunBLog `
    -RunLabel "GPU Run B"

Write-Host ""
Write-Host "=== Independent A/B verification ==="

Invoke-NativePipeline `
    -Step "Independent GPU A/B verification" `
    -LogPath $VerificationLog `
    -Command {
        & relate-option-b-verify-embeddings `
            --run-a-report $RunAReport `
            --run-b-report $RunBReport `
            --identity $GpuIdentity `
            --selection-dir $SelectionDir `
            --required-device cuda `
            --output $RawCheckpoint
    }

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
    raise RuntimeError(f"Unexpected verifier status: {raw.get('status')}")

amended = {
    "checkpoint_id": "option-b-gpu-fixed-batch10-reproduction-v1",
    "status": "GPU_FIXED_BATCH_EMBEDDINGS_REPRODUCED_NOT_YET_CANONICAL",
    "scientific_result_observed": False,
    "protocol_amendment": identity["protocol_amendment"],
    "gpu_identity": {
        "path": str(identity_path).replace("\\", "/"),
        "file_sha256": hashlib.sha256(identity_path.read_bytes()).hexdigest(),
        "fixture_matrix_array_sha256": identity[
            "fixture"
        ]["matrix_array_sha256"],
    },
    "independent_verifier": {
        "path": str(raw_path).replace("\\", "/"),
        "file_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "original_status": raw["status"],
    },
    "splits": raw["splits"],
    "next_required_action": (
        "REVIEW_AND_MERGE_EXPLICIT_GPU_FIXED_BATCH_PROTOCOL_AMENDMENT"
    ),
    "prohibited_actions": [
        "claiming this as the frozen CPU canonical checkpoint",
        "changing device or batch size",
        "scientific metric evaluation before amendment review",
        "silently replacing the merged CPU identity",
    ],
}

payload = json.dumps(amended, indent=2, sort_keys=True) + "\n"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(payload, encoding="utf-8", newline="\n")

print("GPU fixed-batch checkpoint:", output_path)
print("Status:", amended["status"])

for split, value in amended["splits"].items():
    print(
        split,
        value["array_sha256"],
        value["exact_array_equal"],
    )
'@ | python -

Assert-ExitCode "GPU fixed-batch checkpoint creation"

Write-Host ""
Write-Host "=================================================="
Write-Host "GPU fixed-batch A/B reproduction completed."
Write-Host "=================================================="
Write-Host ""
Write-Host "Frozen execution:"
Write-Host "  device     = cuda"
Write-Host "  batch size = $BatchSize"
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
Write-Host "Amendment checkpoint:"
Write-Host "  $AmendedCheckpoint"
Write-Host ""
Write-Host "Do not fit probes until the explicit GPU amendment"
Write-Host "is reviewed and merged into PR #37."

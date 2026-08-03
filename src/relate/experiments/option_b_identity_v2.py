"""Publish immutable Option B embedding identity v2 from the frozen v1 revisions."""

from __future__ import annotations

import argparse
import json
import platform
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

from relate.evidence.hashing import sha256_bytes as _sha256_bytes
from relate.evidence.hashing import sha256_file as _sha256_file
from relate.experiments.option_b_embedding import (
    canonical_embed_loaded,
    embedding_implementation_sha256,
    load_canonical_backend,
    tokenization_config,
    tokenization_config_sha256,
)
from relate.experiments.option_b_identity import (
    DATASET_ID,
    FIXTURE_CODES,
    TOKENIZER_FILES,
)
from relate.experiments.option_b_real_code import MODEL_ID, array_hash

DEFAULT_PREDECESSOR = Path("artifacts/canonical/option-b/option-b-external-identity-v1.json")
DEFAULT_OUTPUT = Path("runs/option-b/identity/option-b-embedding-identity-v2.json")
CANONICAL_DEVICE = "cpu"
CANONICAL_BATCH_SIZE = 5
BATCH_INVARIANCE_SIZES = (len(FIXTURE_CODES), CANONICAL_BATCH_SIZE, 1)


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _load_predecessor(path: Path) -> dict[str, Any]:
    predecessor = json.loads(path.read_text(encoding="utf-8"))
    if predecessor.get("status") != "IDENTITY_CAPTURE_COMPLETE":
        raise ValueError("identity v1 predecessor is incomplete")
    if predecessor.get("model", {}).get("repo_id") != MODEL_ID:
        raise ValueError("identity v1 model does not match frozen Option B model")
    if predecessor.get("dataset", {}).get("repo_id") != DATASET_ID:
        raise ValueError("identity v1 dataset does not match frozen Option B dataset")
    if predecessor.get("dataset", {}).get("subset") != "python":
        raise ValueError("identity v1 dataset subset is not python")
    if not predecessor["model"].get("revision") or not predecessor["dataset"].get("revision"):
        raise ValueError("identity v1 must contain immutable revisions")
    return predecessor


def capture(
    output: Path,
    *,
    predecessor_path: Path = DEFAULT_PREDECESSOR,
    cache_dir: Path | None = None,
    device: str = CANONICAL_DEVICE,
) -> dict[str, Any]:
    """Capture identity v2 and require exact fixture batch invariance."""
    if device != CANONICAL_DEVICE:
        raise ValueError("canonical identity v2 must be captured on cpu")
    predecessor = _load_predecessor(predecessor_path)
    model_revision = predecessor["model"]["revision"]
    dataset_revision = predecessor["dataset"]["revision"]

    try:
        import torch
        from huggingface_hub import snapshot_download
    except ImportError as error:  # pragma: no cover - runtime dependency
        raise RuntimeError("install the option-b dependencies first") from error

    snapshot = Path(
        snapshot_download(
            MODEL_ID,
            revision=model_revision,
            cache_dir=str(cache_dir) if cache_dir else None,
            allow_patterns=list(TOKENIZER_FILES),
        )
    )
    tokenizer, model, torch_module = load_canonical_backend(
        model_id=MODEL_ID,
        revision=model_revision,
        device=device,
        cache_dir=cache_dir,
    )

    matrices = {
        batch_size: canonical_embed_loaded(
            FIXTURE_CODES,
            tokenizer,
            model,
            batch_size=batch_size,
            device=device,
            torch_module=torch_module,
        )
        for batch_size in BATCH_INVARIANCE_SIZES
    }
    canonical = matrices[CANONICAL_BATCH_SIZE].astype(np.float32, copy=False)
    invariance = {
        str(batch_size): {
            "array_sha256": array_hash(matrix),
            "exactly_equal_to_canonical": bool(np.array_equal(matrix, canonical)),
        }
        for batch_size, matrix in matrices.items()
    }
    if not all(item["exactly_equal_to_canonical"] for item in invariance.values()):
        raise RuntimeError("canonical fixture is not exact across frozen batch partitions")

    fixture_rows = []
    for index, (code, embedding) in enumerate(zip(FIXTURE_CODES, canonical, strict=True)):
        fixture_rows.append(
            {
                "index": index,
                "code_sha256": _sha256_bytes(code.encode()),
                "embedding_array_sha256": array_hash(embedding),
            }
        )

    tokenizer_hashes = {
        name: _sha256_file(snapshot / name)
        for name in TOKENIZER_FILES
        if (snapshot / name).exists()
    }
    result = {
        "identity_id": "option-b-embedding-identity-v2",
        "status": "EMBEDDING_IDENTITY_V2_COMPLETE",
        "scientific_result_observed": False,
        "predecessor": {
            "path": str(predecessor_path).replace("\\", "/"),
            "file_sha256": _sha256_file(predecessor_path),
            "identity_id": predecessor.get("identity_id"),
        },
        "model": {
            "repo_id": MODEL_ID,
            "revision": model_revision,
        },
        "dataset": {
            "repo_id": DATASET_ID,
            "revision": dataset_revision,
            "subset": "python",
        },
        "tokenizer_file_sha256": tokenizer_hashes,
        "tokenization_config": tokenization_config(),
        "tokenization_config_sha256": tokenization_config_sha256(),
        "embedding_implementation_sha256": embedding_implementation_sha256(),
        "fixture": {
            "count": len(FIXTURE_CODES),
            "embedding_shape": list(canonical.shape),
            "embedding_dtype": str(canonical.dtype),
            "matrix_array_sha256": array_hash(canonical),
            "preflight_batch_size": CANONICAL_BATCH_SIZE,
            "batch_invariance": invariance,
            "rows": fixture_rows,
        },
        "environment": {
            "canonical_device": device,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "transformers": _version("transformers"),
            "tokenizers": _version("tokenizers"),
            "datasets": _version("datasets"),
            "huggingface_hub": _version("huggingface-hub"),
        },
        "fixture_preflight_required": True,
        "next_allowed_action": "CHUNK_CACHE_RECOVERY_HARDENING",
        "prohibited_actions": [
            "canonical embedding publication before PR 6",
            "primitive probe fitting",
            "hard-negative generation",
            "scientific metric evaluation",
        ],
    }
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    result["file_sha256"] = _sha256_bytes(payload.encode())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--predecessor", type=Path, default=DEFAULT_PREDECESSOR)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--device", default=CANONICAL_DEVICE)
    args = parser.parse_args()
    print(
        json.dumps(
            capture(
                args.output,
                predecessor_path=args.predecessor,
                cache_dir=args.cache_dir,
                device=args.device,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

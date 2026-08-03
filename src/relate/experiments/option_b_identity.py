"""Capture frozen external identities and a ten-sample CodeBERT fixture for Option B."""

from __future__ import annotations

import argparse
import inspect
import json
import platform
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from relate.evidence.hashing import sha256_bytes as _sha256_bytes
from relate.evidence.hashing import sha256_file as _sha256_file
from relate.experiments.option_b_real_code import MODEL_ID, embed_code

DATASET_ID = "code-search-net/code_search_net"
TOKENIZER_FILES = (
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.json",
    "merges.txt",
)
FIXTURE_CODES = (
    "def identity(x):\n    return x\n",
    "def clamp(x, low, high):\n    return max(low, min(x, high))\n",
    "def count_positive(values):\n    return sum(1 for value in values if value > 0)\n",
    "def first_even(values):\n    for value in values:\n        if value % 2 == 0:\n            return value\n    return None\n",  # NOQA E501
    "def safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n",
    "def flatten(rows):\n    return [item for row in rows for item in row]\n",
    "def retry(operation, attempts):\n    for _ in range(attempts):\n        try:\n            return operation()\n        except Exception:\n            pass\n    raise RuntimeError('failed')\n",  # NOQA E501
    "def classify(x):\n    if x < 0:\n        return 'negative'\n    if x == 0:\n        return 'zero'\n    return 'positive'\n",  # NOQA E501
    "def unique_calls(service, items):\n    service.open()\n    for item in items:\n        service.process(item)\n    service.close()\n",  # NOQA E501
    "async def collect(stream):\n    result = []\n    async for item in stream:\n        if item is not None:\n            result.append(item)\n    return result\n",  # NOQA E501
)


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def capture(output: Path, cache_dir: Path | None = None) -> dict[str, Any]:
    try:
        import torch
        from huggingface_hub import dataset_info, model_info, snapshot_download
        from transformers import AutoTokenizer
    except ImportError as error:
        raise RuntimeError("install the option-b dependencies first") from error

    model = model_info(MODEL_ID)
    dataset = dataset_info(DATASET_ID)
    model_revision = model.sha
    dataset_revision = dataset.sha
    if not model_revision or not dataset_revision:
        raise RuntimeError("Hub did not return immutable revisions")

    snapshot = Path(
        snapshot_download(
            MODEL_ID,
            revision=model_revision,
            cache_dir=str(cache_dir) if cache_dir else None,
            allow_patterns=list(TOKENIZER_FILES),
        )
    )
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=model_revision,
        cache_dir=cache_dir,
    )

    fixture_records = [SimpleNamespace(code=code) for code in FIXTURE_CODES]
    embeddings, embedding_metadata = embed_code(
        fixture_records,
        model_id=MODEL_ID,
        revision=model_revision,
        batch_size=5,
        device="cpu",
    )
    embeddings = embeddings.astype(np.float32, copy=False)

    fixture_rows = []
    for index, (code, embedding) in enumerate(zip(FIXTURE_CODES, embeddings, strict=True)):
        token_count = len(tokenizer(code, add_special_tokens=True, truncation=False)["input_ids"])
        fixture_rows.append(
            {
                "index": index,
                "code_sha256": _sha256_bytes(code.encode()),
                "token_count": token_count,
                "embedding_sha256": _sha256_bytes(embedding.tobytes()),
            }
        )

    tokenizer_hashes = {
        name: _sha256_file(snapshot / name)
        for name in TOKENIZER_FILES
        if (snapshot / name).exists()
    }
    pooling_source = inspect.getsource(embed_code).encode()
    result = {
        "identity_id": "option-b-external-identity-v1",
        "status": "IDENTITY_CAPTURE_COMPLETE",
        "model": {
            "repo_id": MODEL_ID,
            "revision": model_revision,
            "embedding_metadata": embedding_metadata,
        },
        "dataset": {
            "repo_id": DATASET_ID,
            "revision": dataset_revision,
            "subset": "python",
        },
        "tokenizer_file_sha256": tokenizer_hashes,
        "pooling_implementation_sha256": _sha256_bytes(pooling_source),
        "fixture": {
            "count": len(FIXTURE_CODES),
            "embedding_shape": list(embeddings.shape),
            "embedding_dtype": str(embeddings.dtype),
            "matrix_sha256": _sha256_bytes(embeddings.tobytes()),
            "rows": fixture_rows,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "transformers": _version("transformers"),
            "tokenizers": _version("tokenizers"),
            "datasets": _version("datasets"),
            "huggingface_hub": _version("huggingface-hub"),
        },
    }
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    result["manifest_sha256"] = _sha256_bytes(payload.encode())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/option-b/identity/option-b-external-identity-v1.json"),
    )
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.output, args.cache_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

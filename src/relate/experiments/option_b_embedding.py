"""Shared canonical CodeBERT tokenization, inference, and pooling implementation."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from relate.experiments.option_b_real_code import MODEL_ID, array_hash

MAX_LENGTH = 256
POOLING_POLICY = "attention-mask mean pooling"
OUTPUT_DTYPE = "float32"
TOKENIZATION_CONFIG: dict[str, Any] = {
    "add_special_tokens": True,
    "padding": "max_length",
    "truncation": True,
    "max_length": MAX_LENGTH,
    "padding_side": "right",
    "truncation_side": "right",
    "return_tensors": "pt",
    "pooling_policy": POOLING_POLICY,
    "output_dtype": OUTPUT_DTYPE,
}


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def tokenization_config() -> dict[str, Any]:
    """Return a copy of the frozen canonical tokenization/pooling configuration."""
    return dict(TOKENIZATION_CONFIG)


def tokenization_config_sha256() -> str:
    """Hash every batch-shape and pooling choice that defines canonical vectors."""
    return _sha256_json(TOKENIZATION_CONFIG)


def configure_tokenizer(tokenizer: Any) -> Any:
    """Set and verify the frozen tokenizer-side configuration."""
    tokenizer.padding_side = TOKENIZATION_CONFIG["padding_side"]
    tokenizer.truncation_side = TOKENIZATION_CONFIG["truncation_side"]
    if tokenizer.padding_side != "right" or tokenizer.truncation_side != "right":
        raise ValueError("tokenizer does not support the frozen right-side configuration")
    return tokenizer


def canonical_tokenize(codes: Sequence[str], tokenizer: Any) -> dict[str, Any]:
    """Tokenize one canonical batch with fixed-length padding."""
    configure_tokenizer(tokenizer)
    return tokenizer(
        list(codes),
        add_special_tokens=True,
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )


def canonical_embed_batch(
    codes: Sequence[str],
    tokenizer: Any,
    model: Any,
    *,
    device: str,
    torch_module: Any | None = None,
) -> np.ndarray:
    """Execute the one canonical tokenization, model, and pooling path."""
    if not codes:
        raise ValueError("canonical embedding batches must not be empty")
    if torch_module is None:
        try:
            import torch as torch_module
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("install Option B dependencies first") from exc

    encoded = canonical_tokenize(codes, tokenizer)
    encoded = {name: tensor.to(device) for name, tensor in encoded.items()}
    with torch_module.inference_mode():
        hidden = model(**encoded).last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
    return pooled.detach().cpu().numpy().astype(np.float32, copy=False)


def canonical_embed_loaded(
    codes: Sequence[str],
    tokenizer: Any,
    model: Any,
    *,
    batch_size: int,
    device: str,
    torch_module: Any | None = None,
) -> np.ndarray:
    """Embed an ordered code sequence using an already-loaded canonical backend."""
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    if not codes:
        raise ValueError("canonical embedding input must not be empty")
    batches = [
        canonical_embed_batch(
            codes[start : start + batch_size],
            tokenizer,
            model,
            device=device,
            torch_module=torch_module,
        )
        for start in range(0, len(codes), batch_size)
    ]
    return np.concatenate(batches, axis=0).astype(np.float32, copy=False)


def load_canonical_backend(
    *,
    model_id: str,
    revision: str,
    device: str,
    cache_dir: Path | None = None,
) -> tuple[Any, Any, Any]:
    """Load the exact tokenizer/model pair used by identity and extraction."""
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("install Option B dependencies first") from exc

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        revision=revision,
        cache_dir=cache_dir,
    )
    configure_tokenizer(tokenizer)
    model = AutoModel.from_pretrained(
        model_id,
        revision=revision,
        cache_dir=cache_dir,
    ).to(device)
    model.eval()
    return tokenizer, model, torch


def canonical_embed_codes(
    codes: Sequence[str],
    *,
    model_id: str = MODEL_ID,
    revision: str,
    batch_size: int,
    device: str,
    cache_dir: Path | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Load the canonical backend once and embed an ordered code sequence."""
    tokenizer, model, torch = load_canonical_backend(
        model_id=model_id,
        revision=revision,
        device=device,
        cache_dir=cache_dir,
    )
    matrix = canonical_embed_loaded(
        codes,
        tokenizer,
        model,
        batch_size=batch_size,
        device=device,
        torch_module=torch,
    )
    return matrix, {
        "model_id": model_id,
        "revision": revision,
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
        "device": device,
        "tokenization_config_sha256": tokenization_config_sha256(),
        "embedding_implementation_sha256": embedding_implementation_sha256(),
    }


def embedding_implementation_sha256() -> str:
    """Hash the exact shared functions executed by identity and extraction."""
    sources = [
        inspect.getsource(configure_tokenizer),
        inspect.getsource(canonical_tokenize),
        inspect.getsource(canonical_embed_batch),
        inspect.getsource(canonical_embed_loaded),
    ]
    return hashlib.sha256("\n---\n".join(sources).encode()).hexdigest()


def verify_fixture_preflight(
    identity: dict[str, Any],
    fixture_codes: Sequence[str],
    tokenizer: Any,
    model: Any,
    *,
    device: str,
    torch_module: Any | None = None,
) -> dict[str, Any]:
    """Recompute and verify the frozen fixture before dataset reconstruction."""
    if identity.get("embedding_implementation_sha256") != embedding_implementation_sha256():
        raise ValueError("embedding implementation does not match identity v2")
    if identity.get("tokenization_config_sha256") != tokenization_config_sha256():
        raise ValueError("tokenization configuration does not match identity v2")

    fixture = identity.get("fixture", {})
    rows = fixture.get("rows", [])
    if len(fixture_codes) != fixture.get("count") or len(rows) != len(fixture_codes):
        raise ValueError("identity v2 fixture row count is invalid")
    for index, (code, row) in enumerate(zip(fixture_codes, rows, strict=True)):
        code_sha = hashlib.sha256(code.encode()).hexdigest()
        if row.get("index") != index or row.get("code_sha256") != code_sha:
            raise ValueError(f"fixture code identity mismatch at row {index}")

    batch_size = int(fixture.get("preflight_batch_size", 0))
    matrix = canonical_embed_loaded(
        fixture_codes,
        tokenizer,
        model,
        batch_size=batch_size,
        device=device,
        torch_module=torch_module,
    )
    if array_hash(matrix) != fixture.get("matrix_array_sha256"):
        raise ValueError("fixture matrix hash does not match identity v2")
    for index, (embedding, row) in enumerate(zip(matrix, rows, strict=True)):
        if array_hash(embedding) != row.get("embedding_array_sha256"):
            raise ValueError(f"fixture embedding hash mismatch at row {index}")
    return {
        "status": "EMBEDDING_FIXTURE_PREFLIGHT_VERIFIED",
        "rows": len(matrix),
        "matrix_array_sha256": array_hash(matrix),
        "device": device,
    }

"""Recovery-safe Option B canonical embedding extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

from relate.experiments import option_b_embeddings as base
from relate.experiments.option_b_cache import CACHE_MODES, OptionBCache
from relate.experiments.option_b_embedding import (
    MAX_LENGTH,
    OUTPUT_DTYPE,
    POOLING_POLICY,
    canonical_embed_batch,
    load_canonical_backend,
    tokenization_config,
    verify_fixture_preflight,
)
from relate.experiments.option_b_identity import FIXTURE_CODES
from relate.experiments.option_b_real_code import MODEL_ID

FINGERPRINT_SCHEMA = "option-b-extraction-fingerprint-v1"
CHUNK_SCHEMA = "option-b-embedding-chunk-v2"
CACHE_TABLE = "embeddings_v2"


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def sequence_sha256(values: Sequence[str]) -> str:
    """Hash an ordered string sequence without delimiter ambiguity."""
    return _sha256_json(list(values))


def _version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def runtime_identity(torch_module: Any, *, device: str) -> dict[str, Any]:
    """Record runtime fields that may affect logical embedding arrays."""
    cuda_version = getattr(getattr(torch_module, "version", None), "cuda", None)
    gpu_name = None
    if device.startswith("cuda") and getattr(torch_module, "cuda", None) is not None:
        if torch_module.cuda.is_available():
            index = 0
            if ":" in device:
                index = int(device.split(":", 1)[1])
            gpu_name = torch_module.cuda.get_device_name(index)
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "torch": getattr(torch_module, "__version__", None),
        "transformers": _version("transformers"),
        "tokenizers": _version("tokenizers"),
        "device": device,
        "cuda_runtime": cuda_version,
        "gpu_name": gpu_name,
    }


def extraction_fingerprint_payload(
    *,
    identity_file_sha256: str,
    identity: dict[str, Any],
    split: str,
    split_manifest_sha256: str,
    stable_keys: Sequence[str],
    source_sha256: Sequence[str],
    batch_size: int,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Build the complete immutable extraction fingerprint payload."""
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    if len(stable_keys) != len(source_sha256):
        raise ValueError("stable-key and source-hash counts must match")
    if not stable_keys:
        raise ValueError("extraction split must not be empty")
    if len(set(stable_keys)) != len(stable_keys):
        raise ValueError("stable keys must be unique within a split")
    return {
        "schema": FINGERPRINT_SCHEMA,
        "identity_file_sha256": identity_file_sha256,
        "identity_id": identity["identity_id"],
        "model": {
            "repo_id": identity["model"]["repo_id"],
            "revision": identity["model"]["revision"],
        },
        "embedding_implementation_sha256": identity["embedding_implementation_sha256"],
        "tokenization_config_sha256": identity["tokenization_config_sha256"],
        "tokenization_config": tokenization_config(),
        "pooling_policy": POOLING_POLICY,
        "output_dtype": OUTPUT_DTYPE,
        "max_length": MAX_LENGTH,
        "split": split,
        "split_manifest_sha256": split_manifest_sha256,
        "stable_key_sequence_sha256": sequence_sha256(stable_keys),
        "source_sequence_sha256": sequence_sha256(source_sha256),
        "rows": len(stable_keys),
        "batch_size": batch_size,
        "runtime": runtime,
    }


def extraction_fingerprint_sha256(payload: dict[str, Any]) -> str:
    if payload.get("schema") != FINGERPRINT_SCHEMA:
        raise ValueError("unexpected extraction fingerprint schema")
    return _sha256_json(payload)


def _ensure_v2_cache(cache: OptionBCache) -> None:
    if cache.connection is None:
        return
    cache.connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {CACHE_TABLE} (
            stable_key TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            extraction_fingerprint_sha256 TEXT NOT NULL,
            dtype TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            payload_sha256 TEXT NOT NULL,
            array_sha256 TEXT NOT NULL,
            PRIMARY KEY (
                stable_key,
                source_sha256,
                extraction_fingerprint_sha256
            )
        )
        """
    )
    cache.connection.commit()


def _get_cached_embedding(
    cache: OptionBCache,
    *,
    stable_key: str,
    source_sha256: str,
    fingerprint_sha256: str,
) -> np.ndarray | None:
    if not cache.reads_enabled:
        return None
    _ensure_v2_cache(cache)
    assert cache.connection is not None
    row = cache.connection.execute(
        f"""
        SELECT dtype, dimensions, embedding, payload_sha256, array_sha256
        FROM {CACHE_TABLE}
        WHERE stable_key = ?
          AND source_sha256 = ?
          AND extraction_fingerprint_sha256 = ?
        """,
        (stable_key, source_sha256, fingerprint_sha256),
    ).fetchone()
    if row is None:
        return None
    dtype, dimensions, payload, payload_sha256, expected_array_sha256 = row
    if dtype != "float32" or int(dimensions) <= 0:
        return None
    raw = bytes(payload)
    if hashlib.sha256(raw).hexdigest() != payload_sha256:
        return None
    value = np.frombuffer(raw, dtype=np.float32).copy()
    if value.shape != (int(dimensions),) or not np.isfinite(value).all():
        return None
    if base.array_hash(value) != expected_array_sha256:
        return None
    return value


def _put_cached_embedding(
    cache: OptionBCache,
    *,
    stable_key: str,
    source_sha256: str,
    fingerprint_sha256: str,
    vector: np.ndarray,
) -> None:
    if not cache.writes_enabled:
        return
    value = np.ascontiguousarray(vector, dtype=np.float32)
    if value.ndim != 1 or not np.isfinite(value).all():
        raise ValueError("cached embedding must be a finite float32 vector")
    _ensure_v2_cache(cache)
    assert cache.connection is not None
    payload = value.tobytes()
    cache.connection.execute(
        f"""
        INSERT INTO {CACHE_TABLE} (
            stable_key, source_sha256, extraction_fingerprint_sha256,
            dtype, dimensions, embedding, payload_sha256, array_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(
            stable_key, source_sha256, extraction_fingerprint_sha256
        ) DO UPDATE SET
            dtype = excluded.dtype,
            dimensions = excluded.dimensions,
            embedding = excluded.embedding,
            payload_sha256 = excluded.payload_sha256,
            array_sha256 = excluded.array_sha256
        """,
        (
            stable_key,
            source_sha256,
            fingerprint_sha256,
            "float32",
            int(value.shape[0]),
            payload,
            hashlib.sha256(payload).hexdigest(),
            base.array_hash(value),
        ),
    )


def _cached_batch(
    *,
    keys: Sequence[str],
    source_sha256: Sequence[str],
    codes: Sequence[str],
    embed_batch: Callable[[list[str]], np.ndarray],
    cache: OptionBCache,
    fingerprint_sha256: str,
) -> tuple[np.ndarray, int, int]:
    vectors: list[np.ndarray | None] = [None] * len(keys)
    missing: list[int] = []
    hits = 0
    for index, (stable_key, source_hash) in enumerate(
        zip(keys, source_sha256, strict=True)
    ):
        vector = _get_cached_embedding(
            cache,
            stable_key=stable_key,
            source_sha256=source_hash,
            fingerprint_sha256=fingerprint_sha256,
        )
        if vector is None:
            missing.append(index)
        else:
            vectors[index] = vector
            hits += 1

    if missing:
        generated = np.asarray(
            embed_batch([codes[index] for index in missing]), dtype=np.float32
        )
        if generated.ndim != 2 or generated.shape[0] != len(missing):
            raise ValueError("embedding backend returned invalid batch shape")
        if not np.isfinite(generated).all():
            raise ValueError("embedding backend returned non-finite values")
        for output_index, row_index in enumerate(missing):
            vector = np.ascontiguousarray(generated[output_index], dtype=np.float32)
            vectors[row_index] = vector
            _put_cached_embedding(
                cache,
                stable_key=keys[row_index],
                source_sha256=source_sha256[row_index],
                fingerprint_sha256=fingerprint_sha256,
                vector=vector,
            )
        cache.commit()

    matrix = np.stack([value for value in vectors if value is not None]).astype(
        np.float32, copy=False
    )
    if matrix.shape[0] != len(keys):
        raise ValueError("embedding cache assembly lost rows")
    return matrix, hits, len(missing)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_save_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        np.save(handle, value, allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _chunk_paths(
    output_dir: Path,
    *,
    fingerprint_sha256: str,
    split: str,
    start: int,
    end: int,
) -> tuple[Path, Path]:
    directory = output_dir / "chunks" / fingerprint_sha256 / split
    stem = f"{start:06d}-{end:06d}"
    return directory / f"{stem}.npy", directory / f"{stem}.json"


def _expected_chunk_identity(
    *,
    fingerprint_sha256: str,
    split: str,
    start: int,
    end: int,
    stable_keys: Sequence[str],
    source_sha256: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema": CHUNK_SCHEMA,
        "extraction_fingerprint_sha256": fingerprint_sha256,
        "split": split,
        "start": start,
        "end": end,
        "rows": end - start,
        "stable_key_sequence_sha256": sequence_sha256(stable_keys),
        "source_sequence_sha256": sequence_sha256(source_sha256),
    }


def _load_verified_chunk(
    matrix_path: Path,
    sidecar_path: Path,
    *,
    expected: dict[str, Any],
    allow_reuse: bool,
) -> tuple[np.ndarray | None, str]:
    if not allow_reuse:
        return None, "reuse-bypassed"
    if not matrix_path.exists() and not sidecar_path.exists():
        return None, "missing"
    if not matrix_path.exists() or not sidecar_path.exists():
        return None, "incomplete"
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "invalid-sidecar"
    for key, value in expected.items():
        if sidecar.get(key) != value:
            return None, f"identity-mismatch:{key}"
    try:
        matrix = np.load(matrix_path, allow_pickle=False)
    except (OSError, ValueError):
        return None, "invalid-npy"
    if matrix.ndim != 2 or matrix.shape[0] != expected["rows"]:
        return None, "shape-mismatch"
    if matrix.dtype != np.float32 or not np.isfinite(matrix).all():
        return None, "dtype-or-finite-mismatch"
    checks = {
        "shape": list(matrix.shape),
        "dtype": str(matrix.dtype),
        "dimensions": int(matrix.shape[1]),
        "array_sha256": base.array_hash(matrix),
        "file_sha256": base.sha256_file(matrix_path),
    }
    for key, value in checks.items():
        if sidecar.get(key) != value:
            return None, f"payload-mismatch:{key}"
    return matrix, "verified"


def _write_chunk(
    matrix_path: Path,
    sidecar_path: Path,
    *,
    matrix: np.ndarray,
    identity: dict[str, Any],
) -> None:
    value = np.ascontiguousarray(matrix, dtype=np.float32)
    if value.ndim != 2 or not np.isfinite(value).all():
        raise ValueError("chunk matrix must be a finite float32 matrix")
    _atomic_save_npy(matrix_path, value)
    sidecar = {
        **identity,
        "shape": list(value.shape),
        "dtype": str(value.dtype),
        "dimensions": int(value.shape[1]),
        "array_sha256": base.array_hash(value),
        "file_sha256": base.sha256_file(matrix_path),
    }
    _atomic_write_json(sidecar_path, sidecar)


def extract_split(
    split: str,
    codes: Sequence[str],
    output_dir: Path,
    embed_batch: Callable[[list[str]], np.ndarray],
    *,
    batch_size: int,
    stable_keys: Sequence[str],
    source_sha256: Sequence[str],
    fingerprint_payload: dict[str, Any],
    cache: OptionBCache,
    cache_mode: str,
) -> dict[str, Any]:
    """Extract one split with fingerprinted cache and verified chunk recovery."""
    if cache_mode not in CACHE_MODES:
        raise ValueError(f"unsupported cache mode: {cache_mode}")
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    if len(codes) != len(stable_keys) or len(codes) != len(source_sha256):
        raise ValueError("code, stable-key, and source-hash counts must match")
    for index, (code, expected_sha) in enumerate(zip(codes, source_sha256, strict=True)):
        actual_sha = hashlib.sha256(code.encode()).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"source code hash mismatch at {split} row {index}")
    fingerprint = extraction_fingerprint_sha256(fingerprint_payload)
    chunks: list[np.ndarray] = []
    cache_hits = 0
    cache_misses = 0
    resumed = 0
    recomputed = 0
    rejection_reasons: Counter[str] = Counter()
    started = time.perf_counter()
    total_batches = (len(codes) + batch_size - 1) // batch_size

    for batch_index, start in enumerate(range(0, len(codes), batch_size), start=1):
        end = min(start + batch_size, len(codes))
        chunk_identity = _expected_chunk_identity(
            fingerprint_sha256=fingerprint,
            split=split,
            start=start,
            end=end,
            stable_keys=stable_keys[start:end],
            source_sha256=source_sha256[start:end],
        )
        matrix_path, sidecar_path = _chunk_paths(
            output_dir,
            fingerprint_sha256=fingerprint,
            split=split,
            start=start,
            end=end,
        )
        chunk, reason = _load_verified_chunk(
            matrix_path,
            sidecar_path,
            expected=chunk_identity,
            allow_reuse=cache_mode == "read-write",
        )
        if chunk is not None:
            resumed += 1
            state = "verified-chunk"
        else:
            rejection_reasons[reason] += 1
            chunk, hits, misses = _cached_batch(
                keys=stable_keys[start:end],
                source_sha256=source_sha256[start:end],
                codes=codes[start:end],
                embed_batch=embed_batch,
                cache=cache,
                fingerprint_sha256=fingerprint,
            )
            cache_hits += hits
            cache_misses += misses
            _write_chunk(
                matrix_path,
                sidecar_path,
                matrix=chunk,
                identity=chunk_identity,
            )
            recomputed += 1
            state = f"cache={hits} hit/{misses} miss; prior={reason}"
        chunks.append(chunk)
        rate = end / max(time.perf_counter() - started, 1e-9)
        print(
            f"[option-b-embed] {split}: batch {batch_index}/{total_batches} "
            f"{end:,}/{len(codes):,} ({100 * end / len(codes):5.1f}%) "
            f"{state} {rate:,.1f} rows/s",
            file=sys.stderr,
            flush=True,
        )

    matrix = np.concatenate(chunks, axis=0).astype(np.float32, copy=False)
    if matrix.shape[0] != len(codes) or not np.isfinite(matrix).all():
        raise ValueError("assembled embedding matrix is invalid")
    matrix_path = output_dir / f"option-b-embeddings-{split}-v2.npy"
    _atomic_save_npy(matrix_path, matrix)
    return {
        "path": str(matrix_path).replace("\\", "/"),
        "rows": int(matrix.shape[0]),
        "dimensions": int(matrix.shape[1]),
        "dtype": str(matrix.dtype),
        "array_sha256": base.array_hash(matrix),
        "file_sha256": base.sha256_file(matrix_path),
        "extraction_fingerprint_sha256": fingerprint,
        "extraction_fingerprint": fingerprint_payload,
        "verified_chunks_resumed": resumed,
        "chunks_recomputed": recomputed,
        "chunk_rejection_reasons": dict(sorted(rejection_reasons.items())),
        "sqlite_cache_hits": cache_hits,
        "sqlite_cache_misses": cache_misses,
    }


def run_extraction(
    identity_path: Path,
    selection_dir: Path,
    output_dir: Path,
    *,
    batch_size: int = 16,
    device: str = "cpu",
    cache_db: Path = base.DEFAULT_CACHE,
    cache_mode: str = "read-write",
) -> dict[str, Any]:
    """Run recovery-safe extraction after exact fixture preflight."""
    identity, manifests = base.verify_inputs(identity_path, selection_dir)
    revision = identity["model"]["revision"]

    tokenizer, model, torch = load_canonical_backend(
        model_id=MODEL_ID,
        revision=revision,
        device=device,
    )
    preflight = verify_fixture_preflight(
        identity,
        FIXTURE_CODES,
        tokenizer,
        model,
        device=device,
        torch_module=torch,
    )

    identity_file_sha = base.sha256_file(identity_path)
    manifest_hashes = base._manifest_hashes(selection_dir)
    runtime = runtime_identity(torch, device=device)

    with OptionBCache(cache_db, cache_mode) as cache:
        codes = base.reconstruct_selected_code(
            identity,
            manifests,
            selection_dir=selection_dir,
            cache=None if cache_mode == "off" else cache,
        )

        def embed_batch(batch: list[str]) -> np.ndarray:
            return canonical_embed_batch(
                batch,
                tokenizer,
                model,
                device=device,
                torch_module=torch,
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts: dict[str, Any] = {}
        for split in base.SPLITS:
            stable_keys = [row["stable_key"] for row in manifests[split]]
            source_hashes = [row["code_sha256"] for row in manifests[split]]
            fingerprint_payload = extraction_fingerprint_payload(
                identity_file_sha256=identity_file_sha,
                identity=identity,
                split=split,
                split_manifest_sha256=manifest_hashes[split],
                stable_keys=stable_keys,
                source_sha256=source_hashes,
                batch_size=batch_size,
                runtime=runtime,
            )
            artifacts[split] = extract_split(
                split,
                codes[split],
                output_dir,
                embed_batch,
                batch_size=batch_size,
                stable_keys=stable_keys,
                source_sha256=source_hashes,
                fingerprint_payload=fingerprint_payload,
                cache=cache,
                cache_mode=cache_mode,
            )

    report = {
        "embedding_id": "option-b-canonical-embeddings-v2",
        "status": "EMBEDDING_RUN_COMPLETE_PENDING_INDEPENDENT_REPRODUCTION",
        "scientific_result_observed": False,
        "identity": {
            "path": str(identity_path).replace("\\", "/"),
            "file_sha256": identity_file_sha,
            "identity_id": identity["identity_id"],
        },
        "fixture_preflight": preflight,
        "model": {
            "repo_id": MODEL_ID,
            "revision": revision,
            "embedding_implementation_sha256": identity[
                "embedding_implementation_sha256"
            ],
            "tokenization_config_sha256": identity["tokenization_config_sha256"],
            "tokenization_config": identity["tokenization_config"],
            "pooling": POOLING_POLICY,
            "max_length": MAX_LENGTH,
            "output_dtype": OUTPUT_DTYPE,
        },
        "selection_manifest_sha256": manifest_hashes,
        "runtime": runtime,
        "cache": {
            "mode": cache_mode,
            "path": None if cache_mode == "off" else str(cache_db).replace("\\", "/"),
            "schema": CACHE_TABLE,
            "legacy_embedding_table_reused": False,
            "canonical_artifact": False,
        },
        "recovery": {
            "fingerprint_schema": FINGERPRINT_SCHEMA,
            "chunk_schema": CHUNK_SCHEMA,
            "chunk_directory_is_fingerprint_scoped": True,
            "refresh_and_off_bypass_chunk_reuse": True,
            "atomic_chunk_writes": True,
        },
        "artifacts": artifacts,
        "next_allowed_action": "INDEPENDENT_EMBEDDING_REPRODUCTION",
        "prohibited_actions": [
            "canonical embedding publication before independent run agreement",
            "primitive probe fitting",
            "hard-negative generation",
            "scientific metric evaluation",
            "threshold, query, model, or language changes",
        ],
    }
    report_path = output_dir / "option-b-canonical-embeddings-v2.json"
    _atomic_write_json(report_path, report)
    report["report_file_sha256"] = base.sha256_file(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", type=Path, default=base.DEFAULT_IDENTITY)
    parser.add_argument("--selection-dir", type=Path, default=base.DEFAULT_SELECTION)
    parser.add_argument("--output-dir", type=Path, default=base.DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cache-db", type=Path, default=base.DEFAULT_CACHE)
    parser.add_argument("--cache-mode", choices=CACHE_MODES, default="read-write")
    args = parser.parse_args()
    print(
        json.dumps(
            run_extraction(
                args.identity,
                args.selection_dir,
                args.output_dir,
                batch_size=args.batch_size,
                device=args.device,
                cache_db=args.cache_db,
                cache_mode=args.cache_mode,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""Extract canonical frozen CodeBERT embeddings without evaluating the premise."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from relate.experiments.option_b_cache import CACHE_MODES, OptionBCache
from relate.experiments.option_b_identity import MODEL_ID

SPLITS = ("train", "validation", "test")
DEFAULT_IDENTITY = Path("artifacts/canonical/option-b/option-b-external-identity-v1.json")
DEFAULT_SELECTION = Path("artifacts/canonical/option-b/selection")
DEFAULT_OUTPUT = Path("runs/option-b/embeddings")
DEFAULT_CACHE = Path(".writer/option-b/cache/option-b.sqlite3")
MAX_LENGTH = 256


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    payload = (
        json.dumps(
            {"dtype": str(array.dtype), "shape": list(array.shape)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + array.tobytes()
    )
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_inputs(
    identity_path: Path, selection_dir: Path
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    identity = load_json(identity_path)
    if identity.get("status") != "IDENTITY_CAPTURE_COMPLETE":
        raise ValueError("identity checkpoint is incomplete")
    if identity["model"]["repo_id"] != MODEL_ID:
        raise ValueError("identity model does not match frozen Option B model")
    report = load_json(selection_dir / "option-b-canonical-row-selection-v1.json")
    if report.get("status") != "CANONICAL_ROW_SELECTION_COMPLETE":
        raise ValueError("canonical row selection is incomplete")
    manifests: dict[str, list[dict[str, Any]]] = {}
    for split in SPLITS:
        path = selection_dir / f"option-b-selected-{split}-v1.jsonl"
        expected = report["artifacts"][split]["selected_manifest"]
        if sha256_file(path) != expected["sha256"]:
            raise ValueError(f"{split} selected manifest hash does not match checkpoint")
        rows = load_jsonl(path)
        if len(rows) != expected["rows"]:
            raise ValueError(f"{split} selected manifest row count does not match checkpoint")
        manifests[split] = rows
    return identity, manifests


def _manifest_hashes(selection_dir: Path) -> dict[str, str]:
    return {
        split: sha256_file(selection_dir / f"option-b-selected-{split}-v1.jsonl")
        for split in SPLITS
    }


def _load_all_cached_code(
    identity: dict[str, Any],
    manifests: dict[str, list[dict[str, Any]]],
    manifest_hashes: dict[str, str],
    cache: OptionBCache,
) -> dict[str, list[str]] | None:
    revision = identity["dataset"]["revision"]
    result: dict[str, list[str]] = {}
    for split in SPLITS:
        codes: list[str] = []
        for row in manifests[split]:
            code = cache.get_code(
                stable_key=row["stable_key"],
                code_sha256=row["code_sha256"],
                dataset_revision=revision,
                selection_manifest_sha256=manifest_hashes[split],
            )
            if code is None:
                return None
            codes.append(code)
        result[split] = codes
    return result


def reconstruct_selected_code(
    identity: dict[str, Any],
    manifests: dict[str, list[dict[str, Any]]],
    *,
    selection_dir: Path = DEFAULT_SELECTION,
    cache: OptionBCache | None = None,
) -> dict[str, list[str]]:
    """Recover code from cache or the exact frozen dataset and verify every identity."""
    manifest_hashes = _manifest_hashes(selection_dir)
    if cache is not None:
        cached = _load_all_cached_code(identity, manifests, manifest_hashes, cache)
        if cached is not None:
            print(
                "[option-b-embed] selected source code: complete SQLite cache hit",
                file=sys.stderr,
                flush=True,
            )
            return cached
        print(
            "[option-b-embed] selected source code: cache incomplete; reconstructing once",
            file=sys.stderr,
            flush=True,
        )

    try:
        from datasets import load_dataset
        from transformers import AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install Option B dependencies with pip install -e '.[option-b]'") from exc

    from relate.experiments.option_b_real_code import (
        OptionBConfig,
        deterministic_limit,
        remove_cross_split_duplicates,
    )
    from relate.experiments.option_b_selection_resilient import build_records_resilient

    revision = identity["dataset"]["revision"]
    model_revision = identity["model"]["revision"]
    print(
        "[option-b-embed] loading frozen tokenizer and CodeSearchNet",
        file=sys.stderr,
        flush=True,
    )
    dataset = load_dataset(identity["dataset"]["repo_id"], "python", revision=revision)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=model_revision)
    config = OptionBConfig()
    records_by_split = {}
    for split in SPLITS:
        started = time.perf_counter()
        rows = [dict(row, _split=split) for row in dataset[split]]
        print(
            f"[option-b-embed] {split}: reconstructing canonical rows from "
            f"{len(rows):,} source rows",
            file=sys.stderr,
            flush=True,
        )
        records, reasons = build_records_resilient(rows, tokenizer, config)
        records_by_split[split] = records
        print(
            f"[option-b-embed] {split}: eligible={len(records):,} "
            f"exclusions={dict(reasons)} elapsed={time.perf_counter()-started:.1f}s",
            file=sys.stderr,
            flush=True,
        )
    deduplicated, _ = remove_cross_split_duplicates(records_by_split)
    limits = {
        "train": config.train_limit,
        "validation": config.validation_limit,
        "test": config.test_limit,
    }
    selected = {
        split: deterministic_limit(deduplicated[split], limits[split]) for split in SPLITS
    }
    result: dict[str, list[str]] = {}
    for split in SPLITS:
        expected_keys = [row["stable_key"] for row in manifests[split]]
        actual_keys = [record.stable_key for record in selected[split]]
        if actual_keys != expected_keys:
            raise ValueError(f"{split} reconstructed rows do not match canonical manifest")
        result[split] = [record.code for record in selected[split]]
        if cache is not None:
            for manifest_row, record in zip(manifests[split], selected[split], strict=True):
                cache.put_code(
                    stable_key=record.stable_key,
                    split=split,
                    code_sha256=manifest_row["code_sha256"],
                    code=record.code,
                    dataset_revision=revision,
                    selection_manifest_sha256=manifest_hashes[split],
                )
            cache.commit()
    return result


def _cached_batch(
    *,
    keys: list[str],
    codes: list[str],
    embed_batch: Callable[[list[str]], np.ndarray],
    cache: OptionBCache | None,
    model_revision: str,
    pooling_sha256: str,
) -> tuple[np.ndarray, int, int]:
    vectors: list[np.ndarray | None] = [None] * len(keys)
    missing_indices: list[int] = []
    hits = 0
    if cache is not None:
        for index, stable_key in enumerate(keys):
            vector = cache.get_embedding(
                stable_key=stable_key,
                model_id=MODEL_ID,
                model_revision=model_revision,
                pooling_sha256=pooling_sha256,
                max_length=MAX_LENGTH,
            )
            if vector is None:
                missing_indices.append(index)
            else:
                vectors[index] = vector
                hits += 1
    else:
        missing_indices = list(range(len(keys)))

    if missing_indices:
        generated = np.asarray(
            embed_batch([codes[index] for index in missing_indices]), dtype=np.float32
        )
        if generated.ndim != 2 or generated.shape[0] != len(missing_indices):
            raise ValueError("embedding backend returned invalid batch shape")
        for output_index, row_index in enumerate(missing_indices):
            vector = generated[output_index]
            vectors[row_index] = vector
            if cache is not None:
                cache.put_embedding(
                    stable_key=keys[row_index],
                    model_id=MODEL_ID,
                    model_revision=model_revision,
                    pooling_sha256=pooling_sha256,
                    max_length=MAX_LENGTH,
                    vector=vector,
                )
        if cache is not None:
            cache.commit()

    matrix = np.stack([vector for vector in vectors if vector is not None]).astype(
        np.float32, copy=False
    )
    if matrix.shape[0] != len(keys):
        raise ValueError("embedding cache assembly lost rows")
    return matrix, hits, len(missing_indices)


def extract_split(
    split: str,
    codes: list[str],
    output_dir: Path,
    embed_batch: Callable[[list[str]], np.ndarray],
    *,
    batch_size: int,
    stable_keys: list[str] | None = None,
    cache: OptionBCache | None = None,
    model_revision: str = "",
    pooling_sha256: str = "",
) -> dict[str, Any]:
    if stable_keys is None:
        stable_keys = [f"{split}:{index}" for index in range(len(codes))]
    if len(stable_keys) != len(codes):
        raise ValueError("stable key count does not match code count")

    chunk_dir = output_dir / "chunks" / split
    chunk_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    chunks: list[np.ndarray] = []
    cache_hits = 0
    cache_misses = 0
    total_batches = (len(codes) + batch_size - 1) // batch_size
    for batch_index, start in enumerate(range(0, len(codes), batch_size), start=1):
        end = min(start + batch_size, len(codes))
        path = chunk_dir / f"{start:06d}-{end:06d}.npy"
        if path.exists():
            chunk = np.load(path, allow_pickle=False)
            state = "chunk-resumed"
        else:
            chunk, hits, misses = _cached_batch(
                keys=stable_keys[start:end],
                codes=codes[start:end],
                embed_batch=embed_batch,
                cache=cache,
                model_revision=model_revision,
                pooling_sha256=pooling_sha256,
            )
            cache_hits += hits
            cache_misses += misses
            np.save(path, chunk, allow_pickle=False)
            state = f"cache={hits} hit/{misses} miss"
        chunks.append(chunk)
        rate = end / max(time.perf_counter() - started, 1e-9)
        print(
            f"[option-b-embed] {split}: batch {batch_index}/{total_batches} "
            f"{end:,}/{len(codes):,} ({100*end/len(codes):5.1f}%) "
            f"{state} {rate:,.1f} rows/s",
            file=sys.stderr,
            flush=True,
        )
    matrix = np.concatenate(chunks, axis=0).astype(np.float32, copy=False)
    matrix_path = output_dir / f"option-b-embeddings-{split}-v1.npy"
    np.save(matrix_path, matrix, allow_pickle=False)
    return {
        "path": str(matrix_path).replace("\\", "/"),
        "rows": int(matrix.shape[0]),
        "dimensions": int(matrix.shape[1]),
        "dtype": str(matrix.dtype),
        "array_sha256": array_hash(matrix),
        "file_sha256": sha256_file(matrix_path),
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
    cache_db: Path = DEFAULT_CACHE,
    cache_mode: str = "read-write",
) -> dict[str, Any]:
    identity, manifests = verify_inputs(identity_path, selection_dir)
    manifest_hashes = _manifest_hashes(selection_dir)
    with OptionBCache(cache_db, cache_mode) as cache:
        active_cache = None if cache_mode == "off" else cache
        codes = reconstruct_selected_code(
            identity,
            manifests,
            selection_dir=selection_dir,
            cache=active_cache,
        )
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "install Option B dependencies with pip install -e '.[option-b]'"
            ) from exc
        revision = identity["model"]["revision"]
        pooling_sha256 = identity["pooling_implementation_sha256"]
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=revision)
        model = AutoModel.from_pretrained(MODEL_ID, revision=revision).to(device)
        model.eval()

        def embed_batch(batch: list[str]) -> np.ndarray:
            encoded = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            )
            encoded = {name: tensor.to(device) for name, tensor in encoded.items()}
            with torch.inference_mode():
                hidden = model(**encoded).last_hidden_state
                mask = encoded["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            return pooled.cpu().numpy().astype(np.float32)

        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = {
            split: extract_split(
                split,
                codes[split],
                output_dir,
                embed_batch,
                batch_size=batch_size,
                stable_keys=[row["stable_key"] for row in manifests[split]],
                cache=active_cache,
                model_revision=revision,
                pooling_sha256=pooling_sha256,
            )
            for split in SPLITS
        }

    report = {
        "embedding_id": "option-b-canonical-embeddings-v1",
        "status": "CANONICAL_EMBEDDING_EXTRACTION_COMPLETE",
        "scientific_result_observed": False,
        "model": {
            "repo_id": MODEL_ID,
            "revision": revision,
            "pooling": "attention-mask mean pooling",
            "pooling_implementation_sha256": pooling_sha256,
            "max_length": MAX_LENGTH,
        },
        "selection_manifest_sha256": manifest_hashes,
        "cache": {
            "mode": cache_mode,
            "path": None if cache_mode == "off" else str(cache_db).replace("\\", "/"),
            "canonical_artifact": False,
            "git_ignored": True,
        },
        "artifacts": artifacts,
        "environment": {
            "torch": torch.__version__,
            "transformers": __import__("transformers").__version__,
            "numpy": np.__version__,
            "device": device,
        },
        "next_allowed_action": "PRIMITIVE_PROBE_FITTING",
        "prohibited_actions": [
            "scientific metric evaluation",
            "threshold changes",
            "query changes",
            "second model or language",
        ],
    }
    report_path = output_dir / "option-b-canonical-embeddings-v1.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report["report_file_sha256"] = sha256_file(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--selection-dir", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cache-db", type=Path, default=DEFAULT_CACHE)
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

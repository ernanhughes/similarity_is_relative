"""Verify frozen Option B evidence and evaluate the registered methods once."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import mean_absolute_error, r2_score

PRIMITIVES = (
    "cyclomatic_complexity",
    "max_control_depth",
    "distinct_call_sites",
)
METHODS = (
    "raw_cosine",
    "raw_euclidean",
    "token_length",
    "true_oracle",
    "predicted_executor",
)
PRIMARY_METHODS = ("raw_cosine", "raw_euclidean", "predicted_executor")
METHOD_INDEX = {name: index for index, name in enumerate(METHODS)}
RETRIEVAL_KS = (10, 50)
ORACLE_NEIGHBOR_RANK_K = 10
CONTINUATION_GAP = 0.10
BOOTSTRAP_REPETITIONS = 2_000
BOOTSTRAP_SEED = 8_112_026
MIN_REPOSITORY_QUERIES = 20
LOO_REPOSITORIES = 10

DEFAULT_SELECTION_DIR = Path("artifacts/canonical/option-b/selection")
DEFAULT_EMBEDDING_DIR = Path("runs/option-b/gpu-fixed-batch-10/embeddings-a")
DEFAULT_EMBEDDING_CHECKPOINT = Path(
    "artifacts/canonical/option-b/embedding-reproduction-v2/"
    "option-b-independent-embedding-reproduction-v2.json"
)
DEFAULT_PROBE_DIR = Path("artifacts/canonical/option-b/probes-v1")
DEFAULT_MANIFEST_DIR = Path("artifacts/canonical/option-b/hard-negative-manifest-v1")
DEFAULT_OUTPUT_DIR = Path("runs/option-b/method-evaluation-v1")

RESULT_NAME = "option-b-method-evaluation-v1.json"
COMPACT_NAME = "option-b-method-evaluation-compact-v1.json"
QUERY_METRICS_NAME = "option-b-method-query-metrics-v1.jsonl"
PRIMARY_SCORES_NAME = "option-b-method-primary-query-scores-v1.npy"
ENVIRONMENT_NAME = "option-b-method-evaluation-environment-v1.json"


@dataclass(frozen=True)
class FrozenEvaluationConfig:
    retrieval_ks: tuple[int, ...] = RETRIEVAL_KS
    oracle_neighbor_rank_k: int = ORACLE_NEIGHBOR_RANK_K
    continuation_gap: float = CONTINUATION_GAP
    bootstrap_repetitions: int = BOOTSTRAP_REPETITIONS
    bootstrap_seed: int = BOOTSTRAP_SEED
    min_repository_queries: int = MIN_REPOSITORY_QUERIES
    leave_one_out_repositories: int = LOO_REPOSITORIES


DEFAULT_EVALUATION_CONFIG = FrozenEvaluationConfig()


@dataclass(frozen=True)
class PairManifest:
    closer: np.ndarray
    farther: np.ndarray
    offsets: np.ndarray
    counts: np.ndarray


@dataclass(frozen=True)
class VerifiedEvaluationInputs:
    stable_keys: dict[str, tuple[str, ...]]
    repositories: dict[str, tuple[str, ...]]
    token_counts: dict[str, np.ndarray]
    true_primitives: dict[str, np.ndarray]
    scaled_true_primitives: dict[str, np.ndarray]
    embeddings: dict[str, np.ndarray]
    predictions: dict[str, np.ndarray]
    query_summaries: tuple[dict[str, Any], ...]
    pairs: PairManifest
    probe_bundle: dict[str, Any]
    evidence: dict[str, Any]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_text_sha256(path: Path, expected: str) -> tuple[str, bool]:
    raw = path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha == expected:
        return raw_sha, False
    normalized = raw.replace(b"\r\n", b"\n")
    normalized_sha = hashlib.sha256(normalized).hexdigest()
    if normalized_sha == expected:
        return normalized_sha, True
    raise ValueError(f"text artifact hash mismatch: {path}")


def _array_hash(value: np.ndarray) -> str:
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


def _sequence_hash(values: Sequence[str]) -> str:
    payload = json.dumps(list(values), separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _json_safe(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(dict(value), indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    digest = hashlib.sha256()
    try:
        with temporary.open("wb") as handle:
            for row in rows:
                line = (
                    json.dumps(
                        dict(row),
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    )
                    + "\n"
                ).encode("utf-8")
                handle.write(line)
                digest.update(line)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return digest.hexdigest()


def _atomic_save_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}.npy")
    try:
        with temporary.open("wb") as handle:
            np.save(handle, value, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _verify_selection(
    selection_dir: Path,
) -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, tuple[str, ...]],
    dict[str, np.ndarray],
    dict[str, np.ndarray],
    dict[str, Any],
]:
    report_path = selection_dir / "option-b-canonical-row-selection-v2.json"
    report = _load_json(report_path)
    if report.get("selection_id") != "option-b-canonical-row-selection-v2":
        raise ValueError("unexpected canonical selection id")
    if report.get("status") != "CANONICAL_ROW_SELECTION_V2_VERIFIED":
        raise ValueError("canonical selection v2 is incomplete")
    if report.get("scientific_result_observed") is not False:
        raise ValueError("selection checkpoint crossed the result boundary")

    keys: dict[str, tuple[str, ...]] = {}
    repositories: dict[str, tuple[str, ...]] = {}
    token_counts: dict[str, np.ndarray] = {}
    primitives: dict[str, np.ndarray] = {}
    evidence: dict[str, Any] = {
        "report": {
            "path": str(report_path).replace("\\", "/"),
            "file_sha256": _file_sha256(report_path),
        },
        "splits": {},
    }

    for split in ("train", "validation", "test"):
        manifest_path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
        primitive_path = selection_dir / f"option-b-primitives-{split}-v2.jsonl"
        expected = report["artifacts"][split]
        manifest_sha, manifest_normalized = _verified_text_sha256(
            manifest_path, expected["selected_manifest"]["sha256"]
        )
        primitive_sha, primitive_normalized = _verified_text_sha256(
            primitive_path, expected["primitive_table"]["sha256"]
        )

        manifest_rows = _load_jsonl(manifest_path)
        primitive_rows = _load_jsonl(primitive_path)
        expected_rows = int(expected["selected_manifest"]["rows"])
        if len(manifest_rows) != expected_rows or len(primitive_rows) != expected_rows:
            raise ValueError(f"{split} canonical row count mismatch")

        split_keys = tuple(str(row["stable_key"]) for row in manifest_rows)
        primitive_keys = tuple(str(row["stable_key"]) for row in primitive_rows)
        if split_keys != primitive_keys:
            raise ValueError(f"{split} primitive order mismatch")
        if len(set(split_keys)) != len(split_keys):
            raise ValueError(f"{split} stable keys are not unique")

        keys[split] = split_keys
        repositories[split] = tuple(str(row["repository"]) for row in manifest_rows)
        token_counts[split] = np.asarray(
            [int(row["token_count"]) for row in manifest_rows], dtype=np.int64
        )
        primitives[split] = np.asarray(
            [[float(row[name]) for name in PRIMITIVES] for row in primitive_rows],
            dtype=np.float64,
        )
        if not np.isfinite(primitives[split]).all():
            raise ValueError(f"{split} primitive table contains non-finite values")
        evidence["splits"][split] = {
            "rows": expected_rows,
            "manifest_file_sha256": manifest_sha,
            "manifest_checkout_crlf_normalized": manifest_normalized,
            "primitive_file_sha256": primitive_sha,
            "primitive_checkout_crlf_normalized": primitive_normalized,
            "stable_key_sequence_sha256": _sequence_hash(split_keys),
        }

    return keys, repositories, token_counts, primitives, evidence


def _verify_embeddings(
    embedding_dir: Path,
    checkpoint_path: Path,
    stable_keys: Mapping[str, Sequence[str]],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    checkpoint = _load_json(checkpoint_path)
    if checkpoint.get("checkpoint_id") != ("option-b-independent-embedding-reproduction-v2"):
        raise ValueError("unexpected embedding reproduction checkpoint id")
    if checkpoint.get("status") != "CANONICAL_EMBEDDINGS_V2_REPRODUCED":
        raise ValueError("canonical embeddings are not reproduced")
    if checkpoint.get("scientific_result_observed") is not False:
        raise ValueError("embedding checkpoint crossed the result boundary")

    matrices: dict[str, np.ndarray] = {}
    evidence: dict[str, Any] = {
        "checkpoint": {
            "path": str(checkpoint_path).replace("\\", "/"),
            "file_sha256": _file_sha256(checkpoint_path),
            "status": checkpoint["status"],
        },
        "splits": {},
    }
    for split in ("train", "validation", "test"):
        path = embedding_dir / f"option-b-embeddings-{split}-v2.npy"
        expected = checkpoint["splits"][split]
        matrix = np.load(path, mmap_mode="r", allow_pickle=False)
        if matrix.dtype != np.float32:
            raise ValueError(f"{split} embedding dtype mismatch")
        if matrix.shape != (len(stable_keys[split]), int(expected["dimensions"])):
            raise ValueError(f"{split} embedding shape mismatch")
        if not np.isfinite(matrix).all():
            raise ValueError(f"{split} embeddings contain non-finite values")
        if _file_sha256(path) != expected["run_a_file_sha256"]:
            raise ValueError(f"{split} embedding file hash mismatch")
        if _array_hash(np.asarray(matrix)) != expected["array_sha256"]:
            raise ValueError(f"{split} embedding array hash mismatch")
        matrices[split] = matrix
        evidence["splits"][split] = {
            "path": str(path).replace("\\", "/"),
            "rows": int(matrix.shape[0]),
            "dimensions": int(matrix.shape[1]),
            "dtype": str(matrix.dtype),
            "file_sha256": _file_sha256(path),
            "array_sha256": expected["array_sha256"],
        }
    return matrices, evidence


def _verify_predictions(
    probe_dir: Path,
    stable_keys: Mapping[str, Sequence[str]],
) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any]]:
    checkpoint_path = probe_dir / "option-b-primitive-probe-publication-v1.json"
    checkpoint = _load_json(checkpoint_path)
    if checkpoint.get("checkpoint_id") != "option-b-primitive-probe-publication-v1":
        raise ValueError("unexpected primitive-probe checkpoint id")
    if checkpoint.get("status") != "PRIMITIVE_PROBE_ARTIFACTS_PUBLISHED_PENDING_REVIEW":
        raise ValueError("primitive-probe artifacts are not published")
    if checkpoint.get("scientific_result_observed") is not False:
        raise ValueError("probe checkpoint crossed the result boundary")

    bundle_path = probe_dir / "option-b-primitive-probe-bundle-v1.json"
    bundle_sha, bundle_normalized = _verified_text_sha256(
        bundle_path, checkpoint["source_fit"]["file_sha256"]
    )
    bundle = _load_json(bundle_path)
    if bundle.get("probe_bundle_id") != "option-b-primitive-probe-bundle-v1":
        raise ValueError("unexpected probe bundle id")

    roles = {
        "train": ("train_candidates", "option-b-predicted-train-candidates-v1.npy"),
        "validation": ("validation_rows", "option-b-predicted-validation-rows-v1.npy"),
        "test": ("test_queries", "option-b-predicted-test-queries-v1.npy"),
    }
    predictions: dict[str, np.ndarray] = {}
    evidence: dict[str, Any] = {
        "checkpoint": {
            "path": str(checkpoint_path).replace("\\", "/"),
            "file_sha256": _file_sha256(checkpoint_path),
            "status": checkpoint["status"],
            "bundle_sha256": checkpoint["source_fit"]["bundle_sha256"],
            "bundle_file_sha256": bundle_sha,
            "bundle_checkout_crlf_normalized": bundle_normalized,
        },
        "splits": {},
    }
    for split, (role, filename) in roles.items():
        path = probe_dir / filename
        expected = checkpoint["predictions"][role]
        values = np.load(path, mmap_mode="r", allow_pickle=False)
        if values.dtype != np.float64:
            raise ValueError(f"{split} prediction dtype mismatch")
        if values.shape != (len(stable_keys[split]), len(PRIMITIVES)):
            raise ValueError(f"{split} prediction shape mismatch")
        if not np.isfinite(values).all():
            raise ValueError(f"{split} predictions contain non-finite values")
        if _file_sha256(path) != expected["file_sha256"]:
            raise ValueError(f"{split} prediction file hash mismatch")
        if _array_hash(np.asarray(values)) != expected["array_sha256"]:
            raise ValueError(f"{split} prediction array hash mismatch")
        if _sequence_hash(stable_keys[split]) != expected["row_order_sha256"]:
            raise ValueError(f"{split} prediction row-order mismatch")
        predictions[split] = values
        evidence["splits"][split] = {
            "path": str(path).replace("\\", "/"),
            "file_sha256": expected["file_sha256"],
            "array_sha256": expected["array_sha256"],
            "row_order_sha256": expected["row_order_sha256"],
        }
    return predictions, bundle, evidence


def _verify_manifest(
    manifest_dir: Path,
    train_keys: Sequence[str],
    test_keys: Sequence[str],
    test_repositories: Sequence[str],
    test_tokens: np.ndarray,
) -> tuple[tuple[dict[str, Any], ...], PairManifest, dict[str, Any], dict[str, Any]]:
    checkpoint_path = manifest_dir / "option-b-hard-negative-manifest-publication-v1.json"
    checkpoint = _load_json(checkpoint_path)
    if checkpoint.get("checkpoint_id") != ("option-b-hard-negative-manifest-publication-v1"):
        raise ValueError("unexpected hard-negative publication checkpoint id")
    if checkpoint.get("status") != ("HARD_NEGATIVE_MANIFEST_PUBLISHED_PENDING_REVIEW"):
        raise ValueError("hard-negative manifest is not published")
    if checkpoint.get("scientific_result_observed") is not False:
        raise ValueError("manifest checkpoint crossed the result boundary")
    if checkpoint.get("next_allowed_action") != ("METHOD_EVALUATION_IMPLEMENTATION_REVIEW"):
        raise ValueError("manifest checkpoint does not permit evaluation implementation")

    report_path = manifest_dir / "option-b-hard-negative-manifest-v1.json"
    report_sha, report_normalized = _verified_text_sha256(
        report_path, checkpoint["generation"]["file_sha256"]
    )
    report = _load_json(report_path)

    query_path = manifest_dir / "option-b-hard-negative-queries-v1.jsonl"
    pair_path = manifest_dir / "option-b-hard-negative-pairs-v1.jsonl.gz"
    query_sha, query_normalized = _verified_text_sha256(
        query_path, checkpoint["artifacts"]["queries"]["file_sha256"]
    )
    if _file_sha256(pair_path) != checkpoint["artifacts"]["pairs"]["file_sha256"]:
        raise ValueError("hard-negative pair archive hash mismatch")

    query_rows = tuple(_load_jsonl(query_path))
    if len(query_rows) != len(test_keys):
        raise ValueError("hard-negative query row count mismatch")
    counts = np.empty(len(test_keys), dtype=np.int64)
    for index, row in enumerate(query_rows):
        if int(row["query_index"]) != index:
            raise ValueError("hard-negative query indices are not contiguous")
        if str(row["query_stable_key"]) != test_keys[index]:
            raise ValueError("hard-negative query stable-key order mismatch")
        if str(row["query_repository"]) != test_repositories[index]:
            raise ValueError("hard-negative query repository mismatch")
        if int(row["query_token_count"]) != int(test_tokens[index]):
            raise ValueError("hard-negative query token-count mismatch")
        counts[index] = int(row["selected_pair_count"])

    total_pairs = int(np.sum(counts))
    if total_pairs != int(checkpoint["counts"]["pairs"]):
        raise ValueError("hard-negative pair count mismatch")
    offsets = np.zeros(len(test_keys) + 1, dtype=np.int64)
    np.cumsum(counts, out=offsets[1:])
    closer = np.empty(total_pairs, dtype=np.int32)
    farther = np.empty(total_pairs, dtype=np.int32)

    raw_digest = hashlib.sha256()
    row_count = 0
    with gzip.open(pair_path, "rb") as handle:
        for line in handle:
            raw_digest.update(line)
            if not line.strip():
                continue
            row = json.loads(line)
            query_index = int(row["query_index"])
            if not 0 <= query_index < len(test_keys):
                raise ValueError("hard-negative pair query index is invalid")
            expected_position = int(offsets[query_index]) + int(row["pair_order"])
            if expected_position != row_count:
                raise ValueError("hard-negative pair stream is not canonical and contiguous")
            if str(row["query_stable_key"]) != test_keys[query_index]:
                raise ValueError("hard-negative pair query stable key mismatch")
            closer_index = int(row["closer_candidate_index"])
            farther_index = int(row["farther_candidate_index"])
            if not 0 <= closer_index < len(train_keys):
                raise ValueError("hard-negative closer candidate index is invalid")
            if not 0 <= farther_index < len(train_keys):
                raise ValueError("hard-negative farther candidate index is invalid")
            if str(row["closer_stable_key"]) != train_keys[closer_index]:
                raise ValueError("hard-negative closer stable key mismatch")
            if str(row["farther_stable_key"]) != train_keys[farther_index]:
                raise ValueError("hard-negative farther stable key mismatch")
            closer[row_count] = closer_index
            farther[row_count] = farther_index
            row_count += 1
    if row_count != total_pairs:
        raise ValueError("hard-negative pair archive row count mismatch")
    if raw_digest.hexdigest() != checkpoint["artifacts"]["pairs"]["uncompressed_file_sha256"]:
        raise ValueError("hard-negative uncompressed pair hash mismatch")

    evidence = {
        "checkpoint": {
            "path": str(checkpoint_path).replace("\\", "/"),
            "file_sha256": _file_sha256(checkpoint_path),
            "status": checkpoint["status"],
            "generation_report_file_sha256": report_sha,
            "generation_report_checkout_crlf_normalized": report_normalized,
        },
        "queries": {
            "path": str(query_path).replace("\\", "/"),
            "rows": len(query_rows),
            "file_sha256": query_sha,
            "checkout_crlf_normalized": query_normalized,
        },
        "pairs": {
            "path": str(pair_path).replace("\\", "/"),
            "rows": row_count,
            "archive_file_sha256": _file_sha256(pair_path),
            "uncompressed_file_sha256": raw_digest.hexdigest(),
        },
    }
    return (
        query_rows,
        PairManifest(closer=closer, farther=farther, offsets=offsets, counts=counts),
        report,
        evidence,
    )


def verify_evaluation_inputs(
    *,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    embedding_dir: Path = DEFAULT_EMBEDDING_DIR,
    embedding_checkpoint_path: Path = DEFAULT_EMBEDDING_CHECKPOINT,
    probe_dir: Path = DEFAULT_PROBE_DIR,
    manifest_dir: Path = DEFAULT_MANIFEST_DIR,
) -> VerifiedEvaluationInputs:
    """Verify every frozen input before opening the scientific result."""
    keys, repositories, tokens, primitives, selection_evidence = _verify_selection(selection_dir)
    embeddings, embedding_evidence = _verify_embeddings(
        embedding_dir, embedding_checkpoint_path, keys
    )
    predictions, probe_bundle, probe_evidence = _verify_predictions(probe_dir, keys)
    query_rows, pairs, manifest_report, manifest_evidence = _verify_manifest(
        manifest_dir,
        keys["train"],
        keys["test"],
        repositories["test"],
        tokens["test"],
    )

    train_median = np.median(primitives["train"], axis=0)
    q25, q75 = np.percentile(primitives["train"], (25, 75), axis=0)
    train_scale = np.maximum(q75 - q25, 1.0)
    if manifest_report["scaling"]["median"] != train_median.tolist():
        raise ValueError("manifest training median mismatch")
    if manifest_report["scaling"]["scale"] != train_scale.tolist():
        raise ValueError("manifest training robust scale mismatch")
    scaled = {
        split: (primitives[split] - train_median) / train_scale
        for split in ("train", "validation", "test")
    }

    evidence = {
        "selection": selection_evidence,
        "embeddings": embedding_evidence,
        "probes": probe_evidence,
        "manifest": manifest_evidence,
        "input_roles": {
            "true_primitives": "oracle, diagnostics, and frozen manifest only",
            "predictions": "predicted executor on both query and candidate sides",
            "embeddings": "raw cosine and raw Euclidean baselines",
        },
    }
    return VerifiedEvaluationInputs(
        stable_keys=keys,
        repositories=repositories,
        token_counts=tokens,
        true_primitives=primitives,
        scaled_true_primitives=scaled,
        embeddings=embeddings,
        predictions=predictions,
        query_summaries=query_rows,
        pairs=pairs,
        probe_bundle=probe_bundle,
        evidence=evidence,
    )


def _score_pairs(closer: np.ndarray, farther: np.ndarray) -> tuple[np.ndarray, int]:
    if closer.shape != farther.shape:
        raise ValueError("closer and farther distance shapes differ")
    ties = closer == farther
    scores = np.where(ties, 0.5, closer < farther).astype(np.float64)
    return scores, int(np.count_nonzero(ties))


def _pairwise_primary_query(
    *,
    query_index: int,
    inputs: VerifiedEvaluationInputs,
) -> tuple[np.ndarray, np.ndarray]:
    start = int(inputs.pairs.offsets[query_index])
    end = int(inputs.pairs.offsets[query_index + 1])
    closer_index = inputs.pairs.closer[start:end]
    farther_index = inputs.pairs.farther[start:end]
    if len(closer_index) == 0:
        return np.full(len(METHODS), np.nan), np.zeros(len(METHODS), dtype=np.int64)

    query_embedding = np.asarray(inputs.embeddings["test"][query_index], dtype=np.float64)
    closer_embedding = np.asarray(inputs.embeddings["train"][closer_index], dtype=np.float64)
    farther_embedding = np.asarray(inputs.embeddings["train"][farther_index], dtype=np.float64)
    query_norm = float(np.sqrt(np.sum(query_embedding * query_embedding, dtype=np.float64)))
    eps = np.finfo(np.float64).eps

    def cosine(values: np.ndarray) -> np.ndarray:
        dots = np.sum(values * query_embedding, axis=1, dtype=np.float64)
        norms = np.sqrt(np.sum(values * values, axis=1, dtype=np.float64))
        return 1.0 - dots / np.maximum(norms * query_norm, eps)

    def euclidean(values: np.ndarray) -> np.ndarray:
        delta = values - query_embedding
        return np.sqrt(np.sum(delta * delta, axis=1, dtype=np.float64))

    query_token = int(inputs.token_counts["test"][query_index])
    closer_token = inputs.token_counts["train"][closer_index]
    farther_token = inputs.token_counts["train"][farther_index]

    query_true = inputs.scaled_true_primitives["test"][query_index]
    closer_true = inputs.scaled_true_primitives["train"][closer_index]
    farther_true = inputs.scaled_true_primitives["train"][farther_index]

    query_prediction = inputs.predictions["test"][query_index]
    closer_prediction = inputs.predictions["train"][closer_index]
    farther_prediction = inputs.predictions["train"][farther_index]

    closer_distances = (
        cosine(closer_embedding),
        euclidean(closer_embedding),
        np.abs(closer_token - query_token).astype(np.float64),
        np.max(np.abs(closer_true - query_true), axis=1),
        np.max(np.abs(closer_prediction - query_prediction), axis=1),
    )
    farther_distances = (
        cosine(farther_embedding),
        euclidean(farther_embedding),
        np.abs(farther_token - query_token).astype(np.float64),
        np.max(np.abs(farther_true - query_true), axis=1),
        np.max(np.abs(farther_prediction - query_prediction), axis=1),
    )

    query_scores = np.empty(len(METHODS), dtype=np.float64)
    tie_counts = np.empty(len(METHODS), dtype=np.int64)
    for index, (closer, farther) in enumerate(
        zip(closer_distances, farther_distances, strict=True)
    ):
        scores, ties = _score_pairs(closer, farther)
        query_scores[index] = float(np.mean(scores))
        tie_counts[index] = ties
    return query_scores, tie_counts


def compute_primary_query_scores(
    inputs: VerifiedEvaluationInputs,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the frozen hard-negative point-estimate inputs query by query."""
    query_count = len(inputs.stable_keys["test"])
    scores = np.empty((query_count, len(METHODS)), dtype=np.float64)
    ties = np.empty((query_count, len(METHODS)), dtype=np.int64)
    for query_index in range(query_count):
        scores[query_index], ties[query_index] = _pairwise_primary_query(
            query_index=query_index,
            inputs=inputs,
        )
    return scores, ties


def decision_from_query_scores(
    scores: np.ndarray,
    pair_counts: np.ndarray,
) -> dict[str, Any]:
    """Apply the registered point-estimate decision without an inconclusive band."""
    values = np.asarray(scores, dtype=np.float64)
    counts = np.asarray(pair_counts, dtype=np.int64)
    if values.ndim != 2 or values.shape[1] != len(METHODS):
        raise ValueError("primary score matrix has the wrong shape")
    if counts.shape != (len(values),):
        raise ValueError("pair counts do not match query scores")
    eligible = counts > 0
    if not np.any(eligible):
        raise ValueError("no query has an informative hard-negative pair")

    point = {name: float(np.mean(values[eligible, METHOD_INDEX[name]])) for name in METHODS}
    raw_best = max(point["raw_cosine"], point["raw_euclidean"])
    gap = point["predicted_executor"] - raw_best
    outcome = "REAL_PREMISE_SUPPORTED" if gap >= CONTINUATION_GAP else "REAL_PREMISE_FAILED"
    raw_best_methods = [name for name in ("raw_cosine", "raw_euclidean") if point[name] == raw_best]
    return {
        "query_equal_weighted_accuracy": point,
        "queries_with_pairs": int(np.count_nonzero(eligible)),
        "queries_without_pairs": int(np.count_nonzero(~eligible)),
        "raw_best": raw_best,
        "raw_best_methods": raw_best_methods,
        "gap": gap,
        "threshold": CONTINUATION_GAP,
        "outcome": outcome,
        "inconclusive_band": False,
        "secondary_metric_override": False,
    }


def _stable_tie_rank(stable_keys: Sequence[str]) -> np.ndarray:
    order = sorted(range(len(stable_keys)), key=lambda index: stable_keys[index])
    ranks = np.empty(len(order), dtype=np.int64)
    for rank, index in enumerate(order):
        ranks[index] = rank
    return ranks


def _deterministic_order(distances: np.ndarray, stable_ranks: np.ndarray) -> np.ndarray:
    return np.lexsort((stable_ranks, np.asarray(distances, dtype=np.float64)))


def _spearman_from_oracle_rank(oracle_rank: np.ndarray, method: np.ndarray) -> float:
    method_rank = rankdata(method, method="average")
    oracle_centered = oracle_rank - np.mean(oracle_rank)
    method_centered = method_rank - np.mean(method_rank)
    denominator = float(
        np.sqrt(
            np.sum(oracle_centered * oracle_centered) * np.sum(method_centered * method_centered)
        )
    )
    if denominator == 0.0:
        return float("nan")
    return float(np.sum(oracle_centered * method_centered) / denominator)


def _secondary_query_metrics(
    *,
    query_index: int,
    inputs: VerifiedEvaluationInputs,
    train_embeddings64: np.ndarray,
    train_embedding_norms: np.ndarray,
    train_embedding_squared_norms: np.ndarray,
    stable_ranks: np.ndarray,
    config: FrozenEvaluationConfig,
) -> tuple[dict[str, dict[str, float | None]], dict[str, np.ndarray]]:
    query_embedding = np.asarray(inputs.embeddings["test"][query_index], dtype=np.float64)
    dot = train_embeddings64 @ query_embedding
    query_norm = float(np.linalg.norm(query_embedding))
    cosine = 1.0 - dot / np.maximum(train_embedding_norms * query_norm, np.finfo(np.float64).eps)
    euclidean = np.sqrt(
        np.maximum(
            train_embedding_squared_norms
            + float(np.dot(query_embedding, query_embedding))
            - 2.0 * dot,
            0.0,
        )
    )
    token = np.abs(inputs.token_counts["train"] - inputs.token_counts["test"][query_index]).astype(
        np.float64
    )
    oracle = np.max(
        np.abs(
            inputs.scaled_true_primitives["train"]
            - inputs.scaled_true_primitives["test"][query_index]
        ),
        axis=1,
    )
    predicted = np.max(
        np.abs(inputs.predictions["train"] - inputs.predictions["test"][query_index]),
        axis=1,
    )
    distances = {
        "raw_cosine": cosine,
        "raw_euclidean": euclidean,
        "token_length": token,
        "true_oracle": oracle,
        "predicted_executor": predicted,
    }

    oracle_order = _deterministic_order(oracle, stable_ranks)
    oracle_rank = rankdata(oracle, method="average")
    rank_k = min(config.oracle_neighbor_rank_k, len(oracle_order))
    oracle_neighbors = oracle_order[:rank_k]
    metrics: dict[str, dict[str, float | None]] = {}
    rank_samples: dict[str, np.ndarray] = {}
    for method, method_distance in distances.items():
        order = _deterministic_order(method_distance, stable_ranks)
        inverse_rank = np.empty(len(order), dtype=np.int64)
        inverse_rank[order] = np.arange(1, len(order) + 1)
        rank_samples[method] = inverse_rank[oracle_neighbors].astype(np.float64)
        correlation = (
            1.0
            if method == "true_oracle"
            else _spearman_from_oracle_rank(oracle_rank, method_distance)
        )
        method_metrics: dict[str, float | None] = {"spearman_with_oracle": _json_safe(correlation)}
        for k in config.retrieval_ks:
            effective_k = min(k, len(order))
            oracle_top = oracle_order[:effective_k]
            method_top = order[:effective_k]
            overlap = np.intersect1d(oracle_top, method_top, assume_unique=True).size
            retrieved_mean = float(np.mean(oracle[method_top]))
            oracle_mean = float(np.mean(oracle[oracle_top]))
            method_metrics[f"recall_at_{k}"] = overlap / effective_k
            method_metrics[f"neighbor_regret_at_{k}"] = retrieved_mean - oracle_mean
            method_metrics[f"constraint_error_at_{k}"] = float(np.max(oracle[method_top]))
        metrics[method] = method_metrics
    return metrics, rank_samples


def _mean_defined(values: Sequence[float | None]) -> float | None:
    defined = [float(value) for value in values if value is not None]
    return float(np.mean(defined)) if defined else None


def _repository_size_quartiles(repositories: Sequence[str]) -> tuple[np.ndarray, list[float]]:
    counts = Counter(repositories)
    names = sorted(counts)
    sizes = np.asarray([counts[name] for name in names], dtype=np.float64)
    boundaries = np.quantile(sizes, np.linspace(0.0, 1.0, 5), method="linear").astype(np.float64)
    repo_quartile = {
        name: int(np.searchsorted(boundaries[1:-1], counts[name], side="right")) for name in names
    }
    return (
        np.asarray([repo_quartile[name] for name in repositories], dtype=np.int64),
        boundaries.tolist(),
    )


def _group_primary(
    scores: np.ndarray,
    pair_counts: np.ndarray,
    groups: Sequence[str | int],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    group_values = np.asarray(groups)
    for group in sorted(set(groups), key=str):
        mask = group_values == group
        eligible = mask & (pair_counts > 0)
        if not np.any(mask):
            continue
        point = {
            method: (
                float(np.mean(scores[eligible, METHOD_INDEX[method]])) if np.any(eligible) else None
            )
            for method in METHODS
        }
        if np.any(eligible):
            raw_best = max(point["raw_cosine"], point["raw_euclidean"])
            gap = point["predicted_executor"] - raw_best
        else:
            raw_best = None
            gap = None
        result[str(group)] = {
            "queries": int(np.count_nonzero(mask)),
            "queries_with_pairs": int(np.count_nonzero(eligible)),
            "accuracy": point,
            "raw_best": raw_best,
            "gap": gap,
        }
    return result


def _repository_analysis(
    scores: np.ndarray,
    pair_counts: np.ndarray,
    repositories: Sequence[str],
    config: FrozenEvaluationConfig,
) -> dict[str, Any]:
    repository_names = sorted(set(repositories))
    repo_indices = {
        name: np.flatnonzero(np.asarray(repositories) == name) for name in repository_names
    }
    eligible_indices = {
        name: indices[pair_counts[indices] > 0] for name, indices in repo_indices.items()
    }

    per_repository: dict[str, Any] = {}
    for name in repository_names:
        indices = eligible_indices[name]
        if len(indices) < config.min_repository_queries:
            continue
        point = {
            method: float(np.mean(scores[indices, METHOD_INDEX[method]])) for method in METHODS
        }
        raw_best = max(point["raw_cosine"], point["raw_euclidean"])
        per_repository[name] = {
            "test_queries": int(len(repo_indices[name])),
            "queries_with_pairs": int(len(indices)),
            "accuracy": point,
            "raw_best": raw_best,
            "gap": point["predicted_executor"] - raw_best,
        }

    eligible_repositories = [name for name in repository_names if len(eligible_indices[name]) > 0]
    method_repo_sums = np.asarray(
        [np.sum(scores[eligible_indices[name]], axis=0) for name in eligible_repositories],
        dtype=np.float64,
    )
    repo_counts = np.asarray(
        [len(eligible_indices[name]) for name in eligible_repositories],
        dtype=np.int64,
    )
    rng = np.random.default_rng(config.bootstrap_seed)
    bootstrap_values = np.empty(
        (config.bootstrap_repetitions, len(PRIMARY_METHODS) + 1),
        dtype=np.float64,
    )
    primary_columns = [METHOD_INDEX[name] for name in PRIMARY_METHODS]
    for repetition in range(config.bootstrap_repetitions):
        selected = rng.integers(0, len(eligible_repositories), len(eligible_repositories))
        denominator = int(np.sum(repo_counts[selected]))
        means = np.sum(method_repo_sums[selected][:, primary_columns], axis=0) / denominator
        gap = means[2] - max(means[0], means[1])
        bootstrap_values[repetition, :3] = means
        bootstrap_values[repetition, 3] = gap

    interval_names = (*PRIMARY_METHODS, "gap")
    intervals = {
        name: {
            "lower_2_5_percent": float(
                np.quantile(bootstrap_values[:, index], 0.025, method="linear")
            ),
            "upper_97_5_percent": float(
                np.quantile(bootstrap_values[:, index], 0.975, method="linear")
            ),
        }
        for index, name in enumerate(interval_names)
    }

    largest = sorted(
        eligible_repositories,
        key=lambda name: (-len(eligible_indices[name]), name),
    )[: config.leave_one_out_repositories]
    all_eligible = pair_counts > 0
    leave_one_out: dict[str, Any] = {}
    repository_array = np.asarray(repositories)
    for name in largest:
        mask = all_eligible & (repository_array != name)
        point = {method: float(np.mean(scores[mask, METHOD_INDEX[method]])) for method in METHODS}
        raw_best = max(point["raw_cosine"], point["raw_euclidean"])
        leave_one_out[name] = {
            "removed_queries": int(len(eligible_indices[name])),
            "remaining_queries": int(np.count_nonzero(mask)),
            "accuracy": point,
            "raw_best": raw_best,
            "gap": point["predicted_executor"] - raw_best,
        }

    return {
        "independent_unit": "repository",
        "per_repository_minimum_queries": config.min_repository_queries,
        "per_repository": per_repository,
        "bootstrap": {
            "scheme": (
                "sample eligible repositories with replacement; include every "
                "eligible query in each sampled repository occurrence"
            ),
            "repetitions": config.bootstrap_repetitions,
            "seed": config.bootstrap_seed,
            "interval": "percentile 95% using NumPy linear quantiles",
            "descriptive_only": True,
            "intervals": intervals,
        },
        "leave_one_repository_out": {
            "selection": (
                "ten largest eligible test repositories; descending query count, "
                "ascending repository-name tie break"
            ),
            "results": leave_one_out,
        },
    }


def _primitive_metrics(inputs: VerifiedEvaluationInputs) -> dict[str, Any]:
    result: dict[str, Any] = {}
    probe_contract = inputs.probe_bundle["contract"]
    for primitive_index, primitive in enumerate(PRIMITIVES):
        split_metrics: dict[str, Any] = {}
        for split in ("train", "validation", "test"):
            true = inputs.scaled_true_primitives[split][:, primitive_index]
            predicted = inputs.predictions[split][:, primitive_index]
            statistic = float(spearmanr(true, predicted).statistic)
            split_metrics[split] = {
                "mae_robust_scaled_units": float(mean_absolute_error(true, predicted)),
                "r2": float(r2_score(true, predicted)),
                "spearman": _json_safe(statistic),
            }
        result[primitive] = {
            "selected_alpha": probe_contract["primitives"][primitive]["selected_alpha"],
            "splits": split_metrics,
        }
    return result


def _peak_memory_bytes() -> int | None:
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            process = ctypes.windll.kernel32.GetCurrentProcess()
            success = ctypes.windll.psapi.GetProcessMemoryInfo(
                process, ctypes.byref(counters), counters.cb
            )
            return int(counters.PeakWorkingSetSize) if success else None
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if platform.system() == "Darwin" else value * 1024
    except (ImportError, OSError, AttributeError):
        return None


def _environment() -> dict[str, Any]:
    import scipy
    import sklearn

    thread_variables = (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    )
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "thread_environment": {name: os.environ.get(name) for name in thread_variables},
    }


def run_method_evaluation(
    *,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    embedding_dir: Path = DEFAULT_EMBEDDING_DIR,
    embedding_checkpoint_path: Path = DEFAULT_EMBEDDING_CHECKPOINT,
    probe_dir: Path = DEFAULT_PROBE_DIR,
    manifest_dir: Path = DEFAULT_MANIFEST_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Execute the frozen scientific evaluation after implementation review."""
    expected = (
        RESULT_NAME,
        COMPACT_NAME,
        QUERY_METRICS_NAME,
        PRIMARY_SCORES_NAME,
        ENVIRONMENT_NAME,
    )
    existing = [name for name in expected if (output_dir / name).exists()]
    if existing:
        raise FileExistsError(f"evaluation output already contains canonical files: {existing}")

    stage_times: dict[str, float] = {}
    started = time.perf_counter()
    inputs = verify_evaluation_inputs(
        selection_dir=selection_dir,
        embedding_dir=embedding_dir,
        embedding_checkpoint_path=embedding_checkpoint_path,
        probe_dir=probe_dir,
        manifest_dir=manifest_dir,
    )
    stage_times["input_verification_seconds"] = time.perf_counter() - started

    primary_started = time.perf_counter()
    primary_scores, primary_ties = compute_primary_query_scores(inputs)
    primary = decision_from_query_scores(primary_scores, inputs.pairs.counts)
    stage_times["primary_metric_seconds"] = time.perf_counter() - primary_started

    pair_weighted: dict[str, float] = {}
    pair_ties: dict[str, Any] = {}
    total_pairs = int(np.sum(inputs.pairs.counts))
    for method in METHODS:
        column = METHOD_INDEX[method]
        weighted_sum = float(np.nansum(primary_scores[:, column] * inputs.pairs.counts))
        pair_weighted[method] = weighted_sum / total_pairs
        tie_count = int(np.sum(primary_ties[:, column]))
        pair_ties[method] = {
            "ties": tie_count,
            "pairs": total_pairs,
            "rate": tie_count / total_pairs,
        }

    uniform_pair_count = len(set(inputs.pairs.counts.tolist())) == 1
    if uniform_pair_count:
        for method in METHODS:
            query_value = primary["query_equal_weighted_accuracy"][method]
            if not math.isclose(pair_weighted[method], query_value, rel_tol=0.0, abs_tol=1e-15):
                raise RuntimeError(
                    "uniform pair counts did not produce matching query and pair estimates"
                )
            pair_weighted[method] = query_value

    eligible = inputs.pairs.counts > 0
    oracle_scores = primary_scores[eligible, METHOD_INDEX["true_oracle"]]
    if not np.all(oracle_scores == 1.0):
        raise RuntimeError("true-oracle hard-negative accuracy is not exactly one")

    secondary_started = time.perf_counter()
    train_embeddings64 = np.asarray(inputs.embeddings["train"], dtype=np.float64)
    train_squared_norms = np.sum(train_embeddings64 * train_embeddings64, axis=1, dtype=np.float64)
    train_norms = np.sqrt(train_squared_norms)
    stable_ranks = _stable_tie_rank(inputs.stable_keys["train"])
    repository_quartiles, quartile_boundaries = _repository_size_quartiles(
        inputs.repositories["test"]
    )

    aggregate_values: dict[str, dict[str, list[float | None]]] = {method: {} for method in METHODS}
    rank_samples: dict[str, list[np.ndarray]] = {method: [] for method in METHODS}
    query_rows: list[dict[str, Any]] = []
    query_count = len(inputs.stable_keys["test"])
    for query_index in range(query_count):
        if query_index % 50 == 0:
            print(
                f"[option-b-evaluation] secondary query {query_index}/{query_count}",
                file=sys.stderr,
                flush=True,
            )
        metrics, ranks = _secondary_query_metrics(
            query_index=query_index,
            inputs=inputs,
            train_embeddings64=train_embeddings64,
            train_embedding_norms=train_norms,
            train_embedding_squared_norms=train_squared_norms,
            stable_ranks=stable_ranks,
            config=DEFAULT_EVALUATION_CONFIG,
        )
        method_rows: dict[str, Any] = {}
        for method in METHODS:
            method_metric = {
                "hard_negative_triplet_accuracy": _json_safe(
                    primary_scores[query_index, METHOD_INDEX[method]]
                ),
                "hard_negative_method_ties": int(primary_ties[query_index, METHOD_INDEX[method]]),
                **metrics[method],
            }
            method_rows[method] = method_metric
            for name, value in metrics[method].items():
                aggregate_values[method].setdefault(name, []).append(value)
            rank_samples[method].append(ranks[method])
        query_rows.append(
            {
                "query_index": query_index,
                "query_stable_key": inputs.stable_keys["test"][query_index],
                "query_repository": inputs.repositories["test"][query_index],
                "query_token_count": int(inputs.token_counts["test"][query_index]),
                "token_length_decile": int(
                    inputs.query_summaries[query_index]["token_length_decile"]
                ),
                "repository_size_quartile": int(repository_quartiles[query_index]),
                "hard_negative_pair_count": int(inputs.pairs.counts[query_index]),
                "methods": method_rows,
            }
        )

    secondary_summary: dict[str, Any] = {}
    for method in METHODS:
        summary = {name: _mean_defined(values) for name, values in aggregate_values[method].items()}
        pooled_ranks = np.concatenate(rank_samples[method])
        summary["oracle_neighbor_predicted_rank_k"] = (
            DEFAULT_EVALUATION_CONFIG.oracle_neighbor_rank_k
        )
        summary["oracle_neighbor_predicted_rank_median"] = float(np.median(pooled_ranks))
        summary["oracle_neighbor_predicted_rank_p90"] = float(
            np.quantile(pooled_ranks, 0.90, method="linear")
        )
        secondary_summary[method] = summary
    stage_times["secondary_metrics_seconds"] = time.perf_counter() - secondary_started

    analysis_started = time.perf_counter()
    repository_analysis = _repository_analysis(
        primary_scores,
        inputs.pairs.counts,
        inputs.repositories["test"],
        DEFAULT_EVALUATION_CONFIG,
    )
    token_deciles = [int(row["token_length_decile"]) for row in inputs.query_summaries]
    grouped = {
        "token_length_decile": _group_primary(primary_scores, inputs.pairs.counts, token_deciles),
        "repository_size_quartile": {
            "boundaries_over_unique_repository_query_counts": quartile_boundaries,
            "assignment_tie_side": "right",
            "results": _group_primary(
                primary_scores, inputs.pairs.counts, repository_quartiles.tolist()
            ),
        },
    }
    primitive_metrics = _primitive_metrics(inputs)
    stage_times["diagnostic_analysis_seconds"] = time.perf_counter() - analysis_started

    output_dir.mkdir(parents=True, exist_ok=True)
    scores_path = output_dir / PRIMARY_SCORES_NAME
    _atomic_save_npy(scores_path, primary_scores)
    query_path = output_dir / QUERY_METRICS_NAME
    query_sha = _atomic_write_jsonl(query_path, query_rows)
    environment_path = output_dir / ENVIRONMENT_NAME
    environment = _environment()
    _atomic_write_json(environment_path, environment)

    result = {
        "evaluation_id": "option-b-method-evaluation-v1",
        "status": "OPTION_B_METHOD_EVALUATION_COMPLETE_PENDING_INDEPENDENT_RECOMPUTATION",
        "scientific_result_observed": True,
        "scientific_decision": primary,
        "primary_metric": {
            "name": "hard-negative triplet accuracy against true-primitive oracle",
            "aggregation": (
                "equal-weighted mean of per-query accuracies over queries with at least "
                "one informative pair"
            ),
            "method_distance_ties": "score 0.5",
            "oracle_ties": "excluded by frozen manifest",
            "query_equal_weighted_accuracy": primary["query_equal_weighted_accuracy"],
            "ordinary_manifest_pair_weighted_accuracy": pair_weighted,
            "uniform_pair_count_verified": uniform_pair_count,
            "pair_count_per_query": (int(inputs.pairs.counts[0]) if uniform_pair_count else None),
            "method_ties": pair_ties,
        },
        "secondary_metrics": secondary_summary,
        "primitive_recoverability": primitive_metrics,
        "repository_dependence": repository_analysis,
        "diagnostic_groups": grouped,
        "config": {
            "methods": list(METHODS),
            "primary_methods": list(PRIMARY_METHODS),
            "retrieval_ks": list(DEFAULT_EVALUATION_CONFIG.retrieval_ks),
            "oracle_neighbor_rank_k": (DEFAULT_EVALUATION_CONFIG.oracle_neighbor_rank_k),
            "candidate_tie_break": "ascending candidate stable key",
            "bootstrap_repetitions": (DEFAULT_EVALUATION_CONFIG.bootstrap_repetitions),
            "bootstrap_seed": DEFAULT_EVALUATION_CONFIG.bootstrap_seed,
            "continuation_gap": DEFAULT_EVALUATION_CONFIG.continuation_gap,
        },
        "artifacts": {
            "primary_query_scores": {
                "path": str(scores_path).replace("\\", "/"),
                "shape": list(primary_scores.shape),
                "dtype": str(primary_scores.dtype),
                "method_columns": list(METHODS),
                "array_sha256": _array_hash(primary_scores),
                "file_sha256": _file_sha256(scores_path),
            },
            "query_metrics": {
                "path": str(query_path).replace("\\", "/"),
                "rows": len(query_rows),
                "file_sha256": query_sha,
            },
            "environment": {
                "path": str(environment_path).replace("\\", "/"),
                "file_sha256": _file_sha256(environment_path),
            },
        },
        "inputs": inputs.evidence,
        "runtime": {
            "stage_seconds": stage_times,
            "total_seconds": time.perf_counter() - started,
            "peak_process_memory_bytes": _peak_memory_bytes(),
        },
        "verification_separation": {
            "runner_import_for_independent_recomputation": "forbidden",
            "next_allowed_action": "INDEPENDENT_METRIC_RECOMPUTATION",
        },
        "prohibited_actions": [
            "threshold, query, model, language, canonical-row, or manifest changes",
            "secondary-metric override of the point-estimate decision",
            "result publication before independent primary recomputation",
        ],
    }
    result_path = output_dir / RESULT_NAME
    _atomic_write_json(result_path, result)
    result["artifacts"]["result"] = {
        "path": str(result_path).replace("\\", "/"),
        "file_sha256": _file_sha256(result_path),
    }

    compact = {
        "evaluation_id": result["evaluation_id"],
        "status": result["status"],
        "scientific_result_observed": True,
        "scientific_decision": primary,
        "primary_metric": result["primary_metric"],
        "result_file_sha256": result["artifacts"]["result"]["file_sha256"],
        "next_allowed_action": "INDEPENDENT_METRIC_RECOMPUTATION",
    }
    compact_path = output_dir / COMPACT_NAME
    _atomic_write_json(compact_path, compact)
    result["artifacts"]["compact"] = {
        "path": str(compact_path).replace("\\", "/"),
        "file_sha256": _file_sha256(compact_path),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-dir", type=Path, default=DEFAULT_SELECTION_DIR)
    parser.add_argument("--embedding-dir", type=Path, default=DEFAULT_EMBEDDING_DIR)
    parser.add_argument(
        "--embedding-checkpoint",
        type=Path,
        default=DEFAULT_EMBEDDING_CHECKPOINT,
    )
    parser.add_argument("--probe-dir", type=Path, default=DEFAULT_PROBE_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_method_evaluation(
        selection_dir=args.selection_dir,
        embedding_dir=args.embedding_dir,
        embedding_checkpoint_path=args.embedding_checkpoint,
        probe_dir=args.probe_dir,
        manifest_dir=args.manifest_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

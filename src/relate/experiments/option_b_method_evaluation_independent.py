"""Independently recompute the frozen Option B primary decision."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

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
METHOD_INDEX = {name: index for index, name in enumerate(METHODS)}
THRESHOLD = 0.10

DEFAULT_SELECTION_DIR = Path("artifacts/canonical/option-b/selection")
DEFAULT_EMBEDDING_DIR = Path("runs/option-b/gpu-fixed-batch-10/embeddings-a")
DEFAULT_EMBEDDING_CHECKPOINT = Path(
    "artifacts/canonical/option-b/embedding-reproduction-v2/"
    "option-b-independent-embedding-reproduction-v2.json"
)
DEFAULT_PROBE_DIR = Path("artifacts/canonical/option-b/probes-v1")
DEFAULT_MANIFEST_DIR = Path("artifacts/canonical/option-b/hard-negative-manifest-v1")
DEFAULT_RESULT_DIR = Path("runs/option-b/method-evaluation-v1")
VERIFICATION_NAME = "option-b-method-evaluation-independent-v1.json"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_text_sha256(path: Path, expected: str) -> None:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected:
        return
    normalized = raw.replace(b"\r\n", b"\n")
    if hashlib.sha256(normalized).hexdigest() != expected:
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _selection_inputs(
    selection_dir: Path,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    report = _load_json(selection_dir / "option-b-canonical-row-selection-v2.json")
    if report.get("status") != "CANONICAL_ROW_SELECTION_V2_VERIFIED":
        raise ValueError("canonical selection v2 is incomplete")

    loaded: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
    for split in ("train", "test"):
        manifest_path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
        primitive_path = selection_dir / f"option-b-primitives-{split}-v2.jsonl"
        expected = report["artifacts"][split]
        _verify_text_sha256(manifest_path, expected["selected_manifest"]["sha256"])
        _verify_text_sha256(primitive_path, expected["primitive_table"]["sha256"])
        loaded[split] = (_load_jsonl(manifest_path), _load_jsonl(primitive_path))

    train_manifest, train_primitive_rows = loaded["train"]
    test_manifest, test_primitive_rows = loaded["test"]
    train_keys = tuple(str(row["stable_key"]) for row in train_manifest)
    test_keys = tuple(str(row["stable_key"]) for row in test_manifest)
    if train_keys != tuple(str(row["stable_key"]) for row in train_primitive_rows):
        raise ValueError("train primitive order mismatch")
    if test_keys != tuple(str(row["stable_key"]) for row in test_primitive_rows):
        raise ValueError("test primitive order mismatch")

    train_tokens = np.asarray([int(row["token_count"]) for row in train_manifest], dtype=np.int64)
    test_tokens = np.asarray([int(row["token_count"]) for row in test_manifest], dtype=np.int64)
    train_true = np.asarray(
        [[float(row[name]) for name in PRIMITIVES] for row in train_primitive_rows],
        dtype=np.float64,
    )
    test_true = np.asarray(
        [[float(row[name]) for name in PRIMITIVES] for row in test_primitive_rows],
        dtype=np.float64,
    )
    median = np.median(train_true, axis=0)
    q25, q75 = np.percentile(train_true, (25, 75), axis=0)
    scale = np.maximum(q75 - q25, 1.0)
    return (
        train_keys,
        test_keys,
        train_tokens,
        test_tokens,
        (train_true - median) / scale,
        (test_true - median) / scale,
    )


def _embedding_inputs(
    embedding_dir: Path,
    checkpoint_path: Path,
    train_rows: int,
    test_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    checkpoint = _load_json(checkpoint_path)
    if checkpoint.get("status") != "CANONICAL_EMBEDDINGS_V2_REPRODUCED":
        raise ValueError("canonical embeddings are not reproduced")
    result: dict[str, np.ndarray] = {}
    for split, rows in (("train", train_rows), ("test", test_rows)):
        path = embedding_dir / f"option-b-embeddings-{split}-v2.npy"
        expected = checkpoint["splits"][split]
        matrix = np.load(path, mmap_mode="r", allow_pickle=False)
        dimensions = int(expected["dimensions"])
        if matrix.dtype != np.float32 or matrix.shape != (rows, dimensions):
            raise ValueError(f"{split} embedding shape or dtype mismatch")
        if _file_sha256(path) != expected["run_a_file_sha256"]:
            raise ValueError(f"{split} embedding file hash mismatch")
        if _array_hash(np.asarray(matrix)) != expected["array_sha256"]:
            raise ValueError(f"{split} embedding array hash mismatch")
        result[split] = matrix
    return result["train"], result["test"]


def _prediction_inputs(
    probe_dir: Path,
    train_rows: int,
    test_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    checkpoint = _load_json(probe_dir / "option-b-primitive-probe-publication-v1.json")
    if checkpoint.get("status") != "PRIMITIVE_PROBE_ARTIFACTS_PUBLISHED_PENDING_REVIEW":
        raise ValueError("primitive-probe artifacts are not published")
    result: dict[str, np.ndarray] = {}
    for split, role, filename, rows in (
        (
            "train",
            "train_candidates",
            "option-b-predicted-train-candidates-v1.npy",
            train_rows,
        ),
        (
            "test",
            "test_queries",
            "option-b-predicted-test-queries-v1.npy",
            test_rows,
        ),
    ):
        path = probe_dir / filename
        expected = checkpoint["predictions"][role]
        values = np.load(path, mmap_mode="r", allow_pickle=False)
        if values.dtype != np.float64 or values.shape != (rows, len(PRIMITIVES)):
            raise ValueError(f"{split} prediction shape or dtype mismatch")
        if _file_sha256(path) != expected["file_sha256"]:
            raise ValueError(f"{split} prediction file hash mismatch")
        if _array_hash(np.asarray(values)) != expected["array_sha256"]:
            raise ValueError(f"{split} prediction array hash mismatch")
        result[split] = values
    return result["train"], result["test"]


def _pair_inputs(
    manifest_dir: Path,
    train_keys: Sequence[str],
    test_keys: Sequence[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    checkpoint = _load_json(manifest_dir / "option-b-hard-negative-manifest-publication-v1.json")
    if checkpoint.get("status") != "HARD_NEGATIVE_MANIFEST_PUBLISHED_PENDING_REVIEW":
        raise ValueError("hard-negative manifest is not published")
    query_path = manifest_dir / "option-b-hard-negative-queries-v1.jsonl"
    pair_path = manifest_dir / "option-b-hard-negative-pairs-v1.jsonl.gz"
    _verify_text_sha256(query_path, checkpoint["artifacts"]["queries"]["file_sha256"])
    if _file_sha256(pair_path) != checkpoint["artifacts"]["pairs"]["file_sha256"]:
        raise ValueError("pair archive hash mismatch")

    queries = _load_jsonl(query_path)
    if len(queries) != len(test_keys):
        raise ValueError("query stream row count mismatch")
    counts = np.asarray([int(row["selected_pair_count"]) for row in queries], dtype=np.int64)
    offsets = np.zeros(len(counts) + 1, dtype=np.int64)
    np.cumsum(counts, out=offsets[1:])
    closer = np.empty(int(offsets[-1]), dtype=np.int32)
    farther = np.empty(int(offsets[-1]), dtype=np.int32)
    digest = hashlib.sha256()
    position = 0
    with gzip.open(pair_path, "rb") as handle:
        for line in handle:
            digest.update(line)
            if not line.strip():
                continue
            row = json.loads(line)
            query_index = int(row["query_index"])
            expected_position = int(offsets[query_index]) + int(row["pair_order"])
            if expected_position != position:
                raise ValueError("pair stream order mismatch")
            closer_index = int(row["closer_candidate_index"])
            farther_index = int(row["farther_candidate_index"])
            if str(row["query_stable_key"]) != test_keys[query_index]:
                raise ValueError("pair query stable key mismatch")
            if str(row["closer_stable_key"]) != train_keys[closer_index]:
                raise ValueError("pair closer stable key mismatch")
            if str(row["farther_stable_key"]) != train_keys[farther_index]:
                raise ValueError("pair farther stable key mismatch")
            closer[position] = closer_index
            farther[position] = farther_index
            position += 1
    if position != len(closer):
        raise ValueError("pair stream row count mismatch")
    if digest.hexdigest() != checkpoint["artifacts"]["pairs"]["uncompressed_file_sha256"]:
        raise ValueError("uncompressed pair stream hash mismatch")
    return closer, farther, offsets, counts


def _score(closer: np.ndarray, farther: np.ndarray) -> float:
    ties = closer == farther
    return float(np.mean(np.where(ties, 0.5, closer < farther)))


def recompute_primary_scores(
    *,
    train_embeddings: np.ndarray,
    test_embeddings: np.ndarray,
    train_tokens: np.ndarray,
    test_tokens: np.ndarray,
    train_true: np.ndarray,
    test_true: np.ndarray,
    train_predictions: np.ndarray,
    test_predictions: np.ndarray,
    closer: np.ndarray,
    farther: np.ndarray,
    offsets: np.ndarray,
) -> np.ndarray:
    scores = np.empty((len(test_embeddings), len(METHODS)), dtype=np.float64)
    eps = np.finfo(np.float64).eps
    query_count = len(test_embeddings)
    for query_index in range(query_count):
        if query_index % 250 == 0:
            print(
                f"[option-b-independent] primary query {query_index}/{query_count}",
                file=sys.stderr,
                flush=True,
            )
        start = int(offsets[query_index])
        end = int(offsets[query_index + 1])
        if start == end:
            scores[query_index] = np.nan
            continue
        left = closer[start:end]
        right = farther[start:end]
        query_embedding = np.asarray(test_embeddings[query_index], dtype=np.float64)
        left_embedding = np.asarray(train_embeddings[left], dtype=np.float64)
        right_embedding = np.asarray(train_embeddings[right], dtype=np.float64)
        query_norm = float(np.sqrt(np.sum(query_embedding * query_embedding)))

        def cosine(
            values: np.ndarray,
            *,
            _query_embedding: np.ndarray = query_embedding,
            _query_norm: float = query_norm,
        ) -> np.ndarray:
            dots = np.sum(
                values * _query_embedding,
                axis=1,
                dtype=np.float64,
            )
            norms = np.sqrt(np.sum(values * values, axis=1, dtype=np.float64))
            return 1.0 - dots / np.maximum(
                norms * _query_norm,
                eps,
            )

        def euclidean(
            values: np.ndarray,
            *,
            _query_embedding: np.ndarray = query_embedding,
        ) -> np.ndarray:
            delta = values - _query_embedding
            return np.sqrt(np.sum(delta * delta, axis=1, dtype=np.float64))

        left_distances = (
            cosine(left_embedding),
            euclidean(left_embedding),
            np.abs(train_tokens[left] - test_tokens[query_index]).astype(np.float64),
            np.max(np.abs(train_true[left] - test_true[query_index]), axis=1),
            np.max(np.abs(train_predictions[left] - test_predictions[query_index]), axis=1),
        )
        right_distances = (
            cosine(right_embedding),
            euclidean(right_embedding),
            np.abs(train_tokens[right] - test_tokens[query_index]).astype(np.float64),
            np.max(np.abs(train_true[right] - test_true[query_index]), axis=1),
            np.max(np.abs(train_predictions[right] - test_predictions[query_index]), axis=1),
        )
        scores[query_index] = [
            _score(left_distance, right_distance)
            for left_distance, right_distance in zip(left_distances, right_distances, strict=True)
        ]
    return scores


def _decision(scores: np.ndarray, counts: np.ndarray) -> dict[str, Any]:
    eligible = counts > 0
    point = {method: float(np.mean(scores[eligible, METHOD_INDEX[method]])) for method in METHODS}
    raw_best = max(point["raw_cosine"], point["raw_euclidean"])
    gap = point["predicted_executor"] - raw_best
    return {
        "query_equal_weighted_accuracy": point,
        "queries_with_pairs": int(np.count_nonzero(eligible)),
        "queries_without_pairs": int(np.count_nonzero(~eligible)),
        "raw_best": raw_best,
        "raw_best_methods": [
            method for method in ("raw_cosine", "raw_euclidean") if point[method] == raw_best
        ],
        "gap": gap,
        "threshold": THRESHOLD,
        "outcome": ("REAL_PREMISE_SUPPORTED" if gap >= THRESHOLD else "REAL_PREMISE_FAILED"),
        "inconclusive_band": False,
        "secondary_metric_override": False,
    }


def verify_method_evaluation(
    *,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    embedding_dir: Path = DEFAULT_EMBEDDING_DIR,
    embedding_checkpoint_path: Path = DEFAULT_EMBEDDING_CHECKPOINT,
    probe_dir: Path = DEFAULT_PROBE_DIR,
    manifest_dir: Path = DEFAULT_MANIFEST_DIR,
    result_dir: Path = DEFAULT_RESULT_DIR,
) -> dict[str, Any]:
    """Recompute the primary result without importing the evaluation runner."""
    verification_path = result_dir / VERIFICATION_NAME
    if verification_path.exists():
        raise FileExistsError("independent evaluation verification already exists")

    result_path = result_dir / "option-b-method-evaluation-v1.json"
    result = _load_json(result_path)
    if result.get("status") != (
        "OPTION_B_METHOD_EVALUATION_COMPLETE_PENDING_INDEPENDENT_RECOMPUTATION"
    ):
        raise ValueError("method evaluation result is not ready for recomputation")
    if result.get("scientific_result_observed") is not True:
        raise ValueError("method evaluation result does not record an observed result")

    (
        train_keys,
        test_keys,
        train_tokens,
        test_tokens,
        train_true,
        test_true,
    ) = _selection_inputs(selection_dir)
    train_embeddings, test_embeddings = _embedding_inputs(
        embedding_dir,
        embedding_checkpoint_path,
        len(train_keys),
        len(test_keys),
    )
    train_predictions, test_predictions = _prediction_inputs(
        probe_dir, len(train_keys), len(test_keys)
    )
    closer, farther, offsets, counts = _pair_inputs(manifest_dir, train_keys, test_keys)

    recomputed = recompute_primary_scores(
        train_embeddings=train_embeddings,
        test_embeddings=test_embeddings,
        train_tokens=train_tokens,
        test_tokens=test_tokens,
        train_true=train_true,
        test_true=test_true,
        train_predictions=train_predictions,
        test_predictions=test_predictions,
        closer=closer,
        farther=farther,
        offsets=offsets,
    )
    published_scores_path = result_dir / "option-b-method-primary-query-scores-v1.npy"
    published_scores = np.load(published_scores_path, allow_pickle=False)
    if published_scores.dtype != np.float64 or published_scores.shape != recomputed.shape:
        raise ValueError("published primary query-score shape or dtype mismatch")
    if not np.array_equal(published_scores, recomputed, equal_nan=True):
        raise ValueError("independent primary query scores differ from the runner")
    if _array_hash(published_scores) != result["artifacts"]["primary_query_scores"]["array_sha256"]:
        raise ValueError("published primary query-score hash mismatch")

    decision = _decision(recomputed, counts)
    if decision != result["scientific_decision"]:
        raise ValueError("independent scientific decision differs from the runner")

    verification = {
        "verification_id": "option-b-method-evaluation-independent-v1",
        "status": "OPTION_B_PRIMARY_DECISION_INDEPENDENTLY_RECOMPUTED",
        "scientific_result_observed": True,
        "runner_imported": False,
        "checks": {
            "selection_artifacts_reverified": True,
            "embedding_arrays_reverified": True,
            "prediction_arrays_reverified": True,
            "hard_negative_stream_reverified": True,
            "primary_query_scores_recomputed": True,
            "query_scores_exactly_equal": True,
            "point_estimates_recomputed": True,
            "registered_gap_recomputed": True,
            "final_outcome_recomputed": True,
        },
        "scientific_decision": decision,
        "artifacts": {
            "source_result": {
                "path": str(result_path).replace("\\", "/"),
                "file_sha256": _file_sha256(result_path),
            },
            "primary_query_scores": {
                "path": str(published_scores_path).replace("\\", "/"),
                "file_sha256": _file_sha256(published_scores_path),
                "array_sha256": _array_hash(published_scores),
            },
        },
        "next_allowed_action": "CANONICAL_OPTION_B_RESULT_PUBLICATION",
        "prohibited_actions": [
            "threshold or outcome changes",
            "secondary-metric override",
            "post-result rescue experiments under Option B",
        ],
    }
    _atomic_write_json(verification_path, verification)
    verification["verification_file_sha256"] = _file_sha256(verification_path)
    return verification


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
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    args = parser.parse_args()
    verification = verify_method_evaluation(
        selection_dir=args.selection_dir,
        embedding_dir=args.embedding_dir,
        embedding_checkpoint_path=args.embedding_checkpoint,
        probe_dir=args.probe_dir,
        manifest_dir=args.manifest_dir,
        result_dir=args.result_dir,
    )
    print(json.dumps(verification, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

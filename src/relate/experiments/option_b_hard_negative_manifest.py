"""Verify Option B evidence and construct the frozen hard-negative manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from relate.evidence.hashing import sha256_file as _sha256_file
from relate.experiments.option_b_real_code import (
    MANIFEST_SEED,
    PRIMITIVES,
    OptionBConfig,
    array_hash,
    robust_scale,
    robust_scale_fit,
)

DEFAULT_SELECTION_DIR = Path("artifacts/canonical/option-b/selection")
DEFAULT_PROBE_CHECKPOINT = Path(
    "artifacts/canonical/option-b/probes-v1/option-b-primitive-probe-publication-v1.json"
)
DEFAULT_OUTPUT_DIR = Path("runs/option-b/hard-negative-manifest-v1")
SELECTION_REPORT_NAME = "option-b-canonical-row-selection-v2.json"
QUERY_FILENAME = "option-b-hard-negative-queries-v1.jsonl"
PAIR_FILENAME = "option-b-hard-negative-pairs-v1.jsonl"
REPORT_FILENAME = "option-b-hard-negative-manifest-v1.json"

SPARSE_PAIR_THRESHOLD = 32
TOKEN_DECILES = 10


@dataclass(frozen=True)
class FrozenManifestConfig:
    manifest_seed: int = MANIFEST_SEED
    token_deciles: int = TOKEN_DECILES
    min_rank_separation: int = OptionBConfig().min_rank_separation
    max_rank_separation: int = OptionBConfig().max_rank_separation
    max_pairs_per_query: int = OptionBConfig().max_pairs_per_query
    sparse_pair_threshold: int = SPARSE_PAIR_THRESHOLD


DEFAULT_MANIFEST_CONFIG = FrozenManifestConfig()


@dataclass(frozen=True)
class ManifestRows:
    stable_keys: tuple[str, ...]
    repositories: tuple[str, ...]
    token_counts: np.ndarray
    true_primitives: np.ndarray


@dataclass(frozen=True)
class VerifiedManifestInputs:
    train: ManifestRows
    test: ManifestRows
    evidence: dict[str, Any]


@dataclass(frozen=True)
class QueryManifest:
    summary: dict[str, Any]
    pairs: tuple[dict[str, Any], ...]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _jsonl_line(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _stable_key_sequence_hash(keys: Sequence[str]) -> str:
    payload = json.dumps(list(keys), separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _verify_probe_checkpoint(path: Path) -> dict[str, Any]:
    checkpoint = _load_json(path)
    if checkpoint.get("checkpoint_id") != "option-b-primitive-probe-publication-v1":
        raise ValueError("unexpected primitive-probe publication checkpoint id")
    if checkpoint.get("status") != "PRIMITIVE_PROBE_ARTIFACTS_PUBLISHED_PENDING_REVIEW":
        raise ValueError("primitive-probe artifacts are not published")
    if checkpoint.get("scientific_result_observed") is not False:
        raise ValueError("probe checkpoint crossed the scientific-result boundary")
    if checkpoint.get("next_allowed_action") != ("HARD_NEGATIVE_MANIFEST_IMPLEMENTATION_REVIEW"):
        raise ValueError("probe checkpoint does not permit manifest implementation")
    source_fit = checkpoint.get("source_fit", {})
    if source_fit.get("test_primitive_labels_loaded") is not False:
        raise ValueError("probe fit used test primitive labels")
    if source_fit.get("folds") != 5:
        raise ValueError("probe checkpoint does not freeze five folds")
    return checkpoint


def _verify_selection_report(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("selection_id") != "option-b-canonical-row-selection-v2":
        raise ValueError("unexpected canonical selection id")
    if report.get("status") != "CANONICAL_ROW_SELECTION_V2_VERIFIED":
        raise ValueError("canonical selection v2 is incomplete")
    if report.get("scientific_result_observed") is not False:
        raise ValueError("selection report crossed the scientific-result boundary")
    config = report.get("config", {})
    required = {
        "min_rank_separation": OptionBConfig().min_rank_separation,
        "max_rank_separation": OptionBConfig().max_rank_separation,
        "max_pairs_per_query": OptionBConfig().max_pairs_per_query,
    }
    for key, expected in required.items():
        if config.get(key) != expected:
            raise ValueError(f"selection report does not freeze {key}={expected}")
    return report


def _load_split(
    selection_dir: Path,
    selection_report: dict[str, Any],
    split: str,
) -> tuple[ManifestRows, dict[str, Any]]:
    if split not in {"train", "test"}:
        raise ValueError("hard-negative construction uses only train candidates and test queries")

    manifest_path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
    primitive_path = selection_dir / f"option-b-primitives-{split}-v2.jsonl"
    expected = selection_report["artifacts"][split]

    manifest_sha = _sha256_file(manifest_path)
    primitive_sha = _sha256_file(primitive_path)
    if manifest_sha != expected["selected_manifest"]["sha256"]:
        raise ValueError(f"{split} selected manifest hash mismatch")
    if primitive_sha != expected["primitive_table"]["sha256"]:
        raise ValueError(f"{split} primitive table hash mismatch")

    manifest_rows = _load_jsonl(manifest_path)
    primitive_rows = _load_jsonl(primitive_path)
    expected_rows = int(expected["selected_manifest"]["rows"])
    if len(manifest_rows) != expected_rows or len(primitive_rows) != expected_rows:
        raise ValueError(f"{split} row count mismatch")

    manifest_keys = tuple(str(row["stable_key"]) for row in manifest_rows)
    primitive_keys = tuple(str(row["stable_key"]) for row in primitive_rows)
    if manifest_keys != primitive_keys:
        raise ValueError(f"{split} primitive order does not match selected manifest")
    if len(set(manifest_keys)) != len(manifest_keys):
        raise ValueError(f"{split} stable keys are not unique")

    token_counts = np.asarray(
        [int(row["token_count"]) for row in manifest_rows],
        dtype=np.int64,
    )
    true_primitives = np.asarray(
        [[float(row[name]) for name in PRIMITIVES] for row in primitive_rows],
        dtype=np.float64,
    )
    if true_primitives.shape != (expected_rows, len(PRIMITIVES)):
        raise ValueError(f"{split} primitive matrix shape mismatch")
    if not np.isfinite(true_primitives).all():
        raise ValueError(f"{split} primitive matrix contains non-finite values")
    if np.any(token_counts < 0):
        raise ValueError(f"{split} token counts contain negative values")

    repositories = tuple(str(row["repository"]) for row in manifest_rows)
    rows = ManifestRows(
        stable_keys=manifest_keys,
        repositories=repositories,
        token_counts=token_counts,
        true_primitives=true_primitives,
    )
    evidence = {
        "selected_manifest": {
            "path": str(manifest_path).replace("\\", "/"),
            "rows": expected_rows,
            "file_sha256": manifest_sha,
            "stable_key_sequence_sha256": _stable_key_sequence_hash(manifest_keys),
        },
        "primitive_table": {
            "path": str(primitive_path).replace("\\", "/"),
            "rows": expected_rows,
            "file_sha256": primitive_sha,
            "stable_key_sequence_sha256": _stable_key_sequence_hash(primitive_keys),
        },
    }
    return rows, evidence


def verify_manifest_inputs(
    *,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    probe_checkpoint_path: Path = DEFAULT_PROBE_CHECKPOINT,
) -> VerifiedManifestInputs:
    """Verify manifest inputs without opening embeddings, predictions, or method results."""
    probe_checkpoint = _verify_probe_checkpoint(probe_checkpoint_path)
    selection_report_path = selection_dir / SELECTION_REPORT_NAME
    selection_report = _verify_selection_report(selection_report_path)
    train, train_evidence = _load_split(selection_dir, selection_report, "train")
    test, test_evidence = _load_split(selection_dir, selection_report, "test")

    evidence = {
        "probe_checkpoint": {
            "path": str(probe_checkpoint_path).replace("\\", "/"),
            "file_sha256": _sha256_file(probe_checkpoint_path),
            "checkpoint_id": probe_checkpoint["checkpoint_id"],
            "status": probe_checkpoint["status"],
        },
        "selection_report": {
            "path": str(selection_report_path).replace("\\", "/"),
            "file_sha256": _sha256_file(selection_report_path),
            "selection_id": selection_report["selection_id"],
            "status": selection_report["status"],
        },
        "splits": {"train": train_evidence, "test": test_evidence},
        "embeddings_loaded": False,
        "probe_predictions_loaded": False,
        "raw_method_results_loaded": False,
    }
    return VerifiedManifestInputs(train=train, test=test, evidence=evidence)


def token_decile_boundaries(
    candidate_token_counts: np.ndarray,
    *,
    deciles: int = TOKEN_DECILES,
) -> np.ndarray:
    """Return training-candidate quantile boundaries using NumPy's linear method."""
    values = np.asarray(candidate_token_counts, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("candidate token counts must be a non-empty vector")
    if deciles < 2:
        raise ValueError("at least two token buckets are required")
    boundaries = np.quantile(
        values,
        np.linspace(0.0, 1.0, deciles + 1),
        method="linear",
    ).astype(np.float64, copy=False)
    if not np.isfinite(boundaries).all():
        raise ValueError("token-decile boundaries are non-finite")
    return boundaries


def assign_token_deciles(values: np.ndarray, boundaries: np.ndarray) -> np.ndarray:
    """Map values into the frozen candidate-derived deciles with right-side ties."""
    counts = np.asarray(values, dtype=np.float64)
    edges = np.asarray(boundaries, dtype=np.float64)
    if counts.ndim != 1 or edges.ndim != 1 or len(edges) < 3:
        raise ValueError("invalid token-decile inputs")
    return np.searchsorted(edges[1:-1], counts, side="right").astype(np.int64)


def _pair_selection_sha256(
    seed: int,
    query_stable_key: str,
    closer_stable_key: str,
    farther_stable_key: str,
) -> str:
    payload = "\n".join(
        (
            str(seed),
            query_stable_key,
            closer_stable_key,
            farther_stable_key,
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def construct_query_manifest(
    *,
    query_index: int,
    query_stable_key: str,
    query_repository: str,
    query_token_count: int,
    query_true_scaled: np.ndarray,
    train_stable_keys: Sequence[str],
    train_true_scaled: np.ndarray,
    candidate_deciles: np.ndarray,
    query_decile: int,
    config: FrozenManifestConfig = DEFAULT_MANIFEST_CONFIG,
) -> QueryManifest:
    """Construct one query's pair list without consulting any method representation."""
    candidate_pool = np.flatnonzero(candidate_deciles == query_decile)
    ordered_pool = sorted(
        (int(index) for index in candidate_pool),
        key=lambda index: (
            float(np.max(np.abs(train_true_scaled[index] - query_true_scaled))),
            train_stable_keys[index],
        ),
    )
    ordered_distances = np.asarray(
        [
            float(np.max(np.abs(train_true_scaled[index] - query_true_scaled)))
            for index in ordered_pool
        ],
        dtype=np.float64,
    )

    eligible: list[dict[str, Any]] = []
    tie_exclusions = 0
    for closer_rank, closer_index in enumerate(ordered_pool):
        for separation in range(
            config.min_rank_separation,
            config.max_rank_separation + 1,
        ):
            farther_rank = closer_rank + separation
            if farther_rank >= len(ordered_pool):
                break
            farther_index = ordered_pool[farther_rank]
            closer_distance = float(ordered_distances[closer_rank])
            farther_distance = float(ordered_distances[farther_rank])
            if closer_distance == farther_distance:
                tie_exclusions += 1
                continue
            selection_sha = _pair_selection_sha256(
                config.manifest_seed,
                query_stable_key,
                train_stable_keys[closer_index],
                train_stable_keys[farther_index],
            )
            eligible.append(
                {
                    "selection_sha256": selection_sha,
                    "query_index": query_index,
                    "query_stable_key": query_stable_key,
                    "closer_candidate_index": closer_index,
                    "closer_stable_key": train_stable_keys[closer_index],
                    "farther_candidate_index": farther_index,
                    "farther_stable_key": train_stable_keys[farther_index],
                    "closer_oracle_distance": closer_distance,
                    "farther_oracle_distance": farther_distance,
                    "closer_oracle_rank": closer_rank,
                    "farther_oracle_rank": farther_rank,
                    "rank_separation": separation,
                }
            )

    selected = sorted(
        eligible,
        key=lambda row: (
            row["selection_sha256"],
            row["closer_stable_key"],
            row["farther_stable_key"],
        ),
    )[: config.max_pairs_per_query]
    pairs = tuple({**row, "pair_order": order} for order, row in enumerate(selected))
    eligible_count = len(eligible)
    summary = {
        "query_index": query_index,
        "query_stable_key": query_stable_key,
        "query_repository": query_repository,
        "query_token_count": int(query_token_count),
        "token_length_decile": int(query_decile),
        "candidate_pool_size": int(len(candidate_pool)),
        "eligible_pair_count": eligible_count,
        "selected_pair_count": len(pairs),
        "oracle_tie_exclusion_count": tie_exclusions,
        "sparse": eligible_count < config.sparse_pair_threshold,
        "zero_informative_pairs": eligible_count == 0,
    }
    return QueryManifest(summary=summary, pairs=pairs)


def iter_manifest(
    inputs: VerifiedManifestInputs,
    *,
    config: FrozenManifestConfig = DEFAULT_MANIFEST_CONFIG,
) -> Iterator[QueryManifest]:
    """Yield every test query in exact canonical order, including zero-pair queries."""
    train_median, train_scale = robust_scale_fit(inputs.train.true_primitives)
    train_scaled = robust_scale(
        inputs.train.true_primitives,
        train_median,
        train_scale,
    ).astype(np.float64, copy=False)
    test_scaled = robust_scale(
        inputs.test.true_primitives,
        train_median,
        train_scale,
    ).astype(np.float64, copy=False)
    boundaries = token_decile_boundaries(
        inputs.train.token_counts,
        deciles=config.token_deciles,
    )
    candidate_deciles = assign_token_deciles(inputs.train.token_counts, boundaries)
    query_deciles = assign_token_deciles(inputs.test.token_counts, boundaries)

    for query_index, query_key in enumerate(inputs.test.stable_keys):
        yield construct_query_manifest(
            query_index=query_index,
            query_stable_key=query_key,
            query_repository=inputs.test.repositories[query_index],
            query_token_count=int(inputs.test.token_counts[query_index]),
            query_true_scaled=test_scaled[query_index],
            train_stable_keys=inputs.train.stable_keys,
            train_true_scaled=train_scaled,
            candidate_deciles=candidate_deciles,
            query_decile=int(query_deciles[query_index]),
            config=config,
        )


def _write_manifest_stream(
    *,
    query_path: Path,
    pair_path: Path,
    manifests: Iterable[QueryManifest],
) -> dict[str, Any]:
    query_path.parent.mkdir(parents=True, exist_ok=True)
    query_temp = query_path.with_name(f".{query_path.name}.tmp-{os.getpid()}")
    pair_temp = pair_path.with_name(f".{pair_path.name}.tmp-{os.getpid()}")
    query_digest = hashlib.sha256()
    pair_digest = hashlib.sha256()
    query_count = 0
    pair_count = 0
    sparse_count = 0
    zero_count = 0
    per_decile = {str(index): {"queries": 0, "pairs": 0} for index in range(TOKEN_DECILES)}

    try:
        with (
            query_temp.open("wb") as query_handle,
            pair_temp.open("wb") as pair_handle,
        ):
            for manifest in manifests:
                summary_line = _jsonl_line(manifest.summary)
                query_handle.write(summary_line)
                query_digest.update(summary_line)
                query_count += 1
                sparse_count += int(bool(manifest.summary["sparse"]))
                zero_count += int(bool(manifest.summary["zero_informative_pairs"]))
                decile_key = str(manifest.summary["token_length_decile"])
                per_decile[decile_key]["queries"] += 1

                for pair in manifest.pairs:
                    pair_line = _jsonl_line(pair)
                    pair_handle.write(pair_line)
                    pair_digest.update(pair_line)
                    pair_count += 1
                    per_decile[decile_key]["pairs"] += 1

            query_handle.flush()
            pair_handle.flush()
            os.fsync(query_handle.fileno())
            os.fsync(pair_handle.fileno())

        os.replace(query_temp, query_path)
        os.replace(pair_temp, pair_path)
    except BaseException:
        query_temp.unlink(missing_ok=True)
        pair_temp.unlink(missing_ok=True)
        raise

    return {
        "queries": {
            "path": str(query_path).replace("\\", "/"),
            "rows": query_count,
            "file_sha256": query_digest.hexdigest(),
        },
        "pairs": {
            "path": str(pair_path).replace("\\", "/"),
            "rows": pair_count,
            "file_sha256": pair_digest.hexdigest(),
        },
        "sparse_queries": sparse_count,
        "zero_pair_queries": zero_count,
        "by_token_decile": per_decile,
    }


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(dict(value), indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def generate_hard_negative_manifest(
    *,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    probe_checkpoint_path: Path = DEFAULT_PROBE_CHECKPOINT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Generate the frozen manifest only after this implementation has been reviewed."""
    expected_outputs = (QUERY_FILENAME, PAIR_FILENAME, REPORT_FILENAME)
    existing = [name for name in expected_outputs if (output_dir / name).exists()]
    if existing:
        raise FileExistsError(
            f"hard-negative output directory already contains canonical files: {existing}"
        )

    inputs = verify_manifest_inputs(
        selection_dir=selection_dir,
        probe_checkpoint_path=probe_checkpoint_path,
    )
    config = FrozenManifestConfig()
    train_median, train_scale = robust_scale_fit(inputs.train.true_primitives)
    boundaries = token_decile_boundaries(
        inputs.train.token_counts,
        deciles=config.token_deciles,
    )

    query_path = output_dir / QUERY_FILENAME
    pair_path = output_dir / PAIR_FILENAME
    artifacts = _write_manifest_stream(
        query_path=query_path,
        pair_path=pair_path,
        manifests=iter_manifest(inputs, config=config),
    )
    if artifacts["queries"]["rows"] != len(inputs.test.stable_keys):
        raise RuntimeError("not every test query was represented in the manifest")

    report = {
        "manifest_id": "option-b-hard-negative-manifest-v1",
        "status": "HARD_NEGATIVE_MANIFEST_GENERATED_PENDING_PUBLICATION_REVIEW",
        "scientific_result_observed": False,
        "construction_scope": {
            "candidate_pool": "all selected training functions",
            "queries": "all selected test functions",
            "true_primitive_usage": (
                "train-only robust scaling and true-oracle manifest construction"
            ),
            "embeddings_loaded": False,
            "probe_predictions_loaded": False,
            "raw_method_results_loaded": False,
        },
        "config": {
            "manifest_seed": config.manifest_seed,
            "token_deciles": config.token_deciles,
            "token_decile_quantile_method": "numpy linear",
            "token_decile_boundary_tie_side": "right",
            "min_rank_separation": config.min_rank_separation,
            "max_rank_separation": config.max_rank_separation,
            "max_pairs_per_query": config.max_pairs_per_query,
            "sparse_pair_threshold": config.sparse_pair_threshold,
            "oracle_distance": "Chebyshev over robust-scaled true primitives",
            "oracle_order_tie_break": "ascending candidate stable key",
            "oracle_ties": "excluded",
            "pair_selection_order": (
                "ascending SHA-256 of seed and query/closer/farther stable keys"
            ),
            "query_omission": "forbidden",
        },
        "inputs": inputs.evidence,
        "scaling": {
            "fit_split": "train",
            "median": train_median.tolist(),
            "scale": train_scale.tolist(),
            "median_array_sha256": array_hash(np.asarray(train_median, dtype=np.float64)),
            "scale_array_sha256": array_hash(np.asarray(train_scale, dtype=np.float64)),
        },
        "token_decile_boundaries": boundaries.tolist(),
        "token_decile_boundaries_array_sha256": array_hash(boundaries),
        "artifacts": artifacts,
        "all_test_queries_represented": True,
        "next_allowed_action": "CANONICAL_HARD_NEGATIVE_MANIFEST_PUBLICATION",
        "prohibited_actions": [
            "method-distance evaluation before manifest publication review",
            "scientific metric evaluation before manifest publication review",
            "query omission based on pair count",
            "manifest regeneration after method results are inspected",
            "threshold, query, model, language, or canonical-row changes",
        ],
    }
    report_path = output_dir / REPORT_FILENAME
    _atomic_write_json(report_path, report)
    report["report_file_sha256"] = _sha256_file(report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-dir", type=Path, default=DEFAULT_SELECTION_DIR)
    parser.add_argument(
        "--probe-checkpoint",
        type=Path,
        default=DEFAULT_PROBE_CHECKPOINT,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = generate_hard_negative_manifest(
        selection_dir=args.selection_dir,
        probe_checkpoint_path=args.probe_checkpoint,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

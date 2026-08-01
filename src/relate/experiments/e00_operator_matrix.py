"""E00.2 exact and supervised operator comparison.

Consumes the frozen E00.1 arrays. It never regenerates synthetic data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import spearmanr
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

from relate.experiments.e00 import (
    BINARY_REGIMES,
    REGIMES,
    Config,
    array_hash,
    orthogonal_matrix,
    split_indices,
)


@dataclass(frozen=True)
class OperatorConfig:
    retrieval_ks: tuple[int, ...] = (10, 25, 50, 100)
    ridge_alpha: float = 1.0
    pls_ranks: tuple[int, ...] = (4, 16)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, np.finfo(float).eps)


def _pairwise_euclidean(queries: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    q2 = np.sum(queries * queries, axis=1, keepdims=True)
    c2 = np.sum(candidates * candidates, axis=1)[None, :]
    squared = np.maximum(q2 + c2 - 2.0 * queries @ candidates.T, 0.0)
    return np.sqrt(squared)


def _pairwise_cosine(queries: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    return 1.0 - _normalise_rows(queries) @ _normalise_rows(candidates).T


def _distance_from_projection(
    x: np.ndarray,
    train: np.ndarray,
    test: np.ndarray,
    transform: Callable[[np.ndarray], np.ndarray],
) -> np.ndarray:
    projected = transform(x)
    return _pairwise_euclidean(projected[test], projected[train])


def _evaluate_distance_matrix(
    distances: np.ndarray,
    candidate_values: np.ndarray,
    query_values: np.ndarray,
    ks: tuple[int, ...],
    target_kind: str,
) -> dict[str, Any]:
    effective_ks = tuple(k for k in ks if 0 < k <= len(candidate_values))
    recall = {k: [] for k in effective_ks}
    regret = {k: [] for k in effective_ks}
    precision = {k: [] for k in effective_ks}
    correlations: list[float] = []
    triplets: list[float] = []
    aps: list[float] = []

    for row, true_q in zip(distances, query_values, strict=True):
        oracle_distance = np.abs(candidate_values - true_q)
        oracle_order = np.argsort(oracle_distance, kind="stable")
        method_order = np.argsort(row, kind="stable")
        correlations.append(float(spearmanr(oracle_distance, row).statistic))

        half = len(row) // 2
        left = np.arange(half)
        right = left + (len(row) - half)
        oracle_delta = oracle_distance[left] - oracle_distance[right]
        method_delta = row[left] - row[right]
        informative = oracle_delta != 0
        if np.any(informative):
            expected = np.sign(oracle_delta[informative])
            observed = np.sign(method_delta[informative])
            score = np.where(observed == 0, 0.5, observed == expected)
            triplets.append(float(np.mean(score)))

        if target_kind == "binary":
            relevant = candidate_values == true_q
            aps.append(float(average_precision_score(relevant.astype(int), -row)))

        for k in effective_ks:
            oracle = oracle_order[:k]
            retrieved = method_order[:k]
            recall[k].append(np.intersect1d(oracle, retrieved, assume_unique=True).size / k)
            regret[k].append(
                float(np.mean(oracle_distance[retrieved]) - np.mean(oracle_distance[oracle]))
            )
            if target_kind == "binary":
                precision[k].append(float(np.mean(candidate_values[retrieved] == true_q)))

    result: dict[str, Any] = {
        "target_kind": target_kind,
        "spearman": float(np.nanmean(correlations)),
        "triplet_accuracy": float(np.nanmean(triplets)),
        "recall_at": {str(k): float(np.mean(recall[k])) for k in effective_ks},
        "neighbor_regret_at": {str(k): float(np.mean(regret[k])) for k in effective_ks},
    }
    if target_kind == "binary":
        result["class_precision_at"] = {
            str(k): float(np.mean(precision[k])) for k in effective_ks
        }
        result["average_precision"] = float(np.mean(aps))
    return result


def frozen_splits(config: Config) -> dict[str, np.ndarray]:
    """Reproduce the original E00 RNG sequence before constructing splits."""
    rng = np.random.default_rng(config.seed)
    orthogonal_matrix(rng, config.dimensions)
    return split_indices(config, rng)


def run(source_directory: Path, output_directory: Path, config: OperatorConfig) -> dict[str, Any]:
    manifest_path = source_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_config = Config(**manifest["config"])
    splits = frozen_splits(source_config)
    train = splits["train"]
    test = splits["test"]

    for name, indices in splits.items():
        if array_hash(indices) != manifest["split_hashes"][name]:
            raise ValueError(f"Frozen split mismatch: {name}")

    result: dict[str, Any] = {
        "experiment_id": "e00-operator-matrix",
        "status": "IMPLEMENTED_POINT_ESTIMATES_ONLY",
        "source_experiment_id": manifest["experiment_id"],
        "source_manifest_sha256": sha256_file(manifest_path),
        "operator_config": {
            "retrieval_ks": list(config.retrieval_ks),
            "ridge_alpha": config.ridge_alpha,
            "pls_ranks": list(config.pls_ranks),
        },
        "regimes": {},
    }

    for regime in REGIMES:
        array_path = source_directory / "arrays" / f"{regime}.npz"
        with np.load(array_path) as payload:
            x = payload["x"]
            y = payload["y"]
        recorded = manifest["regimes"][regime]
        if array_hash(x) != recorded["x_sha256"] or array_hash(y) != recorded["y_sha256"]:
            raise ValueError(f"Source hash mismatch for {regime}")

        target_kind = "binary" if regime in BINARY_REGIMES else "continuous"
        methods: dict[str, np.ndarray] = {
            "raw_euclidean": _pairwise_euclidean(x[test], x[train]),
            "raw_cosine": _pairwise_cosine(x[test], x[train]),
        }

        ridge = Ridge(alpha=config.ridge_alpha).fit(x[train], y[train])
        predicted = ridge.predict(x)
        methods["ridge_predicted_distance"] = np.abs(
            predicted[test, None] - predicted[train][None, :]
        )

        weights = np.square(np.asarray(ridge.coef_, dtype=np.float64))
        methods["diagonal_ridge_metric"] = _pairwise_euclidean(
            x[test] * np.sqrt(weights), x[train] * np.sqrt(weights)
        )

        direction = np.asarray(ridge.coef_, dtype=np.float64)
        direction /= max(float(np.linalg.norm(direction)), np.finfo(float).eps)
        methods["rank1_ridge_projection"] = _distance_from_projection(
            x,
            train,
            test,
            lambda values, direction=direction: values @ direction[:, None],
        )

        if target_kind == "continuous":
            scaler = StandardScaler().fit(x[train])
            scaled = scaler.transform(x)
            for rank in config.pls_ranks:
                components = min(rank, x.shape[1], len(train) - 1)
                pls = PLSRegression(n_components=components, scale=False).fit(
                    scaled[train], y[train]
                )
                methods[f"pls_projection_rank{rank}"] = _distance_from_projection(
                    scaled, train, test, pls.transform
                )

        result["regimes"][regime] = {
            "x_sha256": recorded["x_sha256"],
            "y_sha256": recorded["y_sha256"],
            "methods": {
                name: _evaluate_distance_matrix(
                    distance,
                    candidate_values=y[train],
                    query_values=y[test],
                    ks=config.retrieval_ks,
                    target_kind=target_kind,
                )
                for name, distance in methods.items()
            },
        }

    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "operator-matrix.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["operator_matrix_sha256"] = sha256_file(output_path)
    (output_directory / "operator-matrix-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("runs/e00/canonical-seed-17"))
    parser.add_argument(
        "--output", type=Path, default=Path("runs/e00/operator-matrix-seed-17")
    )
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, OperatorConfig()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

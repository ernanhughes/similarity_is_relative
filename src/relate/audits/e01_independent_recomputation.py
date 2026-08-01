"""Independent recomputation of the material E01 external-review findings."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score

from relate.experiments.e00 import array_hash, orthogonal_matrix, split_indices
from relate.experiments.e01_relational_conjunction import COMPOUNDS, PRIMITIVES

SEEDS = (401, 433, 467, 503, 557)
WEIGHT_GRID: dict[str, tuple[float, float, float]] = {
    "equal": (1.0, 1.0, 1.0),
    "near_equal": (1.0, 1.1, 1.2),
    "moderate": (1.0, 1.5, 2.0),
    "registered": (1.0, 2.0, 3.0),
    "separated": (1.0, 4.0, 16.0),
}
PERMUTATIONS = tuple(itertools.permutations(range(len(PRIMITIVES))))
NON_IDENTITY_PERMUTATIONS = tuple(p for p in PERMUTATIONS if p != (0, 1, 2))
CYCLIC_PERMUTATION = (1, 2, 0)


@dataclass(frozen=True)
class AuditConfig:
    seed_307: int = 307
    seeds: tuple[int, ...] = SEEDS
    samples: int = 6144
    dimensions: int = 64
    train_fraction: float = 0.60
    validation_fraction: float = 0.20
    target_noise_standard_deviation: float = 0.15
    ridge_alpha: float = 1.0
    retrieval_ks: tuple[int, ...] = (10, 25, 50, 100)
    triplets_per_query: int = 256
    saturation_absolute_gap: float = 0.005
    saturation_median_ceiling_fraction: float = 0.99


def _json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _generate(seed: int, config: AuditConfig) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rotation = orthogonal_matrix(rng, config.dimensions)
    split_config = type(
        "SplitConfig",
        (),
        {
            "samples": config.samples,
            "train_fraction": config.train_fraction,
            "validation_fraction": config.validation_fraction,
        },
    )()
    splits = split_indices(split_config, rng)
    latent = rng.normal(size=(config.samples, len(PRIMITIVES)))
    targets = latent + rng.normal(
        scale=config.target_noise_standard_deviation,
        size=latent.shape,
    )
    base = rng.normal(size=(config.samples, config.dimensions))
    base[:, : len(PRIMITIVES)] = latent
    x = (base @ rotation).astype(np.float64)
    return {
        "x": x,
        "latent": latent.astype(np.float64),
        "targets": targets.astype(np.float64),
        "rotation": rotation,
        "splits": splits,
    }


def _fit_predictions(
    data: dict[str, Any], config: AuditConfig
) -> tuple[np.ndarray, dict[str, Any]]:
    x = data["x"]
    targets = data["targets"]
    train = data["splits"]["train"]
    predictions = np.empty_like(targets)
    metrics: dict[str, Any] = {}
    for index, name in enumerate(PRIMITIVES):
        model = Ridge(alpha=config.ridge_alpha).fit(x[train], targets[train, index])
        predictions[:, index] = model.predict(x)
        test = data["splits"]["test"]
        metrics[name] = {
            "test_r2": float(r2_score(targets[test, index], predictions[test, index])),
            "test_mae": float(mean_absolute_error(targets[test, index], predictions[test, index])),
            "coefficient_sha256": array_hash(np.asarray(model.coef_, dtype=np.float64)),
        }
    return predictions, metrics


def _distance(
    values: np.ndarray,
    candidates: np.ndarray,
    queries: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    left = values[queries]
    right = values[candidates]
    weighted_left = left * np.sqrt(weights)[None, :]
    weighted_right = right * np.sqrt(weights)[None, :]
    squared = np.maximum(
        np.sum(weighted_left * weighted_left, axis=1, keepdims=True)
        + np.sum(weighted_right * weighted_right, axis=1)[None, :]
        - 2.0 * weighted_left @ weighted_right.T,
        0.0,
    )
    return np.sqrt(squared)


def _legacy_triplet_accuracy(distances: np.ndarray, oracle: np.ndarray) -> float:
    count = distances.shape[1]
    left = np.arange(count // 2)
    right = left + (count - count // 2)
    observed = distances[:, left] - distances[:, right]
    expected = oracle[:, left] - oracle[:, right]
    informative = expected != 0
    matches = np.where(
        observed[informative] == 0,
        0.5,
        np.sign(observed[informative]) == np.sign(expected[informative]),
    )
    return float(np.mean(matches))


def _manifest(seed: int, queries: np.ndarray, candidates: np.ndarray, count: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rows: list[tuple[int, int, int]] = []
    for query in queries:
        left = rng.choice(candidates, size=count, replace=True)
        right = rng.choice(candidates, size=count, replace=True)
        rows.extend((int(query), int(a), int(b)) for a, b in zip(left, right, strict=True))
    return np.asarray(rows, dtype=np.int64)


def _manifest_triplet_accuracy(
    distances: np.ndarray,
    oracle: np.ndarray,
    manifest: np.ndarray,
    queries: np.ndarray,
    candidates: np.ndarray,
) -> float:
    query_lookup = {int(value): index for index, value in enumerate(queries)}
    candidate_lookup = {int(value): index for index, value in enumerate(candidates)}
    q = np.fromiter((query_lookup[int(value)] for value in manifest[:, 0]), dtype=np.int64)
    a = np.fromiter((candidate_lookup[int(value)] for value in manifest[:, 1]), dtype=np.int64)
    b = np.fromiter((candidate_lookup[int(value)] for value in manifest[:, 2]), dtype=np.int64)
    expected = oracle[q, a] - oracle[q, b]
    observed = distances[q, a] - distances[q, b]
    informative = expected != 0
    return float(
        np.mean(
            np.where(
                observed[informative] == 0,
                0.5,
                np.sign(observed[informative]) == np.sign(expected[informative]),
            )
        )
    )


def _retrieval_metrics(
    distances: np.ndarray,
    oracle: np.ndarray,
    ks: tuple[int, ...],
) -> dict[str, Any]:
    recalls = {k: [] for k in ks}
    regrets = {k: [] for k in ks}
    correlations: list[float] = []
    ranks_of_oracle_neighbors: list[float] = []
    for row, oracle_row in zip(distances, oracle, strict=True):
        oracle_order = np.argsort(oracle_row, kind="stable")
        predicted_order = np.argsort(row, kind="stable")
        ranks = np.empty(len(row), dtype=np.int64)
        ranks[predicted_order] = np.arange(1, len(row) + 1)
        correlations.append(float(spearmanr(oracle_row, row).statistic))
        ranks_of_oracle_neighbors.extend(ranks[oracle_order[:10]].astype(float).tolist())
        for k in ks:
            oracle_k = oracle_order[:k]
            predicted_k = predicted_order[:k]
            recalls[k].append(np.intersect1d(oracle_k, predicted_k).size / k)
            regrets[k].append(
                float(np.mean(oracle_row[predicted_k]) - np.mean(oracle_row[oracle_k]))
            )
    return {
        "spearman": float(np.nanmean(correlations)),
        "recall_at": {str(k): float(np.mean(recalls[k])) for k in ks},
        "neighbor_regret_at": {str(k): float(np.mean(regrets[k])) for k in ks},
        "oracle_neighbor_predicted_rank_median": float(np.median(ranks_of_oracle_neighbors)),
        "oracle_neighbor_predicted_rank_p90": float(np.percentile(ranks_of_oracle_neighbors, 90)),
    }


def _original_status(accuracy: float, control_accuracies: list[float]) -> str:
    regret = 1.0 - accuracy
    margin = min(accuracy - value for value in control_accuracies)
    if accuracy >= 0.88 and regret <= 0.12 and margin >= 0.10:
        return "SUPPORTED_POINT_ESTIMATE"
    if accuracy < 0.70 or regret > 0.30:
        return "UNSUPPORTED_AT_THRESHOLD"
    return "INSUFFICIENT_EVIDENCE"


def _seed_record(seed: int, config: AuditConfig, include_legacy: bool) -> dict[str, Any]:
    data = _generate(seed, config)
    predictions, primitive_metrics = _fit_predictions(data, config)
    train = data["splits"]["train"]
    test = data["splits"]["test"]
    record: dict[str, Any] = {
        "x_sha256": array_hash(data["x"]),
        "latent_sha256": array_hash(data["latent"]),
        "targets_sha256": array_hash(data["targets"]),
        "rotation_sha256": array_hash(data["rotation"]),
        "split_hashes": {name: array_hash(value) for name, value in data["splits"].items()},
        "primitive_metrics": primitive_metrics,
        "compounds": {},
    }
    for compound_index, (compound, raw_weights) in enumerate(COMPOUNDS.items()):
        weights = np.asarray(raw_weights, dtype=float)
        noisy_oracle = _distance(data["targets"], train, test, weights)
        predicted_distance = _distance(predictions, train, test, weights)
        latent_distance = _distance(data["latent"], train, test, weights)
        if include_legacy:
            predicted_accuracy = _legacy_triplet_accuracy(predicted_distance, noisy_oracle)
            latent_accuracy = _legacy_triplet_accuracy(latent_distance, noisy_oracle)
        else:
            manifest = _manifest(
                seed * 1000 + compound_index * 10 + 1,
                test,
                train,
                config.triplets_per_query,
            )
            predicted_accuracy = _manifest_triplet_accuracy(
                predicted_distance, noisy_oracle, manifest, test, train
            )
            latent_accuracy = _manifest_triplet_accuracy(
                latent_distance, noisy_oracle, manifest, test, train
            )
        permutation_accuracies: dict[str, float] = {}
        for permutation in NON_IDENTITY_PERMUTATIONS:
            distance = _distance(predictions[:, permutation], train, test, weights)
            if include_legacy:
                accuracy = _legacy_triplet_accuracy(distance, noisy_oracle)
            else:
                accuracy = _manifest_triplet_accuracy(distance, noisy_oracle, manifest, test, train)
            permutation_accuracies["_".join(map(str, permutation))] = accuracy
        strongest_key = max(permutation_accuracies, key=permutation_accuracies.get)
        strongest = permutation_accuracies[strongest_key]
        compound_record: dict[str, Any] = {
            "weights": list(raw_weights),
            "predicted_accuracy": predicted_accuracy,
            "latent_oracle_accuracy": latent_accuracy,
            "absolute_latent_gap": abs(predicted_accuracy - latent_accuracy),
            "ceiling_fraction": predicted_accuracy / latent_accuracy if latent_accuracy else None,
            "permutation_accuracies": permutation_accuracies,
            "strongest_permutation": strongest_key,
            "strongest_permutation_accuracy": strongest,
            "strongest_permutation_margin": predicted_accuracy - strongest,
            "predicted_retrieval": _retrieval_metrics(
                predicted_distance, noisy_oracle, config.retrieval_ks
            ),
            "latent_retrieval": _retrieval_metrics(
                latent_distance, noisy_oracle, config.retrieval_ks
            ),
        }
        if include_legacy:
            cyclic_key = "_".join(map(str, CYCLIC_PERMUTATION))
            cyclic = permutation_accuracies[cyclic_key]
            compound_record.update(
                {
                    "cyclic_permutation_accuracy": cyclic,
                    "cyclic_permutation_margin": predicted_accuracy - cyclic,
                    "original_status_with_cyclic_control": _original_status(
                        predicted_accuracy, [cyclic]
                    ),
                    "original_status_with_exhaustive_control": _original_status(
                        predicted_accuracy, list(permutation_accuracies.values())
                    ),
                }
            )
        record["compounds"][compound] = compound_record
    return record


def _weight_separation(config: AuditConfig) -> dict[str, Any]:
    data = _generate(config.seed_307, config)
    predictions, _ = _fit_predictions(data, config)
    train = data["splits"]["train"]
    test = data["splits"]["test"]
    results: dict[str, Any] = {}
    margins: list[float] = []
    for name, raw_weights in WEIGHT_GRID.items():
        weights = np.asarray(raw_weights, dtype=float)
        oracle = _distance(data["targets"], train, test, weights)
        predicted = _distance(predictions, train, test, weights)
        predicted_accuracy = _legacy_triplet_accuracy(predicted, oracle)
        wrong = [
            _legacy_triplet_accuracy(
                _distance(predictions[:, permutation], train, test, weights), oracle
            )
            for permutation in NON_IDENTITY_PERMUTATIONS
        ]
        margin = predicted_accuracy - max(wrong)
        margins.append(margin)
        results[name] = {
            "weights": list(raw_weights),
            "predicted_accuracy": predicted_accuracy,
            "strongest_wrong_accuracy": max(wrong),
            "margin": margin,
        }
    symmetric_zero = abs(margins[0]) <= 1e-12
    non_decreasing = all(
        left <= right + 1e-12 for left, right in zip(margins, margins[1:], strict=False)
    )
    return {
        "grid": results,
        "decision": (
            "WEIGHT_SEPARATION_DIAGNOSTIC_SUPPORTED"
            if symmetric_zero and non_decreasing
            else "WEIGHT_SEPARATION_DIAGNOSTIC_NOT_SUPPORTED"
        ),
    }


def run(output: Path, config: AuditConfig | None = None) -> dict[str, Any]:
    config = config or AuditConfig()
    seed_307 = _seed_record(config.seed_307, config, include_legacy=True)
    fresh = {str(seed): _seed_record(seed, config, include_legacy=False) for seed in config.seeds}
    all_fresh_compounds = [
        compound for seed_record in fresh.values() for compound in seed_record["compounds"].values()
    ]
    ceiling_fractions = [
        float(value["ceiling_fraction"])
        for value in all_fresh_compounds
        if value["ceiling_fraction"] is not None
    ]
    saturated = (
        all(
            value["absolute_latent_gap"] <= config.saturation_absolute_gap
            for value in all_fresh_compounds
        )
        and float(np.median(ceiling_fractions)) >= config.saturation_median_ceiling_fraction
    )
    exhaustive_failures = [
        name
        for name, compound in seed_307["compounds"].items()
        if compound["original_status_with_exhaustive_control"] != "SUPPORTED_POINT_ESTIMATE"
    ]
    decisions = {
        "e01_1_exhaustive_control": (
            "ORIGINAL_RULE_RETAINED"
            if not exhaustive_failures
            else "ORIGINAL_RULE_FAILS_WITH_EXHAUSTIVE_CONTROL"
        ),
        "e01_1_exhaustive_control_failed_compounds": exhaustive_failures,
        "ceiling": "SATURATED_AT_LATENT_ORACLE" if saturated else "HEADROOM_PRESENT",
    }
    weight_separation = _weight_separation(config)
    decisions["weight_separation"] = weight_separation["decision"]
    result: dict[str, Any] = {
        "audit_id": "e01-independent-recomputation",
        "status": "AUDIT_RESULT_COMPLETE",
        "verification_class": "INDEPENDENT_RECOMPUTATION",
        "config": asdict(config),
        "config_sha256": _json_hash(asdict(config)),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "seed_307": seed_307,
        "fresh_seeds": fresh,
        "weight_separation": weight_separation,
        "decisions": decisions,
        "claim_promotion_allowed": False,
    }
    result["decision_tree_sha256"] = _json_hash(decisions)
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / "e01-independent-recomputation.json"
    raw_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["result_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    (output / "e01-independent-recomputation-with-hash.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/e01/independent-recomputation"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

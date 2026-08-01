"""E00.3 nulls, uncertainty, nonlinear boundary confirmation, and certification.

Consumes the frozen E00 arrays and the verified E00.2 operator matrix. It does not
regenerate synthetic data. Decisions are scoped to seed 17 and the declared model
families; confirmatory multi-seed replication remains a separate gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPClassifier

from relate.experiments.e00 import REGIMES, Config, array_hash
from relate.experiments.e00_operator_matrix import (
    _pairwise_euclidean,
    frozen_splits,
    sha256_file,
)


@dataclass(frozen=True)
class CertificationConfig:
    seed: int = 1703
    permutations: int = 100
    bootstrap_samples: int = 1000
    null_query_count: int = 200
    null_candidate_count: int = 1024
    confidence_level: float = 0.95
    support_triplet_floor: float = 0.75
    nonlinear_average_precision_floor: float = 0.80
    basis_dependence_delta_floor: float = 0.50
    instability_delta_floor: float = 0.10


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _triplet_scores(
    distances: np.ndarray, candidate_values: np.ndarray, query_values: np.ndarray
) -> np.ndarray:
    """Return one deterministic pairwise-order score per query."""
    scores: list[float] = []
    count = len(candidate_values)
    half = count // 2
    left = np.arange(half)
    right = left + (count - half)
    for row, query in zip(distances, query_values, strict=True):
        oracle = np.abs(candidate_values - query)
        oracle_delta = oracle[left] - oracle[right]
        predicted_delta = row[left] - row[right]
        informative = oracle_delta != 0
        if not np.any(informative):
            scores.append(float("nan"))
            continue
        expected = np.sign(oracle_delta[informative])
        observed = np.sign(predicted_delta[informative])
        values = np.where(observed == 0, 0.5, observed == expected)
        scores.append(float(np.mean(values)))
    return np.asarray(scores, dtype=np.float64)


def _average_precision_scores(
    distances: np.ndarray, candidate_values: np.ndarray, query_values: np.ndarray
) -> np.ndarray:
    """Return average precision per binary query without relying on private APIs."""
    scores: list[float] = []
    for row, query in zip(distances, query_values, strict=True):
        relevant = candidate_values == query
        order = np.argsort(row, kind="stable")
        ranked = relevant[order].astype(np.float64)
        cumulative = np.cumsum(ranked)
        precision = cumulative / np.arange(1, len(ranked) + 1)
        positives = int(np.sum(ranked))
        scores.append(float(np.sum(precision * ranked) / positives) if positives else float("nan"))
    return np.asarray(scores, dtype=np.float64)


def _bootstrap_interval(
    values: np.ndarray, rng: np.random.Generator, samples: int, confidence: float
) -> dict[str, float]:
    clean = values[np.isfinite(values)]
    if clean.size == 0:
        return {"estimate": float("nan"), "lower": float("nan"), "upper": float("nan")}
    draws = rng.integers(0, clean.size, size=(samples, clean.size))
    means = np.mean(clean[draws], axis=1)
    alpha = (1.0 - confidence) / 2.0
    return {
        "estimate": float(np.mean(clean)),
        "lower": float(np.quantile(means, alpha)),
        "upper": float(np.quantile(means, 1.0 - alpha)),
    }


def _bootstrap_difference(
    left: np.ndarray,
    right: np.ndarray,
    rng: np.random.Generator,
    samples: int,
    confidence: float,
) -> dict[str, float]:
    left = left[np.isfinite(left)]
    right = right[np.isfinite(right)]
    left_draws = rng.integers(0, left.size, size=(samples, left.size))
    right_draws = rng.integers(0, right.size, size=(samples, right.size))
    differences = np.mean(left[left_draws], axis=1) - np.mean(right[right_draws], axis=1)
    alpha = (1.0 - confidence) / 2.0
    return {
        "estimate": float(np.mean(left) - np.mean(right)),
        "lower": float(np.quantile(differences, alpha)),
        "upper": float(np.quantile(differences, 1.0 - alpha)),
    }


def _ridge_distances(
    x: np.ndarray, y: np.ndarray, train: np.ndarray, queries: np.ndarray
) -> np.ndarray:
    model = Ridge(alpha=1.0).fit(x[train], y[train])
    predictions = model.predict(x)
    return np.abs(predictions[queries, None] - predictions[train][None, :])


def _diagonal_distances(
    x: np.ndarray, y: np.ndarray, train: np.ndarray, queries: np.ndarray
) -> np.ndarray:
    model = Ridge(alpha=1.0).fit(x[train], y[train])
    weights = np.square(np.asarray(model.coef_, dtype=np.float64))
    root = np.sqrt(weights)
    return _pairwise_euclidean(x[queries] * root, x[train] * root)


def _mlp_xor_distances(
    x: np.ndarray, y: np.ndarray, train: np.ndarray, queries: np.ndarray, seed: int
) -> np.ndarray:
    model = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        alpha=1e-4,
        batch_size=128,
        learning_rate_init=1e-3,
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.2,
        n_iter_no_change=30,
        random_state=seed,
    ).fit(x[train], y[train].astype(int))
    probabilities = model.predict_proba(x)[:, 1]
    return np.abs(probabilities[queries, None] - probabilities[train][None, :])


def _permutation_null(
    x: np.ndarray,
    y: np.ndarray,
    train: np.ndarray,
    queries: np.ndarray,
    rng: np.random.Generator,
    config: CertificationConfig,
    distance_builder: Callable[[np.ndarray, np.ndarray, np.ndarray, np.ndarray], np.ndarray],
) -> dict[str, Any]:
    candidate_subset = np.sort(
        rng.choice(train, size=min(config.null_candidate_count, len(train)), replace=False)
    )
    query_subset = np.sort(
        rng.choice(queries, size=min(config.null_query_count, len(queries)), replace=False)
    )
    values: list[float] = []
    for _ in range(config.permutations):
        permuted = y.copy()
        permuted[train] = rng.permutation(y[train])
        distances = distance_builder(x, permuted, candidate_subset, query_subset)
        scores = _triplet_scores(
            distances, candidate_values=y[candidate_subset], query_values=y[query_subset]
        )
        values.append(float(np.nanmean(scores)))
    array = np.asarray(values, dtype=np.float64)
    return {
        "permutations": config.permutations,
        "query_count": len(query_subset),
        "candidate_count": len(candidate_subset),
        "mean": float(np.mean(array)),
        "q95": float(np.quantile(array, 0.95)),
        "q99": float(np.quantile(array, 0.99)),
        "values_sha256": hashlib.sha256(array.tobytes()).hexdigest(),
    }


def _decision(status: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "evidence": evidence}


def run(
    source_directory: Path,
    operator_directory: Path,
    output_directory: Path,
    config: CertificationConfig,
) -> dict[str, Any]:
    manifest_path = source_directory / "manifest.json"
    operator_path = operator_directory / "operator-matrix.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    operator = json.loads(operator_path.read_text(encoding="utf-8"))
    if operator["source_manifest_sha256"] != sha256_file(manifest_path):
        raise ValueError("Operator matrix does not reference the supplied E00 manifest")

    source_config = Config(**manifest["config"])
    splits = frozen_splits(source_config)
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    rng = np.random.default_rng(config.seed)

    result: dict[str, Any] = {
        "experiment_id": "e00-certification",
        "status": "SEED17_CERTIFICATION_COMPLETE",
        "scope": "single frozen seed; declared operator families only",
        "source_manifest_sha256": sha256_file(manifest_path),
        "operator_matrix_sha256": sha256_file(operator_path),
        "config": asdict(config),
        "regimes": {},
        "decisions": {},
    }

    score_cache: dict[tuple[str, str, str], np.ndarray] = {}
    arrays: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for regime in REGIMES:
        with np.load(source_directory / "arrays" / f"{regime}.npz") as payload:
            x = payload["x"]
            y = payload["y"]
        recorded = manifest["regimes"][regime]
        if array_hash(x) != recorded["x_sha256"] or array_hash(y) != recorded["y_sha256"]:
            raise ValueError(f"Source hash mismatch: {regime}")
        arrays[regime] = (x, y)

        method_results: dict[str, Any] = {}
        for name, builder in (
            ("rank1_ridge_projection", _ridge_distances),
            ("diagonal_ridge_metric", _diagonal_distances),
        ):
            distances = builder(x, y, train, test)
            scores = _triplet_scores(distances, y[train], y[test])
            score_cache[(regime, name, "test")] = scores
            interval = _bootstrap_interval(
                scores, rng, config.bootstrap_samples, config.confidence_level
            )
            null = _permutation_null(x, y, train, test, rng, config, builder)
            method_results[name] = {"triplet_accuracy": interval, "permutation_null": null}

        if regime == "nonlinear_xor":
            distances = _mlp_xor_distances(x, y, train, test, config.seed)
            ap_scores = _average_precision_scores(distances, y[train], y[test])
            method_results["nonlinear_mlp"] = {
                "average_precision": _bootstrap_interval(
                    ap_scores, rng, config.bootstrap_samples, config.confidence_level
                ),
                "model_seed": config.seed,
            }

        if regime == "correlated_nuisance":
            validation_distances = _ridge_distances(x, y, train, validation)
            validation_scores = _triplet_scores(validation_distances, y[train], y[validation])
            test_scores = score_cache[(regime, "rank1_ridge_projection", "test")]
            method_results["shift_gap"] = _bootstrap_difference(
                validation_scores,
                test_scores,
                rng,
                config.bootstrap_samples,
                config.confidence_level,
            )

        result["regimes"][regime] = {"methods": method_results}

    axis_diag = score_cache[("axis_linear", "diagonal_ridge_metric", "test")]
    rotated_diag = score_cache[("rotated_linear", "diagonal_ridge_metric", "test")]
    basis_delta = _bootstrap_difference(
        axis_diag,
        rotated_diag,
        rng,
        config.bootstrap_samples,
        config.confidence_level,
    )
    result["comparisons"] = {"axis_minus_rotated_diagonal_triplet": basis_delta}

    for regime in ("axis_linear", "rotated_linear"):
        evidence = result["regimes"][regime]["methods"]["rank1_ridge_projection"]
        interval = evidence["triplet_accuracy"]
        null = evidence["permutation_null"]
        supported = (
            interval["lower"] >= config.support_triplet_floor and interval["estimate"] > null["q99"]
        )
        result["decisions"][f"{regime}.rank1"] = _decision(
            "SUPPORTED" if supported else "INSUFFICIENT_EVIDENCE",
            "Bootstrap lower bound and permutation-null gate evaluated.",
            evidence,
        )

    absent = result["regimes"]["absent"]["methods"]["rank1_ridge_projection"]
    absent_supported = (
        absent["triplet_accuracy"]["lower"] >= config.support_triplet_floor
        and absent["triplet_accuracy"]["estimate"] > absent["permutation_null"]["q99"]
    )
    result["decisions"]["absent.rank1"] = _decision(
        "FALSE_POSITIVE" if absent_supported else "UNSUPPORTED_AT_THRESHOLD",
        "The absent relation must not cross the support gate.",
        absent,
    )

    xor_linear = result["regimes"]["nonlinear_xor"]["methods"]["rank1_ridge_projection"]
    result["decisions"]["xor.linear"] = _decision(
        "UNSUPPORTED_AT_THRESHOLD"
        if xor_linear["triplet_accuracy"]["lower"] < config.support_triplet_floor
        else "FALSE_POSITIVE",
        "A linear family should not certify XOR.",
        xor_linear,
    )
    xor_nonlinear = result["regimes"]["nonlinear_xor"]["methods"]["nonlinear_mlp"]
    result["decisions"]["xor.nonlinear"] = _decision(
        "SUPPORTED_NONLINEAR_ONLY"
        if xor_nonlinear["average_precision"]["lower"] >= config.nonlinear_average_precision_floor
        else "INSUFFICIENT_EVIDENCE",
        "The nonlinear diagnostic must recover the known XOR relation.",
        xor_nonlinear,
    )

    result["decisions"]["diagonal.basis_dependence"] = _decision(
        "SUPPORTED"
        if basis_delta["lower"] >= config.basis_dependence_delta_floor
        else "INSUFFICIENT_EVIDENCE",
        "Axis-aligned minus rotated diagonal triplet accuracy must exceed the frozen delta.",
        basis_delta,
    )

    shift = result["regimes"]["correlated_nuisance"]["methods"]["shift_gap"]
    result["decisions"]["correlated_nuisance.shift"] = _decision(
        "UNSTABLE_UNDER_SHIFT"
        if shift["lower"] >= config.instability_delta_floor
        else "INSUFFICIENT_EVIDENCE",
        "Validation-minus-test triplet accuracy must exceed the frozen instability delta.",
        shift,
    )

    required = {
        "axis_linear.rank1": "SUPPORTED",
        "rotated_linear.rank1": "SUPPORTED",
        "absent.rank1": "UNSUPPORTED_AT_THRESHOLD",
        "xor.linear": "UNSUPPORTED_AT_THRESHOLD",
        "xor.nonlinear": "SUPPORTED_NONLINEAR_ONLY",
        "diagonal.basis_dependence": "SUPPORTED",
        "correlated_nuisance.shift": "UNSTABLE_UNDER_SHIFT",
    }
    result["gate"] = {
        "required": required,
        "passed": all(
            result["decisions"][key]["status"] == value for key, value in required.items()
        ),
        "claim_promotion_allowed": False,
        "note": "Seed-17 certification can pass, but confirmatory multi-seed replication is still required before claim promotion.",  # NOQA E501
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = output_directory / "certification.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["certification_sha256"] = sha256_file(report_path)
    result["decision_tree_sha256"] = _sha256_json(result["decisions"])
    (output_directory / "certification-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("runs/e00/canonical-seed-17"))
    parser.add_argument("--operators", type=Path, default=Path("runs/e00/operator-matrix-seed-17"))
    parser.add_argument("--output", type=Path, default=Path("runs/e00/certification-seed-17"))
    parser.add_argument("--permutations", type=int, default=100)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    args = parser.parse_args()
    config = CertificationConfig(
        permutations=args.permutations, bootstrap_samples=args.bootstrap_samples
    )
    print(
        json.dumps(run(args.source, args.operators, args.output, config), indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    main()

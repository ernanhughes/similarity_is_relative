"""E00.4 preregistered multi-seed confirmation.

Generates five fresh E00 datasets, performs validation-only nonlinear selection,
computes per-seed evidence and aggregate decisions, and keeps seed 17 excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from relate.experiments.e00 import BINARY_REGIMES, REGIMES, Config, run as run_e00
from relate.experiments.e00_certification import (
    _average_precision_scores,
    _bootstrap_interval,
    _diagonal_distances,
    _permutation_null,
    _ridge_distances,
    _triplet_scores,
    CertificationConfig,
)
from relate.experiments.e00_operator_matrix import frozen_splits, sha256_file

CONFIRMATORY_SEEDS = (23, 41, 59, 83, 101)
HISTORICAL_SEED = 17


@dataclass(frozen=True)
class MultiSeedConfig:
    seeds: tuple[int, ...] = CONFIRMATORY_SEEDS
    permutations: int = 100
    query_bootstrap_samples: int = 1000
    seed_bootstrap_samples: int = 1000
    confidence_level: float = 0.95
    null_query_count: int = 200
    null_candidate_count: int = 1024


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _seed_interval(values: list[float], rng: np.random.Generator, samples: int) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    draws = rng.integers(0, len(array), size=(samples, len(array)))
    means = np.mean(array[draws], axis=1)
    return {
        "values": [float(v) for v in array],
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
        "sample_standard_deviation": float(np.std(array, ddof=1)),
        "lower": float(np.quantile(means, 0.025)),
        "upper": float(np.quantile(means, 0.975)),
    }


def _probability_distances(probabilities: np.ndarray, train: np.ndarray, query: np.ndarray) -> np.ndarray:
    return np.abs(probabilities[query, None] - probabilities[train][None, :])


def _candidate_models(seed: int) -> list[tuple[str, Pipeline]]:
    models: list[tuple[str, Pipeline]] = []
    for c in (0.1, 1.0, 10.0):
        identifier = f"poly2-logistic-c{c:g}"
        models.append(
            (
                identifier,
                Pipeline(
                    [
                        ("scale", StandardScaler()),
                        (
                            "poly",
                            PolynomialFeatures(
                                degree=2, interaction_only=True, include_bias=False
                            ),
                        ),
                        (
                            "model",
                            LogisticRegression(C=c, max_iter=2000, random_state=seed),
                        ),
                    ]
                ),
            )
        )
    for shape in ((16,), (32,), (32, 16)):
        for alpha in (0.0001, 0.001, 0.01):
            shape_id = "x".join(str(value) for value in shape)
            identifier = f"mlp-{shape_id}-alpha{alpha:g}"
            models.append(
                (
                    identifier,
                    Pipeline(
                        [
                            ("scale", StandardScaler()),
                            (
                                "model",
                                MLPClassifier(
                                    hidden_layer_sizes=shape,
                                    activation="relu",
                                    solver="adam",
                                    alpha=alpha,
                                    early_stopping=True,
                                    max_iter=1000,
                                    random_state=seed,
                                ),
                            ),
                        ]
                    ),
                )
            )
    return models


def _validation_select(
    x: np.ndarray,
    y: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    test: np.ndarray,
    seed: int,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    candidates = _candidate_models(seed)
    for identifier, model in candidates:
        caught: list[str] = []
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(x[train], y[train].astype(int))
            caught = [str(item.message) for item in captured]
        probabilities = model.predict_proba(x)[:, 1]
        distances = _probability_distances(probabilities, train, validation)
        scores = _average_precision_scores(distances, y[train], y[validation])
        records.append(
            {
                "model_id": identifier,
                "validation_average_precision": float(np.nanmean(scores)),
                "convergence_warnings": caught,
            }
        )

    selected = sorted(
        records,
        key=lambda value: (-value["validation_average_precision"], value["model_id"]),
    )[0]
    selected_id = selected["model_id"]
    selected_model = dict(candidates)[selected_id]
    development = np.sort(np.concatenate((train, validation)))
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ConvergenceWarning)
        selected_model.fit(x[development], y[development].astype(int))
        refit_warnings = [str(item.message) for item in captured]
    probabilities = selected_model.predict_proba(x)[:, 1]
    test_distances = _probability_distances(probabilities, development, test)
    test_scores = _average_precision_scores(test_distances, y[development], y[test])
    return {
        "candidates": records,
        "selected_model_id": selected_id,
        "tie_breaker": "highest validation AP, then lexical model_id",
        "development_count": int(len(development)),
        "test_count": int(len(test)),
        "refit_convergence_warnings": refit_warnings,
        "test_average_precision_scores": test_scores,
    }


def _load_arrays(seed_directory: Path) -> tuple[dict[str, Any], dict[str, tuple[np.ndarray, np.ndarray]]]:
    manifest = json.loads((seed_directory / "manifest.json").read_text(encoding="utf-8"))
    arrays: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for regime in REGIMES:
        with np.load(seed_directory / "arrays" / f"{regime}.npz") as payload:
            arrays[regime] = (payload["x"], payload["y"])
    return manifest, arrays


def _seed_run(seed: int, root: Path, config: MultiSeedConfig) -> dict[str, Any]:
    seed_dir = root / f"seed-{seed}"
    source = run_e00(Config(seed=seed), seed_dir)
    manifest, arrays = _load_arrays(seed_dir)
    splits = frozen_splits(Config(**manifest["config"]))
    train, validation, test = splits["train"], splits["validation"], splits["test"]
    rng = np.random.default_rng(100_000 + seed)
    cert_config = CertificationConfig(
        seed=10_000 + seed,
        permutations=config.permutations,
        bootstrap_samples=config.query_bootstrap_samples,
        null_query_count=config.null_query_count,
        null_candidate_count=config.null_candidate_count,
        confidence_level=config.confidence_level,
    )

    evidence: dict[str, Any] = {}
    caches: dict[tuple[str, str], np.ndarray] = {}
    for regime in REGIMES:
        x, y = arrays[regime]
        methods: dict[str, Any] = {}
        for method_id, builder in (
            ("rank1", _ridge_distances),
            ("diagonal", _diagonal_distances),
        ):
            distances = builder(x, y, train, test)
            scores = _triplet_scores(distances, y[train], y[test])
            caches[(regime, method_id)] = scores
            methods[method_id] = {
                "triplet_accuracy": _bootstrap_interval(
                    scores, rng, config.query_bootstrap_samples, config.confidence_level
                ),
                "permutation_null": _permutation_null(
                    x, y, train, test, rng, cert_config, builder
                ),
            }
        evidence[regime] = {"methods": methods}

    x_xor, y_xor = arrays["nonlinear_xor"]
    selected = _validation_select(x_xor, y_xor, train, validation, test, seed)
    xor_scores = selected.pop("test_average_precision_scores")
    selected["test_average_precision"] = _bootstrap_interval(
        xor_scores, rng, config.query_bootstrap_samples, config.confidence_level
    )
    evidence["nonlinear_xor"]["nonlinear_selection"] = selected

    x_nuisance, y_nuisance = arrays["correlated_nuisance"]
    validation_distances = _ridge_distances(x_nuisance, y_nuisance, train, validation)
    validation_scores = _triplet_scores(validation_distances, y_nuisance[train], y_nuisance[validation])
    test_scores = caches[("correlated_nuisance", "rank1")]
    shift_gap = float(np.nanmean(validation_scores) - np.nanmean(test_scores))

    axis_diag = float(np.nanmean(caches[("axis_linear", "diagonal")]))
    rotated_diag = float(np.nanmean(caches[("rotated_linear", "diagonal")]))
    axis_rank1 = float(np.nanmean(caches[("axis_linear", "rank1")]))
    rotated_rank1 = float(np.nanmean(caches[("rotated_linear", "rank1")]))
    xor_linear_ap = evidence["nonlinear_xor"]["methods"]["rank1"]["triplet_accuracy"]["estimate"]
    xor_nonlinear_ap = selected["test_average_precision"]["estimate"]

    summary = {
        "seed": seed,
        "manifest_sha256": source["manifest_sha256"],
        "rotation_sha256": manifest["rotation_sha256"],
        "split_hashes": manifest["split_hashes"],
        "evidence": evidence,
        "derived": {
            "diagonal_rotation_retention": rotated_diag / axis_diag,
            "rank1_rotation_retention": rotated_rank1 / axis_rank1,
            "correlated_nuisance_shift_gap": shift_gap,
            "xor_nonlinear_minus_linear": xor_nonlinear_ap - xor_linear_ap,
        },
    }
    (seed_dir / "confirmation.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def _decision(status: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"status": status, "evidence": evidence}


def _aggregate(seed_results: list[dict[str, Any]], config: MultiSeedConfig) -> dict[str, Any]:
    rng = np.random.default_rng(40404)

    def metric(regime: str, method: str, key: str = "triplet_accuracy") -> list[float]:
        return [
            item["evidence"][regime]["methods"][method][key]["estimate"]
            for item in seed_results
        ]

    axis = metric("axis_linear", "rank1")
    rotated = metric("rotated_linear", "rank1")
    absent = metric("absent", "rank1")
    xor_linear = metric("nonlinear_xor", "rank1")
    xor_nonlinear = [
        item["evidence"]["nonlinear_xor"]["nonlinear_selection"]["test_average_precision"][
            "estimate"
        ]
        for item in seed_results
    ]
    diag_retention = [item["derived"]["diagonal_rotation_retention"] for item in seed_results]
    rank_retention = [item["derived"]["rank1_rotation_retention"] for item in seed_results]
    shifts = [item["derived"]["correlated_nuisance_shift_gap"] for item in seed_results]
    nonlinear_delta = [item["derived"]["xor_nonlinear_minus_linear"] for item in seed_results]

    intervals = {
        "axis_rank1": _seed_interval(axis, rng, config.seed_bootstrap_samples),
        "rotated_rank1": _seed_interval(rotated, rng, config.seed_bootstrap_samples),
        "absent_rank1": _seed_interval(absent, rng, config.seed_bootstrap_samples),
        "xor_linear": _seed_interval(xor_linear, rng, config.seed_bootstrap_samples),
        "xor_nonlinear": _seed_interval(xor_nonlinear, rng, config.seed_bootstrap_samples),
        "diagonal_retention": _seed_interval(diag_retention, rng, config.seed_bootstrap_samples),
        "rank1_retention": _seed_interval(rank_retention, rng, config.seed_bootstrap_samples),
        "shift_gap": _seed_interval(shifts, rng, config.seed_bootstrap_samples),
        "xor_nonlinear_minus_linear": _seed_interval(
            nonlinear_delta, rng, config.seed_bootstrap_samples
        ),
    }

    null_exceeds: dict[str, list[bool]] = {}
    for regime in ("axis_linear", "rotated_linear", "absent", "nonlinear_xor"):
        null_exceeds[regime] = [
            item["evidence"][regime]["methods"]["rank1"]["triplet_accuracy"]["estimate"]
            > item["evidence"][regime]["methods"]["rank1"]["permutation_null"]["q99"]
            for item in seed_results
        ]

    linear_support = lambda values, interval, regime: (
        sum(value >= 0.85 for value in values) >= 4
        and sum(null_exceeds[regime]) >= 4
        and interval["lower"] >= 0.80
        and min(values) >= 0.75
    )
    decisions: dict[str, Any] = {}
    decisions["axis_linear.rank1_multiseed"] = _decision(
        "SUPPORTED" if linear_support(axis, intervals["axis_rank1"], "axis_linear") else "INSUFFICIENT_EVIDENCE",
        intervals["axis_rank1"],
    )
    decisions["rotated_linear.rank1_multiseed"] = _decision(
        "SUPPORTED"
        if linear_support(rotated, intervals["rotated_rank1"], "rotated_linear")
        else "INSUFFICIENT_EVIDENCE",
        intervals["rotated_rank1"],
    )
    absent_ok = sum(null_exceeds["absent"]) <= 1 and intervals["absent_rank1"]["mean"] < 0.55
    decisions["absent.rank1_multiseed"] = _decision(
        "UNSUPPORTED_AT_THRESHOLD" if absent_ok else "FALSE_POSITIVE",
        intervals["absent_rank1"],
    )
    xor_linear_ok = (
        sum(null_exceeds["nonlinear_xor"]) <= 1 and intervals["xor_linear"]["mean"] < 0.55
    )
    decisions["xor.linear_multiseed"] = _decision(
        "UNSUPPORTED_AT_THRESHOLD" if xor_linear_ok else "FALSE_POSITIVE",
        intervals["xor_linear"],
    )
    nonlinear_ok = (
        sum(value >= 0.85 for value in xor_nonlinear) >= 4
        and min(xor_nonlinear) >= 0.75
        and intervals["xor_nonlinear"]["lower"] >= 0.80
        and sum(value >= 0.20 for value in nonlinear_delta) >= 4
        and intervals["xor_nonlinear_minus_linear"]["lower"] >= 0.15
    )
    decisions["xor.nonlinear_multiseed"] = _decision(
        "SUPPORTED_NONLINEAR_ONLY" if nonlinear_ok else "INSUFFICIENT_EVIDENCE",
        {
            "nonlinear": intervals["xor_nonlinear"],
            "nonlinear_minus_linear": intervals["xor_nonlinear_minus_linear"],
        },
    )
    basis_ok = (
        sum(value <= 0.75 for value in diag_retention) >= 4
        and intervals["diagonal_retention"]["upper"] <= 0.80
        and sum(value >= 0.95 for value in rank_retention) >= 4
        and intervals["rank1_retention"]["lower"] >= 0.90
    )
    decisions["diagonal.basis_dependence_multiseed"] = _decision(
        "SUPPORTED" if basis_ok else "INSUFFICIENT_EVIDENCE",
        {
            "diagonal_retention": intervals["diagonal_retention"],
            "rank1_retention": intervals["rank1_retention"],
        },
    )
    shift_ok = sum(value >= 0.15 for value in shifts) >= 4 and intervals["shift_gap"]["lower"] >= 0.10
    decisions["correlated_nuisance.shift_multiseed"] = _decision(
        "UNSTABLE_UNDER_SHIFT" if shift_ok else "INSUFFICIENT_EVIDENCE",
        intervals["shift_gap"],
    )

    required = {
        "axis_linear.rank1_multiseed": "SUPPORTED",
        "rotated_linear.rank1_multiseed": "SUPPORTED",
        "absent.rank1_multiseed": "UNSUPPORTED_AT_THRESHOLD",
        "xor.linear_multiseed": "UNSUPPORTED_AT_THRESHOLD",
        "xor.nonlinear_multiseed": "SUPPORTED_NONLINEAR_ONLY",
        "diagonal.basis_dependence_multiseed": "SUPPORTED",
        "correlated_nuisance.shift_multiseed": "UNSTABLE_UNDER_SHIFT",
    }
    passed = all(decisions[key]["status"] == expected for key, expected in required.items())
    return {
        "intervals": intervals,
        "decisions": decisions,
        "gate": {
            "required": required,
            "passed": passed,
            "claim_promotion_allowed": passed,
            "scope": "registered synthetic E00 only",
        },
    }


def run(output: Path, config: MultiSeedConfig = MultiSeedConfig()) -> dict[str, Any]:
    if tuple(config.seeds) != CONFIRMATORY_SEEDS or HISTORICAL_SEED in config.seeds:
        raise ValueError("Confirmatory seeds are frozen and must exclude seed 17")
    output.mkdir(parents=True, exist_ok=True)
    seed_results = [_seed_run(seed, output, config) for seed in config.seeds]
    aggregate = _aggregate(seed_results, config)
    result: dict[str, Any] = {
        "experiment_id": "e00-multiseed-confirmation",
        "status": "MULTISEED_CONFIRMATION_COMPLETE",
        "config": asdict(config),
        "historical_seed_excluded": HISTORICAL_SEED,
        "seeds": seed_results,
        **aggregate,
    }
    result["decision_tree_sha256"] = _json_hash(result["decisions"])
    aggregate_dir = output / "aggregate"
    aggregate_dir.mkdir(exist_ok=True)
    result_path = aggregate_dir / "multiseed-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["aggregate_result_sha256"] = sha256_file(result_path)
    (aggregate_dir / "multiseed-result-with-hash.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/e00/multiseed"))
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

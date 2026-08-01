"""E01.2a multi-seed confirmation for weighted primitive-space composition."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score

from relate.experiments.e00 import array_hash
from relate.experiments.e01_relational_conjunction import (
    COMPOUNDS,
    PRIMITIVES,
    RelationalConjunctionConfig,
    _generate,
    _pairwise_cosine,
    _pairwise_euclidean,
    _weighted_relational_distance,
)

SEEDS = (401, 433, 467, 503, 557)
NON_IDENTITY_PERMUTATIONS = tuple(
    permutation
    for permutation in itertools.permutations(range(len(PRIMITIVES)))
    if permutation != tuple(range(len(PRIMITIVES)))
)


@dataclass(frozen=True)
class MultiSeedCompositionConfig:
    seeds: tuple[int, ...] = SEEDS
    samples: int = 6144
    dimensions: int = 64
    train_fraction: float = 0.60
    validation_fraction: float = 0.20
    target_noise_standard_deviation: float = 0.15
    ridge_alpha: float = 1.0
    triplets_per_query: int = 256
    bootstrap_repetitions: int = 2000
    confidence_level: float = 0.95


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _manifest(seed: int, queries: np.ndarray, candidates: np.ndarray, count: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rows: list[tuple[int, int, int]] = []
    for query in queries:
        left = rng.choice(candidates, size=count, replace=True)
        right = rng.choice(candidates, size=count, replace=True)
        rows.extend((int(query), int(a), int(b)) for a, b in zip(left, right, strict=True))
    return np.asarray(rows, dtype=np.int64)


def _triplet_accuracy(
    distances: np.ndarray,
    oracle: np.ndarray,
    manifest: np.ndarray,
    queries: np.ndarray,
    candidates: np.ndarray,
) -> float:
    query_lookup = {int(value): index for index, value in enumerate(queries)}
    candidate_lookup = {int(value): index for index, value in enumerate(candidates)}
    scores: list[float] = []
    for query, left, right in manifest:
        q = query_lookup[int(query)]
        a = candidate_lookup[int(left)]
        b = candidate_lookup[int(right)]
        oracle_delta = oracle[q, a] - oracle[q, b]
        if oracle_delta == 0:
            continue
        observed_delta = distances[q, a] - distances[q, b]
        scores.append(
            0.5 if observed_delta == 0 else float(np.sign(observed_delta) == np.sign(oracle_delta))
        )
    return float(np.mean(scores))


def _evaluate(
    distances: np.ndarray,
    oracle: np.ndarray,
    manifest: np.ndarray,
    queries: np.ndarray,
    candidates: np.ndarray,
) -> dict[str, float]:
    return {
        "triplet_accuracy": _triplet_accuracy(distances, oracle, manifest, queries, candidates),
        "spearman": float(
            np.nanmean(
                [
                    spearmanr(left, right).statistic
                    for left, right in zip(distances, oracle, strict=True)
                ]
            )
        ),
    }


def _scalar_distance(
    values: np.ndarray, candidates: np.ndarray, queries: np.ndarray, projection: np.ndarray
) -> np.ndarray:
    scalar = values @ projection
    return np.abs(scalar[queries, None] - scalar[candidates][None, :])


def _seed_interval(values: list[float], confidence: float) -> list[float]:
    values_array = np.asarray(values, dtype=float)
    if len(values_array) == 1:
        return [float(values_array[0]), float(values_array[0])]
    alpha = 1.0 - confidence
    rng = np.random.default_rng(90210)
    draws = rng.choice(values_array, size=(20000, len(values_array)), replace=True).mean(axis=1)
    return [float(np.quantile(draws, alpha / 2)), float(np.quantile(draws, 1 - alpha / 2))]


def _decision(summary: dict[str, Any]) -> str:
    if (
        summary["composed_ci95"][0] >= 0.88
        and summary["minimum_composed"] >= 0.84
        and summary["scalar_margin_ci95"][0] > 0.0
        and summary["wrong_alignment_margin_ci95"][0] > 0.0
        and summary["success_count"] >= 4
    ):
        return "SUPPORTED_MULTI_SEED"
    if summary["mean_composed"] < 0.75:
        return "UNSUPPORTED_AT_THRESHOLD"
    return "INSUFFICIENT_EVIDENCE"


def run(output: Path, config: MultiSeedCompositionConfig | None = None) -> dict[str, Any]:
    config = config or MultiSeedCompositionConfig()
    result: dict[str, Any] = {
        "experiment_id": "e01-multiseed-composition-confirmation",
        "stage": "E01.2a",
        "status": "CONFIRMATORY_RESULT_COMPLETE",
        "config": asdict(config),
        "config_sha256": _json_hash(asdict(config)),
        "compound_definitions": COMPOUNDS,
        "compound_definitions_sha256": _json_hash(COMPOUNDS),
        "seeds": {},
        "aggregate": {},
        "decisions": {},
    }

    for seed in config.seeds:
        base_config = RelationalConjunctionConfig(
            seed=seed,
            samples=config.samples,
            dimensions=config.dimensions,
            train_fraction=config.train_fraction,
            validation_fraction=config.validation_fraction,
            target_noise_standard_deviation=config.target_noise_standard_deviation,
            ridge_alpha=config.ridge_alpha,
        )
        generated = _generate(base_config)
        x = generated["x"]
        targets = generated["targets"]
        splits = generated["splits"]
        train = splits["train"]
        predictions = np.empty_like(targets)
        primitive_metrics: dict[str, Any] = {}
        for index, name in enumerate(PRIMITIVES):
            model = Ridge(alpha=config.ridge_alpha).fit(x[train], targets[train, index])
            predictions[:, index] = model.predict(x)
            primitive_metrics[name] = {
                split_name: {
                    "r2": float(r2_score(targets[indices, index], predictions[indices, index])),
                    "mae": float(
                        mean_absolute_error(targets[indices, index], predictions[indices, index])
                    ),
                }
                for split_name, indices in (
                    ("validation", splits["validation"]),
                    ("test", splits["test"]),
                )
            }

        seed_result: dict[str, Any] = {
            "split_hashes": {name: array_hash(value) for name, value in splits.items()},
            "x_sha256": array_hash(x),
            "targets_sha256": array_hash(targets),
            "primitive_metrics": primitive_metrics,
            "compounds": {},
        }
        for compound_index, (compound, raw_weights) in enumerate(COMPOUNDS.items()):
            weights = np.asarray(raw_weights, dtype=float)
            compound_result: dict[str, Any] = {"weights": list(raw_weights), "splits": {}}
            for split_offset, split_name in enumerate(("validation", "test")):
                queries = splits[split_name]
                manifest = _manifest(
                    seed * 1000 + compound_index * 10 + split_offset,
                    queries,
                    train,
                    config.triplets_per_query,
                )
                oracle = _weighted_relational_distance(targets, train, queries, weights)
                methods: dict[str, Any] = {
                    "weighted_product_space": _evaluate(
                        _weighted_relational_distance(predictions, train, queries, weights),
                        oracle,
                        manifest,
                        queries,
                        train,
                    ),
                    "scalar_w": _evaluate(
                        _scalar_distance(predictions, train, queries, weights),
                        oracle,
                        manifest,
                        queries,
                        train,
                    ),
                    "scalar_sqrt_w": _evaluate(
                        _scalar_distance(predictions, train, queries, np.sqrt(weights)),
                        oracle,
                        manifest,
                        queries,
                        train,
                    ),
                    "raw_cosine": _evaluate(
                        _pairwise_cosine(x[queries], x[train]), oracle, manifest, queries, train
                    ),
                    "raw_euclidean": _evaluate(
                        _pairwise_euclidean(x[queries], x[train]), oracle, manifest, queries, train
                    ),
                }
                wrong: dict[str, Any] = {}
                for permutation in NON_IDENTITY_PERMUTATIONS:
                    key = "_".join(map(str, permutation))
                    wrong[key] = _evaluate(
                        _weighted_relational_distance(
                            predictions[:, permutation], train, queries, weights
                        ),
                        oracle,
                        manifest,
                        queries,
                        train,
                    )
                strongest_key = max(wrong, key=lambda key: wrong[key]["triplet_accuracy"])
                methods["wrong_permutations"] = wrong
                methods["strongest_wrong_permutation"] = {
                    "permutation": strongest_key,
                    **wrong[strongest_key],
                }
                methods["oracle_triplet_disagreement"] = (
                    1.0 - methods["weighted_product_space"]["triplet_accuracy"]
                )
                compound_result["splits"][split_name] = {
                    "manifest_sha256": array_hash(manifest),
                    "manifest_triplets": int(len(manifest)),
                    "methods": methods,
                }
            seed_result["compounds"][compound] = compound_result
        result["seeds"][str(seed)] = seed_result

    for compound in COMPOUNDS:
        composed = [
            result["seeds"][str(seed)]["compounds"][compound]["splits"]["test"]["methods"][
                "weighted_product_space"
            ]["triplet_accuracy"]
            for seed in config.seeds
        ]
        scalar = [
            max(
                result["seeds"][str(seed)]["compounds"][compound]["splits"]["test"]["methods"][
                    "scalar_w"
                ]["triplet_accuracy"],
                result["seeds"][str(seed)]["compounds"][compound]["splits"]["test"]["methods"][
                    "scalar_sqrt_w"
                ]["triplet_accuracy"],
            )
            for seed in config.seeds
        ]
        wrong = [
            result["seeds"][str(seed)]["compounds"][compound]["splits"]["test"]["methods"][
                "strongest_wrong_permutation"
            ]["triplet_accuracy"]
            for seed in config.seeds
        ]
        summary = {
            "per_seed_composed": composed,
            "mean_composed": float(np.mean(composed)),
            "median_composed": float(np.median(composed)),
            "minimum_composed": float(np.min(composed)),
            "composed_ci95": _seed_interval(composed, config.confidence_level),
            "scalar_margin_ci95": _seed_interval(
                [a - b for a, b in zip(composed, scalar, strict=True)], config.confidence_level
            ),
            "wrong_alignment_margin_ci95": _seed_interval(
                [a - b for a, b in zip(composed, wrong, strict=True)], config.confidence_level
            ),
            "success_count": int(sum(value >= 0.88 for value in composed)),
        }
        result["aggregate"][compound] = summary
        result["decisions"][compound] = _decision(summary)

    result["gate"] = {
        "passed": all(value == "SUPPORTED_MULTI_SEED" for value in result["decisions"].values()),
        "claim_promotion_allowed": False,
        "note": "E01.2a confirms only weighted product-space composition; support-aware and non-additive gates remain pending.", # NOQA E501 
    }
    result["decision_tree_sha256"] = _json_hash(result["decisions"])
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "multiseed-composition-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["result_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    (output / "multiseed-composition-result-with-hash.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/e01/multiseed-composition"))
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

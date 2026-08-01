"""E01.1 unseen relational-conjunction point-estimate experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

from relate.experiments.e00 import array_hash, orthogonal_matrix, split_indices

PRIMITIVES = ("a", "b", "c")
COMPOUNDS: dict[str, tuple[float, float, float]] = {
    "a2_b": (2.0, 1.0, 0.0),
    "a3_c": (3.0, 0.0, 1.0),
    "b2_c": (0.0, 2.0, 1.0),
    "a_b2_c3": (1.0, 2.0, 3.0),
}


@dataclass(frozen=True)
class RelationalConjunctionConfig:
    seed: int = 307
    samples: int = 6144
    dimensions: int = 64
    train_fraction: float = 0.60
    validation_fraction: float = 0.20
    target_noise_standard_deviation: float = 0.15
    ridge_alpha: float = 1.0
    retrieval_ks: tuple[int, ...] = (10, 25, 50, 100)


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _pairwise_euclidean(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    squared = np.maximum(
        np.sum(left * left, axis=1, keepdims=True)
        + np.sum(right * right, axis=1)[None, :]
        - 2.0 * left @ right.T,
        0.0,
    )
    return np.sqrt(squared)


def _pairwise_cosine(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    denominator = np.maximum(
        np.linalg.norm(left, axis=1, keepdims=True)
        * np.linalg.norm(right, axis=1, keepdims=True).T,
        np.finfo(float).eps,
    )
    return 1.0 - (left @ right.T) / denominator


def _weighted_relational_distance(
    values: np.ndarray,
    candidates: np.ndarray,
    queries: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    delta = values[queries, None, :] - values[candidates][None, :, :]
    return np.sqrt(np.sum(delta * delta * weights[None, None, :], axis=2))


def _scalar_collapse_distance(
    values: np.ndarray,
    candidates: np.ndarray,
    queries: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    collapsed = values @ weights
    return np.abs(collapsed[queries, None] - collapsed[candidates][None, :])


def _triplet_accuracy(distances: np.ndarray, oracle: np.ndarray) -> float:
    count = distances.shape[1]
    left = np.arange(count // 2)
    right = left + (count - count // 2)
    observed_delta = distances[:, left] - distances[:, right]
    oracle_delta = oracle[:, left] - oracle[:, right]
    informative = oracle_delta != 0
    matches = np.where(
        observed_delta[informative] == 0,
        0.5,
        np.sign(observed_delta[informative]) == np.sign(oracle_delta[informative]),
    )
    return float(np.mean(matches))


def _evaluate(distances: np.ndarray, oracle: np.ndarray, ks: tuple[int, ...]) -> dict[str, Any]:
    recalls = {k: [] for k in ks}
    regrets = {k: [] for k in ks}
    correlations: list[float] = []
    true_ranks: list[float] = []
    for row, oracle_row in zip(distances, oracle, strict=True):
        oracle_order = np.argsort(oracle_row, kind="stable")
        predicted_order = np.argsort(row, kind="stable")
        ranks = np.empty(len(row), dtype=np.int64)
        ranks[predicted_order] = np.arange(1, len(row) + 1)
        correlations.append(float(spearmanr(oracle_row, row).statistic))
        true_ranks.extend(ranks[oracle_order[:10]].astype(float).tolist())
        for k in ks:
            oracle_k = oracle_order[:k]
            predicted_k = predicted_order[:k]
            recalls[k].append(np.intersect1d(oracle_k, predicted_k).size / k)
            regrets[k].append(
                float(np.mean(oracle_row[predicted_k]) - np.mean(oracle_row[oracle_k]))
            )
    return {
        "triplet_accuracy": _triplet_accuracy(distances, oracle),
        "spearman": float(np.nanmean(correlations)),
        "recall_at": {str(k): float(np.mean(recalls[k])) for k in ks},
        "neighbor_regret_at": {str(k): float(np.mean(regrets[k])) for k in ks},
        "oracle_neighbor_predicted_rank_median": float(np.median(true_ranks)),
        "oracle_neighbor_predicted_rank_p90": float(np.percentile(true_ranks, 90)),
    }


def _generate(config: RelationalConjunctionConfig) -> dict[str, Any]:
    rng = np.random.default_rng(config.seed)
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
    return {
        "x": (base @ rotation).astype(np.float64),
        "targets": targets.astype(np.float64),
        "rotation": rotation,
        "splits": splits,
    }


def _decision(composed: dict[str, Any], controls: list[dict[str, Any]]) -> str:
    accuracy = composed["triplet_accuracy"]
    regret = 1.0 - accuracy
    margin = min(accuracy - control["triplet_accuracy"] for control in controls)
    if accuracy >= 0.88 and regret <= 0.12 and margin >= 0.10:
        return "SUPPORTED_POINT_ESTIMATE"
    if accuracy < 0.70 or regret > 0.30:
        return "UNSUPPORTED_AT_THRESHOLD"
    return "INSUFFICIENT_EVIDENCE"


def run(
    output: Path,
    config: RelationalConjunctionConfig | None = None,
) -> dict[str, Any]:
    config = config or RelationalConjunctionConfig()
    generated = _generate(config)
    x = generated["x"]
    targets = generated["targets"]
    rotation = generated["rotation"]
    splits = generated["splits"]
    train = splits["train"]

    predictions = np.empty_like(targets)
    coefficient_hashes: dict[str, str] = {}
    for index, name in enumerate(PRIMITIVES):
        model = Ridge(alpha=config.ridge_alpha).fit(x[train], targets[train, index])
        predictions[:, index] = model.predict(x)
        coefficient_hashes[name] = array_hash(np.asarray(model.coef_, dtype=np.float64))

    result: dict[str, Any] = {
        "experiment_id": "e01-relational-conjunction",
        "status": "POINT_ESTIMATE_COMPLETE",
        "config": asdict(config),
        "config_sha256": _json_hash(asdict(config)),
        "compound_definitions": COMPOUNDS,
        "compound_definitions_sha256": _json_hash(COMPOUNDS),
        "rotation_sha256": array_hash(rotation),
        "split_hashes": {name: array_hash(value) for name, value in splits.items()},
        "x_sha256": array_hash(x),
        "primitive_targets_sha256": array_hash(targets),
        "primitive_coefficient_hashes": coefficient_hashes,
        "compounds": {},
        "decisions": {},
    }

    wrong_order = np.asarray([1, 2, 0])
    for compound, raw_weights in COMPOUNDS.items():
        weights = np.asarray(raw_weights, dtype=np.float64)
        compound_result: dict[str, Any] = {"weights": list(raw_weights), "splits": {}}
        for split_name in ("validation", "test"):
            queries = splits[split_name]
            oracle = _weighted_relational_distance(targets, train, queries, weights)
            methods = {
                "posthoc_composed": _evaluate(
                    _weighted_relational_distance(predictions, train, queries, weights),
                    oracle,
                    config.retrieval_ks,
                ),
                "scalar_collapse": _evaluate(
                    _scalar_collapse_distance(predictions, train, queries, weights),
                    oracle,
                    config.retrieval_ks,
                ),
                "wrong_primitive_alignment": _evaluate(
                    _weighted_relational_distance(
                        predictions[:, wrong_order], train, queries, weights
                    ),
                    oracle,
                    config.retrieval_ks,
                ),
                "raw_euclidean": _evaluate(
                    _pairwise_euclidean(x[queries], x[train]), oracle, config.retrieval_ks
                ),
                "raw_cosine": _evaluate(
                    _pairwise_cosine(x[queries], x[train]), oracle, config.retrieval_ks
                ),
            }
            methods["posthoc_composed"]["composition_regret"] = (
                1.0 - methods["posthoc_composed"]["triplet_accuracy"]
            )
            compound_result["splits"][split_name] = methods
        test_methods = compound_result["splits"]["test"]
        controls = [
            test_methods["scalar_collapse"],
            test_methods["wrong_primitive_alignment"],
            test_methods["raw_euclidean"],
            test_methods["raw_cosine"],
        ]
        status = _decision(test_methods["posthoc_composed"], controls)
        result["compounds"][compound] = compound_result
        result["decisions"][compound] = {
            "status": status,
            "composition_regret": test_methods["posthoc_composed"]["composition_regret"],
        }

    result["gate"] = {
        "passed": all(
            decision["status"] == "SUPPORTED_POINT_ESTIMATE"
            for decision in result["decisions"].values()
        ),
        "claim_promotion_allowed": False,
        "note": "E01.1 is a deterministic synthetic point-estimate stage.",
    }
    result["decision_tree_sha256"] = _json_hash(result["decisions"])

    output.mkdir(parents=True, exist_ok=True)
    arrays = output / "arrays"
    arrays.mkdir(exist_ok=True)
    np.savez_compressed(arrays / "relational-conjunction.npz", x=x, targets=targets)
    result_path = output / "relational-conjunction-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["result_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    (output / "relational-conjunction-result-with-hash.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/e01/relational-conjunction-seed-307"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

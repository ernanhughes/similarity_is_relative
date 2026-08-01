"""E01 deterministic unseen primitive-composition experiment."""

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
    "a_plus_b": (1.0, 1.0, 0.0),
    "a_plus_c": (1.0, 0.0, 1.0),
    "b_plus_c": (0.0, 1.0, 1.0),
    "a_plus_2b_minus_c": (1.0, 2.0, -1.0),
}


@dataclass(frozen=True)
class CompositionConfig:
    seed: int = 211
    samples: int = 6144
    dimensions: int = 64
    train_fraction: float = 0.60
    validation_fraction: float = 0.20
    noise_standard_deviation: float = 0.10
    ridge_alpha: float = 1.0
    retrieval_ks: tuple[int, ...] = (10, 25, 50, 100)


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _pairwise_euclidean(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_sq = np.sum(left * left, axis=1, keepdims=True)
    right_sq = np.sum(right * right, axis=1)[None, :]
    squared = np.maximum(left_sq + right_sq - 2.0 * left @ right.T, 0.0)
    return np.sqrt(squared)


def _pairwise_cosine(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_norm = np.linalg.norm(left, axis=1, keepdims=True)
    right_norm = np.linalg.norm(right, axis=1, keepdims=True).T
    denominator = np.maximum(left_norm * right_norm, np.finfo(float).eps)
    return 1.0 - (left @ right.T) / denominator


def _scalar_distances(values: np.ndarray, candidates: np.ndarray, queries: np.ndarray) -> np.ndarray:
    return np.abs(values[queries, None] - values[candidates][None, :])


def _triplet_accuracy(
    distances: np.ndarray,
    candidate_targets: np.ndarray,
    query_targets: np.ndarray,
) -> float:
    scores: list[float] = []
    count = len(candidate_targets)
    left = np.arange(count // 2)
    right = left + (count - count // 2)
    for row, query in zip(distances, query_targets, strict=True):
        oracle = np.abs(candidate_targets - query)
        oracle_delta = oracle[left] - oracle[right]
        predicted_delta = row[left] - row[right]
        informative = oracle_delta != 0
        expected = np.sign(oracle_delta[informative])
        observed = np.sign(predicted_delta[informative])
        values = np.where(observed == 0, 0.5, observed == expected)
        scores.append(float(np.mean(values)))
    return float(np.mean(scores))


def _evaluate(
    distances: np.ndarray,
    candidate_targets: np.ndarray,
    query_targets: np.ndarray,
    ks: tuple[int, ...],
) -> dict[str, Any]:
    recalls = {k: [] for k in ks}
    regrets = {k: [] for k in ks}
    correlations: list[float] = []
    true_ranks: list[float] = []
    for row, query in zip(distances, query_targets, strict=True):
        oracle = np.abs(candidate_targets - query)
        oracle_order = np.argsort(oracle, kind="stable")
        predicted_order = np.argsort(row, kind="stable")
        ranks = np.empty(len(row), dtype=np.int64)
        ranks[predicted_order] = np.arange(1, len(row) + 1)
        correlations.append(float(spearmanr(oracle, row).statistic))
        true_ranks.extend(ranks[oracle_order[:10]].astype(float).tolist())
        for k in ks:
            oracle_k = oracle_order[:k]
            predicted_k = predicted_order[:k]
            overlap = np.intersect1d(oracle_k, predicted_k, assume_unique=True).size
            recalls[k].append(overlap / k)
            regrets[k].append(float(np.mean(oracle[predicted_k]) - np.mean(oracle[oracle_k])))
    return {
        "triplet_accuracy": _triplet_accuracy(distances, candidate_targets, query_targets),
        "spearman": float(np.nanmean(correlations)),
        "recall_at": {str(k): float(np.mean(recalls[k])) for k in ks},
        "neighbor_regret_at": {str(k): float(np.mean(regrets[k])) for k in ks},
        "oracle_neighbor_predicted_rank_median": float(np.median(true_ranks)),
        "oracle_neighbor_predicted_rank_p90": float(np.percentile(true_ranks, 90)),
    }


def _generate(config: CompositionConfig) -> dict[str, Any]:
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
    primitive_targets = latent + rng.normal(
        scale=config.noise_standard_deviation,
        size=latent.shape,
    )
    base = rng.normal(size=(config.samples, config.dimensions))
    base[:, : len(PRIMITIVES)] = latent
    x = (base @ rotation).astype(np.float64)
    return {
        "x": x,
        "primitive_targets": primitive_targets.astype(np.float64),
        "rotation": rotation,
        "splits": splits,
    }


def _decision(metrics: dict[str, Any], oracle: dict[str, Any], controls: list[dict[str, Any]]) -> str:
    composed = metrics["triplet_accuracy"]
    regret = oracle["triplet_accuracy"] - composed
    margin = min(composed - item["triplet_accuracy"] for item in controls)
    if composed >= 0.85 and regret <= 0.05 and margin >= 0.20:
        return "SUPPORTED_POINT_ESTIMATE"
    if composed < 0.70 or regret > 0.15:
        return "UNSUPPORTED_AT_THRESHOLD"
    return "INSUFFICIENT_EVIDENCE"


def run(output: Path, config: CompositionConfig | None = None) -> dict[str, Any]:
    config = config or CompositionConfig()
    generated = _generate(config)
    x = generated["x"]
    primitive_targets = generated["primitive_targets"]
    rotation = generated["rotation"]
    splits = generated["splits"]
    train = splits["train"]

    primitive_predictions = np.empty_like(primitive_targets)
    primitive_coefficients: dict[str, str] = {}
    for index, name in enumerate(PRIMITIVES):
        model = Ridge(alpha=config.ridge_alpha).fit(x[train], primitive_targets[train, index])
        primitive_predictions[:, index] = model.predict(x)
        primitive_coefficients[name] = array_hash(np.asarray(model.coef_, dtype=np.float64))

    result: dict[str, Any] = {
        "experiment_id": "e01-unseen-composition",
        "status": "POINT_ESTIMATE_COMPLETE",
        "config": asdict(config),
        "config_sha256": _json_hash(asdict(config)),
        "compound_definitions": COMPOUNDS,
        "compound_definitions_sha256": _json_hash(COMPOUNDS),
        "rotation_sha256": array_hash(rotation),
        "split_hashes": {name: array_hash(value) for name, value in splits.items()},
        "x_sha256": array_hash(x),
        "primitive_targets_sha256": array_hash(primitive_targets),
        "primitive_coefficient_hashes": primitive_coefficients,
        "compounds": {},
        "decisions": {},
    }

    wrong_permutation = np.asarray([1, 2, 0])
    for compound, raw_weights in COMPOUNDS.items():
        weights = np.asarray(raw_weights, dtype=np.float64)
        target = primitive_targets @ weights
        composed_prediction = primitive_predictions @ weights
        wrong_prediction = primitive_predictions @ weights[wrong_permutation]
        oracle_model = Ridge(alpha=config.ridge_alpha).fit(x[train], target[train])
        oracle_prediction = oracle_model.predict(x)
        compound_result: dict[str, Any] = {"weights": list(raw_weights), "splits": {}}
        for split_name in ("validation", "test"):
            queries = splits[split_name]
            methods = {
                "posthoc_composed": _evaluate(
                    _scalar_distances(composed_prediction, train, queries),
                    target[train],
                    target[queries],
                    config.retrieval_ks,
                ),
                "direct_oracle": _evaluate(
                    _scalar_distances(oracle_prediction, train, queries),
                    target[train],
                    target[queries],
                    config.retrieval_ks,
                ),
                "wrong_composition": _evaluate(
                    _scalar_distances(wrong_prediction, train, queries),
                    target[train],
                    target[queries],
                    config.retrieval_ks,
                ),
                "raw_euclidean": _evaluate(
                    _pairwise_euclidean(x[queries], x[train]),
                    target[train],
                    target[queries],
                    config.retrieval_ks,
                ),
                "raw_cosine": _evaluate(
                    _pairwise_cosine(x[queries], x[train]),
                    target[train],
                    target[queries],
                    config.retrieval_ks,
                ),
            }
            methods["posthoc_composed"]["composition_regret"] = (
                methods["direct_oracle"]["triplet_accuracy"]
                - methods["posthoc_composed"]["triplet_accuracy"]
            )
            compound_result["splits"][split_name] = methods
        test_methods = compound_result["splits"]["test"]
        controls = [
            test_methods["raw_euclidean"],
            test_methods["raw_cosine"],
            test_methods["wrong_composition"],
        ]
        status = _decision(
            test_methods["posthoc_composed"],
            test_methods["direct_oracle"],
            controls,
        )
        result["compounds"][compound] = compound_result
        result["decisions"][compound] = {
            "status": status,
            "composition_regret": test_methods["posthoc_composed"]["composition_regret"],
        }

    result["gate"] = {
        "passed": all(
            item["status"] == "SUPPORTED_POINT_ESTIMATE"
            for item in result["decisions"].values()
        ),
        "claim_promotion_allowed": False,
        "note": "E01.1 is a deterministic point-estimate stage; nulls and replication remain pending.",
    }
    result["decision_tree_sha256"] = _json_hash(result["decisions"])
    output.mkdir(parents=True, exist_ok=True)
    arrays = output / "arrays"
    arrays.mkdir(exist_ok=True)
    np.savez_compressed(arrays / "composition.npz", x=x, primitive_targets=primitive_targets)
    result_path = output / "composition-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["result_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    (output / "composition-result-with-hash.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/e01/composition-seed-211"))
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

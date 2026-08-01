"""E00 deterministic synthetic recoverability experiment.

The initial scaffold deliberately implements only data generation, exact-search
baselines, ridge predicted-distance retrieval, and hash-addressed manifests.
Learned diagonal and low-rank metric operators are the next registered step.
"""

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

REGIMES = (
    "axis_linear",
    "rotated_linear",
    "weak_linear",
    "nonlinear_xor",
    "absent",
    "correlated_nuisance",
)


@dataclass(frozen=True)
class Config:
    seed: int = 17
    samples: int = 4096
    dimensions: int = 64
    train_fraction: float = 0.60
    validation_fraction: float = 0.20
    noise_standard_deviation: float = 0.10
    retrieval_k: int = 10
    retrieval_ks: tuple[int, ...] = (10, 25, 50, 100)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def array_hash(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    header = f"{contiguous.dtype}|{contiguous.shape}".encode()
    return sha256_bytes(header + contiguous.tobytes())


def orthogonal_matrix(rng: np.random.Generator, dimensions: int) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(dimensions, dimensions)))
    signs = np.sign(np.diag(r))
    signs[signs == 0] = 1
    return q * signs


def split_indices(config: Config, rng: np.random.Generator) -> dict[str, np.ndarray]:
    order = rng.permutation(config.samples)
    train_end = int(config.samples * config.train_fraction)
    val_end = train_end + int(config.samples * config.validation_fraction)
    return {
        "train": np.sort(order[:train_end]),
        "validation": np.sort(order[train_end:val_end]),
        "test": np.sort(order[val_end:]),
    }


def generate_regime(
    regime: str,
    config: Config,
    rng: np.random.Generator,
    rotation: np.ndarray,
    splits: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    x = rng.normal(size=(config.samples, config.dimensions))
    noise = rng.normal(scale=config.noise_standard_deviation, size=config.samples)

    if regime == "axis_linear":
        y = x[:, 0] + noise
    elif regime == "rotated_linear":
        latent = x[:, 0] + noise
        x = x @ rotation
        y = latent
    elif regime == "weak_linear":
        x[:, 1:] *= 5.0
        y = 0.25 * x[:, 0] + noise
    elif regime == "nonlinear_xor":
        y = np.logical_xor(x[:, 0] > 0, x[:, 1] > 0).astype(float)
    elif regime == "absent":
        y = rng.normal(size=config.samples)
    elif regime == "correlated_nuisance":
        y = x[:, 0] + noise
        development = np.concatenate((splits["train"], splits["validation"]))
        test = splits["test"]
        x[development, 1] = y[development] + rng.normal(scale=0.02, size=len(development))
        x[test, 1] = rng.normal(size=len(test))
    else:
        raise ValueError(f"Unknown regime: {regime}")

    return x.astype(np.float64), y.astype(np.float64)


def nearest_by_distance(distance: np.ndarray, k: int) -> np.ndarray:
    return np.argpartition(distance, kth=k - 1)[:k]


def _mean_or_nan(values: list[float]) -> float:
    return float(np.mean(values)) if values else float("nan")


def _ndcg_at_k(oracle_distance: np.ndarray, retrieved: np.ndarray, k: int) -> float:
    """Return NDCG using smoothly decaying relevance derived from oracle distance."""
    positive = oracle_distance[oracle_distance > 0]
    scale = float(np.median(positive)) if positive.size else 1.0
    relevance = np.exp(-oracle_distance / max(scale, np.finfo(float).eps))
    discounts = 1.0 / np.log2(np.arange(2, k + 2, dtype=np.float64))
    dcg = float(np.sum(relevance[retrieved[:k]] * discounts))
    ideal = np.argsort(oracle_distance, kind="stable")[:k]
    idcg = float(np.sum(relevance[ideal] * discounts))
    return dcg / idcg if idcg > 0 else 1.0


def _deterministic_triplet_accuracy(
    oracle_distance: np.ndarray, predicted_distance: np.ndarray
) -> float:
    """Compare a deterministic set of candidate pairs for one query.

    Each candidate is paired with the candidate half a pool away. Oracle ties are
    excluded. A predicted tie receives half credit. This avoids introducing an
    additional random seed into the evidence artifact.
    """
    count = len(oracle_distance)
    if count < 2:
        return float("nan")
    left = np.arange(count // 2)
    right = left + (count - count // 2)
    oracle_delta = oracle_distance[left] - oracle_distance[right]
    predicted_delta = predicted_distance[left] - predicted_distance[right]
    informative = oracle_delta != 0
    if not np.any(informative):
        return float("nan")
    oracle_sign = np.sign(oracle_delta[informative])
    predicted_sign = np.sign(predicted_delta[informative])
    scores = np.where(predicted_sign == 0, 0.5, predicted_sign == oracle_sign)
    return float(np.mean(scores))


def evaluate_scalar_retrieval(
    candidate_values: np.ndarray,
    query_values: np.ndarray,
    predicted_candidates: np.ndarray,
    predicted_queries: np.ndarray,
    k: int,
    ks: tuple[int, ...] = (10, 25, 50, 100),
) -> dict[str, Any]:
    """Evaluate scalar-induced retrieval without over-relying on exact top-k overlap.

    The legacy primary-k fields remain for compatibility. Added metrics distinguish
    globally correct orderings and close near misses from exact-neighbour identity.
    """
    candidate_count = len(candidate_values)
    effective_ks = tuple(sorted({value for value in (*ks, k) if 0 < value <= candidate_count}))
    if not effective_ks:
        raise ValueError("At least one retrieval k must fit inside the candidate pool")
    primary_k = min(k, candidate_count)

    recall: dict[int, list[float]] = {value: [] for value in effective_ks}
    retrieved_error: dict[int, list[float]] = {value: [] for value in effective_ks}
    oracle_error: dict[int, list[float]] = {value: [] for value in effective_ks}
    relative_error: dict[int, list[float]] = {value: [] for value in effective_ks}
    ndcg: dict[int, list[float]] = {value: [] for value in effective_ks}
    correlations: list[float] = []
    triplet_accuracies: list[float] = []
    oracle_neighbour_ranks: list[float] = []
    epsilon = np.finfo(float).eps

    for true_q, predicted_q in zip(query_values, predicted_queries, strict=True):
        oracle_distance = np.abs(candidate_values - true_q)
        predicted_distance = np.abs(predicted_candidates - predicted_q)
        oracle_order = np.argsort(oracle_distance, kind="stable")
        predicted_order = np.argsort(predicted_distance, kind="stable")
        predicted_ranks = np.empty(candidate_count, dtype=np.int64)
        predicted_ranks[predicted_order] = np.arange(1, candidate_count + 1)

        correlation = spearmanr(oracle_distance, predicted_distance).statistic
        correlations.append(float(correlation))
        triplet_accuracies.append(
            _deterministic_triplet_accuracy(oracle_distance, predicted_distance)
        )
        oracle_neighbour_ranks.extend(
            predicted_ranks[oracle_order[:primary_k]].astype(float).tolist()
        )

        for current_k in effective_ks:
            oracle = oracle_order[:current_k]
            retrieved = predicted_order[:current_k]
            overlap = np.intersect1d(oracle, retrieved, assume_unique=True).size
            recall[current_k].append(overlap / current_k)

            current_retrieved_error = float(np.mean(oracle_distance[retrieved]))
            current_oracle_error = float(np.mean(oracle_distance[oracle]))
            retrieved_error[current_k].append(current_retrieved_error)
            oracle_error[current_k].append(current_oracle_error)
            relative_error[current_k].append(
                current_retrieved_error / max(current_oracle_error, epsilon)
            )
            ndcg[current_k].append(_ndcg_at_k(oracle_distance, retrieved, current_k))

    recall_summary = {str(value): _mean_or_nan(recall[value]) for value in effective_ks}
    retrieved_error_summary = {
        str(value): _mean_or_nan(retrieved_error[value]) for value in effective_ks
    }
    oracle_error_summary = {
        str(value): _mean_or_nan(oracle_error[value]) for value in effective_ks
    }
    relative_error_summary = {
        str(value): _mean_or_nan(relative_error[value]) for value in effective_ks
    }
    ndcg_summary = {str(value): _mean_or_nan(ndcg[value]) for value in effective_ks}

    return {
        # Backward-compatible primary fields.
        "recall_at_k": recall_summary[str(primary_k)],
        "mean_oracle_distance": retrieved_error_summary[str(primary_k)],
        "spearman": float(np.nanmean(correlations)),
        # Enhanced retrieval diagnostics.
        "primary_k": primary_k,
        "recall_at": recall_summary,
        "retrieved_mean_oracle_distance_at": retrieved_error_summary,
        "oracle_mean_distance_at": oracle_error_summary,
        "relative_neighbor_error_at": relative_error_summary,
        "ndcg_at": ndcg_summary,
        "triplet_accuracy": float(np.nanmean(triplet_accuracies)),
        "oracle_neighbor_predicted_rank_median": float(
            np.nanmedian(oracle_neighbour_ranks)
        ),
        "oracle_neighbor_predicted_rank_p90": float(
            np.nanpercentile(oracle_neighbour_ranks, 90)
        ),
    }


def run(config: Config, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    arrays_dir = output / "arrays"
    arrays_dir.mkdir(exist_ok=True)

    rng = np.random.default_rng(config.seed)
    rotation = orthogonal_matrix(rng, config.dimensions)
    splits = split_indices(config, rng)

    result: dict[str, Any] = {
        "experiment_id": "e00-synthetic-recoverability",
        "status": "IMPLEMENTED_BASELINES_ONLY",
        "config": asdict(config),
        "rotation_sha256": array_hash(rotation),
        "split_hashes": {name: array_hash(value) for name, value in splits.items()},
        "regimes": {},
    }

    for regime in REGIMES:
        x, y = generate_regime(regime, config, rng, rotation, splits)
        np.savez_compressed(arrays_dir / f"{regime}.npz", x=x, y=y)

        train = splits["train"]
        test = splits["test"]
        model = Ridge(alpha=1.0).fit(x[train], y[train])
        predictions = model.predict(x)
        metrics = evaluate_scalar_retrieval(
            candidate_values=y[train],
            query_values=y[test],
            predicted_candidates=predictions[train],
            predicted_queries=predictions[test],
            k=config.retrieval_k,
            ks=config.retrieval_ks,
        )
        result["regimes"][regime] = {
            "x_sha256": array_hash(x),
            "y_sha256": array_hash(y),
            "ridge_predicted_distance": metrics,
        }

    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["manifest_sha256"] = sha256_bytes(manifest_path.read_bytes())
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runs/e00/canonical-seed-17"))
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--samples", type=int, default=4096)
    parser.add_argument("--dimensions", type=int, default=64)
    args = parser.parse_args()
    result = run(
        Config(seed=args.seed, samples=args.samples, dimensions=args.dimensions), args.output
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

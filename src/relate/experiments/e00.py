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


def evaluate_scalar_retrieval(
    candidate_values: np.ndarray,
    query_values: np.ndarray,
    predicted_candidates: np.ndarray,
    predicted_queries: np.ndarray,
    k: int,
) -> dict[str, float]:
    recalls: list[float] = []
    neighbour_errors: list[float] = []
    correlations: list[float] = []

    for true_q, predicted_q in zip(query_values, predicted_queries, strict=True):
        oracle_distance = np.abs(candidate_values - true_q)
        predicted_distance = np.abs(predicted_candidates - predicted_q)
        oracle = set(nearest_by_distance(oracle_distance, k).tolist())
        retrieved = nearest_by_distance(predicted_distance, k)
        recalls.append(len(oracle.intersection(retrieved.tolist())) / k)
        neighbour_errors.append(float(np.mean(oracle_distance[retrieved])))
        correlations.append(float(spearmanr(oracle_distance, predicted_distance).statistic))

    return {
        "recall_at_k": float(np.mean(recalls)),
        "mean_oracle_distance": float(np.mean(neighbour_errors)),
        "spearman": float(np.nanmean(correlations)),
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

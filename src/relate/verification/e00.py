"""Independent verifier for E00 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge

from relate.experiments.e00 import (
    Config,
    REGIMES,
    array_hash,
    evaluate_scalar_retrieval,
    orthogonal_matrix,
    split_indices,
)


def _compare_metric_tree(
    expected: Any,
    observed: Any,
    path: str,
    errors: list[str],
) -> None:
    if isinstance(expected, dict):
        if not isinstance(observed, dict):
            errors.append(f"metric type mismatch: {path}")
            return
        if set(expected) != set(observed):
            errors.append(f"metric keys mismatch: {path}")
            return
        for key in expected:
            _compare_metric_tree(expected[key], observed[key], f"{path}.{key}", errors)
        return

    if isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
        if not np.isclose(float(expected), float(observed), rtol=1e-12, atol=1e-12, equal_nan=True):
            errors.append(
                f"metric mismatch: {path}: recorded={expected!r}, recomputed={observed!r}"
            )
        return

    if expected != observed:
        errors.append(f"metric mismatch: {path}: recorded={expected!r}, recomputed={observed!r}")


def verify(run_directory: Path) -> dict[str, object]:
    manifest_path = run_directory / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = Config(**manifest["config"])
    rng = np.random.default_rng(config.seed)
    rotation = orthogonal_matrix(rng, config.dimensions)
    splits = split_indices(config, rng)

    errors: list[str] = []
    if array_hash(rotation) != manifest["rotation_sha256"]:
        errors.append("rotation hash mismatch")

    for name, indices in splits.items():
        if array_hash(indices) != manifest["split_hashes"][name]:
            errors.append(f"split hash mismatch: {name}")

    verified_metrics = 0
    for regime in REGIMES:
        path = run_directory / "arrays" / f"{regime}.npz"
        if not path.exists():
            errors.append(f"missing array artifact: {regime}")
            continue
        with np.load(path) as payload:
            x = payload["x"]
            y = payload["y"]
        recorded = manifest["regimes"][regime]
        if array_hash(x) != recorded["x_sha256"]:
            errors.append(f"x hash mismatch: {regime}")
        if array_hash(y) != recorded["y_sha256"]:
            errors.append(f"y hash mismatch: {regime}")
        if x.shape != (config.samples, config.dimensions):
            errors.append(f"unexpected x shape: {regime}: {x.shape}")
        if y.shape != (config.samples,):
            errors.append(f"unexpected y shape: {regime}: {y.shape}")

        train = splits["train"]
        test = splits["test"]
        model = Ridge(alpha=1.0).fit(x[train], y[train])
        predictions = model.predict(x)
        recomputed = evaluate_scalar_retrieval(
            candidate_values=y[train],
            query_values=y[test],
            predicted_candidates=predictions[train],
            predicted_queries=predictions[test],
            k=config.retrieval_k,
            ks=tuple(config.retrieval_ks),
        )
        _compare_metric_tree(
            recorded["ridge_predicted_distance"],
            recomputed,
            f"{regime}.ridge_predicted_distance",
            errors,
        )
        verified_metrics += 1

    return {
        "experiment_id": manifest["experiment_id"],
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "verified_regimes": len(REGIMES) - sum(e.startswith("missing") for e in errors),
        "verified_metric_sets": verified_metrics,
        "claim_promotion_allowed": False,
        "note": (
            "E00 verifies deterministic generation, artifact identity, and enhanced "
            "ridge retrieval metrics only. The registered operator suite remains incomplete."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.run_directory)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

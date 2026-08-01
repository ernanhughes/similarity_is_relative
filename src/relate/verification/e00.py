"""Independent verifier for E00 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge

from relate.experiments.e00 import (
    BINARY_REGIMES,
    REGIMES,
    Config,
    array_hash,
    evaluate_scalar_retrieval,
    orthogonal_matrix,
    split_indices,
)


def _compare_metric_tree(
    recorded: Any,
    recomputed: Any,
    path: str,
    errors: list[str],
) -> None:
    """Recursively compare a recorded metric tree with recomputed values."""
    if isinstance(recorded, dict) and isinstance(recomputed, dict):
        recorded_keys = set(recorded)
        recomputed_keys = set(recomputed)
        for missing in sorted(recorded_keys - recomputed_keys):
            errors.append(f"missing recomputed metric: {path}.{missing}")
        for unexpected in sorted(recomputed_keys - recorded_keys):
            errors.append(f"unexpected recomputed metric: {path}.{unexpected}")
        for key in sorted(recorded_keys & recomputed_keys):
            _compare_metric_tree(recorded[key], recomputed[key], f"{path}.{key}", errors)
        return

    if isinstance(recorded, (int, float)) and isinstance(recomputed, (int, float)):
        if not np.isclose(float(recorded), float(recomputed), rtol=1e-12, atol=1e-12):
            errors.append(
                f"metric mismatch: {path}: recorded={recorded!r}, recomputed={recomputed!r}"
            )
        return

    if recorded != recomputed:
        errors.append(f"metric mismatch: {path}: recorded={recorded!r}, recomputed={recomputed!r}")


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
            target_kind="binary" if regime in BINARY_REGIMES else "continuous",
            tolerance_fraction=config.scalar_tolerance_fraction,
            relative_error_minimum_denominator=config.relative_error_minimum_denominator,
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
            "E00 verifies deterministic generation, artifact identity, and target-specific "
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

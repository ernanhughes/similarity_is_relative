"""Independent verifier for E00 artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from relate.experiments.e00 import Config, REGIMES, array_hash, orthogonal_matrix, split_indices


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

    return {
        "experiment_id": manifest["experiment_id"],
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "verified_regimes": len(REGIMES) - sum(e.startswith("missing") for e in errors),
        "claim_promotion_allowed": False,
        "note": "E00 currently verifies generation and ridge baseline artifacts only.",
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

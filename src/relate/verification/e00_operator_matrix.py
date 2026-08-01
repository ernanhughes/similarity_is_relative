"""Independent verifier for the E00.2 operator matrix."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from relate.experiments.e00_operator_matrix import OperatorConfig, run, sha256_file


def _compare_tree(recorded: Any, recomputed: Any, path: str, errors: list[str]) -> None:
    if isinstance(recorded, dict) and isinstance(recomputed, dict):
        recorded_keys = set(recorded)
        recomputed_keys = set(recomputed)
        for missing in sorted(recorded_keys - recomputed_keys):
            errors.append(f"missing recomputed field: {path}.{missing}")
        for unexpected in sorted(recomputed_keys - recorded_keys):
            errors.append(f"unexpected recomputed field: {path}.{unexpected}")
        for key in sorted(recorded_keys & recomputed_keys):
            _compare_tree(recorded[key], recomputed[key], f"{path}.{key}", errors)
        return

    if isinstance(recorded, (int, float)) and isinstance(recomputed, (int, float)):
        if not np.isclose(float(recorded), float(recomputed), rtol=1e-10, atol=1e-12):
            errors.append(
                f"numeric mismatch: {path}: recorded={recorded!r}, recomputed={recomputed!r}"
            )
        return

    if recorded != recomputed:
        errors.append(f"value mismatch: {path}: recorded={recorded!r}, recomputed={recomputed!r}")


def verify(source_directory: Path, operator_directory: Path) -> dict[str, Any]:
    matrix_path = operator_directory / "operator-matrix.json"
    result_path = operator_directory / "operator-matrix-result.json"
    if not matrix_path.exists():
        raise FileNotFoundError(matrix_path)
    if not result_path.exists():
        raise FileNotFoundError(result_path)

    recorded = json.loads(matrix_path.read_text(encoding="utf-8"))
    result_record = json.loads(result_path.read_text(encoding="utf-8"))
    config_payload = recorded["operator_config"]
    config = OperatorConfig(
        retrieval_ks=tuple(config_payload["retrieval_ks"]),
        ridge_alpha=float(config_payload["ridge_alpha"]),
        pls_ranks=tuple(config_payload["pls_ranks"]),
    )

    errors: list[str] = []
    recorded_matrix_hash = result_record.get("operator_matrix_sha256")
    observed_matrix_hash = sha256_file(matrix_path)
    if recorded_matrix_hash != observed_matrix_hash:
        errors.append("operator matrix hash mismatch")

    with tempfile.TemporaryDirectory(prefix="relate-e00-operator-verify-") as temp:
        run(source_directory, Path(temp), config)
        recomputed = json.loads((Path(temp) / "operator-matrix.json").read_text(encoding="utf-8"))
        _compare_tree(recorded, recomputed, "operator_matrix", errors)

    method_sets = sum(
        len(regime_payload["methods"]) for regime_payload in recorded["regimes"].values()
    )
    return {
        "experiment_id": recorded["experiment_id"],
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "verified_regimes": len(recorded["regimes"]),
        "verified_method_sets": method_sets,
        "source_manifest_sha256": recorded["source_manifest_sha256"],
        "operator_matrix_sha256": observed_matrix_hash,
        "claim_promotion_allowed": False,
        "note": (
            "E00.2 verifies exact and supervised operator point estimates only. "
            "Permutation nulls, confidence intervals and certification remain pending."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("runs/e00/canonical-seed-17"))
    parser.add_argument("--operators", type=Path, default=Path("runs/e00/operator-matrix-seed-17"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.source, args.operators)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

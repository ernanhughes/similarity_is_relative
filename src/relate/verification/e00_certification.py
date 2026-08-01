"""Independent verifier for E00.3 certification artifacts."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from relate.experiments.e00_certification import CertificationConfig, run
from relate.experiments.e00_operator_matrix import sha256_file


def _compare(expected: Any, actual: Any, path: str, errors: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected) != set(actual):
            errors.append(f"key mismatch: {path}")
            return
        for key in expected:
            _compare(expected[key], actual[key], f"{path}.{key}", errors)
        return
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if not np.isclose(float(expected), float(actual), rtol=1e-10, atol=1e-12, equal_nan=True):
            errors.append(f"value mismatch: {path}: {expected!r} != {actual!r}")
        return
    if expected != actual:
        errors.append(f"value mismatch: {path}: {expected!r} != {actual!r}")


def verify(source: Path, operators: Path, certification: Path) -> dict[str, Any]:
    result_path = certification / "certification-result.json"
    recorded = json.loads(result_path.read_text(encoding="utf-8"))
    config = CertificationConfig(**recorded["config"])
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="relate-e00-certification-") as directory:
        recomputed = run(source, operators, Path(directory), config)
    _compare(recorded, recomputed, "certification", errors)

    certification_path = certification / "certification.json"
    if sha256_file(certification_path) != recorded["certification_sha256"]:
        errors.append("certification hash mismatch")

    return {
        "experiment_id": "e00-certification",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "verified_decisions": len(recorded["decisions"]),
        "gate_passed": bool(recorded["gate"]["passed"]),
        "claim_promotion_allowed": False,
        "certification_sha256": recorded["certification_sha256"],
        "decision_tree_sha256": recorded["decision_tree_sha256"],
        "note": "E00.3 verifies seed-17 nulls, intervals and decisions. Multi-seed confirmation remains required.",  # NOQA E501
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("runs/e00/canonical-seed-17"))
    parser.add_argument("--operators", type=Path, default=Path("runs/e00/operator-matrix-seed-17"))
    parser.add_argument(
        "--certification", type=Path, default=Path("runs/e00/certification-seed-17")
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify(args.source, args.operators, args.certification)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

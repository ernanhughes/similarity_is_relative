"""Deterministic replay verifier for E01.2a."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from relate.experiments.e01_multiseed_composition import MultiSeedCompositionConfig, run


def _compare(expected: Any, observed: Any, path: str, errors: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(observed, dict):
        if set(expected) != set(observed):
            errors.append(f"{path}: key mismatch")
            return
        for key in sorted(expected):
            _compare(expected[key], observed[key], f"{path}.{key}", errors)
        return
    if isinstance(expected, list) and isinstance(observed, list):
        if len(expected) != len(observed):
            errors.append(f"{path}: length mismatch")
            return
        for index, (left, right) in enumerate(zip(expected, observed, strict=True)):
            _compare(left, right, f"{path}[{index}]", errors)
        return
    if isinstance(expected, float) and isinstance(observed, float):
        if abs(expected - observed) > 1e-12:
            errors.append(f"{path}: {expected!r} != {observed!r}")
        return
    if expected != observed:
        errors.append(f"{path}: {expected!r} != {observed!r}")


def verify(result_path: Path, output_path: Path) -> dict[str, Any]:
    recorded = json.loads(result_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="relate-e01-multiseed-") as temporary:
        reproduced = run(Path(temporary), MultiSeedCompositionConfig())
    left = dict(recorded)
    right = dict(reproduced)
    left.pop("result_sha256", None)
    right.pop("result_sha256", None)
    errors: list[str] = []
    _compare(left, right, "result", errors)
    report = {
        "experiment_id": recorded.get("experiment_id"),
        "verification_class": "DETERMINISTIC_REPLAY",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "verified_seeds": len(recorded.get("seeds", {})),
        "verified_compounds": len(recorded.get("aggregate", {})),
        "verified_decisions": len(recorded.get("decisions", {})),
        "gate_passed": bool(recorded.get("gate", {}).get("passed", False)),
        "claim_promotion_allowed": bool(
            recorded.get("gate", {}).get("claim_promotion_allowed", False)
        ),
        "result_sha256": recorded.get("result_sha256"),
        "decision_tree_sha256": recorded.get("decision_tree_sha256"),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit(1)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result",
        type=Path,
        default=Path("runs/e01/multiseed-composition/multiseed-composition-result-with-hash.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("runs/e01/multiseed-composition/verification.json")
    )
    args = parser.parse_args()
    print(json.dumps(verify(args.result, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

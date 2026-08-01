"""Independent verifier for E00.4 multi-seed confirmation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from relate.experiments.e00_multiseed import CONFIRMATORY_SEEDS, MultiSeedConfig, run
from relate.experiments.e00_operator_matrix import sha256_file


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
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="relate-e00-multiseed-") as temporary:
        reproduced = run(Path(temporary), MultiSeedConfig())

    comparable_recorded = dict(recorded)
    comparable_reproduced = dict(reproduced)
    comparable_recorded.pop("aggregate_result_sha256", None)
    comparable_reproduced.pop("aggregate_result_sha256", None)
    _compare(comparable_recorded, comparable_reproduced, "result", errors)

    gate = recorded.get("gate", {})
    report = {
        "experiment_id": "e00-multiseed-confirmation",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "verified_seeds": list(CONFIRMATORY_SEEDS),
        "verified_decisions": len(recorded.get("decisions", {})),
        "verified_model_selections": len(CONFIRMATORY_SEEDS),
        "gate_passed": bool(gate.get("passed", False)),
        "claim_promotion_allowed": bool(gate.get("claim_promotion_allowed", False)),
        "aggregate_result_sha256": sha256_file(result_path),
        "decision_tree_sha256": recorded.get("decision_tree_sha256"),
        "note": "Verification success is independent of the scientific gate outcome.",
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
        default=Path("runs/e00/multiseed/aggregate/multiseed-result.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/e00/multiseed/aggregate/verification.json"),
    )
    args = parser.parse_args()
    print(json.dumps(verify(args.result, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

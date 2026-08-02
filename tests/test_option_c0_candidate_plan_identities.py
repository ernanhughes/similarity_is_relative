from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN = (
    REPO_ROOT
    / "artifacts"
    / "canonical"
    / "option-c0"
    / "candidate-plan-v1"
    / "option-c0-initial-candidate-plan-v1.json"
)
REGISTRY = (
    REPO_ROOT
    / "artifacts"
    / "canonical"
    / "option-c0"
    / "candidate-plan-v1"
    / "option-c0-candidate-registry-v1.jsonl"
)

EXPECTED_PLAN_FILE_SHA256 = (
    "5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d"
)
EXPECTED_PLAN_CANONICAL_SHA256 = (
    "f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94"
)
EXPECTED_REGISTRY_FILE_SHA256 = (
    "a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_candidate_plan_file_and_canonical_identities_are_distinct_and_frozen():
    plan_bytes = PLAN.read_bytes()
    assert _sha256(plan_bytes) == EXPECTED_PLAN_FILE_SHA256

    value = json.loads(plan_bytes)
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    assert _sha256(canonical) == EXPECTED_PLAN_CANONICAL_SHA256
    assert EXPECTED_PLAN_FILE_SHA256 != EXPECTED_PLAN_CANONICAL_SHA256


def test_candidate_registry_file_identity_is_frozen():
    assert _sha256(REGISTRY.read_bytes()) == EXPECTED_REGISTRY_FILE_SHA256

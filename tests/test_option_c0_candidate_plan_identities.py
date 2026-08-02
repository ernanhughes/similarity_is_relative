from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = REPO_ROOT / "artifacts" / "canonical" / "option-c0" / "candidate-plan-v1"
PLAN = PLAN_DIR / "option-c0-initial-candidate-plan-v1.json"
REGISTRY = PLAN_DIR / "option-c0-candidate-registry-v1.jsonl"
ERRATUM = PLAN_DIR / "option-c0-candidate-plan-identity-erratum-v1.json"

EXPECTED_PLAN_FILE_SHA256 = (
    "5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d"
)
EXPECTED_PLAN_CANONICAL_SHA256 = (
    "7de70669553f180ea0507c68b28dc790e896019d664055fbaa0a535b550c10c6"
)
EXPECTED_REGISTRY_FILE_SHA256 = (
    "a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282"
)
EXPECTED_ERRATUM_FILE_SHA256 = (
    "c1fa786fc5932bd5157ac2659ef8e6c58eb421d0d3200f339b6a096f362dc3dc"
)
STALE_PUBLISHED_DIGEST = (
    "f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return _sha256(payload)


def test_candidate_plan_final_identities_are_distinct_and_frozen():
    plan_bytes = PLAN.read_bytes()
    assert _sha256(plan_bytes) == EXPECTED_PLAN_FILE_SHA256
    assert _canonical_sha256(json.loads(plan_bytes)) == EXPECTED_PLAN_CANONICAL_SHA256
    assert EXPECTED_PLAN_FILE_SHA256 != EXPECTED_PLAN_CANONICAL_SHA256
    assert STALE_PUBLISHED_DIGEST not in {
        EXPECTED_PLAN_FILE_SHA256,
        EXPECTED_PLAN_CANONICAL_SHA256,
    }


def test_registry_stale_digest_is_covered_by_pre_execution_erratum():
    assert _sha256(REGISTRY.read_bytes()) == EXPECTED_REGISTRY_FILE_SHA256
    assert _sha256(ERRATUM.read_bytes()) == EXPECTED_ERRATUM_FILE_SHA256

    registrations = [
        json.loads(line)["payload"]
        for line in REGISTRY.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(registrations) == 6
    assert all(event["event_type"] == "REGISTERED" for event in registrations)
    assert all(
        event["artifact_hashes"]["candidate_plan"] == STALE_PUBLISHED_DIGEST
        for event in registrations
    )

    erratum = json.loads(ERRATUM.read_text(encoding="utf-8"))
    assert erratum["observed_before_execution"] is True
    assert erratum["scientific_result_observed"] is False
    assert erratum["mechanism_result_observed"] is False
    assert erratum["result_branch_created"] is False
    assert erratum["affected_registration_events"] == 6
    assert erratum["stale_published_digest"] == STALE_PUBLISHED_DIGEST
    assert erratum["correct_identities"] == {
        "exact_file_sha256": EXPECTED_PLAN_FILE_SHA256,
        "canonical_json_sha256": EXPECTED_PLAN_CANONICAL_SHA256,
        "candidate_registry_file_sha256": EXPECTED_REGISTRY_FILE_SHA256,
    }

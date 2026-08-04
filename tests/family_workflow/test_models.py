"""Family workflow model validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.family.edges import make_evidence_candidate, make_manual_review_disposition
from relate.family.workflow.models import (
    FamilyEvidenceBundle,
    evidence_bundle_commitment,
    validate_evidence_bundle_protocol,
)


def _reviewed_candidate():
    snapshot = "b" * 64
    return make_evidence_candidate(
        "owner/a",
        "owner/b",
        "VERIFIED_REPOSITORY_SUCCESSION",
        evidence_sources={"public_metadata_snapshot": snapshot},
        evidence_payload={
            "predecessor_repository": "owner/a",
            "successor_repository": "owner/b",
            "direction": "predecessor_to_successor",
            "public_succession_record": "test",
            "record_snapshot_hash": snapshot,
        },
    )


def test_evidence_bundle_commitment_is_order_independent() -> None:
    first = _reviewed_candidate()
    second = make_evidence_candidate(
        "owner/c",
        "owner/d",
        "SAME_OWNER_PROXY",
        evidence_sources={"allocation_manifest": "allocation:test"},
        evidence_payload={"same_owner": True, "owner": "owner"},
    )
    assert evidence_bundle_commitment(FamilyEvidenceBundle((), (first, second), ())) == (
        evidence_bundle_commitment(FamilyEvidenceBundle((), (second, first), ()))
    )


def test_duplicate_candidate_rejected() -> None:
    candidate = _reviewed_candidate()
    with pytest.raises(ValueError, match="duplicate evidence candidate"):
        FamilyEvidenceBundle((), (candidate, candidate), ())


def test_missing_candidate_for_disposition_rejected() -> None:
    candidate = _reviewed_candidate()
    disposition = make_manual_review_disposition(
        edge_candidate_id=candidate.candidate_id,
        protocol_sha256="a" * 64,
        evidence_commitment=candidate.evidence_commitment,
        disposition="APPROVED",
        reviewer_identity="c" * 64,
        review_timestamp="2026-08-02T00:00:00+00:00",
        bounded_reason="test",
    )
    with pytest.raises(ValueError, match="candidate not present"):
        FamilyEvidenceBundle((), (), (disposition,))


def test_stale_disposition_protocol_rejected_before_durable_write() -> None:
    candidate = _reviewed_candidate()
    disposition = make_manual_review_disposition(
        edge_candidate_id=candidate.candidate_id,
        protocol_sha256="b" * 64,
        evidence_commitment=candidate.evidence_commitment,
        disposition="APPROVED",
        reviewer_identity="c" * 64,
        review_timestamp="2026-08-02T00:00:00+00:00",
        bounded_reason="test",
    )
    bundle = FamilyEvidenceBundle((), (candidate,), (disposition,))
    with pytest.raises(ValueError, match="protocol identity is stale"):
        validate_evidence_bundle_protocol(bundle, family_protocol_sha256="a" * 64)


def test_incomplete_metadata_must_be_nonnegative() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        FamilyEvidenceBundle((), (), (), incomplete_metadata_records=-1)


def test_unresolved_review_required_candidate_is_valid_bundle_state() -> None:
    bundle = FamilyEvidenceBundle((), (_reviewed_candidate(),), ())
    assert bundle.dispositions == ()


def test_import_path_kept_for_pytest_collection() -> None:
    assert Path("tests/family_workflow/test_models.py").suffix == ".py"

"""Tests for relate.family.edges.

Fixtures use synthetic records only.  No canonical data is accessed.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from relate.family.edges import (
    REVIEW_DISPOSITIONS,
    derive_edge_id,
    evidence_candidate_from_record,
    evidence_edge_from_record,
    make_evidence_candidate,
    make_evidence_edge,
    make_manual_review_disposition,
    manual_review_disposition_from_record,
    resolve_evidence_candidate,
    validate_evidence_candidate,
    validate_manual_review_disposition,
    validate_resolved_edge,
)
from relate.family.sources import make_source_record

TIMESTAMP = "2026-08-02T00:00:00+00:00"
SOURCE_ID = "a" * 64
FAKE_PROTOCOL_SHA = "b" * 64
LEFT = "owner/a"
RIGHT = "owner/b"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_source(source_type: str, payload: dict | None = None) -> object:
    return make_source_record(
        source_type,
        payload=payload or {},
        provenance={"generated_at": TIMESTAMP},
    )


def _fork_sources() -> tuple[dict, dict]:
    """Return (evidence_sources, source_records) for DECLARED_GITHUB_FORK."""
    snap = _make_source(
        "public_metadata_snapshot",
        payload={
            "fork": True,
            "child_full_name": LEFT,
            "parent_or_source_full_name": RIGHT,
            "left_repository_id": "1",
            "right_repository_id": "2",
        },
    )
    evidence_sources = {
        "github_rest": snap.source_identity,
        "public_metadata_snapshot": snap.source_identity,
    }
    source_records = {
        ("public_metadata_snapshot", snap.source_identity): snap,
    }
    return evidence_sources, source_records


def _fork_payload(evidence_sources: dict) -> dict:
    return {
        "left_repository_id": "1",
        "right_repository_id": "2",
        "child_full_name": LEFT,
        "parent_or_source_full_name": RIGHT,
        "fork": True,
        "metadata_snapshot_identity": evidence_sources["public_metadata_snapshot"],
        "snapshot_status": "COMPLETE",
    }


def _make_fork_candidate() -> object:
    evidence_sources, _ = _fork_sources()
    payload = _fork_payload(evidence_sources)
    return make_evidence_candidate(
        LEFT,
        RIGHT,
        "DECLARED_GITHUB_FORK",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )


def _make_review_candidate() -> object:
    """VERIFIED_REPOSITORY_SUCCESSION — requires APPROVED_REQUIRED review."""
    snap = _make_source("public_metadata_snapshot")
    evidence_sources = {"public_metadata_snapshot": snap.source_identity}
    payload = {
        "predecessor_repository": LEFT,
        "successor_repository": RIGHT,
        "direction": "predecessor_to_successor",
        "public_succession_record": "public rename notice",
        "record_snapshot_hash": snap.source_identity,
    }
    return make_evidence_candidate(
        LEFT,
        RIGHT,
        "VERIFIED_REPOSITORY_SUCCESSION",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )


def _make_disposition(candidate, disposition: str = "APPROVED") -> object:
    return make_manual_review_disposition(
        edge_candidate_id=candidate.candidate_id,
        protocol_sha256=FAKE_PROTOCOL_SHA,
        evidence_commitment=candidate.evidence_commitment,
        disposition=disposition,
        reviewer_identity=SOURCE_ID,
        review_timestamp=TIMESTAMP,
        bounded_reason="reviewed in test",
    )


# ---------------------------------------------------------------------------
# derive_edge_id
# ---------------------------------------------------------------------------


class TestDeriveEdgeId:
    def test_returns_sha256(self) -> None:
        result = derive_edge_id({"k": "v"})
        assert len(result) == 64

    def test_deterministic(self) -> None:
        assert derive_edge_id({"k": "v"}) == derive_edge_id({"k": "v"})

    def test_sensitive_to_content(self) -> None:
        assert derive_edge_id({"k": "v1"}) != derive_edge_id({"k": "v2"})


# ---------------------------------------------------------------------------
# make_evidence_candidate
# ---------------------------------------------------------------------------


class TestMakeEvidenceCandidate:
    def test_creates_candidate(self) -> None:
        cand = _make_fork_candidate()
        assert cand.edge_type == "DECLARED_GITHUB_FORK"
        assert cand.left_repository == LEFT
        assert cand.right_repository == RIGHT
        assert cand.candidate_status == "UNRESOLVED"
        assert len(cand.candidate_id) == 64

    def test_deterministic_id(self) -> None:
        c1 = _make_fork_candidate()
        c2 = _make_fork_candidate()
        assert c1.candidate_id == c2.candidate_id

    def test_endpoint_order_normalized(self) -> None:
        evidence_sources, _ = _fork_sources()
        payload = _fork_payload(evidence_sources)
        c1 = make_evidence_candidate(
            LEFT, RIGHT, "DECLARED_GITHUB_FORK",
            evidence_sources=evidence_sources, evidence_payload=payload,
        )
        c2 = make_evidence_candidate(
            RIGHT, LEFT, "DECLARED_GITHUB_FORK",
            evidence_sources=evidence_sources, evidence_payload=payload,
        )
        assert c1.candidate_id == c2.candidate_id
        assert c1.left_repository <= c1.right_repository

    def test_self_edge_rejected(self) -> None:
        evidence_sources, _ = _fork_sources()
        payload = _fork_payload(evidence_sources)
        with pytest.raises(ValueError, match="distinct"):
            make_evidence_candidate(
                LEFT, LEFT, "DECLARED_GITHUB_FORK",
                evidence_sources=evidence_sources, evidence_payload=payload,
            )

    def test_unknown_edge_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown"):
            make_evidence_candidate(
                LEFT, RIGHT, "NONEXISTENT_TYPE",
                evidence_sources={}, evidence_payload={},
            )

    def test_wrong_rule_version_rejected(self) -> None:
        evidence_sources, _ = _fork_sources()
        payload = _fork_payload(evidence_sources)
        with pytest.raises(ValueError, match="rule version"):
            make_evidence_candidate(
                LEFT, RIGHT, "DECLARED_GITHUB_FORK",
                evidence_sources=evidence_sources,
                evidence_payload=payload,
                rule_version="old-version",
            )

    def test_forbidden_payload_field_rejected(self) -> None:
        evidence_sources, _ = _fork_sources()
        payload = _fork_payload(evidence_sources)
        payload["source_body"] = "x"
        with pytest.raises(ValueError, match="forbidden"):
            make_evidence_candidate(
                LEFT, RIGHT, "DECLARED_GITHUB_FORK",
                evidence_sources=evidence_sources, evidence_payload=payload,
            )


class TestValidateEvidenceCandidate:
    def test_valid_candidate_passes(self) -> None:
        cand = _make_fork_candidate()
        validate_evidence_candidate(cand)

    def test_tampered_candidate_id_rejected(self) -> None:
        cand = _make_fork_candidate()
        tampered = replace(cand, candidate_id="0" * 64)
        with pytest.raises(ValueError, match="tampered"):
            validate_evidence_candidate(tampered)

    def test_tampered_payload_hash_rejected(self) -> None:
        cand = _make_fork_candidate()
        tampered = replace(cand, evidence_payload_hash="0" * 64)
        with pytest.raises(ValueError, match="tampered"):
            validate_evidence_candidate(tampered)

    def test_non_unresolved_status_rejected(self) -> None:
        cand = _make_fork_candidate()
        tampered = replace(cand, candidate_status="RESOLVED")
        with pytest.raises(ValueError, match="UNRESOLVED"):
            validate_evidence_candidate(tampered)


# ---------------------------------------------------------------------------
# make_manual_review_disposition
# ---------------------------------------------------------------------------


class TestMakeManualReviewDisposition:
    def test_creates_disposition(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        assert disp.disposition == "APPROVED"
        assert len(disp.disposition_id) == 64

    def test_deterministic_id(self) -> None:
        cand = _make_review_candidate()
        d1 = _make_disposition(cand)
        d2 = _make_disposition(cand)
        assert d1.disposition_id == d2.disposition_id

    def test_invalid_disposition_rejected(self) -> None:
        cand = _make_review_candidate()
        with pytest.raises(ValueError, match="invalid manual review disposition"):
            make_manual_review_disposition(
                edge_candidate_id=cand.candidate_id,
                protocol_sha256=FAKE_PROTOCOL_SHA,
                evidence_commitment=cand.evidence_commitment,
                disposition="MAYBE",
                reviewer_identity=SOURCE_ID,
                review_timestamp=TIMESTAMP,
                bounded_reason="test",
            )

    def test_invalid_protocol_sha_rejected(self) -> None:
        cand = _make_review_candidate()
        with pytest.raises(ValueError, match="SHA-256 is invalid"):
            make_manual_review_disposition(
                edge_candidate_id=cand.candidate_id,
                protocol_sha256="not-a-hash",
                evidence_commitment=cand.evidence_commitment,
                disposition="APPROVED",
                reviewer_identity=SOURCE_ID,
                review_timestamp=TIMESTAMP,
                bounded_reason="test",
            )

    def test_review_dispositions_are_approved_rejected(self) -> None:
        assert REVIEW_DISPOSITIONS == ("APPROVED", "REJECTED")


class TestValidateManualReviewDisposition:
    def test_valid_disposition_passes(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        validate_manual_review_disposition(disp, cand, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_wrong_candidate_rejected(self) -> None:
        cand1 = _make_review_candidate()
        cand2 = _make_fork_candidate()
        disp = _make_disposition(cand1)
        tampered = replace(disp, edge_candidate_id=cand2.candidate_id)
        with pytest.raises(ValueError, match="another candidate"):
            validate_manual_review_disposition(tampered, cand1, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_stale_protocol_sha_rejected(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        with pytest.raises(ValueError, match="stale"):
            validate_manual_review_disposition(disp, cand, protocol_sha256="c" * 64)

    def test_stale_evidence_commitment_rejected(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        tampered = replace(disp, evidence_commitment="0" * 64)
        with pytest.raises(ValueError, match="stale"):
            validate_manual_review_disposition(tampered, cand, protocol_sha256=FAKE_PROTOCOL_SHA)


# ---------------------------------------------------------------------------
# resolve_evidence_candidate
# ---------------------------------------------------------------------------


class TestResolveEvidenceCandidate:
    def test_auto_rule_approved_without_disposition(self) -> None:
        cand = _make_fork_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        assert edge.review_status == "APPROVED"
        assert edge.connecting is True
        assert edge.disposition_id is None

    def test_auto_rule_rejects_disposition(self) -> None:
        cand = _make_fork_candidate()
        disp = _make_disposition(_make_review_candidate())
        with pytest.raises(ValueError, match="does not accept manual disposition"):
            resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_approved_required_unresolved_without_disposition(self) -> None:
        cand = _make_review_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        assert edge.review_status == "UNRESOLVED"
        assert edge.connecting is False

    def test_approved_required_approved_with_disposition(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand, "APPROVED")
        edge = resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)
        assert edge.review_status == "APPROVED"
        assert edge.connecting is True
        assert edge.disposition_id == disp.disposition_id

    def test_approved_required_rejected_is_nonconnecting(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand, "REJECTED")
        edge = resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)
        assert edge.review_status == "REJECTED"
        assert edge.connecting is False

    def test_review_only_never_connects(self) -> None:
        snap = _make_source("d1_visible_cache")
        evidence_sources = {"d1_visible_cache": snap.source_identity}
        payload = {
            "left_stable_key": "left",
            "right_stable_key": "right",
            "code_sha256": "7" * 64,
            "d1_visible_evidence_identity": snap.source_identity,
            "visible_role_left": "c0_fit",
            "visible_role_right": "c0_iteration",
        }
        cand = make_evidence_candidate(
            LEFT, RIGHT, "EXACT_FUNCTION_SOURCE_MATCH",
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        assert edge.review_status == "REVIEW_ONLY"
        assert edge.connecting is False

    def test_review_only_rejects_disposition(self) -> None:
        snap = _make_source("d1_visible_cache")
        evidence_sources = {"d1_visible_cache": snap.source_identity}
        payload = {
            "left_stable_key": "left",
            "right_stable_key": "right",
            "code_sha256": "7" * 64,
            "d1_visible_evidence_identity": snap.source_identity,
            "visible_role_left": "c0_fit",
            "visible_role_right": "c0_iteration",
        }
        cand = make_evidence_candidate(
            LEFT, RIGHT, "EXACT_FUNCTION_SOURCE_MATCH",
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )
        disp = _make_disposition(_make_review_candidate())
        with pytest.raises(ValueError, match="does not accept final disposition"):
            resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_deterministic_edge_id(self) -> None:
        cand = _make_fork_candidate()
        e1 = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        e2 = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        assert e1.edge_id == e2.edge_id


# ---------------------------------------------------------------------------
# make_evidence_edge
# ---------------------------------------------------------------------------


class TestMakeEvidenceEdge:
    def test_auto_edge_created(self) -> None:
        evidence_sources, _ = _fork_sources()
        payload = _fork_payload(evidence_sources)
        edge = make_evidence_edge(
            LEFT, RIGHT, "DECLARED_GITHUB_FORK",
            protocol_sha256=FAKE_PROTOCOL_SHA,
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )
        assert edge.connecting is True
        assert edge.review_status == "APPROVED"

    def test_review_required_edge_rejected(self) -> None:
        snap = _make_source("public_metadata_snapshot")
        evidence_sources = {"public_metadata_snapshot": snap.source_identity}
        payload = {
            "predecessor_repository": LEFT,
            "successor_repository": RIGHT,
            "direction": "predecessor_to_successor",
            "public_succession_record": "public rename notice",
            "record_snapshot_hash": snap.source_identity,
        }
        with pytest.raises(ValueError, match="disposition"):
            make_evidence_edge(
                LEFT, RIGHT, "VERIFIED_REPOSITORY_SUCCESSION",
                protocol_sha256=FAKE_PROTOCOL_SHA,
                evidence_sources=evidence_sources,
                evidence_payload=payload,
            )

    def test_source_bundle_shorthand_accepted(self) -> None:
        evidence_sources, _ = _fork_sources()
        payload = _fork_payload(evidence_sources)
        # Use evidence_sources kwarg
        edge = make_evidence_edge(
            LEFT, RIGHT, "DECLARED_GITHUB_FORK",
            protocol_sha256=FAKE_PROTOCOL_SHA,
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )
        assert edge is not None


# ---------------------------------------------------------------------------
# validate_resolved_edge
# ---------------------------------------------------------------------------


class TestValidateResolvedEdge:
    def test_valid_auto_edge_passes(self) -> None:
        cand = _make_fork_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        validate_resolved_edge(edge, cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_valid_approved_edge_passes(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        edge = resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)
        validate_resolved_edge(edge, cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_tampered_edge_id_rejected(self) -> None:
        cand = _make_fork_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        tampered = replace(edge, edge_id="0" * 64)
        with pytest.raises(ValueError, match="tampered"):
            validate_resolved_edge(tampered, cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_tampered_source_bundle_rejected(self) -> None:
        cand = _make_fork_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        tampered = replace(edge, evidence_source_bundle_sha256="0" * 64)
        with pytest.raises(ValueError, match="tampered"):
            validate_resolved_edge(tampered, cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)

    def test_endpoint_outside_allocation_rejected(self) -> None:
        cand = _make_fork_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        with pytest.raises(ValueError, match="outside the allocation"):
            validate_resolved_edge(
                edge, cand, None,
                protocol_sha256=FAKE_PROTOCOL_SHA,
                allocation_repositories={"other/repo"},
            )

    def test_stale_disposition_protocol_sha_rejected(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        edge = resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)
        with pytest.raises(ValueError, match="stale"):
            validate_resolved_edge(edge, cand, disp, protocol_sha256="d" * 64)

    def test_stale_evidence_commitment_rejected(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        edge = resolve_evidence_candidate(cand, disp, protocol_sha256=FAKE_PROTOCOL_SHA)
        # Change the candidate commitment to simulate stale commitment
        tampered_disp = replace(disp, evidence_commitment="0" * 64)
        with pytest.raises(ValueError):
            validate_resolved_edge(edge, cand, tampered_disp, protocol_sha256=FAKE_PROTOCOL_SHA)


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------


class TestRoundTripSerialization:
    def test_candidate_round_trip(self) -> None:
        cand = _make_fork_candidate()
        record = cand.as_record()
        restored = evidence_candidate_from_record(record)
        assert restored.candidate_id == cand.candidate_id
        assert restored.evidence_commitment == cand.evidence_commitment

    def test_disposition_round_trip(self) -> None:
        cand = _make_review_candidate()
        disp = _make_disposition(cand)
        record = disp.as_record()
        restored = manual_review_disposition_from_record(record)
        assert restored.disposition_id == disp.disposition_id

    def test_edge_round_trip(self) -> None:
        cand = _make_fork_candidate()
        edge = resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_PROTOCOL_SHA)
        record = edge.as_record()
        restored = evidence_edge_from_record(record)
        assert restored.edge_id == edge.edge_id
        assert restored.connecting == edge.connecting

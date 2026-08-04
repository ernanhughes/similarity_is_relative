"""Commitment tests for relate.family.commitments.

Covers deterministic edge/component commitments, order independence,
content/membership sensitivity, Unicode stability, duplicate/malformed
rejection, and exact compatibility with the historical facade.

These are distinct from the Stage 2C relate.workflows commitment chain:
these bind scientific graph records (resolved edges, components), not
workflow execution steps and results.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.family.commitments import component_commitment, edge_commitment
from relate.family.edges import (
    make_evidence_candidate,
    make_manual_review_disposition,
    resolve_evidence_candidate,
)
from relate.family.graph import build_components

TIMESTAMP = "2026-08-02T00:00:00+00:00"
PROTOCOL_SHA = "a" * 64


def _fork_edge(left: str, right: str, snapshot_id: str = "b" * 64):
    evidence_sources = {"github_rest": snapshot_id, "public_metadata_snapshot": snapshot_id}
    payload = {
        "left_repository_id": "1",
        "right_repository_id": "2",
        "child_full_name": left,
        "parent_or_source_full_name": right,
        "fork": True,
        "metadata_snapshot_identity": snapshot_id,
        "snapshot_status": "COMPLETE",
    }
    candidate = make_evidence_candidate(
        left,
        right,
        "DECLARED_GITHUB_FORK",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    return resolve_evidence_candidate(candidate, None, protocol_sha256=PROTOCOL_SHA)


def _succession_edge(left: str, right: str, disposition_outcome: str, reason: str = "test review"):
    snapshot_id = "c" * 64
    evidence_sources = {"public_metadata_snapshot": snapshot_id}
    payload = {
        "predecessor_repository": left,
        "successor_repository": right,
        "direction": "predecessor_to_successor",
        "public_succession_record": "public rename notice",
        "record_snapshot_hash": snapshot_id,
    }
    candidate = make_evidence_candidate(
        left,
        right,
        "VERIFIED_REPOSITORY_SUCCESSION",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    disposition = make_manual_review_disposition(
        edge_candidate_id=candidate.candidate_id,
        protocol_sha256=PROTOCOL_SHA,
        evidence_commitment=candidate.evidence_commitment,
        disposition=disposition_outcome,
        reviewer_identity="d" * 64,
        review_timestamp=TIMESTAMP,
        bounded_reason=reason,
    )
    edge = resolve_evidence_candidate(candidate, disposition, protocol_sha256=PROTOCOL_SHA)
    return edge, {disposition.disposition_id: disposition}


class TestEdgeCommitment:
    def test_empty_edge_commitment(self) -> None:
        assert edge_commitment([], protocol_sha256=PROTOCOL_SHA) == edge_commitment(
            [], protocol_sha256=PROTOCOL_SHA
        )

    def test_order_independence(self) -> None:
        first = _fork_edge("owner/a", "owner/b")
        second = _fork_edge("owner/c", "owner/d", snapshot_id="e" * 64)
        assert edge_commitment([first, second], protocol_sha256=PROTOCOL_SHA) == edge_commitment(
            [second, first], protocol_sha256=PROTOCOL_SHA
        )

    def test_content_sensitivity(self) -> None:
        first = _fork_edge("owner/a", "owner/b")
        changed = _fork_edge("owner/c", "owner/d", snapshot_id="e" * 64)
        assert edge_commitment([first], protocol_sha256=PROTOCOL_SHA) != edge_commitment(
            [changed], protocol_sha256=PROTOCOL_SHA
        )

    def test_connecting_status_sensitivity(self) -> None:
        approved, approved_dispositions = _succession_edge("owner/a", "owner/b", "APPROVED")
        rejected, rejected_dispositions = _succession_edge(
            "owner/a", "owner/b", "REJECTED", reason="different"
        )
        assert edge_commitment(
            [approved], protocol_sha256=PROTOCOL_SHA, dispositions=approved_dispositions
        ) != edge_commitment(
            [rejected], protocol_sha256=PROTOCOL_SHA, dispositions=rejected_dispositions
        )

    def test_duplicate_edge_id_rejected(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        with pytest.raises(ValueError, match="duplicate edge ID"):
            edge_commitment([edge, edge], protocol_sha256=PROTOCOL_SHA)

    def test_tampered_edge_rejected(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        tampered = replace(edge, edge_id="9" * 64)
        with pytest.raises(ValueError, match="edge_id"):
            edge_commitment([tampered], protocol_sha256=PROTOCOL_SHA)

    def test_unicode_payload_is_stable(self) -> None:
        edge, dispositions = _succession_edge(
            "owner/a", "owner/b", "APPROVED", reason="café ☃ review"
        )
        first = edge_commitment([edge], protocol_sha256=PROTOCOL_SHA, dispositions=dispositions)
        second = edge_commitment([edge], protocol_sha256=PROTOCOL_SHA, dispositions=dispositions)
        assert first == second


class TestComponentCommitment:
    def test_empty_component_commitment(self) -> None:
        assert component_commitment([], protocol_sha256=PROTOCOL_SHA) == component_commitment(
            [], protocol_sha256=PROTOCOL_SHA
        )

    def test_order_independence(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        components = build_components(
            ["owner/a", "owner/b", "owner/c"], [edge], protocol_sha256=PROTOCOL_SHA
        )
        assert component_commitment(
            components, protocol_sha256=PROTOCOL_SHA
        ) == component_commitment(list(reversed(components)), protocol_sha256=PROTOCOL_SHA)

    def test_membership_sensitivity(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        connected = build_components(["owner/a", "owner/b"], [edge], protocol_sha256=PROTOCOL_SHA)
        disconnected = build_components(["owner/a", "owner/b"], [], protocol_sha256=PROTOCOL_SHA)
        assert component_commitment(
            connected, protocol_sha256=PROTOCOL_SHA
        ) != component_commitment(disconnected, protocol_sha256=PROTOCOL_SHA)

    def test_malformed_repository_count_rejected(self) -> None:
        components = [{"component_id": "x", "repositories": ["owner/a"], "repository_count": 2}]
        with pytest.raises(ValueError, match="repository_count is malformed"):
            component_commitment(components, protocol_sha256=PROTOCOL_SHA)

    def test_tampered_component_id_rejected(self) -> None:
        components = [
            {"component_id": "not-the-real-id", "repositories": ["owner/a"], "repository_count": 1}
        ]
        with pytest.raises(ValueError, match="component_id does not match members"):
            component_commitment(components, protocol_sha256=PROTOCOL_SHA)


class TestHistoricalCompatibility:
    def test_component_commitment_same_result_through_both_paths(self) -> None:
        real_protocol_sha256 = historical.protocol_contract()["protocol_sha256"]
        edge = _fork_edge("owner/a", "owner/b")
        components = build_components(
            ["owner/a", "owner/b", "owner/c"], [edge], protocol_sha256=real_protocol_sha256
        )
        clean = component_commitment(components, protocol_sha256=real_protocol_sha256)
        hist = historical.component_commitment(components)
        assert clean == hist

    def test_edge_commitment_same_result_through_both_paths(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        clean = edge_commitment(
            [edge], protocol_sha256=historical.protocol_contract()["protocol_sha256"]
        )
        hist = historical.edge_commitment([edge])
        assert clean == hist

    def test_edge_commitment_wrapper_accepts_explicit_protocol_sha256(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        explicit = historical.edge_commitment([edge], protocol_sha256=PROTOCOL_SHA)
        clean = edge_commitment([edge], protocol_sha256=PROTOCOL_SHA)
        assert explicit == clean

    def test_protocol_sha_unaffected_by_extraction(self) -> None:
        assert (
            historical.protocol_contract()["protocol_sha256"]
            == "a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08"
        )

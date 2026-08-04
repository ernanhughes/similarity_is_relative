"""Outcome tests for relate.family.outcome.

Exercises every frozen outcome string and asserts the bounded-interpretation
invariant: family_graph_outcome never concludes contamination, materiality,
reallocation, or D2 authorization, regardless of input.
"""

from __future__ import annotations

import pytest

from relate.family.edges import make_evidence_candidate, resolve_evidence_candidate
from relate.family.outcome import family_graph_outcome, graph_completeness
from relate.family.sources import make_source_record

TIMESTAMP = "2026-08-02T00:00:00+00:00"
PROTOCOL_SHA = "a" * 64


def _same_owner_candidate(left: str, right: str):
    owner = left.split("/", 1)[0]
    manifest_record = make_source_record(
        "allocation_manifest", payload={"owner": owner}, provenance={}
    )
    evidence_sources = {"allocation_manifest": manifest_record.source_identity}
    payload = {"same_owner": True, "owner": owner}
    candidate = make_evidence_candidate(
        left, right, "SAME_OWNER_PROXY", evidence_sources=evidence_sources, evidence_payload=payload
    )
    registry = {(manifest_record.source_type, manifest_record.source_identity): manifest_record}
    return candidate, registry


def _ast_candidate(left: str, right: str):
    ast_sha = "c" * 64
    visible_record = make_source_record(
        "d1_visible_cache",
        payload={
            "left_stable_key": "left",
            "right_stable_key": "right",
            "normalized_ast_sha256": ast_sha,
            "visible_role_left": "c0_fit",
            "visible_role_right": "c0_iteration",
        },
        provenance={},
    )
    metadata_record = make_source_record(
        "public_metadata_snapshot", payload={"repository_id": "1"}, provenance={}
    )
    evidence_sources = {
        "d1_visible_cache": visible_record.source_identity,
        "public_metadata_snapshot": metadata_record.source_identity,
    }
    payload = {
        "left_stable_key": "left",
        "right_stable_key": "right",
        "normalized_ast_sha256": ast_sha,
        "d1_visible_evidence_identity": visible_record.source_identity,
        "visible_role_left": "c0_fit",
        "visible_role_right": "c0_iteration",
        "left_function_identity": "left_fn",
        "right_function_identity": "right_fn",
        "left_path_suffix": "a.py",
        "right_path_suffix": "b.py",
        "same_normalized_ast": True,
        "same_function_identity": True,
        "same_path_suffix": True,
        "compatible_repository_dates": True,
        "public_shared_package_history": True,
    }
    candidate = make_evidence_candidate(
        left,
        right,
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    registry = {
        (visible_record.source_type, visible_record.source_identity): visible_record,
        (metadata_record.source_type, metadata_record.source_identity): metadata_record,
    }
    return candidate, registry


class TestFamilyGraphOutcomeFrozenValues:
    def test_complete_no_cross_role(self) -> None:
        decision = family_graph_outcome(
            {
                "cross_role_connecting_components": 0,
                "unresolved_connecting_candidate_edges": 0,
                "incomplete_metadata_records": 0,
            }
        )
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"
        assert decision["family_crossing_observed"] is False
        assert decision["allocation_family_disjointness_violated"] is False

    def test_complete_cross_role_observed(self) -> None:
        decision = family_graph_outcome(
            {
                "cross_role_connecting_components": 1,
                "approved_connecting_edges": 1,
                "hard_or_exact_fit_iteration_crossing_observed": False,
            }
        )
        outcome = decision["family_graph_outcome"]
        assert outcome == "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED"
        assert decision["allocation_family_disjointness_violated"] is True
        assert decision["material_contamination_established"] is False
        assert decision["reallocation_required"] is None

    def test_incomplete_metadata(self) -> None:
        decision = family_graph_outcome(
            {"incomplete_metadata_records": 1, "cross_role_connecting_components": 1}
        )
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_METADATA"

    def test_incomplete_review_required(self) -> None:
        decision = family_graph_outcome(
            {"unresolved_connecting_candidate_edges": 1, "cross_role_connecting_components": 1}
        )
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"

    def test_incomplete_metadata_takes_priority_over_review_and_crossing(self) -> None:
        # Fail-closed: completeness must be checked before interpretation.
        decision = family_graph_outcome(
            {
                "incomplete_metadata_records": 1,
                "unresolved_connecting_candidate_edges": 1,
                "cross_role_connecting_components": 1,
            }
        )
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_METADATA"

    def test_unresolved_review_takes_priority_over_crossing(self) -> None:
        decision = family_graph_outcome(
            {"unresolved_connecting_candidate_edges": 1, "cross_role_connecting_components": 1}
        )
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"

    def test_multiple_role_crossings_report_same_outcome_string(self) -> None:
        one = family_graph_outcome({"cross_role_connecting_components": 1})
        many = family_graph_outcome({"cross_role_connecting_components": 5})
        assert one["family_graph_outcome"] == many["family_graph_outcome"]
        assert one["family_crossing_observed"] == many["family_crossing_observed"] is True

    @pytest.mark.parametrize(
        "summary",
        [
            {},
            {"cross_role_connecting_components": 1},
            {"incomplete_metadata_records": 1},
            {"unresolved_connecting_candidate_edges": 1},
            {
                "cross_role_connecting_components": 3,
                "hard_or_exact_fit_iteration_crossing_observed": True,
            },
        ],
    )
    def test_never_concludes_contamination_or_reallocation(self, summary: dict) -> None:
        decision = family_graph_outcome(summary)
        assert decision["material_contamination_established"] is False
        assert decision["reallocation_required"] is None
        assert decision["automatic_reallocation_decision_permitted"] is False


class TestGraphCompleteness:
    def test_nonconnecting_review_evidence_does_not_make_graph_incomplete(self) -> None:
        candidate, registry = _same_owner_candidate("owner/a", "owner/b")
        item = resolve_evidence_candidate(candidate, None, protocol_sha256=PROTOCOL_SHA)
        completeness = graph_completeness(
            [item],
            protocol_sha256=PROTOCOL_SHA,
            candidates={candidate.candidate_id: candidate},
            dispositions={},
            source_records=registry,
        )
        decision = family_graph_outcome(completeness)
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"
        assert completeness["nonconnecting_review_evidence_edges"] == 1

    def test_unresolved_connecting_candidate_makes_graph_incomplete(self) -> None:
        candidate, registry = _ast_candidate("owner/a", "owner/b")
        completeness = graph_completeness(
            [candidate],
            protocol_sha256=PROTOCOL_SHA,
            candidates={},
            dispositions={},
            source_records=registry,
        )
        decision = family_graph_outcome(completeness)
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"

    def test_missing_candidate_for_resolved_edge_raises(self) -> None:
        candidate, registry = _ast_candidate("owner/a", "owner/b")
        item = resolve_evidence_candidate(candidate, None, protocol_sha256=PROTOCOL_SHA)
        with pytest.raises(ValueError, match="missing candidate"):
            graph_completeness(
                [item],
                protocol_sha256=PROTOCOL_SHA,
                candidates={},
                dispositions={},
                source_records=registry,
            )

    def test_incomplete_metadata_records_is_passed_through(self) -> None:
        completeness = graph_completeness(
            [], protocol_sha256=PROTOCOL_SHA, candidates={}, dispositions={}, source_records={},
            incomplete_metadata_records=3,
        )
        assert completeness["incomplete_metadata_records"] == 3
        decision = family_graph_outcome(completeness)
        assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_METADATA"

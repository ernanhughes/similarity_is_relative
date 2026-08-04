from __future__ import annotations

import pytest

from relate.family.models import AllocationEntry, EvidenceEdge
from relate.family.review import materiality_inputs_from_records


def _edge(edge_type: str) -> EvidenceEdge:
    return EvidenceEdge(
        edge_id=edge_type,
        candidate_id=edge_type,
        disposition_id=None,
        left_repository="owner/a",
        right_repository="owner/b",
        edge_type=edge_type,
        connecting=True,
        evidence_sources={},
        evidence_source_bundle_sha256="a" * 64,
        evidence_payload_hash="b" * 64,
        evidence_commitment="c" * 64,
        rule_version="family-protocol-v1",
        confidence_category="high",
        human_review_required=False,
        review_status="APPROVED",
        reason="test",
        evidence_payload={},
    )


def _analysis() -> dict:
    return {
        "role_pair_impacts": [
            {
                "role_pair": ["c0_fit", "c0_iteration"],
                "repositories": ["owner/a", "owner/b"],
                "aggregate_row_count": 30,
            }
        ],
        "largest_crossing_component_repository_count": 2,
    }


def test_materiality_inputs_are_mechanical_and_do_not_conclude() -> None:
    inputs = materiality_inputs_from_records(
        analysis_record=_analysis(),
        allocation_role_row_counts={"c0_fit": 100, "c0_iteration": 200},
        allocation_entries=(
            AllocationEntry("owner/a", "c0_fit", 10),
            AllocationEntry("owner/b", "c0_iteration", 20),
        ),
        resolved_edges=(_edge("DECLARED_GITHUB_FORK"),),
    )
    assert inputs["affected_c0_fit_row_fraction"] == 0.3
    assert inputs["affected_c0_iteration_row_fraction"] == 0.15
    assert inputs["hard_cross_role_edge_count"] == 1
    assert inputs["conditional_cross_role_edge_count"] == 0
    assert inputs["family_disjoint_allocation_feasibility"]["status"] == "NOT_ASSESSED"
    assert inputs["material_contamination_established"] is False
    assert inputs["reallocation_required"] is None


def test_conditional_crossing_count() -> None:
    inputs = materiality_inputs_from_records(
        analysis_record=_analysis(),
        allocation_role_row_counts={"c0_fit": 100, "c0_iteration": 100},
        allocation_entries=(
            AllocationEntry("owner/a", "c0_fit", 10),
            AllocationEntry("owner/b", "c0_iteration", 20),
        ),
        resolved_edges=(_edge("EXPLICIT_COPY_OR_EXTRACTION_HISTORY"),),
    )
    assert inputs["hard_cross_role_edge_count"] == 0
    assert inputs["conditional_cross_role_edge_count"] == 1


def test_zero_denominator_refused() -> None:
    with pytest.raises(ValueError, match="row totals"):
        materiality_inputs_from_records(
            analysis_record=_analysis(),
            allocation_role_row_counts={"c0_fit": 0, "c0_iteration": 1},
            allocation_entries=(),
            resolved_edges=(),
        )


def test_unknown_role_refused() -> None:
    with pytest.raises(ValueError, match="unknown allocation role"):
        materiality_inputs_from_records(
            analysis_record=_analysis(),
            allocation_role_row_counts={"c0_fit": 1, "c0_iteration": 1, "bad": 1},
            allocation_entries=(),
            resolved_edges=(),
        )

"""Role-crossing analysis tests for the Stage 2E family workflow."""

from __future__ import annotations

import pytest

from relate.family.analysis import (
    HARD_OR_EXACT_CONNECTING_EDGE_TYPES,
    analyse_role_crossings,
)
from relate.family.graph import component_id
from relate.family.models import AllocationEntry, EvidenceEdge

PROTOCOL_SHA = "a" * 64


def _edge(
    left: str,
    right: str,
    *,
    edge_type: str = "DECLARED_GITHUB_FORK",
    connecting: bool = True,
) -> EvidenceEdge:
    return EvidenceEdge(
        edge_id=f"{left}|{right}|{edge_type}|{connecting}",
        candidate_id=("e" * 60) + ("0001" if connecting else "0000"),
        disposition_id=None,
        left_repository=left,
        right_repository=right,
        edge_type=edge_type,
        connecting=connecting,
        evidence_sources={},
        evidence_source_bundle_sha256="b" * 64,
        evidence_payload_hash="c" * 64,
        evidence_commitment="d" * 64,
        rule_version="family-protocol-v1",
        confidence_category="high",
        human_review_required=False,
        review_status="APPROVED",
        reason="test",
        evidence_payload={},
    )


def _entries() -> tuple[AllocationEntry, ...]:
    return (
        AllocationEntry("owner/a", "c0_fit", 10),
        AllocationEntry("owner/b", "c0_iteration", 20),
        AllocationEntry("owner/c", "c0_selection", 30),
    )


def _component(*repositories: str) -> dict[str, object]:
    members = tuple(sorted(repositories))
    return {
        "component_id": component_id(members, PROTOCOL_SHA),
        "repositories": members,
        "repository_count": len(members),
    }


def test_singleton_components_have_no_crossings() -> None:
    components = [_component("owner/a"), _component("owner/b"), _component("owner/c")]
    analysis = analyse_role_crossings(_entries(), components, [], protocol_sha256=PROTOCOL_SHA)
    assert analysis.cross_role_connecting_components == 0
    assert analysis.role_pair_impacts == ()


def test_cross_role_component_records_role_pair_and_rows() -> None:
    edge = _edge("owner/a", "owner/b")
    components = [_component("owner/a", "owner/b")]
    analysis = analyse_role_crossings(
        _entries()[:2], components, [edge], protocol_sha256=PROTOCOL_SHA
    )
    assert analysis.cross_role_connecting_components == 1
    assert analysis.role_pair_impacts[0].role_pair == ("c0_fit", "c0_iteration")
    assert analysis.role_pair_impacts[0].aggregate_row_count == 30


def test_exact_ast_is_authoritatively_hard_or_exact() -> None:
    assert "EXACT_AST_WITH_CORROBORATING_PROVENANCE" in HARD_OR_EXACT_CONNECTING_EDGE_TYPES
    edge = _edge(
        "owner/a",
        "owner/b",
        edge_type="EXACT_AST_WITH_CORROBORATING_PROVENANCE",
    )
    components = [_component("owner/a", "owner/b")]
    analysis = analyse_role_crossings(
        _entries()[:2], components, [edge], protocol_sha256=PROTOCOL_SHA
    )
    assert analysis.hard_or_exact_fit_iteration_crossing_observed is True


def test_conditional_non_exact_does_not_set_hard_or_exact_flag() -> None:
    edge = _edge("owner/a", "owner/b", edge_type="SAME_MODULE_LINEAGE_WITH_CORROBORATION")
    components = [_component("owner/a", "owner/b")]
    analysis = analyse_role_crossings(
        _entries()[:2], components, [edge], protocol_sha256=PROTOCOL_SHA
    )
    assert analysis.cross_role_connecting_components == 1
    assert analysis.hard_or_exact_fit_iteration_crossing_observed is False


def test_tampered_component_id_rejected() -> None:
    components = ({"component_id": "0" * 64, "repositories": ["owner/a"], "repository_count": 1},)
    with pytest.raises(ValueError, match="stale or tampered"):
        analyse_role_crossings(_entries()[:1], components, [], protocol_sha256=PROTOCOL_SHA)


def test_duplicate_component_id_rejected() -> None:
    component = _component("owner/a")
    components = (component, {**component, "repositories": ["owner/b"]})
    with pytest.raises(ValueError, match="duplicate component ID"):
        analyse_role_crossings(_entries()[:2], components, [], protocol_sha256=PROTOCOL_SHA)


def test_unknown_repository_rejected() -> None:
    components = [_component("owner/a"), _component("owner/z")]
    with pytest.raises(ValueError, match="unknown repository|missing"):
        analyse_role_crossings(_entries()[:1], components, [], protocol_sha256=PROTOCOL_SHA)


def test_no_materiality_or_reallocation_conclusion() -> None:
    edge = _edge("owner/a", "owner/b")
    components = [_component("owner/a", "owner/b")]
    record = analyse_role_crossings(
        _entries()[:2], components, [edge], protocol_sha256=PROTOCOL_SHA
    ).as_record()
    assert "material_contamination_established" not in record
    assert "reallocation_required" not in record

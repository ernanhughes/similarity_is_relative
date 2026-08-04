"""Bounded family-graph completeness and outcome calculation.

Answers only the frozen bounded question the family-connected allocation
protocol authorizes: whether repositories assigned to different
experimental roles belong to connected repository families under the
frozen evidence rules. This module reports facts about graph completeness
and role crossings; it never concludes contamination, materiality,
reallocation, or D2 authorization — those remain explicit human-review
decisions outside this module's scope (see ``family_graph_outcome``'s
``material_contamination_established``, ``reallocation_required``, and
``automatic_reallocation_decision_permitted`` fields, which are always
``False``/``None``/``False``).

No database access, CLI parsing, file publication, or workflow
orchestration. This module must not import from relate.experiments,
relate.workflows, or relate.cli.

Known limitation (see docs/architecture/capability-continuity.md)
-------------------------------------------------------------------
There is no current implementation of "cross-role component detection" or
"role-pair summaries" that computes ``cross_role_connecting_components``
from components and allocation roles — the historical module never had
one either. ``family_graph_outcome`` only consumes an already-computed
integer summary. This module does not invent that missing computation;
see the continuity ledger for this as a recorded gap for a future stage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relate.family.edges import validate_evidence_candidate, validate_resolved_edge
from relate.family.models import (
    EvidenceCandidate,
    EvidenceEdge,
    ManualReviewDisposition,
    SourceEvidenceRecord,
)
from relate.family.rules import EDGE_RULES
from relate.family.sources import validate_source_registry


def graph_completeness(
    items: Sequence[EvidenceEdge | EvidenceCandidate],
    *,
    protocol_sha256: str,
    candidates: Mapping[str, EvidenceCandidate],
    dispositions: Mapping[str, ManualReviewDisposition],
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord],
    incomplete_metadata_records: int = 0,
) -> dict[str, int]:
    unresolved = 0
    approved = 0
    review_only = 0
    rejected = 0
    for item in items:
        if isinstance(item, EvidenceCandidate):
            validate_evidence_candidate(item)
            validate_source_registry(
                EDGE_RULES[item.edge_type],
                item.left_repository,
                item.right_repository,
                item.evidence_payload,
                item.evidence_sources,
                source_records,
            )
            rule = EDGE_RULES[item.edge_type]
            if rule.is_connecting_candidate and rule.review_requirement == "APPROVED_REQUIRED":
                unresolved += 1
            elif not rule.is_connecting_candidate:
                review_only += 1
            continue
        candidate = candidates.get(item.candidate_id)
        if candidate is None:
            raise ValueError("graph completeness missing candidate")
        disposition = (
            dispositions.get(item.disposition_id) if item.disposition_id is not None else None
        )
        validate_resolved_edge(
            item,
            candidate,
            disposition,
            protocol_sha256=protocol_sha256,
            source_records=source_records,
        )
        rule = EDGE_RULES[item.edge_type]
        if rule.is_connecting_candidate and item.review_status == "UNRESOLVED":
            unresolved += 1
        elif item.connecting:
            approved += 1
        elif rule.is_connecting_candidate and item.review_status == "REJECTED":
            rejected += 1
        elif not rule.is_connecting_candidate:
            review_only += 1
    return {
        "unresolved_connecting_candidate_edges": unresolved,
        "approved_connecting_edges": approved,
        "rejected_connecting_candidates": rejected,
        "nonconnecting_review_evidence_edges": review_only,
        "incomplete_metadata_records": incomplete_metadata_records,
    }


def family_graph_outcome(summary: Mapping[str, Any]) -> dict[str, Any]:
    incomplete_metadata = int(summary.get("incomplete_metadata_records", 0))
    unresolved = int(summary.get("unresolved_connecting_candidate_edges", 0))
    approved = int(summary.get("approved_connecting_edges", 0))
    cross_role_components = int(summary.get("cross_role_connecting_components", 0))
    hard_or_exact = bool(summary.get("hard_or_exact_fit_iteration_crossing_observed", False))
    if incomplete_metadata:
        outcome = "FAMILY_GRAPH_INCOMPLETE_METADATA"
    elif unresolved:
        outcome = "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"
    elif cross_role_components:
        outcome = "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED"
    else:
        outcome = "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"
    return {
        "family_graph_outcome": outcome,
        "family_crossing_observed": cross_role_components > 0,
        "allocation_family_disjointness_violated": cross_role_components > 0,
        "hard_or_exact_fit_iteration_crossing_observed": hard_or_exact,
        "approved_connecting_edges": approved,
        "unresolved_connecting_candidate_edges": unresolved,
        "rejected_connecting_candidates": int(summary.get("rejected_connecting_candidates", 0)),
        "nonconnecting_review_evidence_edges": int(
            summary.get("nonconnecting_review_evidence_edges", 0)
        ),
        "incomplete_metadata_records": incomplete_metadata,
        "material_contamination_established": False,
        "reallocation_required": None,
        "automatic_reallocation_decision_permitted": False,
    }

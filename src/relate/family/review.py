"""Family review-packet boundary for completed noncanonical workflow runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.analysis import bounded_family_outcome_commitment
from relate.family.commitments import component_commitment, edge_commitment
from relate.family.outcome import family_graph_outcome
from relate.family.repositories import ROLE_ORDER, normalize_repository
from relate.family.rules import CONDITIONAL_CONNECTING_EDGE_TYPES, HARD_CONNECTING_EDGE_TYPES
from relate.family.store import FamilyGraphCache
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import FamilyWorkflowPlan
from relate.workflows import WorkflowRunResult, validate_completed_run

FAMILY_REVIEW_PACKET_SCHEMA_ID: Final = "relate-family-review-packet-v1"
PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY: Final = "BOUNDED_FAMILY_RESULT_ONLY"
NOT_CONCLUDED: Final[tuple[str, ...]] = (
    "MATERIAL_CONTAMINATION",
    "MATERIALITY_THRESHOLD",
    "REALLOCATION_REQUIRED",
    "D2_AUTHORIZED",
)

_EXPECTED_STEP_NAMES: Final[tuple[str, ...]] = (
    "verify_family_inputs",
    "register_allocation",
    "register_prepared_evidence",
    "resolve_candidates",
    "assess_graph_readiness",
    "build_family_components",
    "analyse_role_crossings",
    "determine_family_outcome",
)


def _is_under(path: Path, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    base = root.resolve(strict=False)
    return resolved == base or base in resolved.parents


def reject_canonical_path(path: Path, *, repo_root: Path, label: str) -> None:
    """Reject any path contained under ``<repo_root>/artifacts/canonical``."""
    candidate = path if path.is_absolute() else repo_root / path
    if _is_under(candidate, repo_root / "artifacts" / "canonical"):
        raise ValueError(f"canonical path rejected for {label}: {path}")


def _record_by_name(result: WorkflowRunResult) -> dict[str, Any]:
    return {record.step_name: record for record in result.records}


def _phase_commitments(cache: FamilyGraphCache) -> dict[str, str]:
    return {record.phase: record.commitment_sha256 for record in cache.list_phase_commitments()}


def _review_status_counts(edges: Sequence[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for edge in edges:
        counts[edge.review_status] = counts.get(edge.review_status, 0) + 1
    return counts


def materiality_inputs_from_records(
    *,
    analysis_record: Mapping[str, Any],
    allocation_role_row_counts: Mapping[str, int],
    allocation_entries: Sequence[Any],
    resolved_edges: Sequence[Any],
) -> dict[str, Any]:
    """Present mechanically derivable materiality inputs without deciding materiality."""
    unknown_roles = set(allocation_role_row_counts) - set(ROLE_ORDER)
    if unknown_roles:
        raise ValueError(f"unknown allocation role: {sorted(unknown_roles)}")
    fit_total = int(allocation_role_row_counts.get("c0_fit", 0))
    iteration_total = int(allocation_role_row_counts.get("c0_iteration", 0))
    if fit_total <= 0 or iteration_total <= 0:
        raise ValueError("c0_fit and c0_iteration row totals must be positive")

    role_by_repo = {
        normalize_repository(entry.repository): entry.role for entry in allocation_entries
    }
    hard_crossing_edges = 0
    conditional_crossing_edges = 0
    for edge in resolved_edges:
        if not edge.connecting:
            continue
        left_role = role_by_repo.get(normalize_repository(edge.left_repository))
        right_role = role_by_repo.get(normalize_repository(edge.right_repository))
        if left_role is None or right_role is None or left_role == right_role:
            continue
        if edge.edge_type in HARD_CONNECTING_EDGE_TYPES:
            hard_crossing_edges += 1
        elif edge.edge_type in CONDITIONAL_CONNECTING_EDGE_TYPES:
            conditional_crossing_edges += 1

    role_pair_impacts = list(analysis_record["role_pair_impacts"])
    fit_rows = sum(
        int(item["aggregate_row_count"])
        for item in role_pair_impacts
        if "c0_fit" in item["role_pair"]
    )
    iteration_rows = sum(
        int(item["aggregate_row_count"])
        for item in role_pair_impacts
        if "c0_iteration" in item["role_pair"]
    )
    return {
        "affected_role_pairs": role_pair_impacts,
        "largest_crossing_component_repository_count": analysis_record[
            "largest_crossing_component_repository_count"
        ],
        "affected_c0_fit_row_fraction": fit_rows / fit_total,
        "affected_c0_iteration_row_fraction": iteration_rows / iteration_total,
        "hard_cross_role_edge_count": hard_crossing_edges,
        "conditional_cross_role_edge_count": conditional_crossing_edges,
        "family_disjoint_allocation_feasibility": {"status": "NOT_ASSESSED"},
        "materiality_threshold_applied": False,
        "material_contamination_established": False,
        "reallocation_required": None,
    }


@dataclass(frozen=True)
class FamilyReviewPacket:
    """Deterministic packet for human review of bounded family facts only."""

    record: Mapping[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


def family_review_packet_from_record(record: Mapping[str, Any]) -> FamilyReviewPacket:
    """Reconstruct a review packet and require its committed non-conclusion shape."""
    data = dict(record)
    if data.get("schema_id") != FAMILY_REVIEW_PACKET_SCHEMA_ID:
        raise ValueError("unsupported family review packet schema")
    if data.get("publication_scope") != PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY:
        raise ValueError("family review packet publication scope mismatch")
    if data.get("packet_contains") != "BOUNDED_FAMILY_GRAPH_FACTS_ONLY":
        raise ValueError("family review packet scope is not bounded")
    not_concluded = tuple(data.get("not_concluded", ()))
    for required in NOT_CONCLUDED:
        if required not in not_concluded:
            raise ValueError(f"family review packet missing non-conclusion: {required}")
    firewall = data.get("firewall_declarations", {})
    for key in (
        "c0_selection_row_content_accessed",
        "c1_row_content_accessed",
        "hidden_row_content_accessed",
    ):
        if firewall.get(key) is not False:
            raise ValueError(f"family review packet firewall declaration is not false: {key}")
    return FamilyReviewPacket(record=data)


def family_review_packet_commitment(packet: FamilyReviewPacket) -> str:
    return sha256_text(canonical_json(packet.as_record()))


def _validate_expected_definition(plan: FamilyWorkflowPlan) -> None:
    if plan.definition.name != FAMILY_GRAPH_WORKFLOW_NAME:
        raise ValueError("unexpected family workflow name")
    if plan.definition.version != FAMILY_GRAPH_WORKFLOW_VERSION:
        raise ValueError("unexpected family workflow version")
    names = tuple(step.name for step in plan.definition.steps)
    versions = tuple(step.version for step in plan.definition.steps)
    if names != _EXPECTED_STEP_NAMES:
        raise ValueError("unexpected family workflow step order")
    if versions != ("1",) * len(_EXPECTED_STEP_NAMES):
        raise ValueError("unexpected family workflow step version")


def build_family_review_packet(
    *,
    plan: FamilyWorkflowPlan,
    result: WorkflowRunResult,
) -> FamilyReviewPacket:
    """Validate a completed Stage 2E run and return a deterministic review packet."""
    _validate_expected_definition(plan)
    validate_completed_run(plan.definition, plan.context, result)
    reject_canonical_path(plan.context.work_dir, repo_root=plan.context.repo_root, label="work_dir")
    reject_canonical_path(plan.store_spec.path, repo_root=plan.context.repo_root, label="store")

    computed_source_identity = compute_family_workflow_source_identity(plan.context.repo_root)
    if plan.context.identity["workflow_source_identity"] != computed_source_identity:
        raise ValueError("workflow source identity mismatch")

    by_name = _record_by_name(result)
    protocol_sha = plan.context.identity["family_protocol_sha256"]
    with FamilyGraphCache(plan.store_spec.path, identity=plan.store_spec.identity) as cache:
        if cache.identity.family_protocol_sha256 != protocol_sha:
            raise ValueError("store protocol identity mismatch")
        if cache.identity.allocation_manifest_sha256 != plan.context.identity[
            "allocation_manifest_sha256"
        ]:
            raise ValueError("store allocation identity mismatch")
        allocation_entries = cache.list_allocation_repositories()
        edges = cache.list_resolved_edges()
        candidates = cache.list_evidence_candidates()
        candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
        dispositions_by_id = {}
        for candidate in candidates:
            disposition = cache.get_final_disposition_for_candidate(candidate.candidate_id)
            if disposition is not None:
                dispositions_by_id[disposition.disposition_id] = disposition
        source_registry = cache.get_source_registry()
        components = cache.get_component_memberships()
        phases = _phase_commitments(cache)

    edge_sha = edge_commitment(
        edges,
        protocol_sha256=protocol_sha,
        candidates=candidates_by_id,
        dispositions=dispositions_by_id,
        source_records=source_registry,
    )
    if edge_sha != by_name["resolve_candidates"].result.output["edge_commitment"]:
        raise ValueError("resolved edge commitment mismatch")
    if phases.get("resolved_edges") != edge_sha:
        raise ValueError("resolved edge phase mismatch")

    component_sha = component_commitment(components, protocol_sha256=protocol_sha)
    if component_sha != by_name["build_family_components"].result.output["component_commitment"]:
        raise ValueError("component commitment mismatch")
    if phases.get("family_components") != component_sha:
        raise ValueError("component phase mismatch")

    analysis_record = by_name["analyse_role_crossings"].result.output["analysis"]
    analysis_commitment = by_name["analyse_role_crossings"].result.output["analysis_commitment"]
    if phases.get("role_crossing_analysis") != analysis_commitment:
        raise ValueError("role analysis phase mismatch")
    if sha256_text(
        canonical_json(
            {
                "schema_id": "relate-family-role-crossing-analysis-v1",
                "family_protocol_sha256": protocol_sha,
                "analysis": analysis_record,
            }
        )
    ) != analysis_commitment:
        raise ValueError("role analysis commitment mismatch")

    readiness = by_name["assess_graph_readiness"].result.output
    if phases.get("graph_readiness") != readiness["readiness_commitment"]:
        raise ValueError("readiness phase mismatch")
    outcome = by_name["determine_family_outcome"].result.output["outcome"]
    recomputed = dict(readiness["completeness"])
    recomputed["cross_role_connecting_components"] = analysis_record[
        "cross_role_connecting_components"
    ]
    recomputed["hard_or_exact_fit_iteration_crossing_observed"] = analysis_record[
        "hard_or_exact_fit_iteration_crossing_observed"
    ]
    if family_graph_outcome(recomputed) != outcome:
        raise ValueError("bounded outcome does not agree with role analysis")
    outcome_commitment = bounded_family_outcome_commitment(outcome, protocol_sha256=protocol_sha)
    if (
        outcome_commitment
        != by_name["determine_family_outcome"].result.output["outcome_commitment"]
    ):
        raise ValueError("bounded outcome commitment mismatch")
    if phases.get("family_outcome") != outcome_commitment:
        raise ValueError("family outcome phase mismatch")

    allocation_output = by_name["register_allocation"].result.output
    materiality_inputs = materiality_inputs_from_records(
        analysis_record=analysis_record,
        allocation_role_row_counts=allocation_output["role_row_counts"],
        allocation_entries=allocation_entries,
        resolved_edges=edges,
    )

    record = {
        "schema_id": FAMILY_REVIEW_PACKET_SCHEMA_ID,
        "family_protocol_sha256": protocol_sha,
        "workflow": {
            "name": plan.context.workflow_name,
            "version": plan.context.workflow_version,
            "run_id": plan.context.run_id,
            "run_identity_commitment": plan.context.identity["family_workflow_run_identity"],
            "source_identity": plan.context.identity["workflow_source_identity"],
            "allowed_roles": sorted(plan.context.allowed_roles),
        },
        "identities": {
            "allocation_manifest_sha256": plan.context.identity["allocation_manifest_sha256"],
            "allocation_context_sha256": plan.context.identity["allocation_context_sha256"],
            "allocation_repository_commitment_sha256": plan.context.identity[
                "allocation_repository_commitment_sha256"
            ],
            "evidence_bundle_commitment": plan.context.inputs["evidence_bundle_commitment"],
            "resolved_edge_commitment": edge_sha,
            "component_commitment": component_sha,
            "graph_readiness_commitment": readiness["readiness_commitment"],
            "role_crossing_analysis_commitment": analysis_commitment,
            "bounded_outcome_commitment": outcome_commitment,
        },
        "bounded_family_outcome": outcome,
        "bounded_role_crossing_analysis": analysis_record,
        "materiality_inputs": materiality_inputs,
        "firewall_declarations": {
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
            "hidden_row_content_accessed": False,
        },
        "publication_scope": PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY,
        "packet_contains": "BOUNDED_FAMILY_GRAPH_FACTS_ONLY",
        "not_concluded": list(NOT_CONCLUDED),
        "downstream_decisions": {
            "material_contamination": "NOT_DETERMINED",
            "materiality_threshold": "NOT_APPLIED",
            "reallocation_required": "NOT_AUTHORIZED",
            "d2_authorization": "NOT_AUTHORIZED",
        },
    }
    return FamilyReviewPacket(record=record)

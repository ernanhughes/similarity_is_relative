"""Explicit family-graph workflow steps.

Each step is a small ``relate.workflows.WorkflowStep`` implementation: given
the immutable run context and prior results, it performs one durable
operation and returns a ``StepResult``. No step calls
``store.connection.execute(...)`` directly — every durable operation goes
through a public ``FamilyGraphCache`` method. Every durable step opens its
own ``FamilyGraphCache`` using the same cache path and identity rather than
sharing a live connection through workflow context.

A frozen-input or firewall violation (``VerifyFamilyInputsStep``) is an
invariant/security failure: it raises, and the runner turns that into
``WorkflowExecutionError``. Missing metadata or unresolved required review
(``AssessGraphReadinessStep``) is a scientifically incomplete but valid
state: it returns ``StepResult.blocked(...)``.

This module must not import from relate.experiments or relate.cli.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.analysis import analyse_role_crossings
from relate.family.commitments import component_commitment, edge_commitment
from relate.family.edges import resolve_evidence_candidate
from relate.family.graph import build_components
from relate.family.models import EvidenceCandidate, EvidenceEdge, ManualReviewDisposition
from relate.family.outcome import family_graph_outcome, graph_completeness
from relate.family.store import FamilyGraphCache, FamilyGraphCacheIdentity
from relate.family.verification import (
    FamilyProtocolExpectedIdentity,
    FamilyProtocolInputPaths,
    verify_family_protocol_inputs,
)
from relate.family.workflow.models import FamilyEvidenceBundle, evidence_bundle_commitment
from relate.workflows import StepResult, WorkflowContext

_COMPLETE_OUTCOMES = frozenset(
    {
        "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS",
        "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED",
    }
)


def _resolved_edges_and_dispositions(
    cache: FamilyGraphCache,
) -> tuple[
    tuple[EvidenceCandidate, ...],
    dict[str, EvidenceCandidate],
    dict[str, ManualReviewDisposition],
]:
    candidates = cache.list_evidence_candidates()
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    dispositions_by_id: dict[str, ManualReviewDisposition] = {}
    for candidate in candidates:
        disposition = cache.get_final_disposition_for_candidate(candidate.candidate_id)
        if disposition is not None:
            dispositions_by_id[disposition.disposition_id] = disposition
    return candidates, candidates_by_id, dispositions_by_id


class VerifyFamilyInputsStep:
    """Verify frozen protocol inputs and the protocol-level firewall.

    A hash or firewall mismatch raises (fail-closed); it is never blocked.
    """

    name = "verify_family_inputs"
    version = "1"

    def __init__(
        self,
        *,
        input_paths: FamilyProtocolInputPaths,
        expected_identity: FamilyProtocolExpectedIdentity,
    ) -> None:
        self._input_paths = input_paths
        self._expected_identity = expected_identity

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        verified = verify_family_protocol_inputs(self._input_paths, self._expected_identity)
        declared = {
            "allocation_manifest_sha256": verified.allocation_manifest_sha256,
            "allocation_context_sha256": verified.allocation_context_sha256,
            "d1_audit_result_sha256": verified.d1_result_sha256,
            "d1_1_classification_sha256": verified.d1_1_classification_sha256,
        }
        for key, value in declared.items():
            if context.identity.get(key) != value:
                raise ValueError(f"verified identity does not match workflow context: {key}")
        payload: dict[str, Any] = {
            "allocation_manifest_sha256": verified.allocation_manifest_sha256,
            "allocation_context_sha256": verified.allocation_context_sha256,
            "allocation_repository_commitment_sha256": (
                verified.allocation_repository_commitment_sha256
            ),
            "d1_audit_result_sha256": verified.d1_result_sha256,
            "d1_1_classification_sha256": verified.d1_1_classification_sha256,
            "d1_1_overall_outcome": verified.d1_1_overall_outcome,
            "d1_1_family_identity_rule_status": verified.d1_1_family_identity_rule_status,
        }
        return StepResult.completed(output=payload, commitment_payload=payload)


class RegisterAllocationStep:
    """Register the (published, non-hidden) allocation manifest and confirm
    the frozen repository commitment. Never inspects row contents."""

    name = "register_allocation"
    version = "1"

    def __init__(
        self,
        *,
        store_path: Path,
        cache_identity: FamilyGraphCacheIdentity,
        allocation_manifest_path: Path,
    ) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity
        self._allocation_manifest_path = allocation_manifest_path

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            commitment = cache.put_canonical_allocation_manifest(self._allocation_manifest_path)
            entries = cache.list_allocation_repositories()
        role_repository_counts: dict[str, int] = {}
        role_row_counts: dict[str, int] = {}
        for entry in entries:
            role_repository_counts[entry.role] = role_repository_counts.get(entry.role, 0) + 1
            role_row_counts[entry.role] = role_row_counts.get(entry.role, 0) + entry.row_count
        payload: dict[str, Any] = {
            "allocation_repository_commitment_sha256": commitment,
            "repository_count": len(entries),
            "role_repository_counts": role_repository_counts,
            "role_row_counts": role_row_counts,
        }
        return StepResult.completed(output=payload, commitment_payload=payload)


class RegisterPreparedEvidenceStep:
    """Register prepared source records, candidates, and dispositions, then
    write a family phase commitment for the prepared evidence bundle.

    Does not resolve candidates into edges yet.
    """

    name = "register_prepared_evidence"
    version = "1"

    def __init__(
        self,
        *,
        store_path: Path,
        cache_identity: FamilyGraphCacheIdentity,
        evidence_bundle: FamilyEvidenceBundle,
    ) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity
        self._evidence_bundle = evidence_bundle

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        bundle_commitment = evidence_bundle_commitment(self._evidence_bundle)
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            for record in self._evidence_bundle.source_records:
                cache.put_source_record(record)
            for candidate in self._evidence_bundle.candidates:
                cache.put_evidence_candidate(candidate)
            for disposition in self._evidence_bundle.dispositions:
                cache.put_manual_review_disposition(disposition)
            cache.put_phase_commitment(
                "prepared_evidence_bundle",
                status="COMPLETE",
                commitment_sha256=bundle_commitment,
                metadata={
                    "source_record_count": len(self._evidence_bundle.source_records),
                    "candidate_count": len(self._evidence_bundle.candidates),
                    "disposition_count": len(self._evidence_bundle.dispositions),
                    "incomplete_metadata_records": (
                        self._evidence_bundle.incomplete_metadata_records
                    ),
                },
            )
        payload: dict[str, Any] = {
            "evidence_bundle_commitment": bundle_commitment,
            "source_record_count": len(self._evidence_bundle.source_records),
            "candidate_count": len(self._evidence_bundle.candidates),
            "disposition_count": len(self._evidence_bundle.dispositions),
        }
        return StepResult.completed(output=payload, commitment_payload=payload)


class ResolveCandidatesStep:
    """Resolve every registered candidate against its final disposition (if
    any), store the resulting edges, and produce the edge commitment.

    Unresolved review-required candidates produce unresolved, nonconnecting
    edges exactly as ``relate.family.edges.resolve_evidence_candidate``
    already specifies. They are never silently approved.
    """

    name = "resolve_candidates"
    version = "1"

    def __init__(
        self, *, store_path: Path, cache_identity: FamilyGraphCacheIdentity, protocol_sha256: str
    ) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity
        self._protocol_sha256 = protocol_sha256

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            candidates = cache.list_evidence_candidates()
            candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
            dispositions_by_id: dict[str, ManualReviewDisposition] = {}
            review_status_counts: dict[str, int] = {}
            edges: list[EvidenceEdge] = []
            for candidate in candidates:
                disposition = cache.get_final_disposition_for_candidate(candidate.candidate_id)
                if disposition is not None:
                    dispositions_by_id[disposition.disposition_id] = disposition
                edge = resolve_evidence_candidate(
                    candidate, disposition, protocol_sha256=self._protocol_sha256
                )
                cache.put_resolved_edge(edge)
                edges.append(edge)
                review_status_counts[edge.review_status] = (
                    review_status_counts.get(edge.review_status, 0) + 1
                )
            source_registry = cache.get_source_registry()
            commitment = edge_commitment(
                edges,
                protocol_sha256=self._protocol_sha256,
                candidates=candidates_by_id,
                dispositions=dispositions_by_id,
                source_records=source_registry,
            )
        payload: dict[str, Any] = {
            "edge_commitment": commitment,
            "edge_count": len(edges),
            "review_status_counts": review_status_counts,
        }
        return StepResult.completed(output=payload, commitment_payload=payload)


class AssessGraphReadinessStep:
    """Determine whether the graph is ready to build: complete, or blocked
    on missing metadata / unresolved required review.

    Does not build components after a blocked readiness result — the
    runner stops the workflow before any later step executes.
    """

    name = "assess_graph_readiness"
    version = "1"

    def __init__(
        self,
        *,
        store_path: Path,
        cache_identity: FamilyGraphCacheIdentity,
        protocol_sha256: str,
        incomplete_metadata_records: int,
    ) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity
        self._protocol_sha256 = protocol_sha256
        self._incomplete_metadata_records = incomplete_metadata_records

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            edges = cache.list_resolved_edges()
            _candidates, candidates_by_id, dispositions_by_id = _resolved_edges_and_dispositions(
                cache
            )
            source_registry = cache.get_source_registry()
            completeness = graph_completeness(
                edges,
                protocol_sha256=self._protocol_sha256,
                candidates=candidates_by_id,
                dispositions=dispositions_by_id,
                source_records=source_registry,
                incomplete_metadata_records=self._incomplete_metadata_records,
            )
        outcome = family_graph_outcome(completeness)
        payload: dict[str, Any] = {"completeness": completeness, "outcome": outcome}
        if completeness["incomplete_metadata_records"]:
            return StepResult.blocked(
                "FAMILY_GRAPH_INCOMPLETE_METADATA", output=payload, commitment_payload=payload
            )
        if completeness["unresolved_connecting_candidate_edges"]:
            return StepResult.blocked(
                "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED",
                output=payload,
                commitment_payload=payload,
            )
        return StepResult.completed(output=payload, commitment_payload=payload)


class BuildFamilyComponentsStep:
    """Build connected components from allocation entries and resolved
    edges, persist the complete membership snapshot, and commit it.

    Every allocation repository appears exactly once.
    """

    name = "build_family_components"
    version = "1"

    def __init__(
        self, *, store_path: Path, cache_identity: FamilyGraphCacheIdentity, protocol_sha256: str
    ) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity
        self._protocol_sha256 = protocol_sha256

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            allocation_entries = cache.list_allocation_repositories()
            edges = cache.list_resolved_edges()
            _candidates, candidates_by_id, dispositions_by_id = _resolved_edges_and_dispositions(
                cache
            )
            source_registry = cache.get_source_registry()
            repositories = [entry.repository for entry in allocation_entries]
            components = build_components(
                repositories,
                edges,
                protocol_sha256=self._protocol_sha256,
                candidates=candidates_by_id,
                dispositions=dispositions_by_id,
                source_records=source_registry,
            )
            cache.put_component_memberships(components)
            commitment = component_commitment(components, protocol_sha256=self._protocol_sha256)
            cache.put_phase_commitment(
                "family_components",
                status="COMPLETE",
                commitment_sha256=commitment,
                metadata={"component_count": len(components)},
            )
        payload: dict[str, Any] = {
            "component_commitment": commitment,
            "component_count": len(components),
        }
        return StepResult.completed(output=payload, commitment_payload=payload)


class AnalyseRoleCrossingsStep:
    """Load allocation, components, and resolved edges through public store
    APIs, run the bounded cross-role analysis, and persist a phase
    commitment. Never calculates materiality."""

    name = "analyse_role_crossings"
    version = "1"

    def __init__(self, *, store_path: Path, cache_identity: FamilyGraphCacheIdentity) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            allocation_entries = cache.list_allocation_repositories()
            components = cache.get_component_memberships()
            edges = cache.list_resolved_edges()
            analysis = analyse_role_crossings(allocation_entries, components, edges)
            record = analysis.as_record()
            commitment = sha256_text(canonical_json(record))
            cache.put_phase_commitment(
                "role_crossing_analysis",
                status="COMPLETE",
                commitment_sha256=commitment,
                metadata={
                    "cross_role_connecting_components": analysis.cross_role_connecting_components
                },
            )
        payload: dict[str, Any] = {"analysis": record, "analysis_commitment": commitment}
        return StepResult.completed(output=payload, commitment_payload=payload)


class DetermineFamilyOutcomeStep:
    """Combine graph-completeness and crossing summaries into the frozen
    bounded family outcome. Does not publish it, and does not authorize
    reallocation or D2."""

    name = "determine_family_outcome"
    version = "1"

    def __init__(self, *, store_path: Path, cache_identity: FamilyGraphCacheIdentity) -> None:
        self._store_path = store_path
        self._cache_identity = cache_identity

    def execute(
        self, context: WorkflowContext, previous_results: Mapping[str, StepResult]
    ) -> StepResult:
        readiness = previous_results["assess_graph_readiness"]
        crossings = previous_results["analyse_role_crossings"]
        completeness = dict(readiness.output["completeness"])
        analysis_record = crossings.output["analysis"]
        completeness["cross_role_connecting_components"] = analysis_record[
            "cross_role_connecting_components"
        ]
        completeness["hard_or_exact_fit_iteration_crossing_observed"] = analysis_record[
            "hard_or_exact_fit_iteration_crossing_observed"
        ]
        outcome = family_graph_outcome(completeness)
        if outcome["family_graph_outcome"] not in _COMPLETE_OUTCOMES:
            raise ValueError(
                "unexpected incomplete outcome reached DetermineFamilyOutcomeStep: "
                f"{outcome['family_graph_outcome']}"
            )
        outcome_commitment = sha256_text(canonical_json(outcome))
        with FamilyGraphCache(self._store_path, identity=self._cache_identity) as cache:
            cache.put_phase_commitment(
                "family_outcome",
                status="COMPLETE",
                commitment_sha256=outcome_commitment,
                metadata={"family_graph_outcome": outcome["family_graph_outcome"]},
            )
        payload: dict[str, Any] = {"outcome": outcome, "outcome_commitment": outcome_commitment}
        return StepResult.completed(output=payload, commitment_payload=payload)

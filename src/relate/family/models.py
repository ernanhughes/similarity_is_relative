"""Pure immutable dataclasses for the family-connected allocation domain.

No database access, CLI parsing, file publication or workflow orchestration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

# Schema ID embedded in every serialized EvidenceEdge record.
EDGE_SCHEMA_ID: Final = "option-c0-family-evidence-edge-v1"


@dataclass(frozen=True)
class EdgeRule:
    edge_type: str
    category: str
    connecting_policy: str
    required_fields: Mapping[str, str]
    allowed_values: Mapping[str, tuple[Any, ...]]
    forbidden_fields: tuple[str, ...]
    evidence_source_requirements: tuple[str, ...]
    review_requirement: str
    confidence_category: str
    reason_template: str
    negative_conditions: tuple[str, ...]

    @property
    def human_review_required(self) -> bool:
        return self.review_requirement in {"APPROVED_REQUIRED", "UNRESOLVED_REVIEW"}

    @property
    def is_connecting_candidate(self) -> bool:
        return self.category in {"hard_connecting", "conditional_connecting"}


@dataclass(frozen=True)
class AllocationEntry:
    repository: str
    role: str
    row_count: int


@dataclass(frozen=True)
class ManualReviewDisposition:
    disposition_id: str
    edge_candidate_id: str
    protocol_sha256: str
    evidence_commitment: str
    disposition: str
    reviewer_identity: str
    review_timestamp: str
    bounded_reason: str

    def as_record(self) -> dict[str, Any]:
        return {
            "disposition_id": self.disposition_id,
            "edge_candidate_id": self.edge_candidate_id,
            "protocol_sha256": self.protocol_sha256,
            "evidence_commitment": self.evidence_commitment,
            "disposition": self.disposition,
            "reviewer_identity": self.reviewer_identity,
            "review_timestamp": self.review_timestamp,
            "bounded_reason": self.bounded_reason,
        }


@dataclass(frozen=True)
class EvidenceCandidate:
    candidate_id: str
    left_repository: str
    right_repository: str
    edge_type: str
    rule_version: str
    evidence_sources: Mapping[str, str]
    evidence_source_bundle_sha256: str
    evidence_payload: Mapping[str, Any]
    evidence_payload_hash: str
    evidence_commitment: str
    candidate_status: str = "UNRESOLVED"

    def as_record(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "left_repository": self.left_repository,
            "right_repository": self.right_repository,
            "edge_type": self.edge_type,
            "rule_version": self.rule_version,
            "evidence_sources": dict(sorted(self.evidence_sources.items())),
            "evidence_source_bundle_sha256": self.evidence_source_bundle_sha256,
            "evidence_payload_hash": self.evidence_payload_hash,
            "evidence_commitment": self.evidence_commitment,
            "candidate_status": self.candidate_status,
            "evidence_payload": dict(self.evidence_payload),
        }


@dataclass(frozen=True)
class EvidenceEdge:
    edge_id: str
    candidate_id: str
    disposition_id: str | None
    left_repository: str
    right_repository: str
    edge_type: str
    connecting: bool
    evidence_sources: Mapping[str, str]
    evidence_source_bundle_sha256: str
    evidence_payload_hash: str
    evidence_commitment: str
    rule_version: str
    confidence_category: str
    human_review_required: bool
    review_status: str
    reason: str
    evidence_payload: Mapping[str, Any]
    review_disposition_identity: str | None = None

    def as_record(self, *, include_edge_id: bool = True) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_id": EDGE_SCHEMA_ID,
            "candidate_id": self.candidate_id,
            "disposition_id": self.disposition_id,
            "left_repository": self.left_repository,
            "right_repository": self.right_repository,
            "edge_type": self.edge_type,
            "connecting": self.connecting,
            "evidence_sources": dict(sorted(self.evidence_sources.items())),
            "evidence_source_bundle_sha256": self.evidence_source_bundle_sha256,
            "evidence_payload_hash": self.evidence_payload_hash,
            "evidence_commitment": self.evidence_commitment,
            "rule_version": self.rule_version,
            "confidence_category": self.confidence_category,
            "human_review_required": self.human_review_required,
            "review_status": self.review_status,
            "review_disposition_identity": self.review_disposition_identity,
            "reason": self.reason,
            "evidence_payload": dict(self.evidence_payload),
        }
        if include_edge_id:
            record["edge_id"] = self.edge_id
        return record


@dataclass(frozen=True)
class SourceEvidenceRecord:
    source_type: str
    source_identity: str
    payload: Mapping[str, Any]
    provenance: Mapping[str, Any]
    status: str
    record_sha256: str

    def as_record(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_identity": self.source_identity,
            "payload": dict(self.payload),
            "provenance": dict(self.provenance),
            "status": self.status,
            "record_sha256": self.record_sha256,
        }

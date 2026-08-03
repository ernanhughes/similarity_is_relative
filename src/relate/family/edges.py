"""Pure edge, candidate and review construction and validation.

No database access, CLI parsing, file publication or workflow orchestration.

Note on make_evidence_edge
--------------------------
``make_evidence_edge`` accepts ``protocol_sha256`` as an explicit keyword
argument.  The historical protocol module wraps it and supplies the canonical
protocol SHA via ``protocol_contract()["protocol_sha256"]``.  This keeps the
clean domain module free from any dependency on the historical experiment module.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.models import (
    EDGE_SCHEMA_ID,
    EvidenceCandidate,
    EvidenceEdge,
    ManualReviewDisposition,
    SourceEvidenceRecord,
)
from relate.family.repositories import normalize_repository, repository_owner
from relate.family.rules import EDGE_RULES
from relate.family.sources import (
    HASH_PATTERN,
    parse_timestamp,
    payload_hash,
    source_bundle_commitment,
    validate_evidence_source_bundle,
    validate_payload_firewall,
    validate_source_identity,
    validate_source_registry,
)

# Default rule version for new evidence candidates.
PROTOCOL_VERSION: Final = "family-protocol-v1"

# Valid manual review outcomes.
REVIEW_DISPOSITIONS: Final = ("APPROVED", "REJECTED")


def validate_reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        raise ValueError("reason must be nonempty bounded text")
    return value.strip()


def _validate_field_type(field: str, value: Any, expected: str) -> None:
    if expected == "true":
        if value is not True:
            raise ValueError(f"{field} must be exactly true")
    elif expected == "str":
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field} must be a nonempty string")
    elif expected == "repository":
        normalize_repository(value)
    elif expected == "sha256":
        if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
            raise ValueError(f"{field} must be a SHA-256")
    elif expected == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} must be an integer")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{field} must be numeric")
    elif expected == "visible_role":
        if value not in {"c0_fit", "c0_iteration"}:
            raise ValueError(f"{field} must be a visible role")
    else:
        raise ValueError(f"unsupported field type: {expected}")


def derive_edge_id(record: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(dict(record)))


def validate_rule_payload(rule: Any, payload: Mapping[str, Any]) -> None:
    validate_payload_firewall(payload)
    allowed_fields = set(rule.required_fields) | set(rule.allowed_values)
    unexpected = set(payload) - allowed_fields
    if unexpected:
        raise ValueError(f"unexpected evidence payload fields: {sorted(unexpected)}")
    for field in rule.forbidden_fields:
        if field in payload:
            raise ValueError(f"forbidden evidence payload field: {field}")
    for field, expected_type in rule.required_fields.items():
        if field not in payload:
            raise ValueError(f"missing evidence payload field: {field}")
        _validate_field_type(field, payload[field], expected_type)
    for field, allowed in rule.allowed_values.items():
        if payload.get(field) not in allowed:
            raise ValueError(f"{field} has value outside frozen allowed set")


def validate_rule_semantics(
    rule: Any,
    left: str,
    right: str,
    payload: Mapping[str, Any],
) -> None:
    if rule.edge_type == "DECLARED_GITHUB_FORK":
        child = normalize_repository(str(payload["child_full_name"]))
        parent = normalize_repository(str(payload["parent_or_source_full_name"]))
        if {child, parent} != {left, right} or child == parent:
            raise ValueError("fork endpoint names must match edge endpoints")
        if payload["left_repository_id"] == payload["right_repository_id"]:
            raise ValueError("fork repository IDs must be distinct")
    elif rule.edge_type == "VERIFIED_REPOSITORY_SUCCESSION":
        predecessor = normalize_repository(str(payload["predecessor_repository"]))
        successor = normalize_repository(str(payload["successor_repository"]))
        if {predecessor, successor} != {left, right}:
            raise ValueError("succession endpoints must match edge endpoints")
        if payload["direction"] != "predecessor_to_successor":
            raise ValueError("succession direction must be frozen")
    elif rule.edge_type == "SAME_OWNER_PROXY":
        owner = repository_owner(left)
        if repository_owner(right) != owner:
            raise ValueError("same-owner evidence must be derived from endpoints")
        if payload["owner"] != owner:
            raise ValueError("same-owner payload owner does not match endpoints")
    elif rule.edge_type == "EXACT_AST_WITH_CORROBORATING_PROVENANCE":
        if payload["left_stable_key"] == payload["right_stable_key"]:
            raise ValueError("exact-AST stable keys must be distinct")


def validate_source_payload_binding(
    rule: Any,
    evidence_sources: Mapping[str, str],
    payload: Mapping[str, Any],
) -> None:
    public_snapshot = evidence_sources.get("public_metadata_snapshot")
    d1_visible = evidence_sources.get("d1_visible_cache")
    if rule.edge_type == "DECLARED_GITHUB_FORK":
        if payload["metadata_snapshot_identity"] != public_snapshot:
            raise ValueError("fork snapshot identity must match the public metadata source")
        if evidence_sources.get("github_rest") != public_snapshot:
            raise ValueError("fork GitHub REST identity must be committed into metadata snapshot")
    elif rule.edge_type == "VERIFIED_REPOSITORY_SUCCESSION":
        if payload["record_snapshot_hash"] != public_snapshot:
            raise ValueError("succession snapshot identity must match the public metadata source")
    elif rule.edge_type == "VERIFIED_SHARED_PACKAGE_LINEAGE":
        if payload["evidence_snapshot_hash"] != public_snapshot:
            raise ValueError("lineage snapshot identity must match the public metadata source")
    elif d1_visible is not None:
        if "d1_visible_evidence_identity" in payload:
            if payload["d1_visible_evidence_identity"] != d1_visible:
                raise ValueError("D1 identity must match the source bundle")
            return
        for field in (
            "matching_content_sha256",
            "left_scope_identity",
            "right_scope_identity",
            "code_sha256",
            "d1_visible_evidence_identity",
        ):
            if field in payload and payload[field] == d1_visible:
                return
        if rule.edge_type in {
            "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
            "EXACT_FUNCTION_SOURCE_MATCH",
            "SIMHASH_NEAR_FUNCTION",
        }:
            raise ValueError("D1-visible evidence must bind a stable commitment to its source")


def make_evidence_candidate(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
    evidence_sources: Mapping[str, str],
    evidence_payload: Mapping[str, Any],
    rule_version: str = PROTOCOL_VERSION,
) -> EvidenceCandidate:
    left = normalize_repository(left_repository)
    right = normalize_repository(right_repository)
    if left == right:
        raise ValueError("family evidence candidate must connect two distinct repositories")
    if left > right:
        left, right = right, left
    if edge_type not in EDGE_RULES:
        raise ValueError(f"unknown family evidence edge type: {edge_type}")
    rule = EDGE_RULES[edge_type]
    if rule_version != PROTOCOL_VERSION:
        raise ValueError("wrong family edge rule version")
    bundle = validate_evidence_source_bundle(rule, evidence_sources)
    validate_rule_payload(rule, evidence_payload)
    validate_rule_semantics(rule, left, right, evidence_payload)
    validate_source_payload_binding(rule, bundle, evidence_payload)
    evidence_payload_sha = payload_hash(evidence_payload)
    bundle_sha = source_bundle_commitment(bundle)
    base = {
        "left_repository": left,
        "right_repository": right,
        "edge_type": edge_type,
        "rule_version": rule_version,
        "evidence_source_bundle_sha256": bundle_sha,
        "evidence_payload_hash": evidence_payload_sha,
    }
    evidence_commitment = sha256_text(canonical_json(base))
    candidate_id = sha256_text(
        canonical_json(
            {**base, "evidence_commitment": evidence_commitment, "evidence_sources": bundle}
        )
    )
    return EvidenceCandidate(
        candidate_id=candidate_id,
        left_repository=left,
        right_repository=right,
        edge_type=edge_type,
        rule_version=rule_version,
        evidence_sources=bundle,
        evidence_source_bundle_sha256=bundle_sha,
        evidence_payload=evidence_payload,
        evidence_payload_hash=evidence_payload_sha,
        evidence_commitment=evidence_commitment,
    )


def validate_evidence_candidate(candidate: EvidenceCandidate) -> None:
    regenerated = make_evidence_candidate(
        candidate.left_repository,
        candidate.right_repository,
        candidate.edge_type,
        evidence_sources=candidate.evidence_sources,
        evidence_payload=candidate.evidence_payload,
        rule_version=candidate.rule_version,
    )
    for field in (
        "candidate_id",
        "evidence_source_bundle_sha256",
        "evidence_payload_hash",
        "evidence_commitment",
    ):
        if getattr(candidate, field) != getattr(regenerated, field):
            raise ValueError(f"tampered evidence candidate field: {field}")
    if candidate.candidate_status != "UNRESOLVED":
        raise ValueError("evidence candidate status must be UNRESOLVED")


def evidence_candidate_from_record(record: Mapping[str, Any]) -> EvidenceCandidate:
    return EvidenceCandidate(
        candidate_id=str(record["candidate_id"]),
        left_repository=str(record["left_repository"]),
        right_repository=str(record["right_repository"]),
        edge_type=str(record["edge_type"]),
        rule_version=str(record["rule_version"]),
        evidence_sources=dict(record["evidence_sources"]),
        evidence_source_bundle_sha256=str(record["evidence_source_bundle_sha256"]),
        evidence_payload=dict(record["evidence_payload"]),
        evidence_payload_hash=str(record["evidence_payload_hash"]),
        evidence_commitment=str(record["evidence_commitment"]),
        candidate_status=str(record["candidate_status"]),
    )


def make_manual_review_disposition(
    *,
    edge_candidate_id: str,
    protocol_sha256: str,
    evidence_commitment: str,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> ManualReviewDisposition:
    if disposition not in REVIEW_DISPOSITIONS:
        raise ValueError("invalid manual review disposition")
    if not HASH_PATTERN.fullmatch(protocol_sha256):
        raise ValueError("manual disposition protocol SHA-256 is invalid")
    if not HASH_PATTERN.fullmatch(evidence_commitment):
        raise ValueError("manual disposition evidence commitment is invalid")
    parse_timestamp(review_timestamp)
    record = {
        "edge_candidate_id": edge_candidate_id,
        "protocol_sha256": protocol_sha256,
        "evidence_commitment": evidence_commitment,
        "disposition": disposition,
        "reviewer_identity": validate_source_identity(reviewer_identity),
        "review_timestamp": review_timestamp,
        "bounded_reason": validate_reason(bounded_reason),
    }
    return ManualReviewDisposition(disposition_id=derive_edge_id(record), **record)


def validate_manual_review_disposition(
    disposition: ManualReviewDisposition,
    candidate: EvidenceCandidate,
    *,
    protocol_sha256: str,
) -> None:
    if disposition.edge_candidate_id != candidate.candidate_id:
        raise ValueError("manual disposition belongs to another candidate")
    if disposition.protocol_sha256 != protocol_sha256:
        raise ValueError("manual disposition protocol identity is stale")
    if disposition.evidence_commitment != candidate.evidence_commitment:
        raise ValueError("manual disposition evidence commitment is stale")
    expected = make_manual_review_disposition(
        edge_candidate_id=disposition.edge_candidate_id,
        protocol_sha256=disposition.protocol_sha256,
        evidence_commitment=disposition.evidence_commitment,
        disposition=disposition.disposition,
        reviewer_identity=disposition.reviewer_identity,
        review_timestamp=disposition.review_timestamp,
        bounded_reason=disposition.bounded_reason,
    )
    if disposition.disposition_id != expected.disposition_id:
        raise ValueError("manual disposition ID is stale")


def manual_review_disposition_from_record(record: Mapping[str, Any]) -> ManualReviewDisposition:
    return ManualReviewDisposition(
        disposition_id=str(record["disposition_id"]),
        edge_candidate_id=str(record["edge_candidate_id"]),
        protocol_sha256=str(record["protocol_sha256"]),
        evidence_commitment=str(record["evidence_commitment"]),
        disposition=str(record["disposition"]),
        reviewer_identity=str(record["reviewer_identity"]),
        review_timestamp=str(record["review_timestamp"]),
        bounded_reason=str(record["bounded_reason"]),
    )


def resolve_evidence_candidate(
    candidate: EvidenceCandidate,
    disposition: ManualReviewDisposition | None,
    *,
    protocol_sha256: str,
) -> EvidenceEdge:
    validate_evidence_candidate(candidate)
    rule = EDGE_RULES[candidate.edge_type]
    if rule.review_requirement == "AUTO":
        if disposition is not None:
            raise ValueError("automatic evidence rule does not accept manual disposition")
        review_status = "APPROVED"
        connecting = rule.is_connecting_candidate
        disposition_id = None
    elif rule.review_requirement == "REVIEW_ONLY":
        if disposition is not None:
            raise ValueError("review-only evidence does not accept final disposition")
        review_status = "REVIEW_ONLY"
        connecting = False
        disposition_id = None
    else:
        if disposition is None:
            review_status = "UNRESOLVED"
            connecting = False
            disposition_id = None
        else:
            validate_manual_review_disposition(
                disposition,
                candidate,
                protocol_sha256=protocol_sha256,
            )
            review_status = disposition.disposition
            connecting = disposition.disposition == "APPROVED"
            disposition_id = disposition.disposition_id
    base_record = {
        "schema_id": EDGE_SCHEMA_ID,
        "candidate_id": candidate.candidate_id,
        "disposition_id": disposition_id,
        "left_repository": candidate.left_repository,
        "right_repository": candidate.right_repository,
        "edge_type": candidate.edge_type,
        "rule_version": candidate.rule_version,
        "evidence_commitment": candidate.evidence_commitment,
        "evidence_source_bundle_sha256": candidate.evidence_source_bundle_sha256,
        "evidence_payload_hash": candidate.evidence_payload_hash,
        "review_disposition_identity": disposition_id,
    }
    return EvidenceEdge(
        edge_id=derive_edge_id(base_record),
        candidate_id=candidate.candidate_id,
        disposition_id=disposition_id,
        left_repository=candidate.left_repository,
        right_repository=candidate.right_repository,
        edge_type=candidate.edge_type,
        connecting=connecting,
        evidence_sources=candidate.evidence_sources,
        evidence_source_bundle_sha256=candidate.evidence_source_bundle_sha256,
        evidence_payload_hash=candidate.evidence_payload_hash,
        evidence_commitment=candidate.evidence_commitment,
        rule_version=candidate.rule_version,
        confidence_category=rule.confidence_category,
        human_review_required=rule.human_review_required,
        review_status=review_status,
        review_disposition_identity=disposition_id,
        reason=rule.reason_template,
        evidence_payload=candidate.evidence_payload,
    )


def make_evidence_edge(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
    protocol_sha256: str,
    evidence_sources: Mapping[str, str] | None = None,
    evidence_source: str | None = None,
    evidence_source_identity: str | None = None,
    retrieval_timestamp: str | None = None,
    evidence_payload: Mapping[str, Any],
    reason: str | None = None,
    rule_version: str = PROTOCOL_VERSION,
) -> EvidenceEdge:
    del retrieval_timestamp, reason
    if evidence_sources is None:
        if evidence_source is None or evidence_source_identity is None:
            raise ValueError("evidence-source bundle is required")
        evidence_sources = {evidence_source: evidence_source_identity}
    candidate = make_evidence_candidate(
        left_repository,
        right_repository,
        edge_type,
        evidence_sources=evidence_sources,
        evidence_payload=evidence_payload,
        rule_version=rule_version,
    )
    edge = resolve_evidence_candidate(
        candidate,
        None,
        protocol_sha256=protocol_sha256,
    )
    if EDGE_RULES[edge_type].review_requirement == "APPROVED_REQUIRED":
        raise ValueError("review-required evidence must be resolved with a disposition")
    return edge


def validate_evidence_edge(
    edge: EvidenceEdge,
    *,
    protocol_sha256: str,
    allocation_repositories: set[str] | None = None,
) -> None:
    validate_resolved_edge(
        edge,
        None,
        None,
        protocol_sha256=protocol_sha256,
        allocation_repositories=allocation_repositories,
    )


def validate_resolved_edge(
    edge: EvidenceEdge,
    candidate: EvidenceCandidate | None,
    disposition: ManualReviewDisposition | None,
    *,
    protocol_sha256: str,
    allocation_repositories: set[str] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> None:
    if edge.edge_type not in EDGE_RULES:
        raise ValueError("invalid edge type")
    if allocation_repositories is not None and (
        edge.left_repository not in allocation_repositories
        or edge.right_repository not in allocation_repositories
    ):
        raise ValueError("edge endpoint is outside the allocation repository set")
    reconstructed = make_evidence_candidate(
        edge.left_repository,
        edge.right_repository,
        edge.edge_type,
        evidence_sources=edge.evidence_sources,
        evidence_payload=edge.evidence_payload,
        rule_version=edge.rule_version,
    )
    if candidate is None:
        candidate = reconstructed
    else:
        validate_evidence_candidate(candidate)
        for field in (
            "candidate_id",
            "left_repository",
            "right_repository",
            "edge_type",
            "rule_version",
            "evidence_source_bundle_sha256",
            "evidence_payload_hash",
            "evidence_commitment",
        ):
            if getattr(candidate, field) != getattr(reconstructed, field):
                raise ValueError(f"resolved edge candidate mismatch: {field}")
    rule = EDGE_RULES[edge.edge_type]
    if source_records is not None:
        validate_source_registry(
            rule,
            candidate.left_repository,
            candidate.right_repository,
            candidate.evidence_payload,
            candidate.evidence_sources,
            source_records,
        )
    if edge.candidate_id != candidate.candidate_id:
        raise ValueError("tampered evidence edge field: candidate_id")
    if rule.review_requirement == "APPROVED_REQUIRED":
        if edge.review_status in {"APPROVED", "REJECTED"}:
            if disposition is None:
                raise ValueError("resolved reviewed edge requires disposition record")
            validate_manual_review_disposition(
                disposition,
                candidate,
                protocol_sha256=protocol_sha256,
            )
            if edge.disposition_id != disposition.disposition_id:
                raise ValueError("tampered evidence edge field: disposition_id")
            if edge.review_disposition_identity != disposition.disposition_id:
                raise ValueError("tampered evidence edge field: review_disposition_identity")
        elif edge.review_status == "UNRESOLVED":
            if disposition is not None or edge.disposition_id is not None:
                raise ValueError("unresolved reviewed edge must not carry disposition identity")
            if edge.review_disposition_identity is not None:
                raise ValueError("unresolved reviewed edge must not carry disposition identity")
        else:
            raise ValueError("invalid resolved edge review status")
    elif disposition is not None or edge.disposition_id is not None:
        raise ValueError("non-reviewed edge must not carry disposition identity")
    expected = resolve_evidence_candidate(candidate, disposition, protocol_sha256=protocol_sha256)
    for field in (
        "edge_id",
        "candidate_id",
        "disposition_id",
        "left_repository",
        "right_repository",
        "edge_type",
        "connecting",
        "evidence_source_bundle_sha256",
        "evidence_payload_hash",
        "evidence_commitment",
        "rule_version",
        "confidence_category",
        "human_review_required",
        "review_status",
        "review_disposition_identity",
        "reason",
    ):
        if getattr(edge, field) != getattr(expected, field):
            raise ValueError(f"tampered evidence edge field: {field}")
    if dict(edge.evidence_sources) != dict(expected.evidence_sources):
        raise ValueError("tampered evidence edge field: evidence_sources")
    if dict(edge.evidence_payload) != dict(expected.evidence_payload):
        raise ValueError("tampered evidence edge field: evidence_payload")


def evidence_edge_from_record(record: Mapping[str, Any]) -> EvidenceEdge:
    return EvidenceEdge(
        edge_id=str(record["edge_id"]),
        candidate_id=str(record["candidate_id"]),
        disposition_id=record.get("disposition_id"),
        left_repository=str(record["left_repository"]),
        right_repository=str(record["right_repository"]),
        edge_type=str(record["edge_type"]),
        connecting=bool(record["connecting"]),
        evidence_sources=dict(record["evidence_sources"]),
        evidence_source_bundle_sha256=str(record["evidence_source_bundle_sha256"]),
        evidence_payload_hash=str(record["evidence_payload_hash"]),
        evidence_commitment=str(record["evidence_commitment"]),
        rule_version=str(record["rule_version"]),
        confidence_category=str(record["confidence_category"]),
        human_review_required=bool(record["human_review_required"]),
        review_status=str(record["review_status"]),
        reason=str(record["reason"]),
        evidence_payload=dict(record["evidence_payload"]),
        review_disposition_identity=record.get("review_disposition_identity"),
    )

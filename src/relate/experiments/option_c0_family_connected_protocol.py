"""Frozen Option C0 family-connected allocation protocol primitives."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

SCHEMA_ID: Final = "option-c0-family-connected-allocation-contract-v1"
EDGE_SCHEMA_ID: Final = "option-c0-family-evidence-edge-v1"
CACHE_SCHEMA_ID: Final = "option-c0-family-graph-cache-v1"
PROTOCOL_VERSION: Final = "family-protocol-v1"
D1_RESULT_SHA256: Final = "a19c042f725fb20a0a87fa902d2071f30c66d5ee8f96bfde1cd056cba5123420"
D1_1_CLASSIFICATION_SHA256: Final = (
    "64787803c775193335c98dfef7ccdd23989c54d0a110efb0284f7960640c5be4"
)
ALLOCATION_MANIFEST_SHA256: Final = (
    "41e48447171ac2f0553b795f2b3e50dfc5ac389b68fb30607b7d1c496bdb5bfc"
)
ALLOCATION_CONTEXT_SHA256: Final = (
    "a3ae0b5dcbef0ae8e5056900ba44eeb53b4fd53a20f7cea8d842f67197ab02ed"
)
ROLE_ORDER: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
REPOSITORY_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_.-]*/[a-z0-9][a-z0-9_.-]*$")
HASH_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
LOCATOR_PATTERN: Final = re.compile(r"^[a-z][a-z0-9+.-]*:[^\s]+$")
ALLOWED_EVIDENCE_SOURCES: Final = (
    "github_rest",
    "d1_visible_cache",
    "public_metadata_snapshot",
    "manual_review_record",
    "fixture",
)
CONFIDENCE_CATEGORIES: Final = ("high", "medium", "low", "review_only")
REVIEW_DISPOSITIONS: Final = ("APPROVED", "REJECTED", "UNRESOLVED")
METADATA_STATUSES: Final = (
    "COMPLETE",
    "NOT_FOUND",
    "DELETED",
    "RENAMED",
    "ARCHIVED",
    "RATE_LIMITED",
    "REQUEST_FAILED",
)
FORBIDDEN_PAYLOAD_PATTERNS: Final = (
    "source_body",
    "raw_source",
    "code_body",
    "hidden_row_content",
    "c0_selection_row",
    "c1_reserve_row",
    "raw_embedding",
    "embedding_vector",
    "file_contents",
    "unbounded_file",
)


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


EDGE_RULES: Final[Mapping[str, EdgeRule]] = {
    "DECLARED_GITHUB_FORK": EdgeRule(
        edge_type="DECLARED_GITHUB_FORK",
        category="hard_connecting",
        connecting_policy=(
            "connect when GitHub fork metadata proves one endpoint is the other "
            "endpoint's parent/source"
        ),
        required_fields={
            "left_repository_id": "str",
            "right_repository_id": "str",
            "child_full_name": "repository",
            "parent_or_source_full_name": "repository",
            "fork": "true",
            "parent_or_source_endpoint_equals_other_endpoint": "true",
            "metadata_snapshot_identity": "sha256",
            "snapshot_status": "str",
        },
        allowed_values={"snapshot_status": ("COMPLETE",)},
        forbidden_fields=(),
        evidence_source_requirements=("github_rest", "public_metadata_snapshot"),
        review_requirement="AUTO",
        confidence_category="high",
        reason_template="declared GitHub fork relationship connects repositories",
        negative_conditions=("same owner alone is not fork evidence",),
    ),
    "VERIFIED_REPOSITORY_SUCCESSION": EdgeRule(
        edge_type="VERIFIED_REPOSITORY_SUCCESSION",
        category="hard_connecting",
        connecting_policy="connect only after approved public succession or rename/archive review",
        required_fields={
            "predecessor_repository": "repository",
            "successor_repository": "repository",
            "direction": "str",
            "public_succession_record": "str",
            "record_snapshot_hash": "sha256",
            "review_disposition": "str",
            "review_disposition_protocol_sha256": "sha256",
            "review_disposition_evidence_hash": "sha256",
        },
        allowed_values={
            "direction": ("predecessor_to_successor",),
            "review_disposition": ("APPROVED",),
        },
        forbidden_fields=(),
        evidence_source_requirements=("manual_review_record", "public_metadata_snapshot"),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="high",
        reason_template="approved repository succession connects repositories",
        negative_conditions=("similar names or creation dates alone are insufficient",),
    ),
    "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY": EdgeRule(
        edge_type="EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
        category="hard_connecting",
        connecting_policy=(
            "connect only complete repository tree or approved complete "
            "non-generated module scope identity"
        ),
        required_fields={
            "identity_scope": "str",
            "matching_content_sha256": "sha256",
            "left_scope_identity": "sha256",
            "right_scope_identity": "sha256",
            "source_identity_provenance": "str",
            "generated_vendor_boilerplate_exclusion": "true",
            "complete_evidence_status": "str",
        },
        allowed_values={
            "identity_scope": ("complete_repository_source_tree", "approved_non_generated_module"),
            "complete_evidence_status": ("COMPLETE",),
        },
        forbidden_fields=("function_stable_key", "function_code_sha256"),
        evidence_source_requirements=("d1_visible_cache", "public_metadata_snapshot"),
        review_requirement="AUTO",
        confidence_category="high",
        reason_template="complete source scope identity connects repositories",
        negative_conditions=("a single identical function is not a hard repository connection",),
    ),
    "VERIFIED_SHARED_PACKAGE_LINEAGE": EdgeRule(
        edge_type="VERIFIED_SHARED_PACKAGE_LINEAGE",
        category="hard_connecting",
        connecting_policy=(
            "connect approved movement, split, rename, or continuation of the "
            "same package/project lineage"
        ),
        required_fields={
            "lineage_record_type": "str",
            "approved_lineage_record": "str",
            "evidence_snapshot_hash": "sha256",
            "review_disposition": "str",
            "review_disposition_protocol_sha256": "sha256",
            "review_disposition_evidence_hash": "sha256",
        },
        allowed_values={
            "lineage_record_type": ("movement", "split", "rename", "continuation"),
            "review_disposition": ("APPROVED",),
        },
        forbidden_fields=("common_dependency_only", "same_owner_only"),
        evidence_source_requirements=("manual_review_record", "public_metadata_snapshot"),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="high",
        reason_template="approved shared package lineage connects repositories",
        negative_conditions=(
            "common dependency is insufficient",
            "same framework is insufficient",
            "shared package name token is insufficient",
            "same owner is insufficient",
        ),
    ),
    "EXACT_AST_WITH_CORROBORATING_PROVENANCE": EdgeRule(
        edge_type="EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        category="conditional_connecting",
        connecting_policy=(
            "connect only when all corroborating provenance fields are exactly "
            "true and review is approved"
        ),
        required_fields={
            "same_normalized_ast": "true",
            "same_function_identity": "true",
            "same_path_suffix": "true",
            "compatible_repository_dates": "true",
            "public_shared_package_history": "true",
            "review_disposition": "str",
            "review_disposition_protocol_sha256": "sha256",
            "review_disposition_evidence_hash": "sha256",
        },
        allowed_values={"review_disposition": ("APPROVED",)},
        forbidden_fields=(),
        evidence_source_requirements=("manual_review_record", "d1_visible_cache"),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="medium",
        reason_template="approved exact AST plus corroborating provenance connects repositories",
        negative_conditions=("exact AST alone is insufficient",),
    ),
    "SAME_MODULE_LINEAGE_WITH_CORROBORATION": EdgeRule(
        edge_type="SAME_MODULE_LINEAGE_WITH_CORROBORATION",
        category="conditional_connecting",
        connecting_policy="connect only approved same-module lineage with public corroboration",
        required_fields={
            "same_module_lineage": "true",
            "public_shared_package_history": "true",
            "compatible_repository_dates": "true",
            "review_disposition": "str",
            "review_disposition_protocol_sha256": "sha256",
            "review_disposition_evidence_hash": "sha256",
        },
        allowed_values={"review_disposition": ("APPROVED",)},
        forbidden_fields=(),
        evidence_source_requirements=("manual_review_record", "public_metadata_snapshot"),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="medium",
        reason_template="approved same-module lineage connects repositories",
        negative_conditions=("same module name alone is insufficient",),
    ),
    "EXPLICIT_COPY_OR_EXTRACTION_HISTORY": EdgeRule(
        edge_type="EXPLICIT_COPY_OR_EXTRACTION_HISTORY",
        category="conditional_connecting",
        connecting_policy="connect only approved public copy or extraction history",
        required_fields={
            "public_copy_or_extraction_record": "str",
            "compatible_repository_dates": "true",
            "review_disposition": "str",
            "review_disposition_protocol_sha256": "sha256",
            "review_disposition_evidence_hash": "sha256",
        },
        allowed_values={"review_disposition": ("APPROVED",)},
        forbidden_fields=(),
        evidence_source_requirements=("manual_review_record", "public_metadata_snapshot"),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="medium",
        reason_template="approved copy or extraction history connects repositories",
        negative_conditions=("unreviewed copy suspicion is insufficient",),
    ),
    "EXACT_FUNCTION_SOURCE_MATCH": EdgeRule(
        edge_type="EXACT_FUNCTION_SOURCE_MATCH",
        category="nonconnecting_review_evidence",
        connecting_policy="never connects repositories by itself",
        required_fields={
            "left_stable_key": "str",
            "right_stable_key": "str",
            "code_sha256": "sha256",
            "visible_role_left": "visible_role",
            "visible_role_right": "visible_role",
        },
        allowed_values={},
        forbidden_fields=("source_body", "raw_source"),
        evidence_source_requirements=("d1_visible_cache",),
        review_requirement="REVIEW_ONLY",
        confidence_category="review_only",
        reason_template="single exact function source match is review evidence only",
        negative_conditions=("function-level exact source does not hard-connect repositories",),
    ),
    "SAME_OWNER_PROXY": EdgeRule(
        edge_type="SAME_OWNER_PROXY",
        category="nonconnecting_review_evidence",
        connecting_policy="never connects repositories",
        required_fields={"same_owner": "true", "owner": "str"},
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("allocation_manifest",),
        review_requirement="REVIEW_ONLY",
        confidence_category="review_only",
        reason_template="same owner is proxy review evidence only",
        negative_conditions=("same owner is not a family rule",),
    ),
    "SIMILAR_REPOSITORY_NAME": EdgeRule(
        "SIMILAR_REPOSITORY_NAME",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"similarity_method": "str", "score": "number"},
        {},
        (),
        ("allocation_manifest",),
        "REVIEW_ONLY",
        "review_only",
        "similar names are review evidence only",
        ("similar names alone are insufficient",),
    ),
    "SUFFIX_STRIPPED_NAME_MATCH": EdgeRule(
        "SUFFIX_STRIPPED_NAME_MATCH",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"normalized_family_token": "str"},
        {},
        (),
        ("allocation_manifest",),
        "REVIEW_ONLY",
        "review_only",
        "suffix-stripped name match is review evidence only",
        ("shared name tokens alone are insufficient",),
    ),
    "SIMHASH_NEAR_FUNCTION": EdgeRule(
        "SIMHASH_NEAR_FUNCTION",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"left_stable_key": "str", "right_stable_key": "str", "hamming_distance": "int"},
        {},
        ("source_body", "raw_source"),
        ("d1_visible_cache",),
        "REVIEW_ONLY",
        "review_only",
        "SimHash-near function pair is heuristic review evidence only",
        ("SimHash-near alone is insufficient",),
    ),
    "COMMON_FRAMEWORK_OR_BOILERPLATE": EdgeRule(
        "COMMON_FRAMEWORK_OR_BOILERPLATE",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"framework_or_boilerplate_name": "str"},
        {},
        (),
        ("public_metadata_snapshot",),
        "REVIEW_ONLY",
        "review_only",
        "common framework or boilerplate is review evidence only",
        ("common framework is insufficient",),
    ),
    "SHARED_LANGUAGE_OR_TOPIC": EdgeRule(
        "SHARED_LANGUAGE_OR_TOPIC",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"topic_or_language": "str"},
        {},
        (),
        ("public_metadata_snapshot",),
        "REVIEW_ONLY",
        "review_only",
        "shared language or topic is review evidence only",
        ("shared language or topic is insufficient",),
    ),
}
HARD_CONNECTING_EDGE_TYPES: Final = tuple(
    key for key, rule in EDGE_RULES.items() if rule.category == "hard_connecting"
)
CONDITIONAL_CONNECTING_EDGE_TYPES: Final = tuple(
    key for key, rule in EDGE_RULES.items() if rule.category == "conditional_connecting"
)
NONCONNECTING_EDGE_TYPES: Final = tuple(
    key for key, rule in EDGE_RULES.items() if rule.category == "nonconnecting_review_evidence"
)
CONNECTING_EDGE_TYPES: Final = HARD_CONNECTING_EDGE_TYPES + CONDITIONAL_CONNECTING_EDGE_TYPES
ALL_EDGE_TYPES: Final = tuple(EDGE_RULES)


def canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_repository(repository: str) -> str:
    if not isinstance(repository, str):
        raise ValueError("repository identity must be a string")
    value = repository.strip().lower()
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise ValueError(f"malformed repository identity: {repository!r}")
    return value


def repository_owner(repository: str) -> str:
    return normalize_repository(repository).split("/", 1)[0]


@dataclass(frozen=True)
class AllocationEntry:
    repository: str
    role: str
    row_count: int


def load_allocation_manifest(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[AllocationEntry, ...]:
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise ValueError("allocation manifest SHA-256 mismatch")
    entries: list[AllocationEntry] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"allocation line {line_number} must be a JSON object")
        repository = normalize_repository(item.get("repository", ""))
        role = item.get("role")
        row_count = item.get("row_count")
        if role not in ROLE_ORDER:
            raise ValueError(f"invalid role at allocation line {line_number}: {role}")
        if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0:
            raise ValueError(f"invalid row_count at allocation line {line_number}")
        if repository in seen:
            raise ValueError(f"duplicate allocation repository: {repository}")
        seen.add(repository)
        entries.append(AllocationEntry(repository=repository, role=role, row_count=row_count))
    return tuple(sorted(entries, key=lambda entry: entry.repository))


def payload_hash(payload: Mapping[str, Any]) -> str:
    validate_payload_firewall(payload)
    return sha256_text(canonical_json(payload))


def validate_payload_firewall(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(pattern in key_text for pattern in FORBIDDEN_PAYLOAD_PATTERNS):
                raise ValueError(f"forbidden evidence payload field: {path}{key}")
            validate_payload_firewall(item, f"{path}{key}.")
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            validate_payload_firewall(item, f"{path}{index}.")


def parse_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("retrieval timestamp must be a nonempty string")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("retrieval timestamp must be timezone-aware")
    return parsed.isoformat()


def validate_source_identity(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("evidence source identity must be nonempty")
    if HASH_PATTERN.fullmatch(value) or LOCATOR_PATTERN.fullmatch(value):
        return value
    raise ValueError("evidence source identity must be a SHA-256 or frozen locator")


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


@dataclass(frozen=True)
class ManualReviewDisposition:
    edge_candidate_id: str
    protocol_sha256: str
    evidence_commitment: str
    disposition: str
    reviewer_identity: str
    review_timestamp: str
    bounded_reason: str

    def as_record(self) -> dict[str, Any]:
        return {
            "edge_candidate_id": self.edge_candidate_id,
            "protocol_sha256": self.protocol_sha256,
            "evidence_commitment": self.evidence_commitment,
            "disposition": self.disposition,
            "reviewer_identity": self.reviewer_identity,
            "review_timestamp": self.review_timestamp,
            "bounded_reason": self.bounded_reason,
        }


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
    return ManualReviewDisposition(
        edge_candidate_id=edge_candidate_id,
        protocol_sha256=protocol_sha256,
        evidence_commitment=evidence_commitment,
        disposition=disposition,
        reviewer_identity=validate_source_identity(reviewer_identity),
        review_timestamp=review_timestamp,
        bounded_reason=validate_reason(bounded_reason),
    )


@dataclass(frozen=True)
class EvidenceEdge:
    edge_id: str
    left_repository: str
    right_repository: str
    edge_type: str
    connecting: bool
    evidence_source: str
    evidence_source_identity: str
    retrieval_timestamp: str
    evidence_payload_hash: str
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
            "left_repository": self.left_repository,
            "right_repository": self.right_repository,
            "edge_type": self.edge_type,
            "connecting": self.connecting,
            "evidence_source": self.evidence_source,
            "evidence_source_identity": self.evidence_source_identity,
            "retrieval_timestamp": self.retrieval_timestamp,
            "evidence_payload_hash": self.evidence_payload_hash,
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


def edge_candidate_id(
    left: str,
    right: str,
    edge_type: str,
    rule_version: str,
    evidence_source_identity: str,
    evidence_payload_hash: str,
) -> str:
    return sha256_text(
        canonical_json(
            {
                "left_repository": left,
                "right_repository": right,
                "edge_type": edge_type,
                "rule_version": rule_version,
                "evidence_source_identity": evidence_source_identity,
                "evidence_payload_hash": evidence_payload_hash,
            }
        )
    )


def derive_edge_id(record: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(dict(record)))


def validate_rule_payload(rule: EdgeRule, payload: Mapping[str, Any]) -> None:
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


def make_evidence_edge(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
    evidence_source: str,
    evidence_source_identity: str,
    retrieval_timestamp: str,
    evidence_payload: Mapping[str, Any],
    reason: str | None = None,
    rule_version: str = PROTOCOL_VERSION,
) -> EvidenceEdge:
    left = normalize_repository(left_repository)
    right = normalize_repository(right_repository)
    if left == right:
        raise ValueError("family evidence edge must connect two distinct repositories")
    if left > right:
        left, right = right, left
    if edge_type not in EDGE_RULES:
        raise ValueError(f"unknown family evidence edge type: {edge_type}")
    rule = EDGE_RULES[edge_type]
    if rule_version != PROTOCOL_VERSION:
        raise ValueError("wrong family edge rule version")
    if evidence_source not in rule.evidence_source_requirements:
        raise ValueError("evidence source is not allowed for this edge type")
    validate_source_identity(evidence_source_identity)
    timestamp = parse_timestamp(retrieval_timestamp)
    validate_rule_payload(rule, evidence_payload)
    evidence_hash = payload_hash(evidence_payload)
    candidate = edge_candidate_id(
        left,
        right,
        edge_type,
        rule_version,
        evidence_source_identity,
        evidence_hash,
    )
    review_status = (
        "APPROVED"
        if rule.review_requirement in {"AUTO", "APPROVED_REQUIRED"}
        else "REVIEW_ONLY"
    )
    connecting = rule.is_connecting_candidate and review_status == "APPROVED"
    base_record = {
        "schema_id": EDGE_SCHEMA_ID,
        "left_repository": left,
        "right_repository": right,
        "edge_type": edge_type,
        "rule_version": rule_version,
        "evidence_source_identity": evidence_source_identity,
        "evidence_payload_hash": evidence_hash,
        "review_disposition_identity": (
            candidate if rule.review_requirement == "APPROVED_REQUIRED" else None
        ),
    }
    edge_id = derive_edge_id(base_record)
    return EvidenceEdge(
        edge_id=edge_id,
        left_repository=left,
        right_repository=right,
        edge_type=edge_type,
        connecting=connecting,
        evidence_source=evidence_source,
        evidence_source_identity=evidence_source_identity,
        retrieval_timestamp=timestamp,
        evidence_payload_hash=evidence_hash,
        rule_version=rule_version,
        confidence_category=rule.confidence_category,
        human_review_required=rule.human_review_required,
        review_status=review_status,
        review_disposition_identity=base_record["review_disposition_identity"],
        reason=validate_reason(reason or rule.reason_template),
        evidence_payload=evidence_payload,
    )


def validate_evidence_edge(
    edge: EvidenceEdge,
    *,
    protocol_sha256: str,
    allocation_repositories: set[str] | None = None,
) -> None:
    if edge.edge_type not in EDGE_RULES:
        raise ValueError("invalid edge type")
    if edge.left_repository != normalize_repository(edge.left_repository):
        raise ValueError("left endpoint is not normalized")
    if edge.right_repository != normalize_repository(edge.right_repository):
        raise ValueError("right endpoint is not normalized")
    if edge.left_repository >= edge.right_repository:
        raise ValueError("edge endpoints are not in canonical order")
    if allocation_repositories is not None and (
        edge.left_repository not in allocation_repositories
        or edge.right_repository not in allocation_repositories
    ):
        raise ValueError("edge endpoint is outside the allocation repository set")
    regenerated = make_evidence_edge(
        edge.left_repository,
        edge.right_repository,
        edge.edge_type,
        evidence_source=edge.evidence_source,
        evidence_source_identity=edge.evidence_source_identity,
        retrieval_timestamp=edge.retrieval_timestamp,
        evidence_payload=edge.evidence_payload,
        reason=edge.reason,
        rule_version=edge.rule_version,
    )
    for field in (
        "edge_id",
        "evidence_payload_hash",
        "connecting",
        "human_review_required",
        "review_status",
        "confidence_category",
        "review_disposition_identity",
    ):
        if getattr(edge, field) != getattr(regenerated, field):
            raise ValueError(f"tampered evidence edge field: {field}")
    if edge.review_disposition_identity and edge.review_disposition_identity != edge_candidate_id(
        edge.left_repository,
        edge.right_repository,
        edge.edge_type,
        edge.rule_version,
        edge.evidence_source_identity,
        edge.evidence_payload_hash,
    ):
        raise ValueError("stale manual disposition identity")
    if (
        edge.review_disposition_identity
        and protocol_sha256 != protocol_contract()["protocol_sha256"]
    ):
        raise ValueError("manual disposition protocol identity is stale")


class UnionFind:
    def __init__(self, nodes: Sequence[str]) -> None:
        self.parent = {node: node for node in sorted(set(nodes))}

    def find(self, node: str) -> str:
        parent = self.parent[node]
        if parent != node:
            self.parent[node] = self.find(parent)
        return self.parent[node]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            first, second = sorted((left_root, right_root))
            self.parent[second] = first


def component_id(members: Sequence[str], protocol_sha256: str) -> str:
    return sha256_text(
        canonical_json({"members": sorted(members), "protocol_sha256": protocol_sha256})
    )


def _reject_conflicting_duplicates(edges: Sequence[EvidenceEdge]) -> None:
    by_id: dict[str, dict[str, Any]] = {}
    for edge in edges:
        record = edge.as_record()
        if edge.edge_id in by_id and by_id[edge.edge_id] != record:
            raise ValueError("conflicting duplicate edge ID")
        by_id[edge.edge_id] = record


def build_components(
    repositories: Sequence[str],
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str,
) -> list[dict[str, Any]]:
    normalized = sorted({normalize_repository(repository) for repository in repositories})
    allocation_set = set(normalized)
    _reject_conflicting_duplicates(edges)
    uf = UnionFind(normalized)
    for edge in sorted(edges, key=lambda item: item.edge_id):
        validate_evidence_edge(
            edge,
            protocol_sha256=protocol_sha256,
            allocation_repositories=allocation_set,
        )
        if edge.connecting:
            uf.union(edge.left_repository, edge.right_repository)
    by_root: dict[str, list[str]] = {}
    for repository in normalized:
        by_root.setdefault(uf.find(repository), []).append(repository)
    components = [
        {
            "component_id": component_id(members, protocol_sha256),
            "repositories": sorted(members),
            "repository_count": len(members),
        }
        for members in by_root.values()
    ]
    return sorted(components, key=lambda item: item["component_id"])


def component_commitment(components: Sequence[Mapping[str, Any]]) -> str:
    normalized = sorted((dict(component) for component in components), key=canonical_json)
    return sha256_text(canonical_json({"components": normalized}))


def edge_commitment(edges: Sequence[EvidenceEdge]) -> str:
    _reject_conflicting_duplicates(edges)
    records = [edge.as_record() for edge in sorted(edges, key=lambda item: item.edge_id)]
    return sha256_text(canonical_json({"edges": records}))


def public_metadata_snapshot(
    repository: str,
    status: str,
    retrieval_timestamp: str,
    evidence_source_identity: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if status not in METADATA_STATUSES:
        raise ValueError("metadata snapshot status is not frozen")
    timestamp = parse_timestamp(retrieval_timestamp)
    source_identity = validate_source_identity(evidence_source_identity)
    payload_sha = payload_hash(payload)
    base = {
        "repository": normalize_repository(repository),
        "status": status,
        "retrieval_timestamp": timestamp,
        "evidence_source_identity": source_identity,
        "payload_hash": payload_sha,
    }
    return {**base, "snapshot_sha256": sha256_text(canonical_json(base)), "payload": dict(payload)}


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


def edge_rules_contract() -> dict[str, Any]:
    return {
        name: {
            "edge_type": rule.edge_type,
            "category": rule.category,
            "connecting_policy": rule.connecting_policy,
            "required_fields": dict(rule.required_fields),
            "field_types": dict(rule.required_fields),
            "allowed_values": {key: list(value) for key, value in rule.allowed_values.items()},
            "forbidden_fields": list(rule.forbidden_fields),
            "evidence_source_requirements": list(rule.evidence_source_requirements),
            "review_requirement": rule.review_requirement,
            "automatic_or_human_reviewed_disposition": rule.review_requirement,
            "confidence_policy": rule.confidence_category,
            "reason_template": rule.reason_template,
            "negative_exclusion_conditions": list(rule.negative_conditions),
        }
        for name, rule in sorted(EDGE_RULES.items())
    }


def protocol_contract() -> dict[str, Any]:
    contract = {
        "schema_id": SCHEMA_ID,
        "schema_version": "v1",
        "source_allocation_identity": {
            "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
            "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
        },
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
        "repository_normalization_rule": {
            "case": "lowercase",
            "trim_python_unicode_whitespace": True,
            "required_shape": "owner/repository",
            "allowed_pattern": REPOSITORY_PATTERN.pattern,
        },
        "edge_rules": edge_rules_contract(),
        "edge_taxonomy": {
            "hard_connecting": list(HARD_CONNECTING_EDGE_TYPES),
            "conditional_connecting": list(CONDITIONAL_CONNECTING_EDGE_TYPES),
            "nonconnecting_review_evidence": list(NONCONNECTING_EDGE_TYPES),
        },
        "component_algorithm": {
            "sort_connecting_edges": "by immutable edge_id",
            "union_find_uses_connecting_edges_only": True,
            "component_id": "sha256(canonical_json(sorted members + protocol sha256))",
            "transitivity": "applies only through connecting edges",
        },
        "public_metadata_policy": {
            "snapshot_and_hash_public_metadata": True,
            "allowed_statuses": list(METADATA_STATUSES),
            "live_api_responses_not_silent_dependencies": True,
        },
        "cache_schema": {
            "schema_id": CACHE_SCHEMA_ID,
            "path": ".writer/option-c0/cache/option-c0-family-graph-v1.sqlite3",
            "identity_fields": list(FamilyGraphCacheIdentity.__annotations__),
            "tables": [
                "cache_identity",
                "allocation_repositories",
                "repository_metadata_snapshots",
                "typed_evidence_edges",
                "manual_review_dispositions",
                "component_memberships",
                "phase_commitments",
            ],
            "sqlite_pragmas": {"journal_mode": "WAL", "synchronous": "FULL", "foreign_keys": "ON"},
        },
        "decision_rules": {
            "allowed_outcomes": [
                "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS",
                "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED",
                "FAMILY_GRAPH_INCOMPLETE_METADATA",
                "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED",
            ],
            "family_crossing_observed": "true when a connecting component spans roles",
            "allocation_family_disjointness_violated": (
                "true when any connecting component spans roles"
            ),
            "material_contamination_established": "false in automatic run pending human review",
            "reallocation_required": "null in automatic run pending human review",
            "automatic_reallocation_from_crossing": False,
        },
        "permitted_inputs": [
            "published repository names",
            "published role assignments",
            "published aggregate row counts",
            "D1 visible-row hashes and bounded metadata",
            "public repository metadata",
        ],
        "prohibited_actions": [
            "canonical family graph execution in this PR",
            "allocation changes",
            "model refits",
            "C0 replay",
            "C0 selection row-content access",
            "C1 reserve row-content access",
            "D2 execution",
        ],
        "firewall_booleans": {
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
            "hidden_row_content_accessed": False,
        },
    }
    contract["protocol_sha256"] = sha256_text(canonical_json(contract))
    return contract


def verify_protocol_contract(contract: Mapping[str, Any]) -> bool:
    expected = dict(contract)
    observed = expected.pop("protocol_sha256", None)
    return observed == sha256_text(canonical_json(expected))


def write_protocol_contract(path: Path, *, overwrite: bool = False) -> dict[str, Any]:
    if path.exists() and not overwrite:
        raise FileExistsError("protocol contract refuses overwrite")
    contract = protocol_contract()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(canonical_json(contract) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)
    return contract


@dataclass(frozen=True)
class FamilyGraphCacheIdentity:
    family_protocol_sha256: str
    allocation_manifest_sha256: str
    allocation_context_sha256: str
    d1_audit_result_sha256: str
    d1_1_classification_sha256: str
    cache_schema_version: str
    family_runner_source_identity: str

    def as_mapping(self) -> dict[str, str]:
        return {
            "family_protocol_sha256": self.family_protocol_sha256,
            "allocation_manifest_sha256": self.allocation_manifest_sha256,
            "allocation_context_sha256": self.allocation_context_sha256,
            "d1_audit_result_sha256": self.d1_audit_result_sha256,
            "d1_1_classification_sha256": self.d1_1_classification_sha256,
            "cache_schema_version": self.cache_schema_version,
            "family_runner_source_identity": self.family_runner_source_identity,
        }


def default_cache_identity(family_protocol_sha256: str) -> FamilyGraphCacheIdentity:
    return FamilyGraphCacheIdentity(
        family_protocol_sha256=family_protocol_sha256,
        allocation_manifest_sha256=ALLOCATION_MANIFEST_SHA256,
        allocation_context_sha256=ALLOCATION_CONTEXT_SHA256,
        d1_audit_result_sha256=D1_RESULT_SHA256,
        d1_1_classification_sha256=D1_1_CLASSIFICATION_SHA256,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity=sha256_file(Path(__file__)),
    )


class FamilyGraphCache:
    def __init__(self, path: Path, *, identity: FamilyGraphCacheIdentity) -> None:
        self.path = path
        self.identity = identity
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self._create_schema()
        self._verify_pragmas()
        self._bind_identity()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> FamilyGraphCache:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _verify_pragmas(self) -> None:
        foreign_keys = self.connection.execute("PRAGMA foreign_keys").fetchone()[0]
        synchronous = self.connection.execute("PRAGMA synchronous").fetchone()[0]
        journal_mode = self.connection.execute("PRAGMA journal_mode").fetchone()[0]
        if int(foreign_keys) != 1 or int(synchronous) != 2 or str(journal_mode).lower() != "wal":
            raise RuntimeError("family graph cache SQLite pragmas are not enforced")

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cache_identity (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS allocation_repositories (
                repository TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                row_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repository_metadata_snapshots (
                repository TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL,
                FOREIGN KEY(repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS typed_evidence_edges (
                edge_id TEXT PRIMARY KEY,
                left_repository TEXT NOT NULL,
                right_repository TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                connecting INTEGER NOT NULL,
                edge_json TEXT NOT NULL,
                FOREIGN KEY(left_repository) REFERENCES allocation_repositories(repository),
                FOREIGN KEY(right_repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS manual_review_dispositions (
                edge_id TEXT PRIMARY KEY,
                disposition TEXT NOT NULL,
                reviewer_note TEXT NOT NULL,
                FOREIGN KEY(edge_id) REFERENCES typed_evidence_edges(edge_id)
            );
            CREATE TABLE IF NOT EXISTS component_memberships (
                component_id TEXT NOT NULL,
                repository TEXT NOT NULL,
                PRIMARY KEY(component_id, repository),
                FOREIGN KEY(repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS phase_commitments (
                phase TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                commitment_sha256 TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def _bind_identity(self) -> None:
        for key, expected in self.identity.as_mapping().items():
            row = self.connection.execute(
                "SELECT value FROM cache_identity WHERE key = ?",
                (key,),
            ).fetchone()
            if row is not None and row[0] != expected:
                raise ValueError(f"family graph cache identity mismatch: {key}")
        self.connection.executemany(
            """
            INSERT INTO cache_identity(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            sorted(self.identity.as_mapping().items()),
        )
        self.connection.commit()

    def put_allocation_repositories(self, entries: Sequence[AllocationEntry]) -> None:
        self.connection.executemany(
            """
            INSERT INTO allocation_repositories(repository, role, row_count)
            VALUES (?, ?, ?)
            ON CONFLICT(repository) DO UPDATE SET
                role = excluded.role,
                row_count = excluded.row_count
            """,
            [(entry.repository, entry.role, entry.row_count) for entry in entries],
        )
        self.connection.commit()


def validate_frozen_protocol_inputs(repo_root: Path) -> dict[str, Any]:
    allocation = repo_root / (
        "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-repository-allocation-v1.jsonl"
    )
    firewall = repo_root / (
        "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-data-firewall-publication-v1.json"
    )
    d1 = repo_root / (
        "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-integrity-audit-v1.json"
    )
    d11 = repo_root / (
        "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-overlap-classification-v1.json"
    )
    if sha256_file(allocation) != ALLOCATION_MANIFEST_SHA256:
        raise ValueError("canonical allocation manifest hash mismatch")
    if sha256_file(d1) != D1_RESULT_SHA256:
        raise ValueError("canonical D1 result hash mismatch")
    if sha256_file(d11) != D1_1_CLASSIFICATION_SHA256:
        raise ValueError("canonical D1.1 classification hash mismatch")
    firewall_data = json.loads(firewall.read_text(encoding="utf-8"))
    d11_data = json.loads(d11.read_text(encoding="utf-8"))
    if firewall_data.get("allocation_context_sha256") != ALLOCATION_CONTEXT_SHA256:
        raise ValueError("allocation context SHA-256 mismatch")
    classification = d11_data.get("classification", {})
    if classification.get("overall_outcome") != "D1_CLASSIFICATION_INCONCLUSIVE":
        raise ValueError("D1.1 outcome is not inconclusive")
    if classification.get("family_identity_rule_status") != "NOT_FROZEN":
        raise ValueError("D1.1 family identity rule status is not frozen as NOT_FROZEN")
    firewall_booleans = d11_data.get("firewall_booleans", {})
    for key in (
        "c0_selection_rows_accessed",
        "c0_selection_row_content_accessed",
        "c1_rows_accessed",
        "c1_row_content_accessed",
        "hidden_row_content_accessed",
    ):
        if bool(firewall_booleans.get(key)):
            raise ValueError(f"hidden-row firewall field is true: {key}")
    return {
        "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
        "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
    }


def graph_completeness(
    edges: Sequence[EvidenceEdge],
    *,
    incomplete_metadata_records: int = 0,
) -> dict[str, int]:
    unresolved = 0
    approved = 0
    review_only = 0
    rejected = 0
    for item in edges:
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the frozen Option C0 family-connected protocol contract."
    )
    parser.add_argument("--write-contract", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if args.write_contract:
        write_protocol_contract(args.write_contract, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

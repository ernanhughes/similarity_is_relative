"""Frozen Option C0 family-connected allocation protocol primitives."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text

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
ALLOCATION_REPOSITORY_COUNT: Final = 5324
ALLOCATION_ROLE_REPOSITORY_COUNTS: Final = {
    "c0_fit": 2117,
    "c0_iteration": 1058,
    "c0_selection": 545,
    "c1_reserve": 1604,
}
ALLOCATION_ROLE_ROW_COUNTS: Final = {
    "c0_fit": 8007,
    "c0_iteration": 4110,
    "c0_selection": 2070,
    "c1_reserve": 6357,
}
ALLOCATION_REPOSITORY_COMMITMENT_SHA256: Final = (
    "cede73f5321d5a667a26b27a66131b8a324b89423353dd77be45f40c16ffc103"
)
ROLE_ORDER: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
REPOSITORY_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_.-]*/[a-z0-9_.-]+$")
HASH_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
LOCATOR_PATTERN: Final = re.compile(r"^[a-z][a-z0-9+.-]*:[^\s]+$")
ALLOWED_EVIDENCE_SOURCES: Final = (
    "github_rest",
    "d1_visible_cache",
    "public_metadata_snapshot",
    "manual_review_record",
    "allocation_manifest",
    "fixture",
)
CONFIDENCE_CATEGORIES: Final = ("high", "medium", "low", "review_only")
REVIEW_DISPOSITIONS: Final = ("APPROVED", "REJECTED")
METADATA_STATUSES: Final = (
    "COMPLETE",
    "NOT_FOUND",
    "DELETED",
    "RENAMED",
    "ARCHIVED",
    "RATE_LIMITED",
    "REQUEST_FAILED",
)
PUBLIC_METADATA_FIELDS: Final = {
    "repository_id",
    "full_name",
    "owner_login",
    "fork",
    "parent_full_name",
    "source_full_name",
    "archived",
    "created_at",
    "updated_at",
    "homepage",
    "description",
    "rename_or_move_indicator",
    "request_status",
}
MAX_EVIDENCE_STRING_LENGTH: Final = 500
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
        },
        allowed_values={
            "direction": ("predecessor_to_successor",),
        },
        forbidden_fields=(),
        evidence_source_requirements=("public_metadata_snapshot",),
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
            "d1_visible_evidence_identity": "sha256",
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
        },
        allowed_values={
            "lineage_record_type": ("movement", "split", "rename", "continuation"),
        },
        forbidden_fields=("common_dependency_only", "same_owner_only"),
        evidence_source_requirements=("public_metadata_snapshot",),
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
            "left_stable_key": "str",
            "right_stable_key": "str",
            "normalized_ast_sha256": "sha256",
            "d1_visible_evidence_identity": "sha256",
            "visible_role_left": "visible_role",
            "visible_role_right": "visible_role",
            "left_function_identity": "str",
            "right_function_identity": "str",
            "left_path_suffix": "str",
            "right_path_suffix": "str",
            "same_normalized_ast": "true",
            "same_function_identity": "true",
            "same_path_suffix": "true",
            "compatible_repository_dates": "true",
            "public_shared_package_history": "true",
        },
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("d1_visible_cache", "public_metadata_snapshot"),
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
        },
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("public_metadata_snapshot",),
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
        },
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("public_metadata_snapshot",),
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
            "d1_visible_evidence_identity": "sha256",
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
        {
            "left_stable_key": "str",
            "right_stable_key": "str",
            "hamming_distance": "int",
            "d1_visible_evidence_identity": "sha256",
        },
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


def allocation_repository_commitment(entries: Sequence[AllocationEntry]) -> str:
    normalized = tuple(sorted(entries, key=lambda entry: entry.repository))
    repositories = [entry.repository for entry in normalized]
    if len(repositories) != len(set(repositories)):
        raise ValueError("duplicate allocation repository")
    for entry in normalized:
        normalize_repository(entry.repository)
        if entry.role not in ROLE_ORDER:
            raise ValueError("invalid allocation role")
        if isinstance(entry.row_count, bool) or not isinstance(entry.row_count, int):
            raise ValueError("invalid allocation row count")
    rows = [
        {"repository": entry.repository, "role": entry.role, "row_count": entry.row_count}
        for entry in normalized
    ]
    return sha256_text(canonical_json({"allocation_repositories": rows}))


def validate_canonical_allocation_entries(entries: Sequence[AllocationEntry]) -> str:
    normalized = tuple(sorted(entries, key=lambda entry: entry.repository))
    if len(normalized) != ALLOCATION_REPOSITORY_COUNT:
        raise ValueError("noncanonical allocation repository count")
    role_counts = {role: 0 for role in ROLE_ORDER}
    row_counts = {role: 0 for role in ROLE_ORDER}
    for entry in normalized:
        role_counts[entry.role] += 1
        row_counts[entry.role] += entry.row_count
    if role_counts != ALLOCATION_ROLE_REPOSITORY_COUNTS:
        raise ValueError("noncanonical allocation role repository counts")
    if row_counts != ALLOCATION_ROLE_ROW_COUNTS:
        raise ValueError("noncanonical allocation role row counts")
    commitment = allocation_repository_commitment(normalized)
    if commitment != ALLOCATION_REPOSITORY_COMMITMENT_SHA256:
        raise ValueError("noncanonical allocation repository commitment")
    return commitment


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
    elif isinstance(value, str) and len(value) > MAX_EVIDENCE_STRING_LENGTH:
        raise ValueError("evidence string exceeds frozen bound")


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
    if len(value) > MAX_EVIDENCE_STRING_LENGTH:
        raise ValueError("evidence source identity exceeds frozen bound")
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


def validate_evidence_source_bundle(
    rule: EdgeRule,
    evidence_sources: Mapping[str, str],
) -> dict[str, str]:
    required = set(rule.evidence_source_requirements)
    observed = set(evidence_sources)
    if observed != required:
        raise ValueError("evidence-source bundle must contain exactly the required source types")
    return {key: validate_source_identity(evidence_sources[key]) for key in sorted(observed)}


def source_bundle_commitment(evidence_sources: Mapping[str, str]) -> str:
    return sha256_text(canonical_json(dict(sorted(evidence_sources.items()))))


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


def make_source_record(
    source_type: str,
    *,
    payload: Mapping[str, Any],
    provenance: Mapping[str, Any],
    status: str = "COMPLETE",
) -> SourceEvidenceRecord:
    if source_type not in ALLOWED_EVIDENCE_SOURCES:
        raise ValueError("invalid source record type")
    if status not in METADATA_STATUSES and status != "COMPLETE":
        raise ValueError("invalid source record status")
    validate_payload_firewall(payload)
    validate_payload_firewall(provenance)
    base = {
        "source_type": source_type,
        "payload": dict(payload),
        "provenance": dict(provenance),
        "status": status,
    }
    source_identity = sha256_text(canonical_json(base))
    record = {**base, "source_identity": source_identity}
    return SourceEvidenceRecord(
        source_type=source_type,
        source_identity=source_identity,
        payload=dict(payload),
        provenance=dict(provenance),
        status=status,
        record_sha256=sha256_text(canonical_json(record)),
    )


def source_record_from_record(record: Mapping[str, Any]) -> SourceEvidenceRecord:
    return SourceEvidenceRecord(
        source_type=str(record["source_type"]),
        source_identity=str(record["source_identity"]),
        payload=dict(record["payload"]),
        provenance=dict(record["provenance"]),
        status=str(record["status"]),
        record_sha256=str(record["record_sha256"]),
    )


def validate_source_record(record: SourceEvidenceRecord) -> None:
    expected = make_source_record(
        record.source_type,
        payload=record.payload,
        provenance=record.provenance,
        status=record.status,
    )
    for field in ("source_identity", "record_sha256"):
        if getattr(record, field) != getattr(expected, field):
            raise ValueError(f"tampered source record field: {field}")


def validate_source_registry(
    rule: EdgeRule,
    left: str,
    right: str,
    payload: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord],
) -> None:
    for source_type, source_identity in evidence_sources.items():
        record = source_records.get((source_type, source_identity))
        if (
            record is None
            and source_type == "github_rest"
            and source_identity == evidence_sources.get("public_metadata_snapshot")
        ):
            record = source_records.get(("public_metadata_snapshot", source_identity))
        if record is None:
            raise ValueError(f"missing source record: {source_type}")
        validate_source_record(record)
        if record.source_type != source_type and not (
            source_type == "github_rest"
            and record.source_type == "public_metadata_snapshot"
            and source_identity == evidence_sources.get("public_metadata_snapshot")
        ):
            raise ValueError("source record type mismatch")
        if record.source_identity != source_identity:
            raise ValueError("source record identity mismatch")
        if record.status != "COMPLETE":
            raise ValueError("source record is incomplete")
    if rule.edge_type == "DECLARED_GITHUB_FORK":
        record = source_records[
            ("public_metadata_snapshot", evidence_sources["public_metadata_snapshot"])
        ]
        public = record.payload
        if public.get("fork") is not True:
            raise ValueError("fork source record does not prove fork=true")
        if normalize_repository(str(public.get("child_full_name", ""))) not in {left, right}:
            raise ValueError("fork source record child endpoint mismatch")
        if normalize_repository(str(public.get("parent_or_source_full_name", ""))) not in {
            left,
            right,
        }:
            raise ValueError("fork source record parent endpoint mismatch")
        if public.get("left_repository_id") != payload["left_repository_id"]:
            raise ValueError("fork source record repository ID mismatch")
        if public.get("right_repository_id") != payload["right_repository_id"]:
            raise ValueError("fork source record repository ID mismatch")
    elif rule.edge_type == "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY":
        record = source_records[("d1_visible_cache", evidence_sources["d1_visible_cache"])]
        d1_payload = record.payload
        for field in (
            "identity_scope",
            "matching_content_sha256",
            "left_scope_identity",
            "right_scope_identity",
            "generated_vendor_boilerplate_exclusion",
        ):
            if d1_payload.get(field) != payload[field]:
                raise ValueError("D1 source record does not support exact source identity")
    elif rule.edge_type == "EXACT_AST_WITH_CORROBORATING_PROVENANCE":
        record = source_records[("d1_visible_cache", evidence_sources["d1_visible_cache"])]
        d1_payload = record.payload
        for field in (
            "left_stable_key",
            "right_stable_key",
            "normalized_ast_sha256",
            "visible_role_left",
            "visible_role_right",
        ):
            if d1_payload.get(field) != payload[field]:
                raise ValueError("D1 source record does not support exact AST evidence")


def validate_rule_semantics(
    rule: EdgeRule,
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
    rule: EdgeRule,
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


def make_evidence_edge(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
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
        protocol_sha256=protocol_contract()["protocol_sha256"],
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


def _reject_duplicate_edges(edges: Sequence[EvidenceEdge]) -> None:
    seen: set[str] = set()
    for edge in edges:
        if edge.edge_id in seen:
            raise ValueError("duplicate edge ID")
        seen.add(edge.edge_id)


def build_components(
    repositories: Sequence[str],
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str,
    candidates: Mapping[str, EvidenceCandidate] | None = None,
    dispositions: Mapping[str, ManualReviewDisposition] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> list[dict[str, Any]]:
    normalized = sorted({normalize_repository(repository) for repository in repositories})
    allocation_set = set(normalized)
    _reject_duplicate_edges(edges)
    uf = UnionFind(normalized)
    for edge in sorted(edges, key=lambda item: item.edge_id):
        candidate = candidates.get(edge.candidate_id) if candidates is not None else None
        disposition = (
            dispositions.get(edge.disposition_id)
            if dispositions is not None and edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=protocol_sha256,
            allocation_repositories=allocation_set,
            source_records=source_records,
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
    protocol_sha256 = protocol_contract()["protocol_sha256"]
    normalized = []
    for component in components:
        repositories = sorted(normalize_repository(item) for item in component["repositories"])
        if int(component["repository_count"]) != len(repositories):
            raise ValueError("component repository_count is malformed")
        expected_id = component_id(repositories, protocol_sha256)
        if component["component_id"] != expected_id:
            raise ValueError("component_id does not match members")
        normalized.append(
            {
                "component_id": expected_id,
                "repositories": repositories,
                "repository_count": len(repositories),
            }
        )
    normalized = sorted(normalized, key=canonical_json)
    return sha256_text(canonical_json({"components": normalized}))


def edge_commitment(
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str | None = None,
    candidates: Mapping[str, EvidenceCandidate] | None = None,
    dispositions: Mapping[str, ManualReviewDisposition] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> str:
    _reject_duplicate_edges(edges)
    active_protocol = protocol_sha256 or protocol_contract()["protocol_sha256"]
    for edge in edges:
        candidate = candidates.get(edge.candidate_id) if candidates is not None else None
        disposition = (
            dispositions.get(edge.disposition_id)
            if dispositions is not None and edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=active_protocol,
            source_records=source_records,
        )
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
    unexpected = set(payload) - PUBLIC_METADATA_FIELDS
    if unexpected:
        raise ValueError(f"unexpected public metadata fields: {sorted(unexpected)}")
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
            "allocation_repository_commitment_sha256": ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
            "repository_count": ALLOCATION_REPOSITORY_COUNT,
            "role_repository_counts": ALLOCATION_ROLE_REPOSITORY_COUNTS,
            "role_row_counts": ALLOCATION_ROLE_ROW_COUNTS,
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
            "duplicate_edge_ids": "rejected before counts, commitments, publication, and union",
            "union_find_uses_connecting_edges_only": True,
            "reviewed_edges_require_validated_candidate_and_disposition_before_union": True,
            "component_id": "sha256(canonical_json(sorted members + protocol sha256))",
            "transitivity": "applies only through connecting edges",
        },
        "resolved_edge_validation": {
            "approved_required_edges_validate_against_candidate_and_disposition": True,
            "recompute_fields": [
                "canonical endpoint order",
                "edge_id",
                "candidate_id",
                "payload hash",
                "source-bundle hash",
                "evidence commitment",
                "review disposition identity",
                "connecting status",
                "review status",
                "confidence category",
                "human-review requirement",
                "rule version",
                "frozen reason",
            ],
        },
        "evidence_source_binding": {
            "source_requirements_are_conjunctive": True,
            "payload_evidence_identities_must_match_source_bundle_identities": True,
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
                "source_records",
                "evidence_candidates",
                "typed_evidence_edges",
                "manual_review_dispositions",
                "component_memberships",
                "phase_commitments",
            ],
            "sqlite_pragmas": {"journal_mode": "WAL", "synchronous": "FULL", "foreign_keys": "ON"},
            "resolved_edge_foreign_keys": {
                "candidate_id": "evidence_candidates(candidate_id)",
                "disposition_id": "manual_review_dispositions(disposition_id)",
            },
            "final_disposition_uniqueness": "one final disposition per candidate",
        },
        "progress_contract": {
            "fields": [
                "phase",
                "completed",
                "total",
                "percentage",
                "cache_hits",
                "cache_misses",
                "request_rate",
                "elapsed_time",
                "ETA",
            ],
            "checkpoint_cadence": "after every durable phase transition and bounded request batch",
            "phase_status_enum": ["PENDING", "IN_PROGRESS", "COMPLETE", "INCOMPLETE", "FAILED"],
            "resume_cursor_requirements": [
                "cursor value",
                "cursor input identity",
                "phase commitment before cursor",
            ],
            "phase_commitment_requirements": [
                "phase name",
                "status",
                "input identities",
                "ordered output commitment",
                "cache identity",
            ],
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
            "materiality_inputs": [
                "number of connecting family components crossing roles",
                "repositories affected by role pair",
                "rows affected by role pair",
                "largest component",
                "fraction of c0_fit rows affected",
                "fraction of c0_iteration rows affected",
                "hard-edge crossing count",
                "conditional-edge crossing count",
                "whether a valid family-disjoint allocation remains feasible",
            ],
            "materiality_threshold": "no automatic materiality threshold in v1",
            "explicit_human_review_required": True,
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


def validate_firewall_booleans(d1_data: Mapping[str, Any], d11_data: Mapping[str, Any]) -> None:
    common_firewall_keys = (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c0_selection_rows_accessed",
        "c1_rows_accessed",
        "hidden_row_content_accessed",
    )
    d11_firewall_keys = (
        *common_firewall_keys,
        "c0_selection_row_content_accessed",
        "c1_row_content_accessed",
    )
    d11_firewall_booleans = d11_data.get("firewall_booleans", {})
    for key in d11_firewall_keys:
        if key not in d11_firewall_booleans or d11_firewall_booleans[key] is not False:
            raise ValueError(f"hidden-row firewall field is true: {key}")
    d1_firewall = d1_data.get("firewall_booleans", d1_data)
    for key in common_firewall_keys:
        if key not in d1_firewall or d1_firewall[key] is not False:
            raise ValueError(f"D1 hidden-row firewall field is not exactly false: {key}")


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
            CREATE TABLE IF NOT EXISTS source_records (
                source_type TEXT NOT NULL,
                source_identity TEXT NOT NULL,
                record_json TEXT NOT NULL,
                record_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY(source_type, source_identity)
            );
            CREATE TABLE IF NOT EXISTS typed_evidence_edges (
                edge_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                disposition_id TEXT,
                left_repository TEXT NOT NULL,
                right_repository TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                connecting INTEGER NOT NULL,
                edge_json TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES evidence_candidates(candidate_id),
                FOREIGN KEY(disposition_id) REFERENCES manual_review_dispositions(disposition_id),
                FOREIGN KEY(left_repository) REFERENCES allocation_repositories(repository),
                FOREIGN KEY(right_repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS evidence_candidates (
                candidate_id TEXT PRIMARY KEY,
                left_repository TEXT NOT NULL,
                right_repository TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                candidate_json TEXT NOT NULL,
                evidence_commitment TEXT NOT NULL,
                FOREIGN KEY(left_repository) REFERENCES allocation_repositories(repository),
                FOREIGN KEY(right_repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS manual_review_dispositions (
                disposition_id TEXT PRIMARY KEY,
                edge_candidate_id TEXT NOT NULL,
                protocol_sha256 TEXT NOT NULL,
                evidence_commitment TEXT NOT NULL,
                disposition TEXT NOT NULL,
                reviewer_identity TEXT NOT NULL,
                review_timestamp TEXT NOT NULL,
                bounded_reason TEXT NOT NULL,
                FOREIGN KEY(edge_candidate_id) REFERENCES evidence_candidates(candidate_id),
                UNIQUE(edge_candidate_id)
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
        expected = self.identity.as_mapping()
        rows = {
            str(key): str(value)
            for key, value in self.connection.execute("SELECT key, value FROM cache_identity")
        }
        if rows:
            if set(rows) != set(expected):
                raise ValueError("family graph cache identity key set mismatch")
            for key, value in expected.items():
                if rows[key] != value:
                    raise ValueError(f"family graph cache identity mismatch: {key}")
        elif self._has_data_rows():
            raise ValueError("family graph cache contains data without identity")
        self.connection.executemany(
            """
            INSERT INTO cache_identity(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            sorted(self.identity.as_mapping().items()),
        )
        self.connection.commit()

    def _has_data_rows(self) -> bool:
        for table in (
            "allocation_repositories",
            "repository_metadata_snapshots",
            "source_records",
            "evidence_candidates",
            "typed_evidence_edges",
            "manual_review_dispositions",
            "component_memberships",
            "phase_commitments",
        ):
            row = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            if int(row[0]):
                return True
        return False

    def put_allocation_repositories(self, entries: Sequence[AllocationEntry]) -> None:
        commitment = validate_canonical_allocation_entries(entries)
        existing = {
            str(repository): (str(role), int(row_count))
            for repository, role, row_count in self.connection.execute(
                "SELECT repository, role, row_count FROM allocation_repositories"
            )
        }
        incoming = {entry.repository: (entry.role, entry.row_count) for entry in entries}
        if existing and existing != incoming:
            raise ValueError("allocation repositories differ under the same cache identity")
        self.connection.executemany(
            """
            INSERT INTO allocation_repositories(repository, role, row_count)
            VALUES (?, ?, ?)
            ON CONFLICT(repository) DO NOTHING
            """,
            [(entry.repository, entry.role, entry.row_count) for entry in entries],
        )
        self.connection.commit()
        self.connection.execute(
            """
            INSERT INTO phase_commitments(phase, status, commitment_sha256, metadata_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phase) DO UPDATE SET
                status = excluded.status,
                commitment_sha256 = excluded.commitment_sha256,
                metadata_json = excluded.metadata_json
            """,
            (
                "initial_allocation",
                "COMPLETE",
                commitment,
                canonical_json(
                    {
                        "repository_count": ALLOCATION_REPOSITORY_COUNT,
                        "role_repository_counts": ALLOCATION_ROLE_REPOSITORY_COUNTS,
                        "role_row_counts": ALLOCATION_ROLE_ROW_COUNTS,
                    }
                ),
            ),
        )
        self.connection.commit()

    def put_canonical_allocation_manifest(self, canonical_path: Path) -> str:
        entries = load_allocation_manifest(
            canonical_path,
            expected_sha256=ALLOCATION_MANIFEST_SHA256,
        )
        self.put_allocation_repositories(entries)
        return ALLOCATION_REPOSITORY_COMMITMENT_SHA256

    def put_evidence_candidate(self, candidate: EvidenceCandidate) -> None:
        validate_evidence_candidate(candidate)
        record_json = canonical_json(candidate.as_record())
        existing = self.connection.execute(
            "SELECT candidate_json FROM evidence_candidates WHERE candidate_id = ?",
            (candidate.candidate_id,),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != record_json:
                raise ValueError("conflicting evidence candidate content")
            return
        self.connection.execute(
            """
            INSERT INTO evidence_candidates(
                candidate_id, left_repository, right_repository, edge_type,
                candidate_json, evidence_commitment
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.candidate_id,
                candidate.left_repository,
                candidate.right_repository,
                candidate.edge_type,
                record_json,
                candidate.evidence_commitment,
            ),
        )
        self.connection.commit()

    def put_manual_review_disposition(self, disposition: ManualReviewDisposition) -> None:
        candidate = self.get_evidence_candidate(disposition.edge_candidate_id)
        validate_manual_review_disposition(
            disposition,
            candidate,
            protocol_sha256=self.identity.family_protocol_sha256,
        )
        existing = self.get_final_disposition_for_candidate(disposition.edge_candidate_id)
        if existing is not None:
            if existing != disposition:
                raise ValueError("conflicting final disposition for candidate")
            return
        self.connection.execute(
            """
            INSERT INTO manual_review_dispositions(
                disposition_id, edge_candidate_id, protocol_sha256, evidence_commitment,
                disposition, reviewer_identity, review_timestamp, bounded_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                disposition.disposition_id,
                disposition.edge_candidate_id,
                disposition.protocol_sha256,
                disposition.evidence_commitment,
                disposition.disposition,
                disposition.reviewer_identity,
                disposition.review_timestamp,
                disposition.bounded_reason,
            ),
        )
        self.connection.commit()

    def put_resolved_edge(self, edge: EvidenceEdge) -> None:
        candidate = self.get_evidence_candidate(edge.candidate_id)
        disposition = (
            self.get_manual_review_disposition(edge.disposition_id)
            if edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=self.identity.family_protocol_sha256,
            source_records=self.get_source_registry(),
        )
        record_json = canonical_json(edge.as_record())
        existing = self.connection.execute(
            "SELECT edge_json FROM typed_evidence_edges WHERE edge_id = ?",
            (edge.edge_id,),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != record_json:
                raise ValueError("conflicting resolved edge content")
            return
        self.connection.execute(
            """
            INSERT INTO typed_evidence_edges(
                edge_id, candidate_id, disposition_id, left_repository, right_repository,
                edge_type, connecting, edge_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge.edge_id,
                edge.candidate_id,
                edge.disposition_id,
                edge.left_repository,
                edge.right_repository,
                edge.edge_type,
                int(edge.connecting),
                record_json,
            ),
        )
        self.connection.commit()

    def put_source_record(self, record: SourceEvidenceRecord) -> None:
        validate_source_record(record)
        record_json = canonical_json(record.as_record())
        existing = self.connection.execute(
            """
            SELECT record_json FROM source_records
            WHERE source_type = ? AND source_identity = ?
            """,
            (record.source_type, record.source_identity),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != record_json:
                raise ValueError("conflicting source record content")
            return
        self.connection.execute(
            """
            INSERT INTO source_records(
                source_type, source_identity, record_json, record_sha256, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.source_type,
                record.source_identity,
                record_json,
                record.record_sha256,
                record.status,
            ),
        )
        self.connection.commit()

    def get_source_record(self, source_type: str, source_identity: str) -> SourceEvidenceRecord:
        row = self.connection.execute(
            """
            SELECT record_json FROM source_records
            WHERE source_type = ? AND source_identity = ?
            """,
            (source_type, source_identity),
        ).fetchone()
        if row is None:
            raise ValueError("source record not found")
        record = source_record_from_record(json.loads(str(row[0])))
        validate_source_record(record)
        if record.source_type != source_type or record.source_identity != source_identity:
            raise ValueError("source record type or identity mismatch")
        return record

    def get_source_registry(self) -> dict[tuple[str, str], SourceEvidenceRecord]:
        registry: dict[tuple[str, str], SourceEvidenceRecord] = {}
        for source_type, source_identity in self.connection.execute(
            "SELECT source_type, source_identity FROM source_records"
        ):
            record = self.get_source_record(str(source_type), str(source_identity))
            registry[(record.source_type, record.source_identity)] = record
        return registry

    def get_evidence_candidate(self, candidate_id: str) -> EvidenceCandidate:
        row = self.connection.execute(
            "SELECT candidate_json FROM evidence_candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise ValueError("evidence candidate not found")
        candidate = evidence_candidate_from_record(json.loads(str(row[0])))
        validate_evidence_candidate(candidate)
        return candidate

    def get_manual_review_disposition(self, disposition_id: str | None) -> ManualReviewDisposition:
        if disposition_id is None:
            raise ValueError("manual disposition not found")
        row = self.connection.execute(
            """
            SELECT disposition_id, edge_candidate_id, protocol_sha256, evidence_commitment,
                   disposition, reviewer_identity, review_timestamp, bounded_reason
            FROM manual_review_dispositions WHERE disposition_id = ?
            """,
            (disposition_id,),
        ).fetchone()
        if row is None:
            raise ValueError("manual disposition not found")
        disposition = manual_review_disposition_from_record(
            {
                "disposition_id": row[0],
                "edge_candidate_id": row[1],
                "protocol_sha256": row[2],
                "evidence_commitment": row[3],
                "disposition": row[4],
                "reviewer_identity": row[5],
                "review_timestamp": row[6],
                "bounded_reason": row[7],
            }
        )
        candidate = self.get_evidence_candidate(disposition.edge_candidate_id)
        validate_manual_review_disposition(
            disposition,
            candidate,
            protocol_sha256=self.identity.family_protocol_sha256,
        )
        return disposition

    def get_final_disposition_for_candidate(
        self,
        candidate_id: str,
    ) -> ManualReviewDisposition | None:
        row = self.connection.execute(
            "SELECT disposition_id FROM manual_review_dispositions WHERE edge_candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        return self.get_manual_review_disposition(str(row[0]))

    def get_resolved_edge(self, edge_id: str) -> EvidenceEdge:
        row = self.connection.execute(
            "SELECT edge_json FROM typed_evidence_edges WHERE edge_id = ?",
            (edge_id,),
        ).fetchone()
        if row is None:
            raise ValueError("resolved edge not found")
        edge = evidence_edge_from_record(json.loads(str(row[0])))
        candidate = self.get_evidence_candidate(edge.candidate_id)
        disposition = (
            self.get_manual_review_disposition(edge.disposition_id)
            if edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=self.identity.family_protocol_sha256,
            source_records=self.get_source_registry(),
        )
        return edge


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
    d1_data = json.loads(d1.read_text(encoding="utf-8"))
    d11_data = json.loads(d11.read_text(encoding="utf-8"))
    for artifact in (firewall_data, d1_data, d11_data):
        if not isinstance(artifact, dict):
            raise ValueError("canonical protocol input must be a JSON object")
    if firewall_data.get("allocation_context_sha256") != ALLOCATION_CONTEXT_SHA256:
        raise ValueError("allocation context SHA-256 mismatch")
    classification = d11_data.get("classification", {})
    if classification.get("overall_outcome") != "D1_CLASSIFICATION_INCONCLUSIVE":
        raise ValueError("D1.1 outcome is not inconclusive")
    if classification.get("family_identity_rule_status") != "NOT_FROZEN":
        raise ValueError("D1.1 family identity rule status is not frozen as NOT_FROZEN")
    common_firewall_keys = (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c0_selection_rows_accessed",
        "c1_rows_accessed",
        "hidden_row_content_accessed",
    )
    d11_firewall_keys = (
        *common_firewall_keys,
        "c0_selection_row_content_accessed",
        "c1_row_content_accessed",
    )
    d11_firewall_booleans = d11_data.get("firewall_booleans", {})
    for key in d11_firewall_keys:
        if key not in d11_firewall_booleans or d11_firewall_booleans[key] is not False:
            raise ValueError(f"hidden-row firewall field is true: {key}")
    d1_firewall = d1_data.get("firewall_booleans", d1_data)
    for key in common_firewall_keys:
        if key not in d1_firewall or d1_firewall[key] is not False:
            raise ValueError(f"D1 hidden-row firewall field is not exactly false: {key}")
    return {
        "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
        "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
        "allocation_repository_commitment_sha256": ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
    }


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
            dispositions.get(item.disposition_id)
            if item.disposition_id is not None
            else None
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

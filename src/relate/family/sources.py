"""Pure source-evidence construction and validation.

No database access, CLI parsing, file publication or workflow orchestration.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.models import EdgeRule, SourceEvidenceRecord
from relate.family.repositories import normalize_repository

# Patterns for source identity validation.
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


def payload_hash(payload: Mapping[str, Any]) -> str:
    validate_payload_firewall(payload)
    return sha256_text(canonical_json(payload))


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

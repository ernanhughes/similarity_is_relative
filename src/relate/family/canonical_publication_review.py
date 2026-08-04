"""Read-only review and closure for one-shot canonical publication evidence."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.evidence.immutable import refuse_overwrite
from relate.family.canonical_publication import (
    AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    PAYLOAD_POLICY,
    PUBLICATION_CLAIM_SCHEMA_ID,
    PUBLICATION_FAILURE_SCHEMA_ID,
    PUBLICATION_RECEIPT_SCHEMA_ID,
    PUBLICATION_TRACE_SCHEMA_ID,
    ExecutableCanonicalFamilyPublicationAuthorization,
    ExecutableCanonicalFamilyPublicationRequest,
    compute_canonical_publisher_source_identity,
    executable_canonical_publication_authorization_v2_from_record,
    executable_canonical_publication_request_commitment,
    executable_canonical_publication_request_v2_from_record,
)
from relate.family.canonical_publication_authorization import (
    AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    CANONICAL_PUBLICATION_SCOPE,
    CONTINUING_PROHIBITIONS,
    CanonicalFamilyPublicationAuthorization,
    CanonicalFamilyPublicationCandidate,
    CanonicalFamilyPublicationRequest,
    canonical_family_publication_authorization_from_record,
    canonical_family_publication_candidate_commitment,
    canonical_family_publication_candidate_from_record,
    canonical_family_publication_request_commitment,
    canonical_family_publication_request_from_record,
    validate_canonical_family_publication_authorization,
)
from relate.family.execution_review import (
    CanonicalExecutionReviewBundle,
    canonical_execution_review_bundle_commitment,
    canonical_execution_review_bundle_from_record,
)
from relate.family.review import reject_canonical_path
from relate.family.sources import parse_timestamp, validate_source_identity
from relate.family.workflow.models import validate_sha256_identity

PUBLICATION_REVIEW_REPORT_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-evidence-review-report-v1"
)
PUBLICATION_CLOSURE_DISPOSITION_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-closure-disposition-v1"
)
PUBLICATION_CLOSURE_BUNDLE_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-closure-bundle-v1"
)
PUBLICATION_REVIEW_SCOPE: Final = "CANONICAL_PUBLICATION_EVIDENCE_INTEGRITY_AND_CLOSURE_ONLY"
CLOSE_COMPLETED_CANONICAL_PUBLICATION: Final = "CLOSE_COMPLETED_CANONICAL_PUBLICATION"
CLOSE_FAILED_PUBLICATION_WITHOUT_CANONICAL_ARTIFACT: Final = (
    "CLOSE_FAILED_PUBLICATION_WITHOUT_CANONICAL_ARTIFACT"
)
ACKNOWLEDGE_CANONICAL_ARTIFACT_WITH_INCOMPLETE_AUDIT_FINALIZATION: Final = (
    "ACKNOWLEDGE_CANONICAL_ARTIFACT_WITH_INCOMPLETE_AUDIT_FINALIZATION"
)
WITHHOLD_CANONICAL_PUBLICATION_CLOSURE: Final = "WITHHOLD_CANONICAL_PUBLICATION_CLOSURE"
ALLOWED_CLOSURE_DISPOSITIONS: Final = (
    CLOSE_COMPLETED_CANONICAL_PUBLICATION,
    CLOSE_FAILED_PUBLICATION_WITHOUT_CANONICAL_ARTIFACT,
    ACKNOWLEDGE_CANONICAL_ARTIFACT_WITH_INCOMPLETE_AUDIT_FINALIZATION,
    WITHHOLD_CANONICAL_PUBLICATION_CLOSURE,
)
NOT_DETERMINED: Final[tuple[str, ...]] = (
    "MATERIAL_CONTAMINATION",
    "MATERIALITY",
    "ALLOCATION_VALIDITY",
    "ALLOCATION_CHANGE",
    "REALLOCATION",
    "MODEL_REFIT",
    "C0_REPLAY",
    "PROTECTED_ROW_ACCESS",
    "D2_AUTHORIZATION",
)
_MAX_REASON_LENGTH: Final = 500
_COMPLETED_EVENTS: Final[tuple[str, ...]] = (
    "CLAIM_PERSISTED",
    "PUBLISHER_IDENTITY_VERIFIED",
    "CANONICAL_PARENT_VERIFIED",
    "CANDIDATE_BYTES_VERIFIED",
    "CANONICAL_DESTINATION_CREATED",
    "CANONICAL_DESTINATION_VERIFIED",
)


class CanonicalPublicationTerminalStatus(StrEnum):
    VALID_COMPLETED = "VALID_COMPLETED"
    VALID_FAILED_BEFORE_CANONICAL_CREATION = "VALID_FAILED_BEFORE_CANONICAL_CREATION"
    VALID_CANONICAL_FILE_CREATED_AUDIT_FAILED = "VALID_CANONICAL_FILE_CREATED_AUDIT_FAILED"
    INCOMPLETE_TERMINAL_EVIDENCE = "INCOMPLETE_TERMINAL_EVIDENCE"


@dataclass(frozen=True)
class CanonicalPublicationRecordChainValidation:
    stage_2j_request_commitment: str
    stage_2j_authorization_id: str
    executable_request_commitment: str
    executable_authorization_id: str
    candidate_commitment: str
    candidate_file_sha256: str
    execution_review_bundle_commitment: str
    canonical_destination: str
    canonical_parent: str
    audit_work_dir: str
    publisher_source_identity: str
    family_protocol_sha256: str
    execution_review_report_commitment: str
    execution_review_disposition_id: str

    def as_record(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class CanonicalPublicationEvidenceReviewReport:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)

    @property
    def report_commitment(self) -> str:
        return str(self.record["report_commitment"])


@dataclass(frozen=True)
class CanonicalPublicationClosureDisposition:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


@dataclass(frozen=True)
class CanonicalPublicationClosureBundle:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    _reject_nonfinite(value, label=label)
    return dict(value)


def _reject_nonfinite(value: Any, *, label: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} contains a nonfinite number")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(item, label=f"{label}.{key}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nonfinite(item, label=f"{label}[{index}]")


def _commit(record: dict[str, Any], field: str) -> str:
    payload = dict(record)
    declared = payload.pop(field, None)
    observed = sha256_text(canonical_json(payload))
    if declared != observed:
        raise ValueError(f"{field} is stale")
    return observed


def _reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("bounded reason must be nonempty")
    stripped = value.strip()
    if len(stripped) > _MAX_REASON_LENGTH:
        raise ValueError("bounded reason exceeds length limit")
    return stripped


def _validate_relative_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise ValueError(f"{label} must be a repository-relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} is not normalized")
    return path.as_posix()


def _load_optional_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    return _require_object(
        json.loads(path.read_text(encoding="utf-8")), label=str(path)
    ), sha256_file(path)


def _validate_expected_fields(
    record: dict[str, Any], expected: dict[str, Any], *, label: str
) -> None:
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"{label} {key} mismatch")


def _expected_claim_fields(chain: CanonicalPublicationRecordChainValidation) -> dict[str, Any]:
    return {
        "executable_request_commitment": chain.executable_request_commitment,
        "executable_authorization_id": chain.executable_authorization_id,
        "stage_2j_publication_request_commitment": chain.stage_2j_request_commitment,
        "stage_2j_publication_authorization_id": chain.stage_2j_authorization_id,
        "family_protocol_sha256": chain.family_protocol_sha256,
        "canonical_publication_candidate_commitment": chain.candidate_commitment,
        "canonical_publication_candidate_file_sha256": chain.candidate_file_sha256,
        "accepted_execution_review_bundle_commitment": chain.execution_review_bundle_commitment,
        "intended_canonical_destination": chain.canonical_destination,
        "intended_canonical_parent": chain.canonical_parent,
        "canonical_publisher_source_identity": chain.publisher_source_identity,
        "payload_policy": PAYLOAD_POLICY,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }


def _expected_receipt_fields(chain: CanonicalPublicationRecordChainValidation) -> dict[str, Any]:
    return {
        "publication_status": "COMPLETED",
        "executable_request_commitment": chain.executable_request_commitment,
        "executable_authorization_id": chain.executable_authorization_id,
        "stage_2j_publication_request_commitment": chain.stage_2j_request_commitment,
        "stage_2j_publication_authorization_id": chain.stage_2j_authorization_id,
        "family_protocol_sha256": chain.family_protocol_sha256,
        "canonical_publisher_source_identity": chain.publisher_source_identity,
        "canonical_publication_candidate_commitment": chain.candidate_commitment,
        "source_candidate_file_sha256": chain.candidate_file_sha256,
        "published_destination_file_sha256": chain.candidate_file_sha256,
        "accepted_execution_review_bundle_commitment": chain.execution_review_bundle_commitment,
        "execution_review_report_commitment": chain.execution_review_report_commitment,
        "execution_review_disposition_id": chain.execution_review_disposition_id,
        "canonical_destination": chain.canonical_destination,
        "canonical_parent": chain.canonical_parent,
        "payload_policy": PAYLOAD_POLICY,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }


def _expected_failure_fields(chain: CanonicalPublicationRecordChainValidation) -> dict[str, Any]:
    return {
        "executable_request_commitment": chain.executable_request_commitment,
        "executable_authorization_id": chain.executable_authorization_id,
        "stage_2j_publication_request_commitment": chain.stage_2j_request_commitment,
        "stage_2j_publication_authorization_id": chain.stage_2j_authorization_id,
        "canonical_destination": chain.canonical_destination,
        "canonical_publication_candidate_commitment": chain.candidate_commitment,
        "canonical_publication_candidate_file_sha256": chain.candidate_file_sha256,
    }


def canonical_publication_claim_from_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _require_object(record, label="canonical publication claim")
    expected = {
        "schema_id",
        "executable_request_commitment",
        "executable_authorization_id",
        "stage_2j_publication_request_commitment",
        "stage_2j_publication_authorization_id",
        "family_protocol_sha256",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
        "accepted_execution_review_bundle_commitment",
        "intended_canonical_destination",
        "intended_canonical_parent",
        "canonical_publisher_source_identity",
        "payload_policy",
        "continuing_prohibitions",
        "claim_timestamp",
        "claim_commitment",
    }
    if set(data) != expected:
        raise ValueError("canonical publication claim fields are malformed")
    if data["schema_id"] != PUBLICATION_CLAIM_SCHEMA_ID:
        raise ValueError("unsupported canonical publication claim schema")
    for key in (
        "executable_request_commitment",
        "family_protocol_sha256",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
        "accepted_execution_review_bundle_commitment",
        "canonical_publisher_source_identity",
    ):
        validate_sha256_identity(data[key], label=key)
    _validate_relative_path(data["intended_canonical_destination"], label="destination")
    _validate_relative_path(data["intended_canonical_parent"], label="parent")
    parse_timestamp(data["claim_timestamp"])
    if data["payload_policy"] != PAYLOAD_POLICY:
        raise ValueError("claim payload policy mismatch")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("claim prohibitions changed")
    _commit(data, "claim_commitment")
    return data


def canonical_publication_trace_from_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _require_object(record, label="canonical publication trace")
    if set(data) != {"schema_id", "events"}:
        raise ValueError("canonical publication trace fields are malformed")
    if data["schema_id"] != PUBLICATION_TRACE_SCHEMA_ID:
        raise ValueError("unsupported canonical publication trace schema")
    if not isinstance(data["events"], list):
        raise ValueError("trace events must be a list")
    allowed = set(_COMPLETED_EVENTS) | {"PUBLICATION_FAILED"}
    seen: set[str] = set()
    for event in data["events"]:
        item = _require_object(event, label="trace event")
        event_type = item.get("event_type")
        if event_type not in allowed:
            raise ValueError("unsupported trace event type")
        if event_type == "RECEIPT_PERSISTED":
            raise ValueError("receipt persistence is not a trace event")
        parse_timestamp(item["timestamp"])
        for key, value in item.items():
            if key.endswith("_sha256") and value is not None:
                validate_sha256_identity(value, label=key)
            if key in {"destination", "failure_phase"} and value is not None:
                _validate_relative_path(value, label=key)
            if key == "bounded_message" and value is not None and len(str(value)) > 500:
                raise ValueError("trace bounded message is too long")
        if event_type in seen:
            raise ValueError("duplicate trace event")
        seen.add(str(event_type))
    return data


def canonical_publication_receipt_from_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _require_object(record, label="canonical publication receipt")
    expected = {
        "schema_id",
        "publication_status",
        "executable_request_commitment",
        "executable_authorization_id",
        "claim_commitment",
        "stage_2j_publication_request_commitment",
        "stage_2j_publication_authorization_id",
        "family_protocol_sha256",
        "canonical_publisher_source_identity",
        "canonical_publication_candidate_commitment",
        "source_candidate_file_sha256",
        "published_destination_file_sha256",
        "accepted_execution_review_bundle_commitment",
        "execution_review_report_commitment",
        "execution_review_disposition_id",
        "canonical_destination",
        "canonical_parent",
        "created_parent_directories",
        "payload_policy",
        "continuing_prohibitions",
        "trace_file_sha256",
        "publication_timestamp",
        "receipt_commitment",
    }
    if set(data) != expected:
        raise ValueError("canonical publication receipt fields are malformed")
    if data["schema_id"] != PUBLICATION_RECEIPT_SCHEMA_ID:
        raise ValueError("unsupported canonical publication receipt schema")
    if data["publication_status"] != "COMPLETED":
        raise ValueError("unsupported publication receipt status")
    for key, value in data.items():
        if key.endswith("_sha256") or key.endswith("_commitment") or key.endswith("_identity"):
            validate_sha256_identity(value, label=key)
    if data["source_candidate_file_sha256"] != data["published_destination_file_sha256"]:
        raise ValueError("receipt source and destination SHA mismatch")
    _validate_relative_path(data["canonical_destination"], label="destination")
    _validate_relative_path(data["canonical_parent"], label="parent")
    if not isinstance(data["created_parent_directories"], list):
        raise ValueError("created parent directories must be a list")
    for path in data["created_parent_directories"]:
        _validate_relative_path(path, label="created parent")
    parse_timestamp(data["publication_timestamp"])
    if data["payload_policy"] != PAYLOAD_POLICY:
        raise ValueError("receipt payload policy mismatch")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("receipt prohibitions changed")
    _commit(data, "receipt_commitment")
    return data


def canonical_publication_failure_from_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _require_object(record, label="canonical publication failure")
    expected = {
        "schema_id",
        "executable_request_commitment",
        "executable_authorization_id",
        "stage_2j_publication_request_commitment",
        "stage_2j_publication_authorization_id",
        "canonical_destination",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
        "failed_phase",
        "bounded_exception_type",
        "bounded_message",
        "claim_persisted",
        "canonical_parent_created",
        "canonical_file_created",
        "canonical_file_sha256",
        "receipt_persisted",
        "failure_timestamp",
        "failure_commitment",
    }
    if set(data) != expected:
        raise ValueError("canonical publication failure fields are malformed")
    if data["schema_id"] != PUBLICATION_FAILURE_SCHEMA_ID:
        raise ValueError("unsupported canonical publication failure schema")
    for key in (
        "executable_request_commitment",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
    ):
        validate_sha256_identity(data[key], label=key)
    if data["canonical_file_sha256"] is not None:
        validate_sha256_identity(data["canonical_file_sha256"], label="canonical_file_sha256")
    for key in ("claim_persisted", "canonical_file_created", "receipt_persisted"):
        if not isinstance(data[key], bool):
            raise ValueError(f"{key} must be boolean")
    if data["receipt_persisted"] is True:
        raise ValueError("failure cannot claim a persisted receipt")
    if data["canonical_file_created"] is False and data["canonical_file_sha256"] is not None:
        raise ValueError("failure cannot bind canonical SHA when file was not created")
    if len(str(data["bounded_exception_type"])) > 120 or len(str(data["bounded_message"])) > 500:
        raise ValueError("failure bounded fields are too long")
    _validate_relative_path(data["canonical_destination"], label="destination")
    if not isinstance(data["canonical_parent_created"], list):
        raise ValueError("created parent directories must be a list")
    for path in data["canonical_parent_created"]:
        _validate_relative_path(path, label="created parent")
    parse_timestamp(data["failure_timestamp"])
    _commit(data, "failure_commitment")
    return data


def validate_canonical_publication_record_chain(
    *,
    repo_root: Path,
    stage_2j_request: CanonicalFamilyPublicationRequest,
    stage_2j_request_file_sha256: str,
    stage_2j_authorization: CanonicalFamilyPublicationAuthorization,
    stage_2j_authorization_file_sha256: str,
    executable_request: ExecutableCanonicalFamilyPublicationRequest,
    executable_request_file_sha256: str,
    executable_authorization: ExecutableCanonicalFamilyPublicationAuthorization,
    executable_authorization_file_sha256: str,
    candidate: CanonicalFamilyPublicationCandidate,
    candidate_file_sha256: str,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    execution_review_bundle_file_sha256: str,
) -> CanonicalPublicationRecordChainValidation:
    root = repo_root.resolve(strict=False)
    for label, value in {
        "stage_2j_request_file_sha256": stage_2j_request_file_sha256,
        "stage_2j_authorization_file_sha256": stage_2j_authorization_file_sha256,
        "executable_request_file_sha256": executable_request_file_sha256,
        "executable_authorization_file_sha256": executable_authorization_file_sha256,
        "candidate_file_sha256": candidate_file_sha256,
        "execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
    }.items():
        validate_sha256_identity(value, label=label)
    s2j_request = canonical_family_publication_request_from_record(stage_2j_request.as_record())
    s2j_auth = canonical_family_publication_authorization_from_record(
        stage_2j_authorization.as_record()
    )
    candidate = canonical_family_publication_candidate_from_record(candidate.as_record())
    bundle = canonical_execution_review_bundle_from_record(execution_review_bundle.as_record())
    executable_request = executable_canonical_publication_request_v2_from_record(
        executable_request.as_record()
    )
    executable_authorization = executable_canonical_publication_authorization_v2_from_record(
        executable_authorization.as_record()
    )
    s2j_req_record = s2j_request.as_record()
    s2j_auth_record = s2j_auth.as_record()
    exec_req_record = executable_request.as_record()
    exec_auth_record = executable_authorization.as_record()
    cand_commitment = canonical_family_publication_candidate_commitment(candidate)
    bundle_commitment = canonical_execution_review_bundle_commitment(bundle)
    if (
        s2j_auth_record["disposition"]
        != AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION
    ):
        raise ValueError("Stage 2J publication authorization is not authorized")
    if (
        exec_auth_record["disposition"]
        != AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION
    ):
        raise ValueError("executable publication authorization is not authorized")
    s2j_request_commitment = canonical_family_publication_request_commitment(s2j_request)
    executable_request_commitment = executable_canonical_publication_request_commitment(
        executable_request
    )
    s2j_validation = validate_canonical_family_publication_authorization(
        repo_root=root,
        request=s2j_request,
        authorization=s2j_auth,
        candidate=candidate,
        execution_review_bundle=bundle,
        require_destination_absent=False,
        require_current_source_identity=False,
    )
    if s2j_validation.request_commitment != s2j_request_commitment:
        raise ValueError("Stage 2J authorization request commitment mismatch")
    if s2j_validation.authorization_id != s2j_auth_record["authorization_id"]:
        raise ValueError("Stage 2J authorization ID mismatch")
    checks = {
        "stage_2j_publication_request_commitment": s2j_request_commitment,
        "stage_2j_publication_request_file_sha256": stage_2j_request_file_sha256,
        "stage_2j_publication_authorization_id": s2j_auth_record["authorization_id"],
        "stage_2j_publication_authorization_file_sha256": stage_2j_authorization_file_sha256,
        "canonical_publication_candidate_commitment": cand_commitment,
        "canonical_publication_candidate_file_sha256": candidate_file_sha256,
        "accepted_execution_review_bundle_commitment": bundle_commitment,
        "accepted_execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
    }
    for key, value in checks.items():
        if exec_req_record[key] != value:
            raise ValueError(f"executable request {key} mismatch")
    if exec_auth_record["executable_request_commitment"] != executable_request_commitment:
        raise ValueError("executable authorization request commitment mismatch")
    for key in (
        "family_protocol_sha256",
        "stage_2j_publication_request_commitment",
        "stage_2j_publication_authorization_id",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
        "accepted_execution_review_bundle_commitment",
        "intended_canonical_destination",
        "intended_noncanonical_audit_work_dir",
        "canonical_publisher_source_identity",
        "publication_scope",
        "payload_policy",
    ):
        if exec_auth_record[key] != exec_req_record[key]:
            raise ValueError(f"executable authorization {key} mismatch")
    if s2j_req_record["canonical_publication_candidate_file_sha256"] != candidate_file_sha256:
        raise ValueError("Stage 2J candidate file SHA mismatch")
    if (
        s2j_req_record["accepted_execution_review_bundle_file_sha256"]
        != execution_review_bundle_file_sha256
    ):
        raise ValueError("Stage 2J bundle file SHA mismatch")
    destination = _validate_relative_path(
        exec_req_record["intended_canonical_destination"], label="destination"
    )
    parent = _validate_relative_path(exec_req_record["intended_canonical_parent"], label="parent")
    if Path(destination).parent.as_posix() != parent:
        raise ValueError("canonical parent mismatch")
    audit_work_dir = _validate_relative_path(
        exec_req_record["intended_noncanonical_audit_work_dir"], label="audit work dir"
    )
    reject_canonical_path(root / audit_work_dir, repo_root=root, label="review audit work dir")
    if exec_req_record["publication_scope"] != CANONICAL_PUBLICATION_SCOPE:
        raise ValueError("publication scope mismatch")
    if exec_req_record["payload_policy"] != PAYLOAD_POLICY:
        raise ValueError("payload policy mismatch")
    if tuple(exec_req_record["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("continuing prohibitions changed")
    return CanonicalPublicationRecordChainValidation(
        stage_2j_request_commitment=s2j_request_commitment,
        stage_2j_authorization_id=s2j_auth_record["authorization_id"],
        executable_request_commitment=executable_request_commitment,
        executable_authorization_id=exec_auth_record["authorization_id"],
        candidate_commitment=cand_commitment,
        candidate_file_sha256=candidate_file_sha256,
        execution_review_bundle_commitment=bundle_commitment,
        canonical_destination=destination,
        canonical_parent=parent,
        audit_work_dir=audit_work_dir,
        publisher_source_identity=exec_req_record["canonical_publisher_source_identity"],
        family_protocol_sha256=exec_req_record["family_protocol_sha256"],
        execution_review_report_commitment=exec_req_record["execution_review_report_commitment"],
        execution_review_disposition_id=exec_req_record["execution_review_disposition_id"],
    )


def _validate_trace_sequence(
    trace: dict[str, Any],
    *,
    chain: CanonicalPublicationRecordChainValidation,
    failure: dict[str, Any] | None,
) -> dict[str, Any]:
    events = trace["events"]
    event_types = [event["event_type"] for event in events]
    if failure is None:
        if tuple(event_types) != _COMPLETED_EVENTS:
            raise ValueError("completed trace sequence is malformed")
    else:
        if not event_types or event_types[-1] != "PUBLICATION_FAILED":
            raise ValueError("failed trace must end in PUBLICATION_FAILED")
        prefix = tuple(event_types[:-1])
        if prefix != _COMPLETED_EVENTS[: len(prefix)]:
            raise ValueError("failed trace prefix is malformed")
        if failure["claim_persisted"] and "CLAIM_PERSISTED" not in prefix:
            raise ValueError("failure trace does not include persisted claim")
        if not failure["claim_persisted"] and "CLAIM_PERSISTED" in prefix:
            raise ValueError("trace claims persisted claim but failure does not")
        if failure["canonical_file_created"] and "CANONICAL_DESTINATION_CREATED" not in prefix:
            raise ValueError("failure trace does not include canonical creation")
        if not failure["canonical_file_created"] and "CANONICAL_DESTINATION_CREATED" in prefix:
            raise ValueError("trace claims canonical creation but failure does not")
    for event in events:
        if (
            event["event_type"] == "CANDIDATE_BYTES_VERIFIED"
            and event.get("candidate_file_sha256") != chain.candidate_file_sha256
        ):
            raise ValueError("trace candidate SHA mismatch")
        if (
            event.get("destination") is not None
            and event["destination"] != chain.canonical_destination
        ):
            raise ValueError("trace destination mismatch")
        if (
            event.get("destination_file_sha256") is not None
            and event["destination_file_sha256"] != chain.candidate_file_sha256
        ):
            raise ValueError("trace destination SHA mismatch")
    return {"event_count": len(events), "events_validated": True, "event_types": event_types}


def inspect_canonical_publication_evidence(
    *,
    repo_root: Path,
    stage_2j_request: CanonicalFamilyPublicationRequest,
    stage_2j_request_file_sha256: str,
    stage_2j_authorization: CanonicalFamilyPublicationAuthorization,
    stage_2j_authorization_file_sha256: str,
    executable_request: ExecutableCanonicalFamilyPublicationRequest,
    executable_request_file_sha256: str,
    executable_authorization: ExecutableCanonicalFamilyPublicationAuthorization,
    executable_authorization_file_sha256: str,
    candidate_file: Path,
    execution_review_bundle_file: Path,
) -> CanonicalPublicationEvidenceReviewReport:
    root = repo_root.resolve(strict=False)
    candidate_bytes = candidate_file.read_bytes()
    candidate = canonical_family_publication_candidate_from_record(
        _require_object(json.loads(candidate_bytes.decode("utf-8")), label="candidate")
    )
    bundle = canonical_execution_review_bundle_from_record(
        _require_object(
            json.loads(execution_review_bundle_file.read_text(encoding="utf-8")),
            label="execution review bundle",
        )
    )
    chain = validate_canonical_publication_record_chain(
        repo_root=root,
        stage_2j_request=stage_2j_request,
        stage_2j_request_file_sha256=stage_2j_request_file_sha256,
        stage_2j_authorization=stage_2j_authorization,
        stage_2j_authorization_file_sha256=stage_2j_authorization_file_sha256,
        executable_request=executable_request,
        executable_request_file_sha256=executable_request_file_sha256,
        executable_authorization=executable_authorization,
        executable_authorization_file_sha256=executable_authorization_file_sha256,
        candidate=candidate,
        candidate_file_sha256=sha256_file(candidate_file),
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(execution_review_bundle_file),
    )
    audit_dir = root / chain.audit_work_dir
    destination = root / chain.canonical_destination
    claim_raw, claim_sha = _load_optional_json(audit_dir / "canonical-publication-claim.json")
    trace_raw, trace_sha = _load_optional_json(audit_dir / "canonical-publication-trace.json")
    receipt_raw, receipt_sha = _load_optional_json(audit_dir / "canonical-publication-receipt.json")
    failure_raw, failure_sha = _load_optional_json(audit_dir / "canonical-publication-failure.json")
    if receipt_raw is not None and failure_raw is not None:
        raise ValueError("receipt and failure records conflict")
    claim = canonical_publication_claim_from_record(claim_raw) if claim_raw is not None else None
    trace = canonical_publication_trace_from_record(trace_raw) if trace_raw is not None else None
    receipt = (
        canonical_publication_receipt_from_record(receipt_raw) if receipt_raw is not None else None
    )
    failure = (
        canonical_publication_failure_from_record(failure_raw) if failure_raw is not None else None
    )
    if claim is not None:
        _validate_expected_fields(claim, _expected_claim_fields(chain), label="claim")
        if claim["claim_commitment"] != sha256_text(
            canonical_json({k: v for k, v in claim.items() if k != "claim_commitment"})
        ):
            raise ValueError("claim commitment mismatch")
    destination_exists = destination.exists()
    destination_sha = (
        sha256_file(destination) if destination_exists and destination.is_file() else None
    )
    exact_bytes = False
    if destination_exists:
        if not destination.is_file():
            raise ValueError("canonical destination is not a file")
        exact_bytes = destination.read_bytes() == candidate_bytes
        if destination_sha != chain.candidate_file_sha256 or not exact_bytes:
            raise ValueError("canonical destination bytes differ from authorized candidate")
        canonical_family_publication_candidate_from_record(
            _require_object(
                json.loads(destination.read_text(encoding="utf-8")), label="destination"
            )
        )
    if receipt is not None:
        if claim is None or trace is None:
            raise ValueError("completed receipt requires claim and trace")
        _validate_expected_fields(receipt, _expected_receipt_fields(chain), label="receipt")
        if receipt["claim_commitment"] != claim["claim_commitment"]:
            raise ValueError("receipt claim commitment mismatch")
        if receipt["trace_file_sha256"] != trace_sha:
            raise ValueError("receipt trace SHA mismatch")
        if not destination_exists:
            raise ValueError("completed receipt requires canonical destination")
        trace_summary = _validate_trace_sequence(trace, chain=chain, failure=None)
        terminal = CanonicalPublicationTerminalStatus.VALID_COMPLETED
    elif failure is not None:
        _validate_expected_fields(failure, _expected_failure_fields(chain), label="failure")
        if failure["claim_persisted"] and claim is None:
            raise ValueError("failure says claim persisted but claim is missing")
        if failure["canonical_file_created"]:
            if not destination_exists or destination_sha != failure["canonical_file_sha256"]:
                raise ValueError("failure canonical file evidence mismatch")
            terminal = (
                CanonicalPublicationTerminalStatus.VALID_CANONICAL_FILE_CREATED_AUDIT_FAILED
                if trace is not None
                else CanonicalPublicationTerminalStatus.INCOMPLETE_TERMINAL_EVIDENCE
            )
        else:
            if destination_exists:
                raise ValueError("failure says no canonical file but destination exists")
            terminal = (
                CanonicalPublicationTerminalStatus.VALID_FAILED_BEFORE_CANONICAL_CREATION
                if trace is not None
                else CanonicalPublicationTerminalStatus.INCOMPLETE_TERMINAL_EVIDENCE
            )
        trace_summary = (
            _validate_trace_sequence(trace, chain=chain, failure=failure)
            if trace is not None
            else {"event_count": 0, "events_validated": False, "event_types": []}
        )
    else:
        if claim is not None:
            terminal = CanonicalPublicationTerminalStatus.INCOMPLETE_TERMINAL_EVIDENCE
            trace_summary = {
                "event_count": len(trace["events"]) if trace else 0,
                "events_validated": False,
                "event_types": [],
            }
        else:
            raise ValueError("missing terminal publication evidence")
    eligibility = _closure_eligibility(terminal.value)
    record = {
        "schema_id": PUBLICATION_REVIEW_REPORT_SCHEMA_ID,
        "review_scope": PUBLICATION_REVIEW_SCOPE,
        "terminal_status": terminal.value,
        "publication_completed": terminal is CanonicalPublicationTerminalStatus.VALID_COMPLETED,
        "canonical_artifact_exists": destination_exists,
        "canonical_artifact_exact_bytes_verified": exact_bytes,
        "audit_finalization_completed": receipt is not None,
        "family_protocol_sha256": executable_request.as_record()["family_protocol_sha256"],
        "stage_2j_publication_request_commitment": chain.stage_2j_request_commitment,
        "stage_2j_publication_authorization_id": chain.stage_2j_authorization_id,
        "executable_request_commitment": chain.executable_request_commitment,
        "executable_authorization_id": chain.executable_authorization_id,
        "candidate_commitment": chain.candidate_commitment,
        "candidate_file_sha256": chain.candidate_file_sha256,
        "execution_review_bundle_commitment": chain.execution_review_bundle_commitment,
        "canonical_destination": chain.canonical_destination,
        "canonical_destination_file_sha256": destination_sha,
        "claim_commitment": claim["claim_commitment"] if claim is not None else None,
        "receipt_commitment": receipt["receipt_commitment"] if receipt is not None else None,
        "failure_commitment": failure["failure_commitment"] if failure is not None else None,
        "file_sha256": {
            "stage_2j_request": stage_2j_request_file_sha256,
            "stage_2j_authorization": stage_2j_authorization_file_sha256,
            "executable_request": executable_request_file_sha256,
            "executable_authorization": executable_authorization_file_sha256,
            "candidate": sha256_file(candidate_file),
            "execution_review_bundle": sha256_file(execution_review_bundle_file),
            **({"claim": claim_sha} if claim_sha else {}),
            **({"trace": trace_sha} if trace_sha else {}),
            **({"receipt": receipt_sha} if receipt_sha else {}),
            **({"failure": failure_sha} if failure_sha else {}),
            **({"canonical_destination": destination_sha} if destination_sha else {}),
        },
        "record_chain_validation_summary": chain.as_record(),
        "claim_validation_summary": {"present": claim is not None, "validated": claim is not None},
        "trace_validation_summary": trace_summary,
        "receipt_validation_summary": {
            "present": receipt is not None,
            "validated": receipt is not None,
        },
        "failure_validation_summary": {
            "present": failure is not None,
            "validated": failure is not None,
        },
        "canonical_byte_validation_summary": {
            "destination_exists": destination_exists,
            "exact_bytes_verified": exact_bytes,
            "destination_sha256": destination_sha,
        },
        "historical_source_identity": {
            "record_chain_publisher_source_identity": chain.publisher_source_identity,
        },
        "current_source_comparison": {
            "current_publisher_source_identity": compute_canonical_publisher_source_identity(root),
            "current_publisher_source_matches_execution": (
                compute_canonical_publisher_source_identity(root) == chain.publisher_source_identity
            ),
        },
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
        "closure_eligibility": eligibility,
        "not_determined": list(NOT_DETERMINED),
    }
    return CanonicalPublicationEvidenceReviewReport(
        record={**record, "report_commitment": sha256_text(canonical_json(record))}
    )


def _closure_eligibility(status: str) -> dict[str, bool]:
    return {
        "completed_publication_closure": status
        == CanonicalPublicationTerminalStatus.VALID_COMPLETED,
        "failed_attempt_closure": status
        == CanonicalPublicationTerminalStatus.VALID_FAILED_BEFORE_CANONICAL_CREATION,
        "partial_success_acknowledgement": status
        == CanonicalPublicationTerminalStatus.VALID_CANONICAL_FILE_CREATED_AUDIT_FAILED,
    }


def _validate_report_semantics(data: dict[str, Any]) -> None:
    status = data["terminal_status"]
    completed = status == CanonicalPublicationTerminalStatus.VALID_COMPLETED
    failed_before = (
        status == CanonicalPublicationTerminalStatus.VALID_FAILED_BEFORE_CANONICAL_CREATION
    )
    partial = status == CanonicalPublicationTerminalStatus.VALID_CANONICAL_FILE_CREATED_AUDIT_FAILED
    incomplete = status == CanonicalPublicationTerminalStatus.INCOMPLETE_TERMINAL_EVIDENCE
    if data["publication_completed"] is not completed:
        raise ValueError("publication completion flag does not match terminal status")
    if data["audit_finalization_completed"] is not completed:
        raise ValueError("audit finalization flag does not match terminal status")
    if completed:
        if not data["canonical_artifact_exists"]:
            raise ValueError("completed report requires canonical artifact")
        if not data["canonical_artifact_exact_bytes_verified"]:
            raise ValueError("completed report requires exact canonical bytes")
        if data["receipt_commitment"] is None:
            raise ValueError("completed report requires receipt commitment")
        if data["failure_commitment"] is not None:
            raise ValueError("completed report cannot have failure commitment")
        if data["canonical_destination_file_sha256"] != data["candidate_file_sha256"]:
            raise ValueError("completed report destination SHA mismatch")
        if not data["trace_validation_summary"].get("events_validated"):
            raise ValueError("completed report requires validated trace")
        if not data["receipt_validation_summary"].get("validated"):
            raise ValueError("completed report requires validated receipt")
    elif failed_before:
        if data["canonical_artifact_exists"]:
            raise ValueError("failed-before-canonical report cannot have artifact")
        if data["canonical_artifact_exact_bytes_verified"]:
            raise ValueError("failed-before-canonical report cannot verify bytes")
        if data["canonical_destination_file_sha256"] is not None:
            raise ValueError("failed-before-canonical report cannot bind destination SHA")
        if data["receipt_commitment"] is not None:
            raise ValueError("failed-before-canonical report cannot have receipt commitment")
        if data["failure_commitment"] is None:
            raise ValueError("failed-before-canonical report requires failure commitment")
        if not data["trace_validation_summary"].get("events_validated"):
            raise ValueError("failed-before-canonical report requires validated trace")
        if not data["failure_validation_summary"].get("validated"):
            raise ValueError("failed-before-canonical report requires validated failure")
    elif partial:
        if not data["canonical_artifact_exists"]:
            raise ValueError("partial-success report requires canonical artifact")
        if not data["canonical_artifact_exact_bytes_verified"]:
            raise ValueError("partial-success report requires exact canonical bytes")
        if data["canonical_destination_file_sha256"] != data["candidate_file_sha256"]:
            raise ValueError("partial-success report destination SHA mismatch")
        if data["receipt_commitment"] is not None:
            raise ValueError("partial-success report cannot have receipt commitment")
        if data["failure_commitment"] is None:
            raise ValueError("partial-success report requires failure commitment")
        if not data["trace_validation_summary"].get("events_validated"):
            raise ValueError("partial-success report requires validated trace")
        if not data["failure_validation_summary"].get("validated"):
            raise ValueError("partial-success report requires validated failure")
    elif incomplete:
        if data["publication_completed"] or data["audit_finalization_completed"]:
            raise ValueError("incomplete report cannot claim completed finalization")
        if data["receipt_commitment"] is not None:
            raise ValueError("incomplete report cannot have receipt commitment")
    byte_summary = data["canonical_byte_validation_summary"]
    if byte_summary.get("destination_exists") != data["canonical_artifact_exists"]:
        raise ValueError("canonical byte summary existence mismatch")
    if byte_summary.get("exact_bytes_verified") != data["canonical_artifact_exact_bytes_verified"]:
        raise ValueError("canonical byte summary exact-bytes mismatch")
    if byte_summary.get("destination_sha256") != data["canonical_destination_file_sha256"]:
        raise ValueError("canonical byte summary destination SHA mismatch")


def _disposition_is_eligible(report_record: dict[str, Any], disposition: str) -> bool:
    eligibility = report_record["closure_eligibility"]
    return (
        disposition == WITHHOLD_CANONICAL_PUBLICATION_CLOSURE
        or (
            disposition == CLOSE_COMPLETED_CANONICAL_PUBLICATION
            and eligibility["completed_publication_closure"]
        )
        or (
            disposition == CLOSE_FAILED_PUBLICATION_WITHOUT_CANONICAL_ARTIFACT
            and eligibility["failed_attempt_closure"]
        )
        or (
            disposition == ACKNOWLEDGE_CANONICAL_ARTIFACT_WITH_INCOMPLETE_AUDIT_FINALIZATION
            and eligibility["partial_success_acknowledgement"]
        )
    )


def canonical_publication_evidence_review_report_from_record(
    record: dict[str, Any],
) -> CanonicalPublicationEvidenceReviewReport:
    data = _require_object(record, label="canonical publication evidence review report")
    required = {
        "schema_id",
        "review_scope",
        "terminal_status",
        "publication_completed",
        "canonical_artifact_exists",
        "canonical_artifact_exact_bytes_verified",
        "audit_finalization_completed",
        "family_protocol_sha256",
        "stage_2j_publication_request_commitment",
        "stage_2j_publication_authorization_id",
        "executable_request_commitment",
        "executable_authorization_id",
        "candidate_commitment",
        "candidate_file_sha256",
        "execution_review_bundle_commitment",
        "canonical_destination",
        "canonical_destination_file_sha256",
        "claim_commitment",
        "receipt_commitment",
        "failure_commitment",
        "file_sha256",
        "record_chain_validation_summary",
        "claim_validation_summary",
        "trace_validation_summary",
        "receipt_validation_summary",
        "failure_validation_summary",
        "canonical_byte_validation_summary",
        "historical_source_identity",
        "current_source_comparison",
        "continuing_prohibitions",
        "closure_eligibility",
        "not_determined",
        "report_commitment",
    }
    if set(data) != required:
        raise ValueError("publication review report fields are malformed")
    if data["schema_id"] != PUBLICATION_REVIEW_REPORT_SCHEMA_ID:
        raise ValueError("unsupported publication review report schema")
    if data["review_scope"] != PUBLICATION_REVIEW_SCOPE:
        raise ValueError("publication review scope mismatch")
    if data["terminal_status"] not in {item.value for item in CanonicalPublicationTerminalStatus}:
        raise ValueError("invalid terminal status")
    if data["closure_eligibility"] != _closure_eligibility(data["terminal_status"]):
        raise ValueError("closure eligibility is stale")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("publication review prohibitions changed")
    for key in (
        "family_protocol_sha256",
        "stage_2j_publication_request_commitment",
        "executable_request_commitment",
        "candidate_commitment",
        "candidate_file_sha256",
        "execution_review_bundle_commitment",
    ):
        validate_sha256_identity(data[key], label=key)
    _validate_relative_path(data["canonical_destination"], label="canonical destination")
    _validate_report_semantics(data)
    _commit(data, "report_commitment")
    return CanonicalPublicationEvidenceReviewReport(record=data)


def make_canonical_publication_closure_disposition(
    *,
    report: CanonicalPublicationEvidenceReviewReport,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> CanonicalPublicationClosureDisposition:
    if disposition not in ALLOWED_CLOSURE_DISPOSITIONS:
        raise ValueError("invalid publication closure disposition")
    report_record = canonical_publication_evidence_review_report_from_record(
        report.as_record()
    ).as_record()
    if not _disposition_is_eligible(report_record, disposition):
        raise ValueError("publication closure disposition is not eligible")
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    payload = {
        "schema_id": PUBLICATION_CLOSURE_DISPOSITION_SCHEMA_ID,
        "review_report_commitment": report_record["report_commitment"],
        "terminal_status": report_record["terminal_status"],
        "family_protocol_sha256": report_record["family_protocol_sha256"],
        "executable_request_commitment": report_record["executable_request_commitment"],
        "executable_authorization_id": report_record["executable_authorization_id"],
        "candidate_commitment": report_record["candidate_commitment"],
        "canonical_destination": report_record["canonical_destination"],
        "canonical_destination_file_sha256": report_record["canonical_destination_file_sha256"],
        "review_scope": PUBLICATION_REVIEW_SCOPE,
        "disposition": disposition,
        "reviewer_identity": reviewer,
        "review_timestamp": timestamp,
        "bounded_reason": reason,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }
    return CanonicalPublicationClosureDisposition(
        record={**payload, "disposition_id": sha256_text(canonical_json(payload))}
    )


def canonical_publication_closure_disposition_from_record(
    record: dict[str, Any],
    *,
    report: CanonicalPublicationEvidenceReviewReport | None = None,
) -> CanonicalPublicationClosureDisposition:
    data = _require_object(record, label="canonical publication closure disposition")
    expected = {
        "schema_id",
        "review_report_commitment",
        "terminal_status",
        "family_protocol_sha256",
        "executable_request_commitment",
        "executable_authorization_id",
        "candidate_commitment",
        "canonical_destination",
        "canonical_destination_file_sha256",
        "review_scope",
        "disposition",
        "reviewer_identity",
        "review_timestamp",
        "bounded_reason",
        "continuing_prohibitions",
        "disposition_id",
    }
    if set(data) != expected:
        raise ValueError("publication closure disposition fields are malformed")
    if data["schema_id"] != PUBLICATION_CLOSURE_DISPOSITION_SCHEMA_ID:
        raise ValueError("unsupported publication closure disposition schema")
    if data["disposition"] not in ALLOWED_CLOSURE_DISPOSITIONS:
        raise ValueError("invalid publication closure disposition")
    validate_source_identity(data["reviewer_identity"])
    parse_timestamp(data["review_timestamp"])
    _reason(data["bounded_reason"])
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("publication closure prohibitions changed")
    if report is not None:
        report_record = canonical_publication_evidence_review_report_from_record(
            report.as_record()
        ).as_record()
        if data["review_report_commitment"] != report_record["report_commitment"]:
            raise ValueError("closure disposition is for another report")
        mirrored = {
            "terminal_status": report_record["terminal_status"],
            "family_protocol_sha256": report_record["family_protocol_sha256"],
            "executable_request_commitment": report_record["executable_request_commitment"],
            "executable_authorization_id": report_record["executable_authorization_id"],
            "candidate_commitment": report_record["candidate_commitment"],
            "canonical_destination": report_record["canonical_destination"],
            "canonical_destination_file_sha256": report_record["canonical_destination_file_sha256"],
            "review_scope": PUBLICATION_REVIEW_SCOPE,
        }
        _validate_expected_fields(data, mirrored, label="closure disposition")
        if not _disposition_is_eligible(report_record, data["disposition"]):
            raise ValueError("publication closure disposition is not eligible")
    _commit(data, "disposition_id")
    return CanonicalPublicationClosureDisposition(record=data)


def make_canonical_publication_closure_bundle(
    report: CanonicalPublicationEvidenceReviewReport,
    disposition: CanonicalPublicationClosureDisposition,
) -> CanonicalPublicationClosureBundle:
    report = canonical_publication_evidence_review_report_from_record(report.as_record())
    disposition = canonical_publication_closure_disposition_from_record(
        disposition.as_record(), report=report
    )
    report_record = report.as_record()
    disposition_record = disposition.as_record()
    payload = {
        "schema_id": PUBLICATION_CLOSURE_BUNDLE_SCHEMA_ID,
        "publication_evidence_review_report": report_record,
        "publication_evidence_review_report_commitment": report_record["report_commitment"],
        "publication_closure_disposition": disposition_record,
        "publication_closure_disposition_commitment": sha256_text(
            canonical_json(disposition_record)
        ),
        "terminal_status": report_record["terminal_status"],
        "canonical_destination": report_record["canonical_destination"],
        "canonical_destination_file_sha256": report_record["canonical_destination_file_sha256"],
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }
    return CanonicalPublicationClosureBundle(
        record={**payload, "bundle_commitment": sha256_text(canonical_json(payload))}
    )


def canonical_publication_closure_bundle_from_record(
    record: dict[str, Any],
) -> CanonicalPublicationClosureBundle:
    data = _require_object(record, label="canonical publication closure bundle")
    expected = {
        "schema_id",
        "publication_evidence_review_report",
        "publication_evidence_review_report_commitment",
        "publication_closure_disposition",
        "publication_closure_disposition_commitment",
        "terminal_status",
        "canonical_destination",
        "canonical_destination_file_sha256",
        "continuing_prohibitions",
        "bundle_commitment",
    }
    if set(data) != expected:
        raise ValueError("publication closure bundle fields are malformed")
    if data["schema_id"] != PUBLICATION_CLOSURE_BUNDLE_SCHEMA_ID:
        raise ValueError("unsupported publication closure bundle schema")
    report = canonical_publication_evidence_review_report_from_record(
        data["publication_evidence_review_report"]
    )
    disposition = canonical_publication_closure_disposition_from_record(
        data["publication_closure_disposition"], report=report
    )
    if data["publication_evidence_review_report_commitment"] != report.report_commitment:
        raise ValueError("closure bundle report commitment mismatch")
    if data["publication_closure_disposition_commitment"] != sha256_text(
        canonical_json(disposition.as_record())
    ):
        raise ValueError("closure bundle disposition commitment mismatch")
    mirrored = {
        "terminal_status": report.as_record()["terminal_status"],
        "canonical_destination": report.as_record()["canonical_destination"],
        "canonical_destination_file_sha256": report.as_record()[
            "canonical_destination_file_sha256"
        ],
    }
    _validate_expected_fields(data, mirrored, label="closure bundle")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("closure bundle prohibitions changed")
    _commit(data, "bundle_commitment")
    return CanonicalPublicationClosureBundle(record=data)


def canonical_publication_closure_bundle_commitment(
    bundle: CanonicalPublicationClosureBundle,
) -> str:
    return canonical_publication_closure_bundle_from_record(bundle.as_record()).as_record()[
        "bundle_commitment"
    ]


def write_canonical_publication_closure_bundle(
    *,
    report: CanonicalPublicationEvidenceReviewReport,
    disposition: CanonicalPublicationClosureDisposition,
    destination: Path,
    repo_root: Path,
) -> CanonicalPublicationClosureBundle:
    reject_canonical_path(destination, repo_root=repo_root, label="publication closure bundle")
    reject_canonical_path(
        destination.parent, repo_root=repo_root, label="publication closure parent"
    )
    refuse_overwrite(destination, label="publication closure bundle")
    bundle = make_canonical_publication_closure_bundle(report, disposition)
    atomic_write_json(destination, bundle.as_record())
    return bundle

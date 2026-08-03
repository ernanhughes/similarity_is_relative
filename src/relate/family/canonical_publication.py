"""One-shot executor for authorized canonical family-result publication."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from relate.evidence.atomic_io import atomic_create_bytes_no_replace, atomic_write_json
from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.canonical_publication_authorization import (
    CANONICAL_PUBLICATION_SCOPE,
    CONTINUING_PROHIBITIONS,
    CanonicalFamilyPublicationAuthorization,
    CanonicalFamilyPublicationCandidate,
    CanonicalFamilyPublicationRequest,
    canonical_family_publication_candidate_commitment,
    canonical_family_publication_candidate_from_record,
    canonical_family_publication_request_commitment,
    validate_canonical_family_publication_authorization,
    validate_intended_canonical_destination,
)
from relate.family.execution_review import (
    CanonicalExecutionReviewBundle,
    canonical_execution_review_bundle_commitment,
    canonical_execution_review_bundle_from_record,
)
from relate.family.review import reject_canonical_path
from relate.family.sources import parse_timestamp, validate_source_identity
from relate.family.workflow.models import validate_sha256_identity

EXECUTABLE_PUBLICATION_REQUEST_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-request-v2"
)
EXECUTABLE_PUBLICATION_AUTHORIZATION_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-authorization-v2"
)
CANONICAL_PUBLISHER_SOURCE_MANIFEST_SCHEMA_ID: Final = (
    "relate-family-canonical-publisher-source-manifest-v1"
)
PUBLICATION_CLAIM_SCHEMA_ID: Final = "relate-family-canonical-publication-claim-v1"
PUBLICATION_TRACE_SCHEMA_ID: Final = "relate-family-canonical-publication-trace-v1"
PUBLICATION_RECEIPT_SCHEMA_ID: Final = (
    "relate-family-authorized-canonical-publication-receipt-v1"
)
PUBLICATION_FAILURE_SCHEMA_ID: Final = "relate-family-canonical-publication-failure-v1"
EXECUTABLE_PUBLICATION_SCOPE: Final = (
    "EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION"
)
PAYLOAD_POLICY: Final = "PUBLISH_EXACT_AUTHORIZED_CANDIDATE_FILE_BYTES"
AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION: Final = (
    "AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION"
)
WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION: Final = (
    "WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION"
)
ALLOWED_EXECUTABLE_PUBLICATION_DISPOSITIONS: Final = (
    AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
)
_MAX_REASON_LENGTH: Final = 500
_SOURCE_FILES: Final[tuple[str, ...]] = (
    "src/relate/family/canonical_publication.py",
    "src/relate/family/canonical_publication_authorization.py",
    "src/relate/family/execution_review.py",
    "src/relate/family/review.py",
    "src/relate/evidence/atomic_io.py",
    "src/relate/evidence/canonical_json.py",
    "src/relate/evidence/hashing.py",
    "src/relate/evidence/immutable.py",
)


class AuthorizedCanonicalPublicationStatus(StrEnum):
    WITHHELD = "WITHHELD"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class ExecutableCanonicalFamilyPublicationRequest:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


@dataclass(frozen=True)
class ExecutableCanonicalFamilyPublicationAuthorization:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


@dataclass(frozen=True)
class ExecutableCanonicalPublicationValidation:
    status: str
    request_commitment: str
    authorization_id: str
    candidate_commitment: str
    intended_canonical_destination: str
    intended_noncanonical_audit_work_dir: str
    canonical_publisher_source_identity: str
    executable_publication_authority: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "request_commitment": self.request_commitment,
            "authorization_id": self.authorization_id,
            "candidate_commitment": self.candidate_commitment,
            "intended_canonical_destination": self.intended_canonical_destination,
            "intended_noncanonical_audit_work_dir": self.intended_noncanonical_audit_work_dir,
            "canonical_publisher_source_identity": self.canonical_publisher_source_identity,
            "executable_publication_authority": self.executable_publication_authority,
        }


@dataclass(frozen=True)
class AuthorizedCanonicalPublicationResult:
    status: AuthorizedCanonicalPublicationStatus
    request_commitment: str
    authorization_id: str
    candidate_commitment: str
    canonical_destination: Path | None = None
    canonical_destination_file_sha256: str | None = None
    audit_work_dir: Path | None = None
    receipt_commitment: str | None = None
    receipt_file_sha256: str | None = None

    def as_summary(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "request_commitment": self.request_commitment,
            "authorization_id": self.authorization_id,
            "candidate_commitment": self.candidate_commitment,
            "canonical_destination": str(self.canonical_destination)
            if self.canonical_destination is not None
            else None,
            "canonical_destination_file_sha256": self.canonical_destination_file_sha256,
            "audit_work_dir": str(self.audit_work_dir) if self.audit_work_dir else None,
            "receipt_commitment": self.receipt_commitment,
            "receipt_file_sha256": self.receipt_file_sha256,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat()


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


def _is_under(path: Path, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    base = root.resolve(strict=False)
    return resolved == base or base in resolved.parents


def _repo_relative(repo_root: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()


def compute_canonical_publisher_source_identity(repo_root: Path) -> str:
    root = repo_root.resolve(strict=False)
    files = {relative: sha256_file(root / relative) for relative in _SOURCE_FILES}
    manifest = {
        "schema_id": CANONICAL_PUBLISHER_SOURCE_MANIFEST_SCHEMA_ID,
        "source_files": dict(sorted(files.items())),
    }
    return sha256_text(canonical_json(manifest))


def _validate_audit_work_dir(repo_root: Path, work_dir: Path) -> str:
    root = repo_root.resolve(strict=False)
    path = (work_dir if work_dir.is_absolute() else root / work_dir).resolve(strict=False)
    if not _is_under(path, root):
        raise ValueError("audit work directory must be beneath repository")
    reject_canonical_path(path, repo_root=root, label="canonical publication audit work dir")
    if path.exists():
        raise ValueError("audit work directory already exists")
    relative = _repo_relative(root, path)
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("audit work directory is not normalized")
    return relative


def _validate_parent_safety(repo_root: Path, destination: str, parent: str) -> None:
    root = repo_root.resolve(strict=False)
    observed_parent = Path(destination).parent.as_posix()
    if parent != observed_parent:
        raise ValueError("canonical parent mismatch")
    canonical_root = (root / "artifacts" / "canonical").resolve(strict=False)
    current = root
    for segment in Path(parent).parts:
        current = current / segment
        if current.exists() and current.is_symlink():
            raise ValueError("canonical parent path contains symlink")
        if current.exists() and not current.is_dir():
            raise ValueError("canonical parent path contains non-directory")
        if current.resolve(strict=False) != canonical_root and (
            canonical_root not in current.resolve(strict=False).parents
            and current.resolve(strict=False) != root
            and root not in current.resolve(strict=False).parents
        ):
            raise ValueError("canonical parent path escapes repository")


def _verify_stage_2j_chain(
    *,
    repo_root: Path,
    stage_2j_request: CanonicalFamilyPublicationRequest,
    stage_2j_request_file_sha256: str,
    stage_2j_authorization: CanonicalFamilyPublicationAuthorization,
    stage_2j_authorization_file_sha256: str,
    candidate: CanonicalFamilyPublicationCandidate,
    candidate_file_sha256: str,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    execution_review_bundle_file_sha256: str,
) -> dict[str, Any]:
    for label, value in {
        "stage_2j_request_file_sha256": stage_2j_request_file_sha256,
        "stage_2j_authorization_file_sha256": stage_2j_authorization_file_sha256,
        "candidate_file_sha256": candidate_file_sha256,
        "execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
    }.items():
        validate_sha256_identity(value, label=label)
    validation = validate_canonical_family_publication_authorization(
        repo_root=repo_root,
        request=stage_2j_request,
        authorization=stage_2j_authorization,
        candidate=candidate,
        execution_review_bundle=execution_review_bundle,
    )
    if validation.status != "AUTHORIZED":
        raise ValueError("Stage 2J canonical publication authorization is not authorized")
    request_record = stage_2j_request.as_record()
    authorization_record = stage_2j_authorization.as_record()
    candidate_record = candidate.as_record()
    if request_record["canonical_publication_candidate_file_sha256"] != candidate_file_sha256:
        raise ValueError("Stage 2J candidate file SHA mismatch")
    if request_record["accepted_execution_review_bundle_file_sha256"] != (
        execution_review_bundle_file_sha256
    ):
        raise ValueError("Stage 2J execution review bundle file SHA mismatch")
    return {
        "stage_2j_request_commitment": canonical_family_publication_request_commitment(
            stage_2j_request
        ),
        "stage_2j_authorization_id": authorization_record["authorization_id"],
        "candidate_commitment": canonical_family_publication_candidate_commitment(candidate),
        "bundle_commitment": canonical_execution_review_bundle_commitment(
            execution_review_bundle
        ),
        "request": request_record,
        "candidate": candidate_record,
    }


def make_executable_canonical_family_publication_request_v2(
    *,
    repo_root: Path,
    stage_2j_request: CanonicalFamilyPublicationRequest,
    stage_2j_request_file_sha256: str,
    stage_2j_authorization: CanonicalFamilyPublicationAuthorization,
    stage_2j_authorization_file_sha256: str,
    candidate: CanonicalFamilyPublicationCandidate,
    candidate_file_sha256: str,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    execution_review_bundle_file_sha256: str,
    intended_noncanonical_audit_work_dir: Path,
) -> ExecutableCanonicalFamilyPublicationRequest:
    root = repo_root.resolve(strict=False)
    chain = _verify_stage_2j_chain(
        repo_root=root,
        stage_2j_request=stage_2j_request,
        stage_2j_request_file_sha256=stage_2j_request_file_sha256,
        stage_2j_authorization=stage_2j_authorization,
        stage_2j_authorization_file_sha256=stage_2j_authorization_file_sha256,
        candidate=candidate,
        candidate_file_sha256=candidate_file_sha256,
        execution_review_bundle=execution_review_bundle,
        execution_review_bundle_file_sha256=execution_review_bundle_file_sha256,
    )
    request_record = chain["request"]
    destination = validate_intended_canonical_destination(
        root, Path(request_record["intended_canonical_destination"])
    )
    audit_work_dir = _validate_audit_work_dir(root, intended_noncanonical_audit_work_dir)
    if (
        audit_work_dir == destination
        or audit_work_dir == request_record["intended_canonical_parent"]
    ):
        raise ValueError("audit work directory aliases canonical destination")
    publisher_identity = compute_canonical_publisher_source_identity(root)
    source = chain["candidate"]["source_execution_identity"]
    payload = {
        "schema_id": EXECUTABLE_PUBLICATION_REQUEST_SCHEMA_ID,
        "execution_scope": EXECUTABLE_PUBLICATION_SCOPE,
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "stage_2j_publication_request_commitment": chain["stage_2j_request_commitment"],
        "stage_2j_publication_request_file_sha256": stage_2j_request_file_sha256,
        "stage_2j_publication_authorization_id": chain["stage_2j_authorization_id"],
        "stage_2j_publication_authorization_file_sha256": stage_2j_authorization_file_sha256,
        "canonical_publication_candidate_commitment": chain["candidate_commitment"],
        "canonical_publication_candidate_file_sha256": candidate_file_sha256,
        "accepted_execution_review_bundle_commitment": chain["bundle_commitment"],
        "accepted_execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
        "execution_review_report_commitment": source["execution_review_report_commitment"],
        "execution_review_disposition_id": source["execution_review_disposition_id"],
        "canonical_execution_request_commitment": source[
            "canonical_execution_request_commitment"
        ],
        "canonical_execution_authorization_id": source[
            "canonical_execution_authorization_id"
        ],
        "canonical_execution_receipt_commitment": source[
            "canonical_execution_receipt_commitment"
        ],
        "canonical_execution_review_packet_commitment": request_record[
            "canonical_execution_review_packet_commitment"
        ],
        "intended_canonical_destination": destination,
        "intended_canonical_parent": request_record["intended_canonical_parent"],
        "intended_noncanonical_audit_work_dir": audit_work_dir,
        "canonical_publisher_source_identity": publisher_identity,
        "publication_scope": CANONICAL_PUBLICATION_SCOPE,
        "payload_policy": PAYLOAD_POLICY,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }
    return ExecutableCanonicalFamilyPublicationRequest(
        record={**payload, "request_commitment": sha256_text(canonical_json(payload))}
    )


def executable_canonical_publication_request_v2_from_record(
    record: dict[str, Any],
) -> ExecutableCanonicalFamilyPublicationRequest:
    data = _require_object(record, label="executable canonical publication request")
    required = set(make_executable_canonical_family_publication_request_v2.__annotations__)
    expected = {
        "schema_id",
        "execution_scope",
        "family_protocol_sha256",
        "stage_2j_publication_request_commitment",
        "stage_2j_publication_request_file_sha256",
        "stage_2j_publication_authorization_id",
        "stage_2j_publication_authorization_file_sha256",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
        "accepted_execution_review_bundle_commitment",
        "accepted_execution_review_bundle_file_sha256",
        "execution_review_report_commitment",
        "execution_review_disposition_id",
        "canonical_execution_request_commitment",
        "canonical_execution_authorization_id",
        "canonical_execution_receipt_commitment",
        "canonical_execution_review_packet_commitment",
        "intended_canonical_destination",
        "intended_canonical_parent",
        "intended_noncanonical_audit_work_dir",
        "canonical_publisher_source_identity",
        "publication_scope",
        "payload_policy",
        "continuing_prohibitions",
        "request_commitment",
    }
    if required and set(data) != expected:
        raise ValueError("executable canonical publication request fields are malformed")
    if data["schema_id"] != EXECUTABLE_PUBLICATION_REQUEST_SCHEMA_ID:
        raise ValueError("unsupported executable canonical publication request schema")
    if data["execution_scope"] != EXECUTABLE_PUBLICATION_SCOPE:
        raise ValueError("executable canonical publication request scope mismatch")
    if data["publication_scope"] != CANONICAL_PUBLICATION_SCOPE:
        raise ValueError("executable canonical publication scope mismatch")
    if data["payload_policy"] != PAYLOAD_POLICY:
        raise ValueError("executable canonical publication payload policy mismatch")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("executable canonical publication prohibitions changed")
    for key, value in data.items():
        if key.endswith("_sha256") or key.endswith("_commitment") or key.endswith("_identity"):
            validate_sha256_identity(value, label=key)
    _commit(data, "request_commitment")
    return ExecutableCanonicalFamilyPublicationRequest(record=data)


def executable_canonical_publication_request_commitment(
    request: ExecutableCanonicalFamilyPublicationRequest,
) -> str:
    return executable_canonical_publication_request_v2_from_record(
        request.as_record()
    ).as_record()["request_commitment"]


def make_executable_canonical_family_publication_authorization_v2(
    *,
    request: ExecutableCanonicalFamilyPublicationRequest,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> ExecutableCanonicalFamilyPublicationAuthorization:
    if disposition not in ALLOWED_EXECUTABLE_PUBLICATION_DISPOSITIONS:
        raise ValueError("invalid executable canonical publication disposition")
    request_record = executable_canonical_publication_request_v2_from_record(
        request.as_record()
    ).as_record()
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    payload = {
        "schema_id": EXECUTABLE_PUBLICATION_AUTHORIZATION_SCHEMA_ID,
        "authorization_scope": EXECUTABLE_PUBLICATION_SCOPE,
        "executable_request_commitment": request_record["request_commitment"],
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "stage_2j_publication_request_commitment": request_record[
            "stage_2j_publication_request_commitment"
        ],
        "stage_2j_publication_authorization_id": request_record[
            "stage_2j_publication_authorization_id"
        ],
        "canonical_publication_candidate_commitment": request_record[
            "canonical_publication_candidate_commitment"
        ],
        "canonical_publication_candidate_file_sha256": request_record[
            "canonical_publication_candidate_file_sha256"
        ],
        "accepted_execution_review_bundle_commitment": request_record[
            "accepted_execution_review_bundle_commitment"
        ],
        "intended_canonical_destination": request_record["intended_canonical_destination"],
        "intended_noncanonical_audit_work_dir": request_record[
            "intended_noncanonical_audit_work_dir"
        ],
        "canonical_publisher_source_identity": request_record[
            "canonical_publisher_source_identity"
        ],
        "publication_scope": CANONICAL_PUBLICATION_SCOPE,
        "payload_policy": PAYLOAD_POLICY,
        "disposition": disposition,
        "reviewer_identity": reviewer,
        "review_timestamp": timestamp,
        "bounded_reason": reason,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }
    return ExecutableCanonicalFamilyPublicationAuthorization(
        record={**payload, "authorization_id": sha256_text(canonical_json(payload))}
    )


def executable_canonical_publication_authorization_v2_from_record(
    record: dict[str, Any],
) -> ExecutableCanonicalFamilyPublicationAuthorization:
    data = _require_object(record, label="executable canonical publication authorization")
    expected = {
        "schema_id",
        "authorization_scope",
        "executable_request_commitment",
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
        "disposition",
        "reviewer_identity",
        "review_timestamp",
        "bounded_reason",
        "continuing_prohibitions",
        "authorization_id",
    }
    if set(data) != expected:
        raise ValueError("executable canonical publication authorization fields are malformed")
    if data["schema_id"] != EXECUTABLE_PUBLICATION_AUTHORIZATION_SCHEMA_ID:
        raise ValueError("unsupported executable canonical publication authorization schema")
    if data["authorization_scope"] != EXECUTABLE_PUBLICATION_SCOPE:
        raise ValueError("executable canonical publication authorization scope mismatch")
    if data["disposition"] not in ALLOWED_EXECUTABLE_PUBLICATION_DISPOSITIONS:
        raise ValueError("invalid executable canonical publication disposition")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("executable canonical publication authorization prohibitions changed")
    validate_source_identity(data["reviewer_identity"])
    parse_timestamp(data["review_timestamp"])
    _reason(data["bounded_reason"])
    _commit(data, "authorization_id")
    return ExecutableCanonicalFamilyPublicationAuthorization(record=data)


def validate_executable_canonical_publication_authorization(
    *,
    repo_root: Path,
    stage_2j_request: CanonicalFamilyPublicationRequest,
    stage_2j_request_file_sha256: str,
    stage_2j_authorization: CanonicalFamilyPublicationAuthorization,
    stage_2j_authorization_file_sha256: str,
    request: ExecutableCanonicalFamilyPublicationRequest,
    authorization: ExecutableCanonicalFamilyPublicationAuthorization,
    candidate: CanonicalFamilyPublicationCandidate,
    candidate_file_sha256: str,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    execution_review_bundle_file_sha256: str,
) -> ExecutableCanonicalPublicationValidation:
    root = repo_root.resolve(strict=False)
    request_record = executable_canonical_publication_request_v2_from_record(
        request.as_record()
    ).as_record()
    auth_record = executable_canonical_publication_authorization_v2_from_record(
        authorization.as_record()
    ).as_record()
    chain = _verify_stage_2j_chain(
        repo_root=root,
        stage_2j_request=stage_2j_request,
        stage_2j_request_file_sha256=stage_2j_request_file_sha256,
        stage_2j_authorization=stage_2j_authorization,
        stage_2j_authorization_file_sha256=stage_2j_authorization_file_sha256,
        candidate=candidate,
        candidate_file_sha256=candidate_file_sha256,
        execution_review_bundle=execution_review_bundle,
        execution_review_bundle_file_sha256=execution_review_bundle_file_sha256,
    )
    expected = {
        "stage_2j_publication_request_commitment": chain["stage_2j_request_commitment"],
        "stage_2j_publication_request_file_sha256": stage_2j_request_file_sha256,
        "stage_2j_publication_authorization_id": chain["stage_2j_authorization_id"],
        "stage_2j_publication_authorization_file_sha256": stage_2j_authorization_file_sha256,
        "canonical_publication_candidate_commitment": chain["candidate_commitment"],
        "canonical_publication_candidate_file_sha256": candidate_file_sha256,
        "accepted_execution_review_bundle_commitment": chain["bundle_commitment"],
        "accepted_execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
    }
    for key, value in expected.items():
        if request_record[key] != value:
            raise ValueError(f"executable canonical publication request {key} mismatch")
    if request_record["canonical_publisher_source_identity"] != (
        compute_canonical_publisher_source_identity(root)
    ):
        raise ValueError("canonical publisher source identity mismatch")
    destination = validate_intended_canonical_destination(
        root, Path(request_record["intended_canonical_destination"])
    )
    if destination != request_record["intended_canonical_destination"]:
        raise ValueError("canonical destination mismatch")
    _validate_parent_safety(root, destination, request_record["intended_canonical_parent"])
    _validate_audit_work_dir(root, Path(request_record["intended_noncanonical_audit_work_dir"]))
    if auth_record["executable_request_commitment"] != request_record["request_commitment"]:
        raise ValueError("authorization is for another executable request")
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
        if auth_record[key] != request_record[key]:
            raise ValueError(f"authorization {key} mismatch")
    authorized = (
        auth_record["disposition"]
        == AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION
    )
    return ExecutableCanonicalPublicationValidation(
        status="AUTHORIZED" if authorized else "WITHHELD",
        request_commitment=request_record["request_commitment"],
        authorization_id=auth_record["authorization_id"],
        candidate_commitment=chain["candidate_commitment"],
        intended_canonical_destination=destination,
        intended_noncanonical_audit_work_dir=request_record[
            "intended_noncanonical_audit_work_dir"
        ],
        canonical_publisher_source_identity=request_record[
            "canonical_publisher_source_identity"
        ],
        executable_publication_authority=authorized,
    )


def _event(event_type: str, **values: Any) -> dict[str, Any]:
    return {"event_type": event_type, "timestamp": _now(), **values}


def _json_file_sha256(value: dict[str, Any]) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def _claim(request: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_id": PUBLICATION_CLAIM_SCHEMA_ID,
        "executable_request_commitment": request["request_commitment"],
        "executable_authorization_id": auth["authorization_id"],
        "stage_2j_publication_request_commitment": request[
            "stage_2j_publication_request_commitment"
        ],
        "stage_2j_publication_authorization_id": request[
            "stage_2j_publication_authorization_id"
        ],
        "family_protocol_sha256": request["family_protocol_sha256"],
        "canonical_publication_candidate_commitment": request[
            "canonical_publication_candidate_commitment"
        ],
        "canonical_publication_candidate_file_sha256": request[
            "canonical_publication_candidate_file_sha256"
        ],
        "accepted_execution_review_bundle_commitment": request[
            "accepted_execution_review_bundle_commitment"
        ],
        "intended_canonical_destination": request["intended_canonical_destination"],
        "intended_canonical_parent": request["intended_canonical_parent"],
        "canonical_publisher_source_identity": request["canonical_publisher_source_identity"],
        "payload_policy": PAYLOAD_POLICY,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
        "claim_timestamp": _now(),
    }
    return {**payload, "claim_commitment": sha256_text(canonical_json(payload))}


def _write_failure(
    *,
    audit_dir: Path,
    request: dict[str, Any],
    auth: dict[str, Any],
    failed_phase: str,
    exc: Exception,
    claim_persisted: bool,
    parent_created: list[str],
    canonical_file_sha256: str | None,
    receipt_persisted: bool,
    events: list[dict[str, Any]],
) -> None:
    canonical_file_created = canonical_file_sha256 is not None
    payload = {
        "schema_id": PUBLICATION_FAILURE_SCHEMA_ID,
        "executable_request_commitment": request["request_commitment"],
        "executable_authorization_id": auth["authorization_id"],
        "stage_2j_publication_request_commitment": request[
            "stage_2j_publication_request_commitment"
        ],
        "stage_2j_publication_authorization_id": request[
            "stage_2j_publication_authorization_id"
        ],
        "canonical_destination": request["intended_canonical_destination"],
        "canonical_publication_candidate_commitment": request[
            "canonical_publication_candidate_commitment"
        ],
        "canonical_publication_candidate_file_sha256": request[
            "canonical_publication_candidate_file_sha256"
        ],
        "failed_phase": failed_phase
        if not canonical_file_created
        else "CANONICAL_FILE_CREATED_AUDIT_FINALIZATION_FAILED",
        "bounded_exception_type": type(exc).__name__[:120],
        "bounded_message": str(exc)[:500],
        "claim_persisted": claim_persisted,
        "canonical_parent_created": parent_created,
        "canonical_file_created": canonical_file_created,
        "canonical_file_sha256": canonical_file_sha256,
        "receipt_persisted": receipt_persisted,
        "failure_timestamp": _now(),
    }
    failure = {**payload, "failure_commitment": sha256_text(canonical_json(payload))}
    events.append(
        _event(
            "PUBLICATION_FAILED",
            destination=request["intended_canonical_destination"],
            destination_file_sha256=canonical_file_sha256,
            failure_phase=failed_phase,
            bounded_message=str(exc)[:500],
        )
    )
    original = exc
    try:
        atomic_write_json(audit_dir / "canonical-publication-failure.json", failure)
    except Exception:
        raise original from None
    try:
        atomic_write_json(
            audit_dir / "canonical-publication-trace.json",
            {"schema_id": PUBLICATION_TRACE_SCHEMA_ID, "events": events},
        )
    except Exception:
        raise original from None


def _create_parent_chain(repo_root: Path, relative_parent: str) -> list[str]:
    root = repo_root.resolve(strict=False)
    canonical_root = (root / "artifacts" / "canonical").resolve(strict=False)
    current = root
    created: list[str] = []
    for segment in Path(relative_parent).parts:
        current = current / segment
        resolved = current.resolve(strict=False)
        if current.exists() and current.is_symlink():
            raise ValueError("canonical parent path contains symlink")
        if current.exists() and not current.is_dir():
            raise ValueError("canonical parent path contains non-directory")
        safely_contained = (
            resolved == canonical_root
            or canonical_root in resolved.parents
            or resolved == root
            or root in resolved.parents
        )
        if not safely_contained:
            raise ValueError("canonical parent path escapes repository")
        if not current.exists():
            current.mkdir()
            created.append(_repo_relative(root, current))
    return created


def execute_authorized_canonical_publication(
    *,
    repo_root: Path,
    stage_2j_request: CanonicalFamilyPublicationRequest,
    stage_2j_authorization: CanonicalFamilyPublicationAuthorization,
    executable_request: ExecutableCanonicalFamilyPublicationRequest,
    executable_authorization: ExecutableCanonicalFamilyPublicationAuthorization,
    candidate_file: Path,
    execution_review_bundle_file: Path,
    stage_2j_request_file_sha256: str,
    stage_2j_authorization_file_sha256: str,
) -> AuthorizedCanonicalPublicationResult:
    root = repo_root.resolve(strict=False)
    candidate_bytes = candidate_file.read_bytes()
    candidate_file_sha = sha256_file(candidate_file)
    candidate_record = _require_object(
        json.loads(candidate_bytes.decode("utf-8")), label="candidate file"
    )
    candidate = canonical_family_publication_candidate_from_record(candidate_record)
    bundle = canonical_execution_review_bundle_from_record(
        json.loads(execution_review_bundle_file.read_text(encoding="utf-8"))
    )
    validation = validate_executable_canonical_publication_authorization(
        repo_root=root,
        stage_2j_request=stage_2j_request,
        stage_2j_request_file_sha256=stage_2j_request_file_sha256,
        stage_2j_authorization=stage_2j_authorization,
        stage_2j_authorization_file_sha256=stage_2j_authorization_file_sha256,
        request=executable_request,
        authorization=executable_authorization,
        candidate=candidate,
        candidate_file_sha256=candidate_file_sha,
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(execution_review_bundle_file),
    )
    request_record = executable_request.as_record()
    auth_record = executable_authorization.as_record()
    destination = root / request_record["intended_canonical_destination"]
    audit_dir = root / request_record["intended_noncanonical_audit_work_dir"]
    if validation.status == "WITHHELD":
        return AuthorizedCanonicalPublicationResult(
            status=AuthorizedCanonicalPublicationStatus.WITHHELD,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            candidate_commitment=validation.candidate_commitment,
        )
    audit_dir.mkdir(parents=True, exist_ok=False)
    events: list[dict[str, Any]] = []
    claim_persisted = False
    receipt_persisted = False
    created_parents: list[str] = []
    canonical_sha: str | None = None
    try:
        claim = _claim(request_record, auth_record)
        atomic_write_json(audit_dir / "canonical-publication-claim.json", claim)
        claim_persisted = True
        events.append(_event("CLAIM_PERSISTED"))
        if compute_canonical_publisher_source_identity(root) != request_record[
            "canonical_publisher_source_identity"
        ]:
            raise ValueError("canonical publisher source identity mismatch")
        events.append(_event("PUBLISHER_IDENTITY_VERIFIED"))
        created_parents = _create_parent_chain(root, request_record["intended_canonical_parent"])
        _validate_parent_safety(
            root,
            request_record["intended_canonical_destination"],
            request_record["intended_canonical_parent"],
        )
        events.append(_event("CANONICAL_PARENT_VERIFIED"))
        if (
            sha256_file(candidate_file)
            != request_record["canonical_publication_candidate_file_sha256"]
        ):
            raise ValueError("candidate file changed after validation")
        events.append(
            _event(
                "CANDIDATE_BYTES_VERIFIED",
                candidate_file_sha256=request_record[
                    "canonical_publication_candidate_file_sha256"
                ],
            )
        )
        validate_intended_canonical_destination(
            root, Path(request_record["intended_canonical_destination"])
        )
        atomic_create_bytes_no_replace(destination, candidate_bytes)
        events.append(
            _event(
                "CANONICAL_DESTINATION_CREATED",
                destination=_repo_relative(root, destination),
            )
        )
        canonical_sha = sha256_file(destination)
        if canonical_sha != request_record["canonical_publication_candidate_file_sha256"]:
            raise ValueError("published destination SHA mismatch")
        canonical_family_publication_candidate_from_record(
            json.loads(destination.read_text(encoding="utf-8"))
        )
        events.append(
            _event(
                "CANONICAL_DESTINATION_VERIFIED",
                destination=_repo_relative(root, destination),
                destination_file_sha256=canonical_sha,
            )
        )
        trace_path = audit_dir / "canonical-publication-trace.json"
        atomic_write_json(trace_path, {"schema_id": PUBLICATION_TRACE_SCHEMA_ID, "events": events})
        trace_sha = sha256_file(trace_path)
        payload = {
            "schema_id": PUBLICATION_RECEIPT_SCHEMA_ID,
            "publication_status": "COMPLETED",
            "executable_request_commitment": request_record["request_commitment"],
            "executable_authorization_id": auth_record["authorization_id"],
            "claim_commitment": claim["claim_commitment"],
            "stage_2j_publication_request_commitment": request_record[
                "stage_2j_publication_request_commitment"
            ],
            "stage_2j_publication_authorization_id": request_record[
                "stage_2j_publication_authorization_id"
            ],
            "family_protocol_sha256": request_record["family_protocol_sha256"],
            "canonical_publisher_source_identity": request_record[
                "canonical_publisher_source_identity"
            ],
            "canonical_publication_candidate_commitment": request_record[
                "canonical_publication_candidate_commitment"
            ],
            "source_candidate_file_sha256": request_record[
                "canonical_publication_candidate_file_sha256"
            ],
            "published_destination_file_sha256": canonical_sha,
            "accepted_execution_review_bundle_commitment": request_record[
                "accepted_execution_review_bundle_commitment"
            ],
            "execution_review_report_commitment": request_record[
                "execution_review_report_commitment"
            ],
            "execution_review_disposition_id": request_record["execution_review_disposition_id"],
            "canonical_destination": request_record["intended_canonical_destination"],
            "canonical_parent": request_record["intended_canonical_parent"],
            "created_parent_directories": created_parents,
            "payload_policy": PAYLOAD_POLICY,
            "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
            "trace_file_sha256": trace_sha,
            "publication_timestamp": _now(),
        }
        receipt = {**payload, "receipt_commitment": sha256_text(canonical_json(payload))}
        receipt_file_sha = _json_file_sha256(receipt)
        atomic_write_json(audit_dir / "canonical-publication-receipt.json", receipt)
        receipt_persisted = True
        return AuthorizedCanonicalPublicationResult(
            status=AuthorizedCanonicalPublicationStatus.COMPLETED,
            request_commitment=request_record["request_commitment"],
            authorization_id=auth_record["authorization_id"],
            candidate_commitment=request_record["canonical_publication_candidate_commitment"],
            canonical_destination=destination,
            canonical_destination_file_sha256=canonical_sha,
            audit_work_dir=audit_dir,
            receipt_commitment=receipt["receipt_commitment"],
            receipt_file_sha256=receipt_file_sha,
        )
    except Exception as exc:
        if canonical_sha is None and destination.exists():
            try:
                canonical_sha = sha256_file(destination)
            except Exception:
                canonical_sha = None
        _write_failure(
            audit_dir=audit_dir,
            request=request_record,
            auth=auth_record,
            failed_phase="PUBLICATION_EXECUTION",
            exc=exc,
            claim_persisted=claim_persisted,
            parent_created=created_parents,
            canonical_file_sha256=canonical_sha
            if canonical_sha == request_record["canonical_publication_candidate_file_sha256"]
            else None,
            receipt_persisted=receipt_persisted,
            events=events,
        )
        raise

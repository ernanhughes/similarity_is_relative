"""Validation-only authorization boundary for future canonical family publication."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.execution_review import (
    ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
    CanonicalExecutionReviewBundle,
    canonical_execution_review_bundle_commitment,
    canonical_execution_review_bundle_from_record,
)
from relate.family.review import (
    NOT_CONCLUDED as REVIEW_NOT_CONCLUDED,
)
from relate.family.review import (
    PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY,
    FamilyReviewPacket,
    family_review_packet_commitment,
    family_review_packet_from_record,
)
from relate.family.sources import parse_timestamp, validate_source_identity
from relate.family.workflow.models import validate_sha256_identity

CANONICAL_PUBLICATION_CANDIDATE_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-candidate-v1"
)
CANONICAL_PUBLICATION_REQUEST_SCHEMA_ID: Final = "relate-family-canonical-publication-request-v1"
CANONICAL_PUBLICATION_AUTHORIZATION_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-authorization-v1"
)
CANONICAL_PUBLICATION_VALIDATION_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-authorization-validation-v1"
)
CANONICAL_PUBLICATION_CONTRACT_SOURCE_MANIFEST_SCHEMA_ID: Final = (
    "relate-family-canonical-publication-contract-source-manifest-v1"
)
CANONICAL_PUBLICATION_SCOPE: Final = "CANONICAL_BOUNDED_FAMILY_RESULT_ONLY"
CANONICAL_PUBLICATION_REQUEST_SCOPE: Final = "EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION"
AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION: Final = (
    "AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION"
)
WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION: Final = (
    "WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION"
)
ALLOWED_CANONICAL_PUBLICATION_DISPOSITIONS: Final = (
    AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
)
CONTINUING_PROHIBITIONS: Final[tuple[str, ...]] = (
    "MATERIALITY_DETERMINATION",
    "MATERIAL_CONTAMINATION_CONCLUSION",
    "ALLOCATION_CHANGE",
    "REALLOCATION",
    "MODEL_REFIT",
    "C0_REPLAY",
    "PROTECTED_ROW_ACCESS",
    "D2",
)
_MAX_REASON_LENGTH: Final = 500
_SOURCE_FILES: Final[tuple[str, ...]] = (
    "src/relate/family/canonical_publication_authorization.py",
    "src/relate/family/execution_review.py",
    "src/relate/family/review.py",
    "src/relate/family/sources.py",
    "src/relate/family/workflow/models.py",
    "src/relate/evidence/canonical_json.py",
    "src/relate/evidence/hashing.py",
)


@dataclass(frozen=True)
class CanonicalFamilyPublicationCandidate:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


@dataclass(frozen=True)
class CanonicalFamilyPublicationRequest:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


@dataclass(frozen=True)
class CanonicalFamilyPublicationAuthorization:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


@dataclass(frozen=True)
class CanonicalPublicationAuthorizationValidation:
    status: str
    request_commitment: str
    authorization_id: str
    candidate_commitment: str
    intended_canonical_destination: str

    def as_record(self) -> dict[str, Any]:
        return {
            "schema_id": CANONICAL_PUBLICATION_VALIDATION_SCHEMA_ID,
            "status": self.status,
            "request_commitment": self.request_commitment,
            "authorization_id": self.authorization_id,
            "candidate_commitment": self.candidate_commitment,
            "intended_canonical_destination": self.intended_canonical_destination,
            "executable_publication_authority": False,
        }


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


def validate_intended_canonical_destination(repo_root: Path, destination: Path) -> str:
    root = repo_root.resolve(strict=False)
    canonical_root = (root / "artifacts" / "canonical").resolve(strict=False)
    candidate = (destination if destination.is_absolute() else root / destination).resolve(
        strict=False
    )
    if candidate == canonical_root:
        raise ValueError("canonical publication destination cannot be canonical root")
    if not _is_under(candidate, canonical_root):
        raise ValueError("canonical publication destination must be beneath artifacts/canonical")
    if candidate.exists():
        raise ValueError("canonical publication destination already exists")
    if candidate.suffix != ".json":
        raise ValueError("canonical publication destination must be a JSON file")
    relative = _repo_relative(root, candidate)
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("canonical publication destination is not normalized")
    return relative


def compute_canonical_publication_contract_source_identity(repo_root: Path) -> str:
    root = repo_root.resolve(strict=False)
    files = {}
    for relative in _SOURCE_FILES:
        path = root / relative
        files[relative] = sha256_file(path)
    manifest = {
        "schema_id": CANONICAL_PUBLICATION_CONTRACT_SOURCE_MANIFEST_SCHEMA_ID,
        "source_files": dict(sorted(files.items())),
    }
    return sha256_text(canonical_json(manifest))


def _accepted_bundle(
    bundle: CanonicalExecutionReviewBundle,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = canonical_execution_review_bundle_from_record(bundle.as_record()).as_record()
    report = parsed["execution_review_report"]
    disposition = parsed["execution_review_disposition"]
    if disposition["disposition"] != ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW:
        raise ValueError("execution review disposition is not accepted")
    if report["terminal_execution_status"] != "VALID_COMPLETED":
        raise ValueError("execution review report is not completed")
    if report["eligible_for_publication_authorization_review"] is not True:
        raise ValueError("execution review report is not eligible")
    if report["scientific_payload_equivalence"]["matches"] is not True:
        raise ValueError("scientific payload equivalence is not true")
    if report["store_validation_summary"].get("logical_store_validation") != "VALIDATED":
        raise ValueError("logical store validation is not validated")
    if report["trace_validation_summary"].get("runner_events_validated") is not True:
        raise ValueError("runner trace validation is not true")
    return report, disposition


def _validate_packet_against_report(
    packet: FamilyReviewPacket, report: dict[str, Any]
) -> dict[str, Any]:
    packet_record = family_review_packet_from_record(packet.as_record()).as_record()
    if family_review_packet_commitment(packet) != report["review_packet_commitment"]:
        raise ValueError("review packet commitment mismatch")
    file_sha = report["file_sha256"].get("canonical_execution_review_packet")
    validate_sha256_identity(file_sha, label="canonical_execution_review_packet file SHA")
    if packet_record["publication_scope"] != PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY:
        raise ValueError("review packet publication scope mismatch")
    for required in REVIEW_NOT_CONCLUDED:
        if required not in packet_record["not_concluded"]:
            raise ValueError(f"review packet missing non-conclusion: {required}")
    downstream = packet_record["downstream_decisions"]
    expected_downstream = {
        "material_contamination": "NOT_DETERMINED",
        "materiality_threshold": "NOT_APPLIED",
        "reallocation_required": "NOT_AUTHORIZED",
        "d2_authorization": "NOT_AUTHORIZED",
    }
    if downstream != expected_downstream:
        raise ValueError("review packet downstream decisions changed")
    return packet_record


def make_canonical_family_publication_candidate(
    *,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    execution_review_bundle_file_sha256: str,
    canonical_execution_review_packet: FamilyReviewPacket,
    canonical_execution_review_packet_file_sha256: str,
) -> CanonicalFamilyPublicationCandidate:
    validate_sha256_identity(
        execution_review_bundle_file_sha256, label="execution_review_bundle_file_sha256"
    )
    validate_sha256_identity(
        canonical_execution_review_packet_file_sha256,
        label="canonical_execution_review_packet_file_sha256",
    )
    report, disposition = _accepted_bundle(execution_review_bundle)
    packet = _validate_packet_against_report(canonical_execution_review_packet, report)
    if (
        canonical_execution_review_packet_file_sha256
        != report["file_sha256"]["canonical_execution_review_packet"]
    ):
        raise ValueError("review packet file SHA mismatch")
    bundle_commitment = canonical_execution_review_bundle_commitment(execution_review_bundle)
    payload = {
        "schema_id": CANONICAL_PUBLICATION_CANDIDATE_SCHEMA_ID,
        "publication_scope": CANONICAL_PUBLICATION_SCOPE,
        "family_protocol_sha256": packet["family_protocol_sha256"],
        "bounded_family_review_packet": packet,
        "bounded_family_review_packet_commitment": family_review_packet_commitment(
            canonical_execution_review_packet
        ),
        "bounded_family_review_packet_file_sha256": canonical_execution_review_packet_file_sha256,
        "accepted_execution_review_bundle": execution_review_bundle.as_record(),
        "accepted_execution_review_bundle_commitment": bundle_commitment,
        "accepted_execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
        "source_execution_identity": {
            "canonical_execution_request_commitment": report[
                "canonical_execution_request_commitment"
            ],
            "canonical_execution_authorization_id": report["canonical_execution_authorization_id"],
            "canonical_execution_receipt_commitment": report["receipt_commitment"],
            "execution_review_report_commitment": report["report_commitment"],
            "execution_review_disposition_id": disposition["disposition_id"],
        },
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
        "authorization_limit": "ONE_EXACT_CANDIDATE_ONE_EXACT_ABSENT_CANONICAL_DESTINATION",
    }
    return CanonicalFamilyPublicationCandidate(
        record={**payload, "candidate_commitment": sha256_text(canonical_json(payload))}
    )


def canonical_family_publication_candidate_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyPublicationCandidate:
    data = _require_object(record, label="canonical publication candidate")
    required = {
        "schema_id",
        "publication_scope",
        "family_protocol_sha256",
        "bounded_family_review_packet",
        "bounded_family_review_packet_commitment",
        "bounded_family_review_packet_file_sha256",
        "accepted_execution_review_bundle",
        "accepted_execution_review_bundle_commitment",
        "accepted_execution_review_bundle_file_sha256",
        "source_execution_identity",
        "continuing_prohibitions",
        "authorization_limit",
        "candidate_commitment",
    }
    if set(data) != required:
        raise ValueError("canonical publication candidate fields are malformed")
    if data["schema_id"] != CANONICAL_PUBLICATION_CANDIDATE_SCHEMA_ID:
        raise ValueError("unsupported canonical publication candidate schema")
    if data["publication_scope"] != CANONICAL_PUBLICATION_SCOPE:
        raise ValueError("canonical publication scope mismatch")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("canonical publication prohibitions changed")
    validate_sha256_identity(data["family_protocol_sha256"], label="family_protocol_sha256")
    packet = family_review_packet_from_record(data["bounded_family_review_packet"])
    bundle = canonical_execution_review_bundle_from_record(data["accepted_execution_review_bundle"])
    rebuilt = make_canonical_family_publication_candidate(
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=data["accepted_execution_review_bundle_file_sha256"],
        canonical_execution_review_packet=packet,
        canonical_execution_review_packet_file_sha256=data[
            "bounded_family_review_packet_file_sha256"
        ],
    ).as_record()
    if data != rebuilt:
        raise ValueError("canonical publication candidate is stale")
    return CanonicalFamilyPublicationCandidate(record=data)


def canonical_family_publication_candidate_commitment(
    candidate: CanonicalFamilyPublicationCandidate,
) -> str:
    return canonical_family_publication_candidate_from_record(candidate.as_record()).as_record()[
        "candidate_commitment"
    ]


def make_canonical_family_publication_request(
    *,
    repo_root: Path,
    candidate: CanonicalFamilyPublicationCandidate,
    candidate_file_sha256: str,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    execution_review_bundle_file_sha256: str,
    intended_canonical_destination: Path,
) -> CanonicalFamilyPublicationRequest:
    validate_sha256_identity(candidate_file_sha256, label="candidate_file_sha256")
    validate_sha256_identity(
        execution_review_bundle_file_sha256, label="execution_review_bundle_file_sha256"
    )
    candidate_record = canonical_family_publication_candidate_from_record(
        candidate.as_record()
    ).as_record()
    bundle_commitment = canonical_execution_review_bundle_commitment(execution_review_bundle)
    if bundle_commitment != candidate_record["accepted_execution_review_bundle_commitment"]:
        raise ValueError("request bundle does not match candidate")
    if (
        execution_review_bundle_file_sha256
        != candidate_record["accepted_execution_review_bundle_file_sha256"]
    ):
        raise ValueError("request bundle file SHA does not match candidate")
    destination = validate_intended_canonical_destination(repo_root, intended_canonical_destination)
    parent = str(Path(destination).parent).replace("\\", "/")
    source_identity = compute_canonical_publication_contract_source_identity(repo_root)
    source = candidate_record["source_execution_identity"]
    payload = {
        "schema_id": CANONICAL_PUBLICATION_REQUEST_SCHEMA_ID,
        "request_scope": CANONICAL_PUBLICATION_REQUEST_SCOPE,
        "family_protocol_sha256": candidate_record["family_protocol_sha256"],
        "canonical_publication_contract_source_identity": source_identity,
        "canonical_publication_candidate_commitment": candidate_record["candidate_commitment"],
        "canonical_publication_candidate_file_sha256": candidate_file_sha256,
        "accepted_execution_review_bundle_commitment": bundle_commitment,
        "accepted_execution_review_bundle_file_sha256": execution_review_bundle_file_sha256,
        "execution_review_report_commitment": source["execution_review_report_commitment"],
        "execution_review_disposition_id": source["execution_review_disposition_id"],
        "canonical_execution_request_commitment": source["canonical_execution_request_commitment"],
        "canonical_execution_authorization_id": source["canonical_execution_authorization_id"],
        "canonical_execution_receipt_commitment": source["canonical_execution_receipt_commitment"],
        "canonical_execution_review_packet_commitment": candidate_record[
            "bounded_family_review_packet_commitment"
        ],
        "intended_canonical_destination": destination,
        "intended_canonical_parent": parent,
        "publication_scope": CANONICAL_PUBLICATION_SCOPE,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
        "executable_publication_authority": False,
    }
    return CanonicalFamilyPublicationRequest(
        record={**payload, "request_commitment": sha256_text(canonical_json(payload))}
    )


def canonical_family_publication_request_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyPublicationRequest:
    data = _require_object(record, label="canonical publication request")
    required = {
        "schema_id",
        "request_scope",
        "family_protocol_sha256",
        "canonical_publication_contract_source_identity",
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
        "publication_scope",
        "continuing_prohibitions",
        "executable_publication_authority",
        "request_commitment",
    }
    if set(data) != required:
        raise ValueError("canonical publication request fields are malformed")
    if data["schema_id"] != CANONICAL_PUBLICATION_REQUEST_SCHEMA_ID:
        raise ValueError("unsupported canonical publication request schema")
    if data["request_scope"] != CANONICAL_PUBLICATION_REQUEST_SCOPE:
        raise ValueError("canonical publication request scope mismatch")
    if data["publication_scope"] != CANONICAL_PUBLICATION_SCOPE:
        raise ValueError("canonical publication request publication scope mismatch")
    if data["executable_publication_authority"] is not False:
        raise ValueError("Stage 2J request cannot be executable")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("canonical publication request prohibitions changed")
    for key in (
        "family_protocol_sha256",
        "canonical_publication_contract_source_identity",
        "canonical_publication_candidate_commitment",
        "canonical_publication_candidate_file_sha256",
        "accepted_execution_review_bundle_commitment",
        "accepted_execution_review_bundle_file_sha256",
        "execution_review_report_commitment",
        "canonical_execution_request_commitment",
        "canonical_execution_receipt_commitment",
        "canonical_execution_review_packet_commitment",
    ):
        validate_sha256_identity(data[key], label=key)
    if not isinstance(data["intended_canonical_destination"], str) or data[
        "intended_canonical_destination"
    ].startswith("/"):
        raise ValueError("canonical destination must be repository-relative")
    _commit(data, "request_commitment")
    return CanonicalFamilyPublicationRequest(record=data)


def canonical_family_publication_request_commitment(
    request: CanonicalFamilyPublicationRequest,
) -> str:
    return canonical_family_publication_request_from_record(request.as_record()).as_record()[
        "request_commitment"
    ]


def make_canonical_family_publication_authorization(
    *,
    repo_root: Path,
    request: CanonicalFamilyPublicationRequest,
    candidate: CanonicalFamilyPublicationCandidate,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> CanonicalFamilyPublicationAuthorization:
    if disposition not in ALLOWED_CANONICAL_PUBLICATION_DISPOSITIONS:
        raise ValueError("invalid canonical publication authorization disposition")
    validation = _validate_request_chain(
        repo_root=repo_root,
        request=request,
        candidate=candidate,
        execution_review_bundle=execution_review_bundle,
        require_destination_absent=True,
    )
    request_record = request.as_record()
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    payload = {
        "schema_id": CANONICAL_PUBLICATION_AUTHORIZATION_SCHEMA_ID,
        "authorization_scope": CANONICAL_PUBLICATION_REQUEST_SCOPE,
        "canonical_publication_request_commitment": validation["request_commitment"],
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "canonical_publication_candidate_commitment": validation["candidate_commitment"],
        "accepted_execution_review_bundle_commitment": request_record[
            "accepted_execution_review_bundle_commitment"
        ],
        "execution_review_report_commitment": request_record["execution_review_report_commitment"],
        "execution_review_disposition_id": request_record["execution_review_disposition_id"],
        "intended_canonical_destination": request_record["intended_canonical_destination"],
        "publication_scope": CANONICAL_PUBLICATION_SCOPE,
        "disposition": disposition,
        "reviewer_identity": reviewer,
        "review_timestamp": timestamp,
        "bounded_reason": reason,
        "continuing_prohibitions": list(CONTINUING_PROHIBITIONS),
    }
    return CanonicalFamilyPublicationAuthorization(
        record={**payload, "authorization_id": sha256_text(canonical_json(payload))}
    )


def canonical_family_publication_authorization_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyPublicationAuthorization:
    data = _require_object(record, label="canonical publication authorization")
    required = {
        "schema_id",
        "authorization_scope",
        "canonical_publication_request_commitment",
        "family_protocol_sha256",
        "canonical_publication_candidate_commitment",
        "accepted_execution_review_bundle_commitment",
        "execution_review_report_commitment",
        "execution_review_disposition_id",
        "intended_canonical_destination",
        "publication_scope",
        "disposition",
        "reviewer_identity",
        "review_timestamp",
        "bounded_reason",
        "continuing_prohibitions",
        "authorization_id",
    }
    if set(data) != required:
        raise ValueError("canonical publication authorization fields are malformed")
    if data["schema_id"] != CANONICAL_PUBLICATION_AUTHORIZATION_SCHEMA_ID:
        raise ValueError("unsupported canonical publication authorization schema")
    if data["authorization_scope"] != CANONICAL_PUBLICATION_REQUEST_SCOPE:
        raise ValueError("canonical publication authorization scope mismatch")
    if data["publication_scope"] != CANONICAL_PUBLICATION_SCOPE:
        raise ValueError("canonical publication authorization publication scope mismatch")
    if data["disposition"] not in ALLOWED_CANONICAL_PUBLICATION_DISPOSITIONS:
        raise ValueError("invalid canonical publication authorization disposition")
    if tuple(data["continuing_prohibitions"]) != CONTINUING_PROHIBITIONS:
        raise ValueError("canonical publication authorization prohibitions changed")
    validate_source_identity(data["reviewer_identity"])
    parse_timestamp(data["review_timestamp"])
    _reason(data["bounded_reason"])
    _commit(data, "authorization_id")
    return CanonicalFamilyPublicationAuthorization(record=data)


def _validate_request_chain(
    *,
    repo_root: Path,
    request: CanonicalFamilyPublicationRequest,
    candidate: CanonicalFamilyPublicationCandidate,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    require_destination_absent: bool,
    require_current_source_identity: bool = True,
) -> dict[str, str]:
    request_record = canonical_family_publication_request_from_record(
        request.as_record()
    ).as_record()
    candidate_record = canonical_family_publication_candidate_from_record(
        candidate.as_record()
    ).as_record()
    bundle_commitment = canonical_execution_review_bundle_commitment(execution_review_bundle)
    candidate_commitment = candidate_record["candidate_commitment"]
    if request_record["canonical_publication_candidate_commitment"] != candidate_commitment:
        raise ValueError("request is for another candidate")
    if request_record["accepted_execution_review_bundle_commitment"] != bundle_commitment:
        raise ValueError("request is for another execution review bundle")
    if require_current_source_identity and request_record[
        "canonical_publication_contract_source_identity"
    ] != compute_canonical_publication_contract_source_identity(repo_root):
        raise ValueError("canonical publication contract source identity mismatch")
    if require_destination_absent:
        destination = validate_intended_canonical_destination(
            repo_root, Path(request_record["intended_canonical_destination"])
        )
        if destination != request_record["intended_canonical_destination"]:
            raise ValueError("canonical destination normalization mismatch")
    return {
        "request_commitment": request_record["request_commitment"],
        "candidate_commitment": candidate_commitment,
    }


def validate_canonical_family_publication_authorization(
    *,
    repo_root: Path,
    request: CanonicalFamilyPublicationRequest,
    authorization: CanonicalFamilyPublicationAuthorization,
    candidate: CanonicalFamilyPublicationCandidate,
    execution_review_bundle: CanonicalExecutionReviewBundle,
    require_destination_absent: bool = True,
    require_current_source_identity: bool = True,
) -> CanonicalPublicationAuthorizationValidation:
    validation = _validate_request_chain(
        repo_root=repo_root,
        request=request,
        candidate=candidate,
        execution_review_bundle=execution_review_bundle,
        require_destination_absent=require_destination_absent,
        require_current_source_identity=require_current_source_identity,
    )
    request_record = request.as_record()
    auth_record = canonical_family_publication_authorization_from_record(
        authorization.as_record()
    ).as_record()
    expected = {
        "canonical_publication_request_commitment": validation["request_commitment"],
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "canonical_publication_candidate_commitment": validation["candidate_commitment"],
        "accepted_execution_review_bundle_commitment": request_record[
            "accepted_execution_review_bundle_commitment"
        ],
        "execution_review_report_commitment": request_record["execution_review_report_commitment"],
        "execution_review_disposition_id": request_record["execution_review_disposition_id"],
        "intended_canonical_destination": request_record["intended_canonical_destination"],
        "publication_scope": CANONICAL_PUBLICATION_SCOPE,
    }
    for key, value in expected.items():
        if auth_record[key] != value:
            raise ValueError(f"canonical publication authorization {key} mismatch")
    status = (
        "AUTHORIZED"
        if auth_record["disposition"] == AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION
        else "WITHHELD"
    )
    return CanonicalPublicationAuthorizationValidation(
        status=status,
        request_commitment=validation["request_commitment"],
        authorization_id=auth_record["authorization_id"],
        candidate_commitment=validation["candidate_commitment"],
        intended_canonical_destination=request_record["intended_canonical_destination"],
    )

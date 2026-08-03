"""Canonical family execution request and authorization records.

This module defines identity-bound requests and human authorizations for a
future canonical family execution. It never executes the workflow, constructs a
canonical workflow config, writes a store, or publishes a canonical result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.review import (
    FamilyReviewPacket,
    family_review_packet_commitment,
)
from relate.family.sources import parse_timestamp, validate_source_identity
from relate.family.verification import (
    FamilyProtocolExpectedIdentity,
    FamilyProtocolInputPaths,
    verify_family_protocol_inputs,
)
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import (
    FamilyEvidenceBundle,
    evidence_bundle_commitment,
    validate_sha256_identity,
)

CANONICAL_EXECUTION_REQUEST_SCHEMA_ID: Final = "relate-family-canonical-execution-request-v1"
CANONICAL_EXECUTION_AUTHORIZATION_SCHEMA_ID: Final = (
    "relate-family-canonical-execution-authorization-v1"
)
CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID: Final = "relate-family-canonical-execution-request-v2"
CANONICAL_EXECUTION_AUTHORIZATION_V2_SCHEMA_ID: Final = (
    "relate-family-canonical-execution-authorization-v2"
)
CANONICAL_EXECUTION_REQUEST_SCOPE: Final = (
    "EXACT_CANONICAL_FAMILY_EXECUTION_TO_NONCANONICAL_STAGING_ONLY"
)
CANONICAL_EXECUTION_AUTHORIZATION_SCOPE: Final = "EXACT_CANONICAL_FAMILY_EXECUTION"
AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION: Final = "AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION"
WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION: Final = "WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION"
ALLOWED_CANONICAL_EXECUTION_DISPOSITIONS: Final = (
    AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
    WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
)
PROHIBITIONS: Final[tuple[str, ...]] = (
    "CANONICAL_RESULT_PUBLICATION",
    "MATERIALITY_DETERMINATION",
    "MATERIAL_CONTAMINATION_CONCLUSION",
    "ALLOCATION_CHANGE",
    "REALLOCATION",
    "MODEL_REFIT",
    "C0_REPLAY",
    "D2",
    "PROTECTED_ROW_ACCESS",
)
CANONICAL_EXECUTOR_SOURCE_MANIFEST_SCHEMA_ID: Final = (
    "relate-family-canonical-executor-source-manifest-v1"
)
CANONICAL_EXECUTOR_CRITICAL_SOURCE_FILES: Final[tuple[str, ...]] = tuple(
    sorted(
        (
            "src/relate/family/execution.py",
            "src/relate/family/authorization.py",
            "src/relate/family/review.py",
            "src/relate/family/workflow/composition.py",
            "src/relate/family/workflow/models.py",
            "src/relate/family/workflow/steps.py",
            "src/relate/workflows/runner.py",
            "src/relate/workflows/validation.py",
        )
    )
)
_MAX_REASON_LENGTH: Final = 500


def compute_canonical_executor_source_identity(repo_root: Path) -> str:
    root = repo_root.resolve(strict=False)
    workflow_identity = compute_family_workflow_source_identity(root)
    manifest = {
        relative_path: sha256_file(root / relative_path)
        for relative_path in CANONICAL_EXECUTOR_CRITICAL_SOURCE_FILES
    }
    return sha256_text(
        canonical_json(
            {
                "schema_id": CANONICAL_EXECUTOR_SOURCE_MANIFEST_SCHEMA_ID,
                "family_workflow_source_identity": workflow_identity,
                "files": manifest,
            }
        )
    )


def _reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("bounded reason must be nonempty")
    stripped = value.strip()
    if len(stripped) > _MAX_REASON_LENGTH:
        raise ValueError("bounded reason exceeds length limit")
    return stripped


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    resolved = (path if path.is_absolute() else repo_root / path).resolve(strict=False)
    root = repo_root.resolve(strict=False)
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path is outside repository: {path}") from exc


def _is_under(path: Path, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    base = root.resolve(strict=False)
    return resolved == base or base in resolved.parents


def _require_canonical(path: Path, *, repo_root: Path, label: str) -> None:
    candidate = path if path.is_absolute() else repo_root / path
    if not _is_under(candidate, repo_root / "artifacts" / "canonical"):
        raise ValueError(f"{label} must resolve under artifacts/canonical")


def _reject_canonical(path: Path, *, repo_root: Path, label: str) -> None:
    candidate = path if path.is_absolute() else repo_root / path
    if _is_under(candidate, repo_root / "artifacts" / "canonical"):
        raise ValueError(f"{label} must not resolve under artifacts/canonical")


def _require_absent(path: Path, *, label: str) -> None:
    if path.exists():
        raise ValueError(f"{label} must not already exist")


def _require_strictly_beneath(child: Path, parent: Path, *, label: str) -> None:
    resolved_child = child.resolve(strict=False)
    resolved_parent = parent.resolve(strict=False)
    if resolved_child == resolved_parent or resolved_parent not in resolved_child.parents:
        raise ValueError(f"{label} must be strictly beneath work_dir")


def _require_not_same(left: Path, right: Path, *, label: str) -> None:
    if left.resolve(strict=False) == right.resolve(strict=False):
        raise ValueError(f"{label} reuses a rehearsal path")


@dataclass(frozen=True)
class CanonicalFamilyExecutionRequest:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


def canonical_execution_request_commitment(request: CanonicalFamilyExecutionRequest) -> str:
    payload = dict(request.as_record())
    declared = payload.pop("request_commitment", None)
    observed = sha256_text(canonical_json(payload))
    if declared is not None and declared != observed:
        raise ValueError("canonical execution request commitment is stale")
    return observed


def make_canonical_execution_request(
    *,
    repo_root: Path,
    review_packet: FamilyReviewPacket,
    evidence_bundle: FamilyEvidenceBundle,
    requested_run_id: str,
    allowed_roles: frozenset[str],
    canonical_input_paths: FamilyProtocolInputPaths,
    expected_identity: FamilyProtocolExpectedIdentity,
    intended_work_dir: Path,
    intended_store_path: Path,
    rehearsal_store_path: Path | None = None,
) -> CanonicalFamilyExecutionRequest:
    """Create a request for future canonical execution; perform no execution."""
    root = repo_root.resolve(strict=False)
    for label, path in (
        ("allocation_manifest", canonical_input_paths.allocation_manifest),
        ("firewall_publication", canonical_input_paths.firewall_publication),
        ("d1_result", canonical_input_paths.d1_result),
        ("d1_1_classification", canonical_input_paths.d1_1_classification),
    ):
        _require_canonical(path, repo_root=root, label=label)
    _reject_canonical(intended_work_dir, repo_root=root, label="intended work directory")
    _reject_canonical(intended_store_path, repo_root=root, label="intended store path")
    store = intended_store_path if intended_store_path.is_absolute() else root / intended_store_path
    if store.exists():
        raise ValueError("intended canonical execution store path is not fresh")
    if rehearsal_store_path is not None and store.resolve(strict=False) == (
        rehearsal_store_path if rehearsal_store_path.is_absolute() else root / rehearsal_store_path
    ).resolve(strict=False):
        raise ValueError("intended store path reuses rehearsal store")

    verified = verify_family_protocol_inputs(canonical_input_paths, expected_identity)
    packet_record = review_packet.as_record()
    source_identity = compute_family_workflow_source_identity(root)
    protocol_sha = packet_record["family_protocol_sha256"]
    if packet_record["workflow"]["source_identity"] != source_identity:
        raise ValueError("review packet source identity does not match current source")
    if (
        packet_record["identities"]["allocation_manifest_sha256"]
        != verified.allocation_manifest_sha256
    ):
        raise ValueError("review packet allocation manifest identity mismatch")
    if (
        packet_record["identities"]["allocation_context_sha256"]
        != verified.allocation_context_sha256
    ):
        raise ValueError("review packet allocation context identity mismatch")
    if (
        packet_record["identities"]["allocation_repository_commitment_sha256"]
        != verified.allocation_repository_commitment_sha256
    ):
        raise ValueError("review packet allocation repository commitment mismatch")
    bundle_commitment = evidence_bundle_commitment(evidence_bundle)
    if packet_record["identities"]["evidence_bundle_commitment"] != bundle_commitment:
        raise ValueError("review packet evidence bundle commitment mismatch")
    if sorted(allowed_roles) != list(packet_record["workflow"]["allowed_roles"]):
        raise ValueError("allowed roles do not match review packet")

    record = {
        "schema_id": CANONICAL_EXECUTION_REQUEST_SCHEMA_ID,
        "request_scope": CANONICAL_EXECUTION_REQUEST_SCOPE,
        "family_protocol_sha256": protocol_sha,
        "workflow_name": FAMILY_GRAPH_WORKFLOW_NAME,
        "workflow_version": FAMILY_GRAPH_WORKFLOW_VERSION,
        "workflow_source_identity": source_identity,
        "requested_run_id": requested_run_id,
        "allowed_roles": sorted(allowed_roles),
        "review_packet_commitment": family_review_packet_commitment(review_packet),
        "prepared_evidence_bundle_commitment": bundle_commitment,
        "canonical_inputs": {
            "allocation_manifest_path": _repo_relative(
                canonical_input_paths.allocation_manifest, repo_root=root
            ),
            "allocation_manifest_sha256": verified.allocation_manifest_sha256,
            "firewall_publication_path": _repo_relative(
                canonical_input_paths.firewall_publication, repo_root=root
            ),
            "allocation_context_sha256": verified.allocation_context_sha256,
            "d1_result_path": _repo_relative(canonical_input_paths.d1_result, repo_root=root),
            "d1_result_sha256": verified.d1_result_sha256,
            "d1_1_classification_path": _repo_relative(
                canonical_input_paths.d1_1_classification, repo_root=root
            ),
            "d1_1_classification_sha256": verified.d1_1_classification_sha256,
            "allocation_repository_commitment_sha256": (
                verified.allocation_repository_commitment_sha256
            ),
        },
        "intended_noncanonical_staging": {
            "work_dir": _repo_relative(intended_work_dir, repo_root=root),
            "fresh_store_path": _repo_relative(intended_store_path, repo_root=root),
        },
        "prohibitions": list(PROHIBITIONS),
    }
    commitment = sha256_text(canonical_json(record))
    return CanonicalFamilyExecutionRequest(record={**record, "request_commitment": commitment})


def make_canonical_execution_request_v2(
    *,
    repo_root: Path,
    review_packet: FamilyReviewPacket,
    evidence_bundle: FamilyEvidenceBundle,
    requested_run_id: str,
    allowed_roles: frozenset[str],
    canonical_input_paths: FamilyProtocolInputPaths,
    expected_identity: FamilyProtocolExpectedIdentity,
    intended_work_dir: Path,
    intended_store_path: Path,
    rehearsal_work_dir: Path | None = None,
    rehearsal_store_path: Path | None = None,
) -> CanonicalFamilyExecutionRequest:
    """Create an executable v2 request record; perform no writes or execution."""
    root = repo_root.resolve(strict=False)
    work_dir = intended_work_dir if intended_work_dir.is_absolute() else root / intended_work_dir
    store = intended_store_path if intended_store_path.is_absolute() else root / intended_store_path
    _reject_canonical(work_dir, repo_root=root, label="intended work directory")
    _reject_canonical(store, repo_root=root, label="intended store path")
    _require_absent(work_dir, label="intended canonical execution work directory")
    _require_absent(store, label="intended canonical execution store path")
    _require_strictly_beneath(store, work_dir, label="fresh_store_path")
    if rehearsal_work_dir is not None:
        other = (
            rehearsal_work_dir if rehearsal_work_dir.is_absolute() else root / rehearsal_work_dir
        )
        _require_not_same(work_dir, other, label="work directory")
    if rehearsal_store_path is not None:
        other = (
            rehearsal_store_path
            if rehearsal_store_path.is_absolute()
            else root / rehearsal_store_path
        )
        _require_not_same(store, other, label="store path")

    for label, path in (
        ("allocation_manifest", canonical_input_paths.allocation_manifest),
        ("firewall_publication", canonical_input_paths.firewall_publication),
        ("d1_result", canonical_input_paths.d1_result),
        ("d1_1_classification", canonical_input_paths.d1_1_classification),
    ):
        _require_canonical(path, repo_root=root, label=label)

    verified = verify_family_protocol_inputs(canonical_input_paths, expected_identity)
    packet_record = review_packet.as_record()
    source_identity = compute_family_workflow_source_identity(root)
    executor_identity = compute_canonical_executor_source_identity(root)
    protocol_sha = packet_record["family_protocol_sha256"]
    bundle_commitment = evidence_bundle_commitment(evidence_bundle)
    if packet_record["workflow"]["source_identity"] != source_identity:
        raise ValueError("review packet source identity does not match current source")
    if packet_record["identities"]["evidence_bundle_commitment"] != bundle_commitment:
        raise ValueError("review packet evidence bundle commitment mismatch")
    if sorted(allowed_roles) != list(packet_record["workflow"]["allowed_roles"]):
        raise ValueError("allowed roles do not match review packet")

    record = {
        "schema_id": CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID,
        "request_scope": CANONICAL_EXECUTION_REQUEST_SCOPE,
        "family_protocol_sha256": protocol_sha,
        "workflow_name": FAMILY_GRAPH_WORKFLOW_NAME,
        "workflow_version": FAMILY_GRAPH_WORKFLOW_VERSION,
        "workflow_source_identity": source_identity,
        "canonical_executor_source_identity": executor_identity,
        "requested_run_id": requested_run_id,
        "allowed_roles": sorted(allowed_roles),
        "review_packet_commitment": family_review_packet_commitment(review_packet),
        "prepared_evidence_bundle_commitment": bundle_commitment,
        "canonical_inputs": {
            "allocation_manifest_path": _repo_relative(
                canonical_input_paths.allocation_manifest, repo_root=root
            ),
            "allocation_manifest_sha256": verified.allocation_manifest_sha256,
            "firewall_publication_path": _repo_relative(
                canonical_input_paths.firewall_publication, repo_root=root
            ),
            "firewall_publication_sha256": sha256_file(
                root / _repo_relative(canonical_input_paths.firewall_publication, repo_root=root)
            ),
            "allocation_context_sha256": verified.allocation_context_sha256,
            "d1_result_path": _repo_relative(canonical_input_paths.d1_result, repo_root=root),
            "d1_result_sha256": verified.d1_result_sha256,
            "d1_1_classification_path": _repo_relative(
                canonical_input_paths.d1_1_classification, repo_root=root
            ),
            "d1_1_classification_sha256": verified.d1_1_classification_sha256,
            "allocation_repository_commitment_sha256": (
                verified.allocation_repository_commitment_sha256
            ),
        },
        "intended_noncanonical_staging": {
            "work_dir": _repo_relative(work_dir, repo_root=root),
            "fresh_store_path": _repo_relative(store, repo_root=root),
        },
        "prohibitions": list(PROHIBITIONS),
    }
    commitment = sha256_text(canonical_json(record))
    return CanonicalFamilyExecutionRequest(record={**record, "request_commitment": commitment})


def canonical_execution_request_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyExecutionRequest:
    if record.get("schema_id") != CANONICAL_EXECUTION_REQUEST_SCHEMA_ID:
        raise ValueError("unsupported canonical execution request schema")
    request = CanonicalFamilyExecutionRequest(record=dict(record))
    canonical_execution_request_commitment(request)
    for item in PROHIBITIONS:
        if item not in record.get("prohibitions", ()):
            raise ValueError(f"canonical execution request missing prohibition: {item}")
    return request


def canonical_execution_request_v2_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyExecutionRequest:
    if record.get("schema_id") != CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID:
        if record.get("schema_id") == CANONICAL_EXECUTION_REQUEST_SCHEMA_ID:
            raise ValueError(
                "v1 canonical execution authorization is validation-only and is not executable"
            )
        raise ValueError("unsupported executable canonical execution request schema")
    required = {
        "schema_id",
        "request_scope",
        "family_protocol_sha256",
        "workflow_name",
        "workflow_version",
        "workflow_source_identity",
        "canonical_executor_source_identity",
        "requested_run_id",
        "allowed_roles",
        "review_packet_commitment",
        "prepared_evidence_bundle_commitment",
        "canonical_inputs",
        "intended_noncanonical_staging",
        "prohibitions",
        "request_commitment",
    }
    missing = required - set(record)
    if missing:
        raise ValueError(f"canonical execution v2 request missing fields: {sorted(missing)}")
    unexpected = set(record) - required
    if unexpected:
        raise ValueError(f"unexpected canonical execution v2 request fields: {sorted(unexpected)}")
    request = CanonicalFamilyExecutionRequest(record=dict(record))
    canonical_execution_request_commitment(request)
    validate_sha256_identity(
        record["canonical_executor_source_identity"],
        label="canonical_executor_source_identity",
    )
    inputs = record["canonical_inputs"]
    if not isinstance(inputs, dict):
        raise ValueError("canonical_inputs must be an object")
    for key in (
        "allocation_manifest_sha256",
        "firewall_publication_sha256",
        "allocation_context_sha256",
        "allocation_repository_commitment_sha256",
        "d1_result_sha256",
        "d1_1_classification_sha256",
    ):
        validate_sha256_identity(inputs[key], label=key)
    staging = record["intended_noncanonical_staging"]
    if not isinstance(staging, dict):
        raise ValueError("intended_noncanonical_staging must be an object")
    for item in PROHIBITIONS:
        if item not in record.get("prohibitions", ()):
            raise ValueError(f"canonical execution request missing prohibition: {item}")
    return request


@dataclass(frozen=True)
class CanonicalFamilyExecutionAuthorization:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


def derive_canonical_execution_authorization_id(payload: dict[str, Any]) -> str:
    return sha256_text(canonical_json(payload))


def make_canonical_execution_authorization(
    *,
    request: CanonicalFamilyExecutionRequest,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> CanonicalFamilyExecutionAuthorization:
    if disposition not in ALLOWED_CANONICAL_EXECUTION_DISPOSITIONS:
        raise ValueError("invalid canonical execution authorization disposition")
    request_record = request.as_record()
    request_commitment = canonical_execution_request_commitment(request)
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    payload = {
        "schema_id": CANONICAL_EXECUTION_AUTHORIZATION_SCHEMA_ID,
        "authorization_scope": CANONICAL_EXECUTION_AUTHORIZATION_SCOPE,
        "canonical_execution_request_commitment": request_commitment,
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "workflow_source_identity": request_record["workflow_source_identity"],
        "review_packet_commitment": request_record["review_packet_commitment"],
        "requested_run_id": request_record["requested_run_id"],
        "disposition": disposition,
        "reviewer_identity": reviewer,
        "review_timestamp": timestamp,
        "bounded_reason": reason,
    }
    return CanonicalFamilyExecutionAuthorization(
        record={
            **payload,
            "authorization_id": derive_canonical_execution_authorization_id(payload),
        }
    )


def make_canonical_execution_authorization_v2(
    *,
    request: CanonicalFamilyExecutionRequest,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> CanonicalFamilyExecutionAuthorization:
    if disposition not in ALLOWED_CANONICAL_EXECUTION_DISPOSITIONS:
        raise ValueError("invalid canonical execution authorization disposition")
    request = canonical_execution_request_v2_from_record(request.as_record())
    request_record = request.as_record()
    request_commitment = canonical_execution_request_commitment(request)
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    payload = {
        "schema_id": CANONICAL_EXECUTION_AUTHORIZATION_V2_SCHEMA_ID,
        "authorization_scope": CANONICAL_EXECUTION_AUTHORIZATION_SCOPE,
        "canonical_execution_request_commitment": request_commitment,
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "workflow_source_identity": request_record["workflow_source_identity"],
        "canonical_executor_source_identity": request_record["canonical_executor_source_identity"],
        "review_packet_commitment": request_record["review_packet_commitment"],
        "requested_run_id": request_record["requested_run_id"],
        "disposition": disposition,
        "reviewer_identity": reviewer,
        "review_timestamp": timestamp,
        "bounded_reason": reason,
    }
    return CanonicalFamilyExecutionAuthorization(
        record={
            **payload,
            "authorization_id": derive_canonical_execution_authorization_id(payload),
        }
    )


def canonical_execution_authorization_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyExecutionAuthorization:
    if record.get("schema_id") != CANONICAL_EXECUTION_AUTHORIZATION_SCHEMA_ID:
        raise ValueError("unsupported canonical execution authorization schema")
    payload = dict(record)
    authorization_id = payload.pop("authorization_id", None)
    if payload.get("disposition") not in ALLOWED_CANONICAL_EXECUTION_DISPOSITIONS:
        raise ValueError("invalid canonical execution authorization disposition")
    validate_sha256_identity(
        payload["canonical_execution_request_commitment"],
        label="canonical_execution_request_commitment",
    )
    validate_sha256_identity(payload["family_protocol_sha256"], label="family_protocol_sha256")
    validate_sha256_identity(payload["workflow_source_identity"], label="workflow_source_identity")
    validate_sha256_identity(payload["review_packet_commitment"], label="review_packet_commitment")
    validate_source_identity(payload["reviewer_identity"])
    parse_timestamp(payload["review_timestamp"])
    _reason(payload["bounded_reason"])
    if authorization_id != derive_canonical_execution_authorization_id(payload):
        raise ValueError("canonical execution authorization ID is stale")
    return CanonicalFamilyExecutionAuthorization(record=dict(record))


def canonical_execution_authorization_v2_from_record(
    record: dict[str, Any],
) -> CanonicalFamilyExecutionAuthorization:
    if record.get("schema_id") != CANONICAL_EXECUTION_AUTHORIZATION_V2_SCHEMA_ID:
        if record.get("schema_id") == CANONICAL_EXECUTION_AUTHORIZATION_SCHEMA_ID:
            raise ValueError(
                "v1 canonical execution authorization is validation-only and is not executable"
            )
        raise ValueError("unsupported executable canonical execution authorization schema")
    allowed = {
        "schema_id",
        "authorization_scope",
        "canonical_execution_request_commitment",
        "family_protocol_sha256",
        "workflow_source_identity",
        "canonical_executor_source_identity",
        "review_packet_commitment",
        "requested_run_id",
        "disposition",
        "reviewer_identity",
        "review_timestamp",
        "bounded_reason",
        "authorization_id",
    }
    unexpected = set(record) - allowed
    if unexpected:
        raise ValueError(
            f"unexpected canonical execution v2 authorization fields: {sorted(unexpected)}"
        )
    payload = dict(record)
    authorization_id = payload.pop("authorization_id", None)
    if payload.get("disposition") not in ALLOWED_CANONICAL_EXECUTION_DISPOSITIONS:
        raise ValueError("invalid canonical execution authorization disposition")
    for key in (
        "canonical_execution_request_commitment",
        "family_protocol_sha256",
        "workflow_source_identity",
        "canonical_executor_source_identity",
        "review_packet_commitment",
    ):
        validate_sha256_identity(payload[key], label=key)
    validate_source_identity(payload["reviewer_identity"])
    parse_timestamp(payload["review_timestamp"])
    _reason(payload["bounded_reason"])
    if authorization_id != derive_canonical_execution_authorization_id(payload):
        raise ValueError("canonical execution authorization ID is stale")
    return CanonicalFamilyExecutionAuthorization(record=dict(record))


@dataclass(frozen=True)
class CanonicalExecutionAuthorizationValidation:
    status: str
    request_commitment: str
    authorization_id: str

    def as_record(self) -> dict[str, str]:
        return {
            "status": self.status,
            "request_commitment": self.request_commitment,
            "authorization_id": self.authorization_id,
        }


def validate_canonical_execution_authorization(
    *,
    request: CanonicalFamilyExecutionRequest,
    authorization: CanonicalFamilyExecutionAuthorization,
    repo_root: Path,
    review_packet: FamilyReviewPacket,
    evidence_bundle: FamilyEvidenceBundle,
) -> CanonicalExecutionAuthorizationValidation:
    """Validate request and authorization; never execute or write."""
    root = repo_root.resolve(strict=False)
    request = canonical_execution_request_from_record(request.as_record())
    authorization = canonical_execution_authorization_from_record(authorization.as_record())
    request_record = request.as_record()
    auth = authorization.as_record()
    request_commitment = canonical_execution_request_commitment(request)
    if auth["canonical_execution_request_commitment"] != request_commitment:
        raise ValueError("authorization is for another canonical execution request")
    if auth["family_protocol_sha256"] != request_record["family_protocol_sha256"]:
        raise ValueError("authorization protocol mismatch")
    if auth["workflow_source_identity"] != request_record["workflow_source_identity"]:
        raise ValueError("authorization source identity mismatch")
    if auth["review_packet_commitment"] != request_record["review_packet_commitment"]:
        raise ValueError("authorization review packet mismatch")
    if auth["requested_run_id"] != request_record["requested_run_id"]:
        raise ValueError("authorization run ID mismatch")
    if compute_family_workflow_source_identity(root) != request_record["workflow_source_identity"]:
        raise ValueError("current workflow source identity differs from request")
    if family_review_packet_commitment(review_packet) != request_record["review_packet_commitment"]:
        raise ValueError("review packet commitment mismatch")
    if (
        evidence_bundle_commitment(evidence_bundle)
        != request_record["prepared_evidence_bundle_commitment"]
    ):
        raise ValueError("evidence bundle commitment mismatch")
    inputs = request_record["canonical_inputs"]
    paths = FamilyProtocolInputPaths(
        allocation_manifest=root / inputs["allocation_manifest_path"],
        firewall_publication=root / inputs["firewall_publication_path"],
        d1_result=root / inputs["d1_result_path"],
        d1_1_classification=root / inputs["d1_1_classification_path"],
    )
    expected = FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=inputs["allocation_manifest_sha256"],
        allocation_context_sha256=inputs["allocation_context_sha256"],
        allocation_repository_commitment_sha256=inputs["allocation_repository_commitment_sha256"],
        d1_result_sha256=inputs["d1_result_sha256"],
        d1_1_classification_sha256=inputs["d1_1_classification_sha256"],
    )
    for label, path in (
        ("allocation_manifest", paths.allocation_manifest),
        ("firewall_publication", paths.firewall_publication),
        ("d1_result", paths.d1_result),
        ("d1_1_classification", paths.d1_1_classification),
    ):
        _require_canonical(path, repo_root=root, label=label)
    verify_family_protocol_inputs(paths, expected)
    staging = request_record["intended_noncanonical_staging"]
    work_dir = root / staging["work_dir"]
    store_path = root / staging["fresh_store_path"]
    _reject_canonical(work_dir, repo_root=root, label="intended work directory")
    _reject_canonical(store_path, repo_root=root, label="intended store path")
    if store_path.exists():
        raise ValueError("intended canonical execution store path is no longer fresh")
    status = (
        "AUTHORIZED"
        if auth["disposition"] == AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION
        else "WITHHELD"
    )
    return CanonicalExecutionAuthorizationValidation(
        status=status,
        request_commitment=request_commitment,
        authorization_id=auth["authorization_id"],
    )


def validate_executable_canonical_authorization_v2(
    *,
    request: CanonicalFamilyExecutionRequest,
    authorization: CanonicalFamilyExecutionAuthorization,
    repo_root: Path,
    review_packet: FamilyReviewPacket,
    evidence_bundle: FamilyEvidenceBundle,
) -> CanonicalExecutionAuthorizationValidation:
    """Validate an executable v2 request/authorization pair; perform no writes."""
    root = repo_root.resolve(strict=False)
    request = canonical_execution_request_v2_from_record(request.as_record())
    authorization = canonical_execution_authorization_v2_from_record(authorization.as_record())
    request_record = request.as_record()
    auth = authorization.as_record()
    request_commitment = canonical_execution_request_commitment(request)
    if auth["canonical_execution_request_commitment"] != request_commitment:
        raise ValueError("authorization is for another canonical execution request")
    for key in (
        "family_protocol_sha256",
        "workflow_source_identity",
        "canonical_executor_source_identity",
        "review_packet_commitment",
        "requested_run_id",
    ):
        if auth[key] != request_record[key]:
            raise ValueError(f"authorization {key} mismatch")
    if compute_family_workflow_source_identity(root) != request_record["workflow_source_identity"]:
        raise ValueError("current workflow source identity differs from request")
    if (
        compute_canonical_executor_source_identity(root)
        != request_record["canonical_executor_source_identity"]
    ):
        raise ValueError("current canonical executor source identity differs from request")
    if family_review_packet_commitment(review_packet) != request_record["review_packet_commitment"]:
        raise ValueError("review packet commitment mismatch")
    if (
        evidence_bundle_commitment(evidence_bundle)
        != request_record["prepared_evidence_bundle_commitment"]
    ):
        raise ValueError("evidence bundle commitment mismatch")

    inputs = request_record["canonical_inputs"]
    paths = FamilyProtocolInputPaths(
        allocation_manifest=root / inputs["allocation_manifest_path"],
        firewall_publication=root / inputs["firewall_publication_path"],
        d1_result=root / inputs["d1_result_path"],
        d1_1_classification=root / inputs["d1_1_classification_path"],
    )
    expected = FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=inputs["allocation_manifest_sha256"],
        allocation_context_sha256=inputs["allocation_context_sha256"],
        allocation_repository_commitment_sha256=inputs["allocation_repository_commitment_sha256"],
        d1_result_sha256=inputs["d1_result_sha256"],
        d1_1_classification_sha256=inputs["d1_1_classification_sha256"],
    )
    for label, path in (
        ("allocation_manifest", paths.allocation_manifest),
        ("firewall_publication", paths.firewall_publication),
        ("d1_result", paths.d1_result),
        ("d1_1_classification", paths.d1_1_classification),
    ):
        _require_canonical(path, repo_root=root, label=label)
    if sha256_file(paths.firewall_publication) != inputs["firewall_publication_sha256"]:
        raise ValueError("canonical firewall publication file SHA mismatch")
    verify_family_protocol_inputs(paths, expected)

    staging = request_record["intended_noncanonical_staging"]
    work_dir = root / staging["work_dir"]
    store_path = root / staging["fresh_store_path"]
    _reject_canonical(work_dir, repo_root=root, label="intended work directory")
    _reject_canonical(store_path, repo_root=root, label="intended store path")
    _require_absent(work_dir, label="intended canonical execution work directory")
    _require_absent(store_path, label="intended canonical execution store path")
    _require_strictly_beneath(store_path, work_dir, label="fresh_store_path")
    for item in PROHIBITIONS:
        if item not in request_record.get("prohibitions", ()):
            raise ValueError(f"canonical execution request missing prohibition: {item}")
    status = (
        "AUTHORIZED"
        if auth["disposition"] == AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION
        else "WITHHELD"
    )
    return CanonicalExecutionAuthorizationValidation(
        status=status,
        request_commitment=request_commitment,
        authorization_id=auth["authorization_id"],
    )

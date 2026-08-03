"""Read-only review boundary for authorized canonical execution evidence.

This module inspects Stage 2H staged execution artifacts. It never executes
the family workflow, never publishes canonical results, and never writes under
``artifacts/canonical``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.evidence.immutable import refuse_overwrite
from relate.family.authorization import (
    CanonicalFamilyExecutionAuthorization,
    CanonicalFamilyExecutionRequest,
    canonical_execution_authorization_v2_from_record,
    canonical_execution_request_commitment,
    canonical_execution_request_v2_from_record,
    compute_canonical_executor_source_identity,
)
from relate.family.execution import (
    canonical_execution_claim_from_record,
    canonical_execution_receipt_from_record,
)
from relate.family.review import (
    FamilyReviewPacket,
    family_review_packet_commitment,
    family_review_packet_from_record,
    reject_canonical_path,
)
from relate.family.sources import parse_timestamp, validate_source_identity
from relate.family.verification import (
    FamilyProtocolExpectedIdentity,
    FamilyProtocolInputPaths,
    verify_family_protocol_inputs,
)
from relate.family.workflow.composition import compute_family_workflow_source_identity
from relate.family.workflow.models import (
    FamilyEvidenceBundle,
    evidence_bundle_commitment,
    validate_sha256_identity,
)

EXECUTION_REVIEW_REPORT_SCHEMA_ID: Final = (
    "relate-family-canonical-execution-review-report-v1"
)
EXECUTION_REVIEW_DISPOSITION_SCHEMA_ID: Final = (
    "relate-family-canonical-execution-review-disposition-v1"
)
EXECUTION_REVIEW_BUNDLE_SCHEMA_ID: Final = (
    "relate-family-canonical-execution-review-bundle-v1"
)
EXECUTION_REVIEW_SCOPE: Final = "CANONICAL_EXECUTION_EVIDENCE_INTEGRITY_ONLY"
BOUNDED_SCIENTIFIC_PAYLOAD_SCHEMA_ID: Final = (
    "relate-family-bounded-scientific-payload-v1"
)
FAILURE_SCHEMA_ID: Final = "relate-family-canonical-execution-failure-v1"
TRACE_SCHEMA_ID: Final = "relate-family-canonical-execution-trace-v1"
ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW: Final = (
    "ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW"
)
WITHHOLD_EXECUTION_EVIDENCE: Final = "WITHHOLD_EXECUTION_EVIDENCE"
ALLOWED_EXECUTION_REVIEW_DISPOSITIONS: Final = (
    ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
    WITHHOLD_EXECUTION_EVIDENCE,
)
NOT_DETERMINED: Final[tuple[str, ...]] = (
    "MATERIAL_CONTAMINATION",
    "MATERIALITY",
    "ALLOCATION_VALIDITY",
    "REALLOCATION",
    "CANONICAL_PUBLICATION",
    "MODEL_REFIT",
    "C0_REPLAY",
    "PROTECTED_ROW_ACCESS",
    "D2_AUTHORIZATION",
)
EXPECTED_STEP_NAMES: Final[tuple[str, ...]] = (
    "verify_family_inputs",
    "register_allocation",
    "register_prepared_evidence",
    "resolve_candidates",
    "assess_graph_readiness",
    "build_family_components",
    "analyse_role_crossings",
    "determine_family_outcome",
)
_MAX_REASON_LENGTH: Final = 500


class ExecutionReviewTerminalStatus(StrEnum):
    VALID_COMPLETED = "VALID_COMPLETED"
    VALID_BLOCKED = "VALID_BLOCKED"
    VALID_FAILED = "VALID_FAILED"
    FAILED_BEFORE_CLAIM_PERSISTED = "FAILED_BEFORE_CLAIM_PERSISTED"


@dataclass(frozen=True)
class CanonicalExecutionReviewReport:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)

    @property
    def report_commitment(self) -> str:
        return str(self.record["report_commitment"])


def _reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("bounded reason must be nonempty")
    stripped = value.strip()
    if len(stripped) > _MAX_REASON_LENGTH:
        raise ValueError("bounded reason exceeds length limit")
    return stripped


def _commit(record: dict[str, Any], field: str) -> str:
    payload = dict(record)
    declared = payload.pop(field, None)
    observed = sha256_text(canonical_json(payload))
    if declared is not None and declared != observed:
        raise ValueError(f"{field} is stale")
    return observed


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _load_json_object(path: Path) -> dict[str, Any]:
    import json

    return _require_object(json.loads(path.read_text(encoding="utf-8")), label=str(path))


def _relative(repo_root: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()


def _repo_path(repo_root: Path, value: str) -> Path:
    return (repo_root / value).resolve(strict=False)


def _is_under(path: Path, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    base = root.resolve(strict=False)
    return resolved == base or base in resolved.parents


def _validate_work_dir(*, repo_root: Path, request_record: dict[str, Any], work_dir: Path) -> None:
    expected = _repo_path(repo_root, request_record["intended_noncanonical_staging"]["work_dir"])
    if work_dir.resolve(strict=False) != expected:
        raise ValueError("work_dir is not the authorized work directory")
    if not _is_under(work_dir, repo_root):
        raise ValueError("work_dir escapes repository")
    reject_canonical_path(work_dir, repo_root=repo_root, label="execution review work_dir")
    store = _repo_path(
        repo_root, request_record["intended_noncanonical_staging"]["fresh_store_path"]
    )
    if store.resolve(strict=False) == work_dir.resolve(strict=False):
        raise ValueError("authorized store must be strictly beneath work_dir")
    if work_dir.resolve(strict=False) not in store.resolve(strict=False).parents:
        raise ValueError("authorized store must be strictly beneath work_dir")


def _optional_artifact(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    return _load_json_object(path), sha256_file(path)


def canonical_execution_failure_from_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _require_object(record, label="canonical execution failure")
    allowed = {
        "schema_id",
        "canonical_execution_request_commitment",
        "canonical_execution_authorization_id",
        "failed_step",
        "bounded_exception_type",
        "bounded_message",
    }
    if data.get("schema_id") != FAILURE_SCHEMA_ID:
        raise ValueError("unsupported canonical execution failure schema")
    unexpected = set(data) - allowed
    if unexpected:
        raise ValueError(f"unexpected failure fields: {sorted(unexpected)}")
    for key in ("canonical_execution_request_commitment",):
        validate_sha256_identity(data[key], label=key)
    if not isinstance(data["canonical_execution_authorization_id"], str):
        raise ValueError("authorization ID must be a string")
    failed_step = data.get("failed_step")
    if failed_step is not None and (
        not isinstance(failed_step, str) or len(failed_step) > 120
    ):
        raise ValueError("failed_step is malformed")
    for key in ("bounded_exception_type", "bounded_message"):
        if not isinstance(data.get(key), str) or len(data[key]) > 500:
            raise ValueError(f"{key} is malformed")
    return data


def canonical_execution_trace_from_record(record: dict[str, Any]) -> dict[str, Any]:
    data = _require_object(record, label="canonical execution trace")
    if data.get("schema_id") != TRACE_SCHEMA_ID:
        raise ValueError("unsupported canonical execution trace schema")
    if set(data) != {"schema_id", "events"}:
        raise ValueError("unexpected trace fields")
    events = data["events"]
    if not isinstance(events, list):
        raise ValueError("trace events must be a list")
    allowed = {
        "event_type",
        "step_name",
        "step_version",
        "timestamp",
        "input_commitment",
        "output_commitment",
        "latency_seconds",
        "blocked_reason",
        "failure_message",
    }
    for event in events:
        item = _require_object(event, label="trace event")
        unexpected = set(item) - allowed
        if unexpected:
            raise ValueError(f"unexpected trace event fields: {sorted(unexpected)}")
        if item.get("event_type") not in {
            "STEP_STARTED",
            "STEP_COMPLETED",
            "STEP_BLOCKED",
            "STEP_FAILED",
        }:
            raise ValueError("unsupported trace event type")
        if not isinstance(item.get("step_name"), str) or not item["step_name"].strip():
            raise ValueError("trace step_name is malformed")
        if not isinstance(item.get("step_version"), str) or not item["step_version"].strip():
            raise ValueError("trace step_version is malformed")
        parse_timestamp(item["timestamp"])
        for key in ("input_commitment", "output_commitment"):
            if item.get(key) is not None:
                validate_sha256_identity(item[key], label=key)
        latency = item.get("latency_seconds")
        if latency is not None and (
            not isinstance(latency, int | float) or not math.isfinite(latency) or latency < 0
        ):
            raise ValueError("trace latency is malformed")
        if item["event_type"] != "STEP_BLOCKED" and item.get("blocked_reason") is not None:
            raise ValueError("blocked_reason is only valid for STEP_BLOCKED")
        if item["event_type"] != "STEP_FAILED" and item.get("failure_message") is not None:
            raise ValueError("failure_message is only valid for STEP_FAILED")
    return data


def bounded_scientific_payload_commitment(packet: FamilyReviewPacket) -> str:
    record = packet.as_record()
    identities = dict(record.get("identities", {}))
    workflow = dict(record.get("workflow", {}))
    payload = {
        "schema_id": BOUNDED_SCIENTIFIC_PAYLOAD_SCHEMA_ID,
        "family_protocol_sha256": record["family_protocol_sha256"],
        "workflow_name": workflow.get("name"),
        "workflow_version": workflow.get("version"),
        "allowed_roles": workflow.get("allowed_roles"),
        "identities": identities,
        "bounded_family_outcome": record.get("bounded_family_outcome"),
        "bounded_role_crossing_analysis": record.get("bounded_role_crossing_analysis"),
        "materiality_inputs": record.get("materiality_inputs"),
        "firewall_declarations": record.get("firewall_declarations"),
        "publication_scope": record.get("publication_scope"),
        "packet_contains": record.get("packet_contains"),
        "not_concluded": record.get("not_concluded"),
        "downstream_decisions": record.get("downstream_decisions"),
    }
    return sha256_text(canonical_json(payload))


def _validate_receipt_steps(receipt: dict[str, Any]) -> dict[str, Any]:
    steps = receipt.get("ordered_steps")
    if not isinstance(steps, list):
        raise ValueError("receipt ordered_steps must be a list")
    names = tuple(item.get("step_name") for item in steps if isinstance(item, dict))
    status = receipt["execution_status"]
    if status == "COMPLETED":
        if names != EXPECTED_STEP_NAMES:
            raise ValueError("completed receipt has unexpected step order")
        if any(item.get("status") != "COMPLETED" for item in steps):
            raise ValueError("completed receipt contains non-completed step")
    elif status == "BLOCKED":
        if not names or EXPECTED_STEP_NAMES[: len(names)] != names:
            raise ValueError("blocked receipt has unexpected step prefix")
        blocked = [item for item in steps if item.get("status") == "BLOCKED"]
        if len(blocked) != 1 or steps[-1].get("status") != "BLOCKED":
            raise ValueError("blocked receipt must end with one blocked step")
        if not steps[-1].get("blocked_reason"):
            raise ValueError("blocked receipt missing blocked reason")
    else:
        raise ValueError("unsupported receipt status")
    for item in steps:
        if item.get("step_version") != "1":
            raise ValueError("unexpected receipt step version")
        validate_sha256_identity(item["input_commitment"], label="step input commitment")
        validate_sha256_identity(item["output_commitment"], label="step output commitment")
    return {"step_count": len(steps), "step_names": list(names)}


def _validate_trace_against_receipt(
    trace: dict[str, Any], receipt: dict[str, Any] | None
) -> dict[str, Any]:
    events = trace["events"]
    if receipt is None:
        return {"event_count": len(events), "runner_events_validated": False}
    by_step = {item["step_name"]: item for item in receipt["ordered_steps"]}
    for event in events:
        step = by_step.get(event["step_name"])
        if step is None:
            raise ValueError("trace event references step absent from receipt")
        if event["event_type"] == "STEP_STARTED":
            if event.get("input_commitment") != step["input_commitment"]:
                raise ValueError("trace input commitment mismatch")
        if event["event_type"] in {"STEP_COMPLETED", "STEP_BLOCKED"}:
            if event.get("output_commitment") != step["output_commitment"]:
                raise ValueError("trace output commitment mismatch")
    return {"event_count": len(events), "runner_events_validated": True}


def inspect_authorized_canonical_execution(
    *,
    repo_root: Path,
    request: CanonicalFamilyExecutionRequest,
    authorization: CanonicalFamilyExecutionAuthorization,
    authorization_review_packet: FamilyReviewPacket,
    evidence_bundle: FamilyEvidenceBundle,
    work_dir: Path,
    file_identities: dict[str, str] | None = None,
) -> CanonicalExecutionReviewReport:
    root = repo_root.resolve(strict=False)
    request = canonical_execution_request_v2_from_record(request.as_record())
    authorization = canonical_execution_authorization_v2_from_record(authorization.as_record())
    request_record = request.as_record()
    auth_record = authorization.as_record()
    request_commitment = canonical_execution_request_commitment(request)
    if auth_record["canonical_execution_request_commitment"] != request_commitment:
        raise ValueError("authorization is for another request")
    if family_review_packet_commitment(authorization_review_packet) != request_record[
        "review_packet_commitment"
    ]:
        raise ValueError("authorization review packet commitment mismatch")
    if evidence_bundle_commitment(evidence_bundle) != request_record[
        "prepared_evidence_bundle_commitment"
    ]:
        raise ValueError("evidence bundle commitment mismatch")
    _validate_work_dir(repo_root=root, request_record=request_record, work_dir=work_dir)

    inputs = request_record["canonical_inputs"]
    verify_family_protocol_inputs(
        FamilyProtocolInputPaths(
            allocation_manifest=root / inputs["allocation_manifest_path"],
            firewall_publication=root / inputs["firewall_publication_path"],
            d1_result=root / inputs["d1_result_path"],
            d1_1_classification=root / inputs["d1_1_classification_path"],
        ),
        FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=inputs["allocation_manifest_sha256"],
            allocation_context_sha256=inputs["allocation_context_sha256"],
            allocation_repository_commitment_sha256=inputs[
                "allocation_repository_commitment_sha256"
            ],
            d1_result_sha256=inputs["d1_result_sha256"],
            d1_1_classification_sha256=inputs["d1_1_classification_sha256"],
        ),
    )

    claim_raw, claim_file_sha = _optional_artifact(work_dir / "canonical-execution-claim.json")
    receipt_raw, receipt_file_sha = _optional_artifact(
        work_dir / "canonical-execution-receipt.json"
    )
    failure_raw, failure_file_sha = _optional_artifact(
        work_dir / "canonical-execution-failure.json"
    )
    trace_raw, trace_file_sha = _optional_artifact(work_dir / "canonical-execution-trace.json")
    packet_raw, packet_file_sha = _optional_artifact(
        work_dir / "canonical-execution-review-packet.json"
    )
    if trace_raw is None:
        raise ValueError("canonical execution trace is required")
    trace = canonical_execution_trace_from_record(trace_raw)
    claim = canonical_execution_claim_from_record(claim_raw) if claim_raw is not None else None
    receipt = (
        canonical_execution_receipt_from_record(receipt_raw) if receipt_raw is not None else None
    )
    failure = (
        canonical_execution_failure_from_record(failure_raw) if failure_raw is not None else None
    )
    if receipt is not None and failure is not None:
        raise ValueError("receipt and failure record conflict")
    if receipt is None and failure is None:
        raise ValueError("missing terminal execution evidence")

    execution_packet: FamilyReviewPacket | None = None
    execution_packet_commitment: str | None = None
    if packet_raw is not None:
        execution_packet = family_review_packet_from_record(packet_raw)
        execution_packet_commitment = family_review_packet_commitment(execution_packet)

    if receipt is not None and receipt["execution_status"] == "COMPLETED":
        if execution_packet is None:
            raise ValueError("completed receipt requires review packet")
        terminal_status = ExecutionReviewTerminalStatus.VALID_COMPLETED
    elif receipt is not None and receipt["execution_status"] == "BLOCKED":
        if execution_packet is not None:
            raise ValueError("blocked receipt forbids review packet")
        terminal_status = ExecutionReviewTerminalStatus.VALID_BLOCKED
    elif failure is not None and claim is None:
        if execution_packet is not None:
            raise ValueError("failed execution forbids review packet")
        terminal_status = ExecutionReviewTerminalStatus.FAILED_BEFORE_CLAIM_PERSISTED
    else:
        if execution_packet is not None:
            raise ValueError("failed execution forbids review packet")
        terminal_status = ExecutionReviewTerminalStatus.VALID_FAILED

    if claim is not None:
        if claim["canonical_execution_request_commitment"] != request_commitment:
            raise ValueError("claim request commitment mismatch")
        if claim["canonical_execution_authorization_id"] != auth_record["authorization_id"]:
            raise ValueError("claim authorization ID mismatch")
    if failure is not None:
        if failure["canonical_execution_request_commitment"] != request_commitment:
            raise ValueError("failure request commitment mismatch")
        if failure["canonical_execution_authorization_id"] != auth_record["authorization_id"]:
            raise ValueError("failure authorization ID mismatch")

    receipt_summary: dict[str, Any] = {}
    if receipt is not None:
        if claim is None:
            raise ValueError("receipt requires claim")
        if receipt["canonical_execution_request_commitment"] != request_commitment:
            raise ValueError("receipt request commitment mismatch")
        if receipt["canonical_execution_authorization_id"] != auth_record["authorization_id"]:
            raise ValueError("receipt authorization ID mismatch")
        if receipt["claim_commitment"] != claim["claim_commitment"]:
            raise ValueError("receipt claim commitment mismatch")
        if receipt["staging_work_directory"] != _relative(root, work_dir):
            raise ValueError("receipt work directory mismatch")
        if receipt["staging_store_path"] != request_record["intended_noncanonical_staging"][
            "fresh_store_path"
        ]:
            raise ValueError("receipt store path mismatch")
        receipt_summary = _validate_receipt_steps(receipt)
        if execution_packet_commitment is not None and receipt.get(
            "canonical_run_review_packet_commitment"
        ) != execution_packet_commitment:
            raise ValueError("receipt review-packet commitment mismatch")

    trace_summary = _validate_trace_against_receipt(trace, receipt)
    rehearsal_payload = bounded_scientific_payload_commitment(authorization_review_packet)
    execution_payload = (
        bounded_scientific_payload_commitment(execution_packet)
        if execution_packet is not None
        else None
    )
    scientific_equivalent = execution_payload == rehearsal_payload if execution_payload else False
    if (
        terminal_status is ExecutionReviewTerminalStatus.VALID_COMPLETED
        and not scientific_equivalent
    ):
        raise ValueError("canonical execution scientific payload differs from rehearsal")

    store_path = _repo_path(
        root, request_record["intended_noncanonical_staging"]["fresh_store_path"]
    )
    if terminal_status is ExecutionReviewTerminalStatus.VALID_COMPLETED and not store_path.exists():
        raise ValueError("completed execution store is missing")
    files = {
        **(file_identities or {}),
        "claim": claim_file_sha,
        "receipt": receipt_file_sha,
        "failure": failure_file_sha,
        "trace": trace_file_sha,
        "canonical_execution_review_packet": packet_file_sha,
    }
    files = {key: value for key, value in files.items() if value is not None}
    current_workflow = compute_family_workflow_source_identity(root)
    current_executor = compute_canonical_executor_source_identity(root)
    record = {
        "schema_id": EXECUTION_REVIEW_REPORT_SCHEMA_ID,
        "review_scope": EXECUTION_REVIEW_SCOPE,
        "terminal_execution_status": terminal_status.value,
        "canonical_execution_request_commitment": request_commitment,
        "canonical_execution_authorization_id": auth_record["authorization_id"],
        "authorized_work_directory": _relative(root, work_dir),
        "authorized_store_path": _relative(root, store_path),
        "claim_commitment": claim.get("claim_commitment") if claim is not None else None,
        "receipt_commitment": receipt.get("receipt_commitment") if receipt is not None else None,
        "review_packet_commitment": execution_packet_commitment,
        "file_sha256": files,
        "source_identity_consistency": {
            "record_chain_workflow_source_identity": request_record["workflow_source_identity"],
            "record_chain_executor_source_identity": request_record[
                "canonical_executor_source_identity"
            ],
        },
        "current_source_comparison": {
            "current_workflow_source_matches_execution": (
                current_workflow == request_record["workflow_source_identity"]
            ),
            "current_executor_source_matches_execution": (
                current_executor == request_record["canonical_executor_source_identity"]
            ),
        },
        "trace_validation_summary": trace_summary,
        "store_validation_summary": {
            "store_exists": store_path.exists(),
            "logical_store_validation": "REQUIRED_FOR_COMPLETED_ONLY",
        },
        "receipt_validation_summary": receipt_summary,
        "scientific_payload_equivalence": {
            "authorization_rehearsal_payload_commitment": rehearsal_payload,
            "canonical_execution_payload_commitment": execution_payload,
            "matches": scientific_equivalent,
        },
        "continuing_prohibitions": list(request_record["prohibitions"]),
        "eligible_for_publication_authorization_review": (
            terminal_status is ExecutionReviewTerminalStatus.VALID_COMPLETED
            and scientific_equivalent
        ),
        "not_determined": list(NOT_DETERMINED),
    }
    return CanonicalExecutionReviewReport(
        record={**record, "report_commitment": sha256_text(canonical_json(record))}
    )


def canonical_execution_review_report_from_record(
    record: dict[str, Any],
) -> CanonicalExecutionReviewReport:
    data = _require_object(record, label="canonical execution review report")
    if data.get("schema_id") != EXECUTION_REVIEW_REPORT_SCHEMA_ID:
        raise ValueError("unsupported canonical execution review report schema")
    _commit(data, "report_commitment")
    return CanonicalExecutionReviewReport(record=data)


@dataclass(frozen=True)
class CanonicalExecutionReviewDisposition:
    record: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return dict(self.record)


def make_canonical_execution_review_disposition(
    *,
    report: CanonicalExecutionReviewReport,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> CanonicalExecutionReviewDisposition:
    if disposition not in ALLOWED_EXECUTION_REVIEW_DISPOSITIONS:
        raise ValueError("invalid execution review disposition")
    report_record = report.as_record()
    eligible = bool(report_record["eligible_for_publication_authorization_review"])
    if (
        disposition == ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW
        and not eligible
    ):
        raise ValueError("execution review report is not eligible for acceptance")
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    payload = {
        "schema_id": EXECUTION_REVIEW_DISPOSITION_SCHEMA_ID,
        "review_report_commitment": report.report_commitment,
        "canonical_execution_request_commitment": report_record[
            "canonical_execution_request_commitment"
        ],
        "canonical_execution_authorization_id": report_record[
            "canonical_execution_authorization_id"
        ],
        "terminal_execution_status": report_record["terminal_execution_status"],
        "review_scope": EXECUTION_REVIEW_SCOPE,
        "disposition": disposition,
        "reviewer_identity": reviewer,
        "review_timestamp": timestamp,
        "bounded_reason": reason,
    }
    return CanonicalExecutionReviewDisposition(
        record={**payload, "disposition_id": sha256_text(canonical_json(payload))}
    )


def canonical_execution_review_disposition_from_record(
    record: dict[str, Any],
) -> CanonicalExecutionReviewDisposition:
    data = _require_object(record, label="execution review disposition")
    if data.get("schema_id") != EXECUTION_REVIEW_DISPOSITION_SCHEMA_ID:
        raise ValueError("unsupported execution review disposition schema")
    payload = dict(data)
    declared = payload.pop("disposition_id", None)
    if declared != sha256_text(canonical_json(payload)):
        raise ValueError("execution review disposition ID is stale")
    if data["disposition"] not in ALLOWED_EXECUTION_REVIEW_DISPOSITIONS:
        raise ValueError("invalid execution review disposition")
    validate_source_identity(data["reviewer_identity"])
    parse_timestamp(data["review_timestamp"])
    _reason(data["bounded_reason"])
    return CanonicalExecutionReviewDisposition(record=data)


@dataclass(frozen=True)
class CanonicalExecutionReviewBundleReceipt:
    bundle_commitment: str
    bundle_file_sha256: str
    report_commitment: str
    disposition_id: str

    def as_record(self) -> dict[str, str]:
        return {
            "bundle_commitment": self.bundle_commitment,
            "bundle_file_sha256": self.bundle_file_sha256,
            "report_commitment": self.report_commitment,
            "disposition_id": self.disposition_id,
        }


def make_canonical_execution_review_bundle(
    report: CanonicalExecutionReviewReport,
    disposition: CanonicalExecutionReviewDisposition,
) -> dict[str, Any]:
    report_record = report.as_record()
    disposition_record = disposition.as_record()
    if disposition_record["review_report_commitment"] != report.report_commitment:
        raise ValueError("execution review disposition is for another report")
    payload = {
        "schema_id": EXECUTION_REVIEW_BUNDLE_SCHEMA_ID,
        "execution_review_report": report_record,
        "execution_review_report_commitment": report.report_commitment,
        "execution_review_disposition": disposition_record,
        "execution_review_disposition_commitment": sha256_text(
            canonical_json(disposition_record)
        ),
    }
    return {**payload, "bundle_commitment": sha256_text(canonical_json(payload))}


def write_canonical_execution_review_bundle(
    *,
    report: CanonicalExecutionReviewReport,
    disposition: CanonicalExecutionReviewDisposition,
    destination: Path,
    repo_root: Path,
) -> CanonicalExecutionReviewBundleReceipt:
    reject_canonical_path(destination, repo_root=repo_root, label="execution review bundle")
    reject_canonical_path(destination.parent, repo_root=repo_root, label="execution review parent")
    refuse_overwrite(destination, label="execution review bundle")
    bundle = make_canonical_execution_review_bundle(report, disposition)
    atomic_write_json(destination, bundle)
    return CanonicalExecutionReviewBundleReceipt(
        bundle_commitment=bundle["bundle_commitment"],
        bundle_file_sha256=sha256_file(destination),
        report_commitment=report.report_commitment,
        disposition_id=disposition.as_record()["disposition_id"],
    )

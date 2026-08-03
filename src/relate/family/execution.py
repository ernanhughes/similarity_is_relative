"""One-shot authorized canonical-input family execution to staging.

This capability consumes only executable v2 request and authorization
records. It reads frozen canonical inputs, writes only to the authorized
noncanonical staging directory, and never publishes canonical results.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.authorization import (
    AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
    CanonicalFamilyExecutionAuthorization,
    CanonicalFamilyExecutionRequest,
    canonical_execution_authorization_v2_from_record,
    canonical_execution_request_v2_from_record,
    compute_canonical_executor_source_identity,
    validate_executable_canonical_authorization_v2,
)
from relate.family.review import build_family_review_packet, family_review_packet_commitment
from relate.family.verification import FamilyProtocolExpectedIdentity, FamilyProtocolInputPaths
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    _build_family_workflow_plan_from_validated_inputs,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import FamilyEvidenceBundle, evidence_bundle_commitment
from relate.workflows import WorkflowExecutionError, WorkflowRunner, WorkflowRunStatus
from relate.workflows.trace import WorkflowTraceEvent, WorkflowTraceSink

CANONICAL_EXECUTION_SCOPE: Final = (
    "AUTHORIZED_CANONICAL_INPUT_EXECUTION_TO_NONCANONICAL_STAGING"
)
CANONICAL_RUN_SCHEMA_ID: Final = "relate-family-authorized-canonical-run-v1"
AUTHORIZED_RUNNER_SOURCE_SCHEMA_ID: Final = "relate-family-authorized-runner-source-v1"
CANONICAL_EXECUTION_CLAIM_SCHEMA_ID: Final = "relate-family-canonical-execution-claim-v1"
CANONICAL_EXECUTION_RECEIPT_SCHEMA_ID: Final = (
    "relate-family-authorized-canonical-execution-receipt-v1"
)


class AuthorizedCanonicalExecutionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    WITHHELD = "WITHHELD"


@dataclass(frozen=True)
class AuthorizedCanonicalFamilyExecutionResult:
    status: AuthorizedCanonicalExecutionStatus
    request_commitment: str
    authorization_id: str
    work_dir: Path | None = None
    store_path: Path | None = None
    review_packet_commitment: str | None = None
    receipt_commitment: str | None = None
    receipt_file_sha256: str | None = None
    blocked_step: str | None = None
    failed_step: str | None = None

    def as_summary(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "request_commitment": self.request_commitment,
            "authorization_id": self.authorization_id,
            **({"work_dir": _posix(self.work_dir)} if self.work_dir is not None else {}),
            **({"store_path": _posix(self.store_path)} if self.store_path is not None else {}),
            **(
                {"review_packet_commitment": self.review_packet_commitment}
                if self.review_packet_commitment is not None
                else {}
            ),
            **(
                {"receipt_commitment": self.receipt_commitment}
                if self.receipt_commitment is not None
                else {}
            ),
            **(
                {"receipt_file_sha256": self.receipt_file_sha256}
                if self.receipt_file_sha256 is not None
                else {}
            ),
            **({"blocked_step": self.blocked_step} if self.blocked_step is not None else {}),
            **({"failed_step": self.failed_step} if self.failed_step is not None else {}),
        }


class _ListTraceSink:
    def __init__(self) -> None:
        self.events: list[WorkflowTraceEvent] = []

    def record(self, event: WorkflowTraceEvent) -> None:
        self.events.append(event)


class _TeeTraceSink:
    def __init__(
        self,
        *,
        internal_sink: _ListTraceSink,
        caller_sink: WorkflowTraceSink | None,
    ) -> None:
        self._internal_sink = internal_sink
        self._caller_sink = caller_sink

    def record(self, event: WorkflowTraceEvent) -> None:
        self._internal_sink.record(event)
        if self._caller_sink is not None:
            self._caller_sink.record(event)


def _posix(path: Path) -> str:
    return path.as_posix()


def _repo_path(repo_root: Path, value: str) -> Path:
    return (repo_root / value).resolve(strict=False)


def _relative(repo_root: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()


def _commit(record: dict[str, Any], field: str) -> dict[str, Any]:
    payload = dict(record)
    declared = payload.pop(field, None)
    observed = sha256_text(canonical_json(payload))
    if declared is not None and declared != observed:
        raise ValueError(f"{field} is stale")
    return {**record, field: observed}


def authorized_runner_source_identity(
    *, workflow_source_identity: str, canonical_executor_source_identity: str
) -> str:
    return sha256_text(
        canonical_json(
            {
                "schema_id": AUTHORIZED_RUNNER_SOURCE_SCHEMA_ID,
                "workflow_source_identity": workflow_source_identity,
                "canonical_executor_source_identity": canonical_executor_source_identity,
            }
        )
    )


def authorized_canonical_run_identity(
    *,
    family_protocol_sha256: str,
    workflow_source_identity: str,
    canonical_executor_source_identity: str,
    request_commitment: str,
    authorization_id: str,
    review_packet_commitment: str,
    evidence_bundle_commitment: str,
    requested_run_id: str,
) -> str:
    return sha256_text(
        canonical_json(
            {
                "schema_id": CANONICAL_RUN_SCHEMA_ID,
                "family_protocol_sha256": family_protocol_sha256,
                "workflow_source_identity": workflow_source_identity,
                "canonical_executor_source_identity": canonical_executor_source_identity,
                "request_commitment": request_commitment,
                "authorization_id": authorization_id,
                "review_packet_commitment": review_packet_commitment,
                "evidence_bundle_commitment": evidence_bundle_commitment,
                "requested_run_id": requested_run_id,
            }
        )
    )


def _claim_record(
    *,
    request_record: dict[str, Any],
    request_commitment: str,
    authorization_id: str,
    store_path: str,
) -> dict[str, Any]:
    record = {
        "schema_id": CANONICAL_EXECUTION_CLAIM_SCHEMA_ID,
        "canonical_execution_request_commitment": request_commitment,
        "canonical_execution_authorization_id": authorization_id,
        "requested_run_id": request_record["requested_run_id"],
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "workflow_source_identity": request_record["workflow_source_identity"],
        "canonical_executor_source_identity": request_record[
            "canonical_executor_source_identity"
        ],
        "intended_store_path": store_path,
        "prohibitions": list(request_record["prohibitions"]),
    }
    return _commit(record, "claim_commitment")


def canonical_execution_claim_from_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema_id") != CANONICAL_EXECUTION_CLAIM_SCHEMA_ID:
        raise ValueError("unsupported canonical execution claim schema")
    allowed = {
        "schema_id",
        "canonical_execution_request_commitment",
        "canonical_execution_authorization_id",
        "requested_run_id",
        "family_protocol_sha256",
        "workflow_source_identity",
        "canonical_executor_source_identity",
        "intended_store_path",
        "prohibitions",
        "claim_commitment",
    }
    unexpected = set(record) - allowed
    if unexpected:
        raise ValueError(f"unexpected canonical execution claim fields: {sorted(unexpected)}")
    for item in (
        "CANONICAL_RESULT_PUBLICATION",
        "MATERIALITY_DETERMINATION",
        "REALLOCATION",
        "D2",
        "PROTECTED_ROW_ACCESS",
    ):
        if item not in record.get("prohibitions", ()):
            raise ValueError(f"canonical execution claim missing prohibition: {item}")
    return _commit(dict(record), "claim_commitment")


def _receipt_record(
    *,
    status: AuthorizedCanonicalExecutionStatus,
    repo_root: Path,
    request_record: dict[str, Any],
    request_commitment: str,
    authorization_id: str,
    claim_commitment: str,
    plan: Any,
    result: Any,
    review_packet_commitment_value: str | None,
) -> dict[str, Any]:
    step_records = [
        {
            "step_name": record.step_name,
            "step_version": record.step_version,
            "status": record.status.value,
            "input_commitment": record.input_commitment,
            "output_commitment": record.output_commitment,
            **(
                {"blocked_reason": record.result.blocked_reason}
                if record.result.blocked_reason is not None
                else {}
            ),
        }
        for record in result.records
    ]
    record = {
        "schema_id": CANONICAL_EXECUTION_RECEIPT_SCHEMA_ID,
        "execution_status": status.value,
        "family_protocol_sha256": request_record["family_protocol_sha256"],
        "workflow_name": FAMILY_GRAPH_WORKFLOW_NAME,
        "workflow_version": FAMILY_GRAPH_WORKFLOW_VERSION,
        "requested_run_id": request_record["requested_run_id"],
        "workflow_source_identity": request_record["workflow_source_identity"],
        "canonical_executor_source_identity": request_record[
            "canonical_executor_source_identity"
        ],
        "authorised_runner_source_identity": plan.store_spec.identity.family_runner_source_identity,
        "canonical_execution_request_commitment": request_commitment,
        "canonical_execution_authorization_id": authorization_id,
        "claim_commitment": claim_commitment,
        "canonical_inputs": dict(request_record["canonical_inputs"]),
        "staging_work_directory": _relative(repo_root, plan.context.work_dir),
        "staging_store_path": _relative(repo_root, plan.store_spec.path),
        "store_identity_mapping": plan.store_spec.identity.as_mapping(),
        "workflow_run_identity_commitment": plan.context.identity[
            "family_workflow_run_identity"
        ],
        "ordered_steps": step_records,
        "continuing_prohibitions": list(request_record["prohibitions"]),
        **(
            {"canonical_run_review_packet_commitment": review_packet_commitment_value}
            if review_packet_commitment_value is not None
            else {}
        ),
    }
    return _commit(record, "receipt_commitment")


def canonical_execution_receipt_from_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema_id") != CANONICAL_EXECUTION_RECEIPT_SCHEMA_ID:
        raise ValueError("unsupported canonical execution receipt schema")
    allowed = {
        "schema_id",
        "execution_status",
        "family_protocol_sha256",
        "workflow_name",
        "workflow_version",
        "requested_run_id",
        "workflow_source_identity",
        "canonical_executor_source_identity",
        "authorised_runner_source_identity",
        "canonical_execution_request_commitment",
        "canonical_execution_authorization_id",
        "claim_commitment",
        "canonical_inputs",
        "staging_work_directory",
        "staging_store_path",
        "store_identity_mapping",
        "workflow_run_identity_commitment",
        "ordered_steps",
        "continuing_prohibitions",
        "canonical_run_review_packet_commitment",
        "receipt_commitment",
    }
    unexpected = set(record) - allowed
    if unexpected:
        raise ValueError(f"unexpected canonical execution receipt fields: {sorted(unexpected)}")
    if record.get("execution_status") not in {
        AuthorizedCanonicalExecutionStatus.COMPLETED.value,
        AuthorizedCanonicalExecutionStatus.BLOCKED.value,
    }:
        raise ValueError("unsupported canonical execution receipt status")
    return _commit(dict(record), "receipt_commitment")


def _write_failure_record(
    *,
    work_dir: Path,
    request_commitment: str,
    authorization_id: str,
    failed_step: str | None,
    exc: BaseException,
) -> None:
    atomic_write_json(
        work_dir / "canonical-execution-failure.json",
        {
            "schema_id": "relate-family-canonical-execution-failure-v1",
            "canonical_execution_request_commitment": request_commitment,
            "canonical_execution_authorization_id": authorization_id,
            "failed_step": failed_step,
            "bounded_exception_type": type(exc).__name__,
            "bounded_message": str(exc)[:500],
        },
    )


def _write_trace(work_dir: Path, sink: _ListTraceSink) -> None:
    atomic_write_json(
        work_dir / "canonical-execution-trace.json",
        {
            "schema_id": "relate-family-canonical-execution-trace-v1",
            "events": [
                {
                    "event_type": event.event_type.value,
                    "step_name": event.step_name,
                    "step_version": event.step_version,
                    "timestamp": event.timestamp,
                    "input_commitment": event.input_commitment,
                    "output_commitment": event.output_commitment,
                    "latency_seconds": event.latency_seconds,
                    "blocked_reason": event.blocked_reason,
                    "failure_message": event.failure_message,
                }
                for event in sink.events
            ],
        },
    )


def execute_authorized_canonical_family(
    *,
    repo_root: Path,
    request: CanonicalFamilyExecutionRequest,
    authorization: CanonicalFamilyExecutionAuthorization,
    review_packet: Any,
    evidence_bundle: FamilyEvidenceBundle,
    trace_sink: WorkflowTraceSink | None = None,
) -> AuthorizedCanonicalFamilyExecutionResult:
    root = repo_root.resolve(strict=False)
    request = canonical_execution_request_v2_from_record(request.as_record())
    authorization = canonical_execution_authorization_v2_from_record(authorization.as_record())
    request_record = request.as_record()
    auth_record = authorization.as_record()
    validation = validate_executable_canonical_authorization_v2(
        request=request,
        authorization=authorization,
        repo_root=root,
        review_packet=review_packet,
        evidence_bundle=evidence_bundle,
    )
    if auth_record["disposition"] != AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION:
        return AuthorizedCanonicalFamilyExecutionResult(
            status=AuthorizedCanonicalExecutionStatus.WITHHELD,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
        )

    inputs = request_record["canonical_inputs"]
    staging = request_record["intended_noncanonical_staging"]
    work_dir = _repo_path(root, staging["work_dir"])
    store_path = _repo_path(root, staging["fresh_store_path"])
    work_dir.mkdir(parents=True, exist_ok=False)
    sink = _ListTraceSink()
    runner_sink = _TeeTraceSink(internal_sink=sink, caller_sink=trace_sink)
    try:
        claim = _claim_record(
            request_record=request_record,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            store_path=staging["fresh_store_path"],
        )
        atomic_write_json(work_dir / "canonical-execution-claim.json", claim)

        expected = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=inputs["allocation_manifest_sha256"],
            allocation_context_sha256=inputs["allocation_context_sha256"],
            allocation_repository_commitment_sha256=inputs[
                "allocation_repository_commitment_sha256"
            ],
            d1_result_sha256=inputs["d1_result_sha256"],
            d1_1_classification_sha256=inputs["d1_1_classification_sha256"],
        )
        workflow_source = compute_family_workflow_source_identity(root)
        executor_source = compute_canonical_executor_source_identity(root)
        run_identity = authorized_canonical_run_identity(
            family_protocol_sha256=request_record["family_protocol_sha256"],
            workflow_source_identity=workflow_source,
            canonical_executor_source_identity=executor_source,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            review_packet_commitment=request_record["review_packet_commitment"],
            evidence_bundle_commitment=evidence_bundle_commitment(evidence_bundle),
            requested_run_id=request_record["requested_run_id"],
        )
        runner_source = authorized_runner_source_identity(
            workflow_source_identity=workflow_source,
            canonical_executor_source_identity=executor_source,
        )
        plan = _build_family_workflow_plan_from_validated_inputs(
            run_id=request_record["requested_run_id"],
            workflow_name=FAMILY_GRAPH_WORKFLOW_NAME,
            workflow_version=FAMILY_GRAPH_WORKFLOW_VERSION,
            repo_root=root,
            work_dir=work_dir,
            store_path=store_path,
            allowed_roles=frozenset(request_record["allowed_roles"]),
            family_protocol_sha256=request_record["family_protocol_sha256"],
            expected_identity=expected,
            input_paths=FamilyProtocolInputPaths(
                allocation_manifest=root / inputs["allocation_manifest_path"],
                firewall_publication=root / inputs["firewall_publication_path"],
                d1_result=root / inputs["d1_result_path"],
                d1_1_classification=root / inputs["d1_1_classification_path"],
            ),
            allocation_manifest_path=root / inputs["allocation_manifest_path"],
            workflow_source_identity=workflow_source,
            evidence_bundle=evidence_bundle,
            extra_identity={
                "execution_scope": CANONICAL_EXECUTION_SCOPE,
                "canonical_execution_request_commitment": validation.request_commitment,
                "canonical_execution_authorization_id": validation.authorization_id,
                "canonical_executor_source_identity": executor_source,
                "authorized_canonical_run_identity": run_identity,
            },
            extra_inputs={"execution_scope": CANONICAL_EXECUTION_SCOPE},
            family_runner_source_identity=runner_source,
        )
        result = WorkflowRunner(plan.definition, trace_sink=runner_sink).run(plan.context)
        if result.status is WorkflowRunStatus.BLOCKED:
            receipt = _receipt_record(
                status=AuthorizedCanonicalExecutionStatus.BLOCKED,
                repo_root=root,
                request_record=request_record,
                request_commitment=validation.request_commitment,
                authorization_id=validation.authorization_id,
                claim_commitment=claim["claim_commitment"],
                plan=plan,
                result=result,
                review_packet_commitment_value=None,
            )
            receipt_path = work_dir / "canonical-execution-receipt.json"
            atomic_write_json(receipt_path, receipt)
            _write_trace(work_dir, sink)
            return AuthorizedCanonicalFamilyExecutionResult(
                status=AuthorizedCanonicalExecutionStatus.BLOCKED,
                request_commitment=validation.request_commitment,
                authorization_id=validation.authorization_id,
                work_dir=work_dir,
                store_path=store_path,
                receipt_commitment=receipt["receipt_commitment"],
                receipt_file_sha256=sha256_file(receipt_path),
                blocked_step=result.blocked_step,
            )

        packet = build_family_review_packet(plan=plan, result=result)
        packet_path = work_dir / "canonical-execution-review-packet.json"
        atomic_write_json(packet_path, packet.as_record())
        packet_commitment = family_review_packet_commitment(packet)
        receipt = _receipt_record(
            status=AuthorizedCanonicalExecutionStatus.COMPLETED,
            repo_root=root,
            request_record=request_record,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            claim_commitment=claim["claim_commitment"],
            plan=plan,
            result=result,
            review_packet_commitment_value=packet_commitment,
        )
        receipt_path = work_dir / "canonical-execution-receipt.json"
        atomic_write_json(receipt_path, receipt)
        _write_trace(work_dir, sink)
        return AuthorizedCanonicalFamilyExecutionResult(
            status=AuthorizedCanonicalExecutionStatus.COMPLETED,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            work_dir=work_dir,
            store_path=store_path,
            review_packet_commitment=packet_commitment,
            receipt_commitment=receipt["receipt_commitment"],
            receipt_file_sha256=sha256_file(receipt_path),
        )
    except WorkflowExecutionError as exc:
        _write_failure_record(
            work_dir=work_dir,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            failed_step=exc.failed_step_name,
            exc=exc.__cause__ or exc,
        )
        _write_trace(work_dir, sink)
        raise
    except Exception as exc:
        _write_failure_record(
            work_dir=work_dir,
            request_commitment=validation.request_commitment,
            authorization_id=validation.authorization_id,
            failed_step=None,
            exc=exc,
        )
        _write_trace(work_dir, sink)
        raise

"""The workflow runner: ordering, commitment chaining, tracing, stop
behaviour, and resume-prefix validation.

The runner knows nothing about SQL, family edge types, allocation rules,
canonical artifact paths, or model logic. It receives already-constructed
step objects and an immutable context, and executes them in the declared
order, injecting no dynamic loading, no decorator registration, and no
signature inspection.
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Mapping
from types import MappingProxyType

from relate.workflows.commitments import step_input_commitment, step_output_commitment
from relate.workflows.errors import (
    WorkflowDefinitionError,
    WorkflowExecutionError,
    WorkflowResumeError,
)
from relate.workflows.models import (
    StepExecutionRecord,
    StepResult,
    StepStatus,
    WorkflowCheckpoint,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowRunResult,
    WorkflowRunStatus,
)
from relate.workflows.trace import (
    NullTraceSink,
    WorkflowTraceEvent,
    WorkflowTraceEventType,
    WorkflowTraceSink,
)


class WorkflowRunner:
    """Executes a WorkflowDefinition against a WorkflowContext."""

    def __init__(
        self,
        definition: WorkflowDefinition,
        *,
        trace_sink: WorkflowTraceSink | None = None,
    ) -> None:
        self._definition = definition
        self._trace_sink = trace_sink if trace_sink is not None else NullTraceSink()

    def run(
        self,
        context: WorkflowContext,
        *,
        resume_from: WorkflowCheckpoint | None = None,
    ) -> WorkflowRunResult:
        self._check_context_matches_definition(context)
        if resume_from is not None:
            validated_prefix = self._validate_resume(context, resume_from)
        else:
            validated_prefix = ()

        records: list[StepExecutionRecord] = list(validated_prefix)
        prior_commitments: list[str] = [record.output_commitment for record in records]
        start_index = len(records)

        for step in self._definition.steps[start_index:]:
            input_commitment = step_input_commitment(
                context=context,
                step_name=step.name,
                step_version=step.version,
                prior_commitments=prior_commitments,
            )
            self._trace_sink.record(
                WorkflowTraceEvent(
                    event_type=WorkflowTraceEventType.STEP_STARTED,
                    workflow_name=context.workflow_name,
                    workflow_version=context.workflow_version,
                    run_id=context.run_id,
                    step_name=step.name,
                    step_version=step.version,
                    timestamp=_now(),
                    input_commitment=input_commitment,
                )
            )
            started_at = time.monotonic()
            previous_results: Mapping[str, StepResult] = MappingProxyType(
                {record.step_name: record.result for record in records}
            )
            try:
                result = step.execute(context, previous_results)
            except Exception as exc:  # noqa: BLE001 - intentionally fail-closed on any step exception
                latency = time.monotonic() - started_at
                self._trace_sink.record(
                    WorkflowTraceEvent(
                        event_type=WorkflowTraceEventType.STEP_FAILED,
                        workflow_name=context.workflow_name,
                        workflow_version=context.workflow_version,
                        run_id=context.run_id,
                        step_name=step.name,
                        step_version=step.version,
                        timestamp=_now(),
                        input_commitment=input_commitment,
                        latency_seconds=latency,
                        failure_message=str(exc),
                    )
                )
                raise WorkflowExecutionError(
                    f"step {step.name!r} raised {type(exc).__name__}: {exc}",
                    partial_records=tuple(records),
                    failed_step_name=step.name,
                    cause=exc,
                ) from exc

            if not isinstance(result, StepResult):
                type_error = TypeError(
                    f"step {step.name!r} returned {type(result).__name__}, expected StepResult"
                )
                raise WorkflowExecutionError(
                    str(type_error),
                    partial_records=tuple(records),
                    failed_step_name=step.name,
                    cause=type_error,
                ) from type_error

            latency = time.monotonic() - started_at
            output_commitment = step_output_commitment(
                step_name=step.name,
                step_version=step.version,
                input_commitment=input_commitment,
                status=result.status,
                commitment_payload=result.commitment_payload,
                blocked_reason=result.blocked_reason,
            )
            record = StepExecutionRecord(
                step_name=step.name,
                step_version=step.version,
                status=result.status,
                input_commitment=input_commitment,
                output_commitment=output_commitment,
                result=result,
            )
            records.append(record)
            prior_commitments.append(output_commitment)

            event_type = (
                WorkflowTraceEventType.STEP_COMPLETED
                if result.status is StepStatus.COMPLETED
                else WorkflowTraceEventType.STEP_BLOCKED
            )
            self._trace_sink.record(
                WorkflowTraceEvent(
                    event_type=event_type,
                    workflow_name=context.workflow_name,
                    workflow_version=context.workflow_version,
                    run_id=context.run_id,
                    step_name=step.name,
                    step_version=step.version,
                    timestamp=_now(),
                    input_commitment=input_commitment,
                    output_commitment=output_commitment,
                    latency_seconds=latency,
                    blocked_reason=result.blocked_reason,
                )
            )

            if result.status is StepStatus.BLOCKED:
                return WorkflowRunResult(
                    workflow_name=context.workflow_name,
                    workflow_version=context.workflow_version,
                    run_id=context.run_id,
                    status=WorkflowRunStatus.BLOCKED,
                    records=tuple(records),
                    blocked_step=step.name,
                )

        return WorkflowRunResult(
            workflow_name=context.workflow_name,
            workflow_version=context.workflow_version,
            run_id=context.run_id,
            status=WorkflowRunStatus.COMPLETED,
            records=tuple(records),
            blocked_step=None,
        )

    def _check_context_matches_definition(self, context: WorkflowContext) -> None:
        if context.workflow_name != self._definition.name:
            raise WorkflowDefinitionError(
                "context.workflow_name does not match this runner's workflow definition"
            )
        if context.workflow_version != self._definition.version:
            raise WorkflowDefinitionError(
                "context.workflow_version does not match this runner's workflow definition"
            )

    def _validate_resume(
        self,
        context: WorkflowContext,
        checkpoint: WorkflowCheckpoint,
    ) -> tuple[StepExecutionRecord, ...]:
        if checkpoint.workflow_name != self._definition.name:
            raise WorkflowResumeError("checkpoint workflow name does not match this workflow")
        if checkpoint.workflow_version != self._definition.version:
            raise WorkflowResumeError("checkpoint workflow version does not match this workflow")
        if checkpoint.run_id != context.run_id:
            raise WorkflowResumeError("checkpoint run identity does not match this run context")
        if len(checkpoint.completed_steps) > len(self._definition.steps):
            raise WorkflowResumeError(
                "checkpoint has more completed steps than this workflow declares"
            )

        prior_commitments: list[str] = []
        for index, record in enumerate(checkpoint.completed_steps):
            declared = self._definition.steps[index]
            if record.step_name != declared.name or record.step_version != declared.version:
                raise WorkflowResumeError(
                    f"checkpoint step at position {index} ({record.step_name!r}, "
                    f"{record.step_version!r}) does not match the declared step "
                    f"({declared.name!r}, {declared.version!r})"
                )
            if record.status is not StepStatus.COMPLETED:
                # WorkflowCheckpoint's own constructor already prevents this,
                # but a checkpoint could in principle be handed in with a
                # tampered `status` via direct attribute assignment, so the
                # runner re-checks rather than trusting the object shape alone.
                raise WorkflowResumeError(
                    f"checkpoint step {record.step_name!r} is not COMPLETED and "
                    "cannot be resumed as a completed prefix"
                )

            expected_input = step_input_commitment(
                context=context,
                step_name=declared.name,
                step_version=declared.version,
                prior_commitments=prior_commitments,
            )
            if expected_input != record.input_commitment:
                raise WorkflowResumeError(
                    f"checkpoint step {record.step_name!r} has a tampered or stale input commitment"
                )

            expected_output = step_output_commitment(
                step_name=declared.name,
                step_version=declared.version,
                input_commitment=expected_input,
                status=record.result.status,
                commitment_payload=record.result.commitment_payload,
                blocked_reason=record.result.blocked_reason,
            )
            if expected_output != record.output_commitment:
                raise WorkflowResumeError(
                    f"checkpoint step {record.step_name!r} has a tampered output commitment"
                )

            prior_commitments.append(record.output_commitment)

        return checkpoint.completed_steps


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()

"""Public validation helpers for completed workflow run records."""

from __future__ import annotations

from relate.workflows.commitments import step_input_commitment, step_output_commitment
from relate.workflows.errors import WorkflowResumeError
from relate.workflows.models import (
    StepStatus,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowRunResult,
)


def validate_completed_run(
    definition: WorkflowDefinition,
    context: WorkflowContext,
    result: WorkflowRunResult,
) -> None:
    """Validate that *result* is a complete, untampered run of *definition*.

    This is the public, non-executing equivalent of the runner's resume-prefix
    validation for consumers that need to review a completed run without
    calling any workflow steps.
    """
    if result.status.value != "COMPLETED":
        raise WorkflowResumeError("workflow result is not completed")
    if result.workflow_name != definition.name or context.workflow_name != definition.name:
        raise WorkflowResumeError("workflow name does not match definition")
    if (
        result.workflow_version != definition.version
        or context.workflow_version != definition.version
    ):
        raise WorkflowResumeError("workflow version does not match definition")
    if result.run_id != context.run_id:
        raise WorkflowResumeError("workflow run identity does not match context")
    if len(result.records) != len(definition.steps):
        raise WorkflowResumeError("workflow result does not contain every declared step")

    prior_commitments: list[str] = []
    for index, record in enumerate(result.records):
        step = definition.steps[index]
        if record.step_name != step.name or record.step_version != step.version:
            raise WorkflowResumeError("workflow step order or version does not match definition")
        if (
            record.status is not StepStatus.COMPLETED
            or record.result.status is not StepStatus.COMPLETED
        ):
            raise WorkflowResumeError("workflow result contains a non-completed step")
        expected_input = step_input_commitment(
            context=context,
            step_name=step.name,
            step_version=step.version,
            prior_commitments=prior_commitments,
        )
        if record.input_commitment != expected_input:
            raise WorkflowResumeError(f"step {step.name!r} input commitment is stale")
        expected_output = step_output_commitment(
            step_name=step.name,
            step_version=step.version,
            input_commitment=expected_input,
            status=record.result.status,
            commitment_payload=record.result.commitment_payload,
            blocked_reason=record.result.blocked_reason,
        )
        if record.output_commitment != expected_output:
            raise WorkflowResumeError(f"step {step.name!r} output commitment is stale")
        prior_commitments.append(record.output_commitment)

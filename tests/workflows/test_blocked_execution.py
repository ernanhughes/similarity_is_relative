"""Blocked-execution tests for relate.workflows.

A blocked step means the workflow cannot legitimately continue (missing
review, incomplete metadata, missing authorization), not a software failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.workflows.errors import WorkflowDefinitionError
from relate.workflows.models import (
    StepResult,
    StepStatus,
    WorkflowCheckpoint,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowRunStatus,
)
from relate.workflows.runner import WorkflowRunner


def _context(**overrides: object) -> WorkflowContext:
    base = dict(
        workflow_name="demo",
        workflow_version="1",
        run_id="run-1",
        repo_root=Path("."),
        work_dir=Path("."),
        allowed_roles=frozenset({"visible"}),
        identity={},
        inputs={},
    )
    base.update(overrides)
    return WorkflowContext(**base)


class _CompletedStep:
    def __init__(self, name: str) -> None:
        self.name = name
        self.version = "1"

    def execute(self, context, previous_results):
        return StepResult.completed(
            output={"from": self.name}, commitment_payload={"from": self.name}
        )


class _BlockingStep:
    name = "review_gate"
    version = "1"

    def execute(self, context, previous_results):
        return StepResult.blocked("manual review required")


class _NeverRunStep:
    name = "after_block"
    version = "1"

    def execute(self, context, previous_results):
        raise AssertionError("must not execute after a blocked step")


class TestBlockedResultConstruction:
    def test_bounded_reason_required(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            StepResult.blocked("")


class TestBlockedRunOutcome:
    def test_run_status_is_blocked(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _BlockingStep())
        )
        result = WorkflowRunner(definition).run(_context())
        assert result.status is WorkflowRunStatus.BLOCKED
        assert result.blocked_step == "review_gate"

    def test_blocked_step_record_is_retained(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _BlockingStep())
        )
        result = WorkflowRunner(definition).run(_context())
        assert [record.step_name for record in result.records] == ["a", "review_gate"]
        blocked_record = result.records[-1]
        assert blocked_record.status is StepStatus.BLOCKED
        assert blocked_record.result.blocked_reason == "manual review required"

    def test_later_steps_do_not_execute(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _BlockingStep(), _NeverRunStep())
        )
        result = WorkflowRunner(definition).run(_context())
        assert len(result.records) == 2
        assert result.status is WorkflowRunStatus.BLOCKED

    def test_a_completed_only_run_is_not_reported_as_blocked(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_CompletedStep("a"),))
        result = WorkflowRunner(definition).run(_context())
        assert result.status is WorkflowRunStatus.COMPLETED


class TestBlockedCheckpointBoundary:
    def test_blocked_run_checkpoint_excludes_blocked_step(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _BlockingStep())
        )
        result = WorkflowRunner(definition).run(_context())
        checkpoint = result.completed_checkpoint()
        assert [record.step_name for record in checkpoint.completed_steps] == ["a"]

    def test_blocked_record_cannot_be_constructed_into_a_checkpoint_directly(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _BlockingStep())
        )
        result = WorkflowRunner(definition).run(_context())
        with pytest.raises(WorkflowDefinitionError):
            WorkflowCheckpoint(
                workflow_name="demo",
                workflow_version="1",
                run_id="run-1",
                completed_steps=result.records,  # includes the BLOCKED record
            )

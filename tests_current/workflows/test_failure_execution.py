"""Failure-execution tests for relate.workflows.

Unexpected exceptions raised by a step must stop the workflow immediately,
preserve completed records, expose the original cause, and never be
reported as a completed or blocked run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.workflows.errors import WorkflowExecutionError
from relate.workflows.models import StepResult, StepStatus, WorkflowContext, WorkflowDefinition
from relate.workflows.runner import WorkflowRunner
from relate.workflows.trace import InMemoryTraceSink, WorkflowTraceEventType


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


class _RaisingStep:
    name = "boom"
    version = "1"

    def execute(self, context, previous_results):
        raise ValueError("synthetic failure")


class _NeverRunStep:
    name = "after_failure"
    version = "1"

    def execute(self, context, previous_results):
        raise AssertionError("must not execute after a failed step")


class TestFailurePropagation:
    def test_original_exception_is_retained_as_cause(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_RaisingStep(),))
        with pytest.raises(WorkflowExecutionError) as excinfo:
            WorkflowRunner(definition).run(_context())
        assert isinstance(excinfo.value.cause, ValueError)
        assert isinstance(excinfo.value.__cause__, ValueError)
        assert str(excinfo.value.cause) == "synthetic failure"

    def test_failed_step_name_is_recorded(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _RaisingStep())
        )
        with pytest.raises(WorkflowExecutionError) as excinfo:
            WorkflowRunner(definition).run(_context())
        assert excinfo.value.failed_step_name == "boom"

    def test_completed_prior_records_are_retained(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _RaisingStep())
        )
        with pytest.raises(WorkflowExecutionError) as excinfo:
            WorkflowRunner(definition).run(_context())
        partial = excinfo.value.partial_records
        assert [record.step_name for record in partial] == ["a"]
        assert all(record.status is StepStatus.COMPLETED for record in partial)

    def test_failed_step_produces_no_completed_record(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _RaisingStep())
        )
        with pytest.raises(WorkflowExecutionError) as excinfo:
            WorkflowRunner(definition).run(_context())
        assert "boom" not in [record.step_name for record in excinfo.value.partial_records]

    def test_later_steps_do_not_execute(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CompletedStep("a"), _RaisingStep(), _NeverRunStep())
        )
        with pytest.raises(WorkflowExecutionError):
            WorkflowRunner(definition).run(_context())

    def test_run_is_never_reported_as_completed(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_RaisingStep(),))
        # The only way this run can end is by raising; there is no return path
        # here that could produce a WorkflowRunResult at all.
        with pytest.raises(WorkflowExecutionError):
            result = WorkflowRunner(definition).run(_context())
            pytest.fail(f"expected WorkflowExecutionError, got a result instead: {result}")

    def test_step_returning_wrong_type_raises_execution_error(self) -> None:
        class BadStep:
            name = "bad"
            version = "1"

            def execute(self, context, previous_results):
                return {"not": "a StepResult"}  # type: ignore[return-value]

        definition = WorkflowDefinition(name="demo", version="1", steps=(BadStep(),))
        with pytest.raises(WorkflowExecutionError):
            WorkflowRunner(definition).run(_context())


class TestFailureTrace:
    def test_failure_trace_is_emitted(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_RaisingStep(),))
        with pytest.raises(WorkflowExecutionError):
            WorkflowRunner(definition, trace_sink=sink).run(_context())
        event_types = [event.event_type for event in sink.events]
        assert WorkflowTraceEventType.STEP_STARTED in event_types
        assert WorkflowTraceEventType.STEP_FAILED in event_types
        failed_event = next(
            e for e in sink.events if e.event_type is WorkflowTraceEventType.STEP_FAILED
        )
        assert failed_event.failure_message is not None
        assert "synthetic failure" in failed_event.failure_message

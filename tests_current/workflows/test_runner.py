"""Runner tests for relate.workflows.runner.WorkflowRunner.

Covers ordered execution, single-execution-per-step, visibility of prior
completed results, commitment chaining, and absence of mutable context
leakage between steps.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.workflows.errors import WorkflowDefinitionError
from relate.workflows.models import (
    StepResult,
    StepStatus,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowRunStatus,
)
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


class _RecordingStep:
    def __init__(self, name: str, version: str = "1") -> None:
        self.name = name
        self.version = version
        self.call_count = 0
        self.seen_previous_results: list[dict] = []

    def execute(self, context, previous_results):
        self.call_count += 1
        self.seen_previous_results.append(dict(previous_results))
        return StepResult.completed(
            output={"from": self.name}, commitment_payload={"from": self.name}
        )


class _MutationAttemptStep:
    """Tries to mutate the context and previous_results it receives."""

    name = "mutator"
    version = "1"

    def execute(self, context, previous_results):
        with pytest.raises((TypeError, AttributeError)):
            previous_results["intruder"] = None  # type: ignore[index]
        with pytest.raises((TypeError, AttributeError)):
            context.inputs["intruder"] = None  # type: ignore[index]
        return StepResult.completed(output=None, commitment_payload=None)


class TestOrderedExecution:
    def test_steps_execute_in_declared_order(self) -> None:
        order: list[str] = []

        class OrderTrackingStep:
            def __init__(self, name: str) -> None:
                self.name = name
                self.version = "1"

            def execute(self, context, previous_results):
                order.append(self.name)
                return StepResult.completed(output=None, commitment_payload=None)

        definition = WorkflowDefinition(
            name="demo",
            version="1",
            steps=(OrderTrackingStep("a"), OrderTrackingStep("b"), OrderTrackingStep("c")),
        )
        WorkflowRunner(definition).run(_context())
        assert order == ["a", "b", "c"]

    def test_each_step_executes_exactly_once(self) -> None:
        step_a, step_b = _RecordingStep("a"), _RecordingStep("b")
        definition = WorkflowDefinition(name="demo", version="1", steps=(step_a, step_b))
        WorkflowRunner(definition).run(_context())
        assert step_a.call_count == 1
        assert step_b.call_count == 1

    def test_previous_completed_results_are_visible(self) -> None:
        step_a, step_b = _RecordingStep("a"), _RecordingStep("b")
        definition = WorkflowDefinition(name="demo", version="1", steps=(step_a, step_b))
        WorkflowRunner(definition).run(_context())
        assert step_a.seen_previous_results == [{}]
        assert list(step_b.seen_previous_results[0]) == ["a"]
        assert step_b.seen_previous_results[0]["a"].output == {"from": "a"}

    def test_final_status_completed_only_after_all_steps(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_RecordingStep("a"), _RecordingStep("b"))
        )
        result = WorkflowRunner(definition).run(_context())
        assert result.status is WorkflowRunStatus.COMPLETED
        assert len(result.records) == 2
        assert all(record.status is StepStatus.COMPLETED for record in result.records)


class TestCommitmentChain:
    def test_commitments_form_a_valid_chain(self) -> None:
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_RecordingStep("a"), _RecordingStep("b"))
        )
        result = WorkflowRunner(definition).run(_context())
        record_a, record_b = result.records
        # step b's input commitment must depend on step a's output commitment.
        assert record_a.output_commitment != record_b.input_commitment
        different_definition = WorkflowDefinition(
            name="demo", version="1", steps=(_RecordingStep("a"), _RecordingStep("b"))
        )
        rerun = WorkflowRunner(different_definition).run(_context())
        assert rerun.records[0].output_commitment == record_a.output_commitment
        assert rerun.records[1].input_commitment == record_b.input_commitment


class TestNoMutableContextLeakage:
    def test_step_cannot_mutate_context_or_previous_results(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_MutationAttemptStep(),))
        result = WorkflowRunner(definition).run(_context())
        assert result.status is WorkflowRunStatus.COMPLETED

    def test_context_definition_mismatch_rejected(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_RecordingStep("a"),))
        mismatched_context = _context(workflow_name="other")
        with pytest.raises(WorkflowDefinitionError):
            WorkflowRunner(definition).run(mismatched_context)


class TestTraceOrdering:
    def test_trace_events_appear_in_order(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_RecordingStep("a"), _RecordingStep("b"))
        )
        WorkflowRunner(definition, trace_sink=sink).run(_context())
        event_types = [(event.step_name, event.event_type) for event in sink.events]
        assert event_types == [
            ("a", WorkflowTraceEventType.STEP_STARTED),
            ("a", WorkflowTraceEventType.STEP_COMPLETED),
            ("b", WorkflowTraceEventType.STEP_STARTED),
            ("b", WorkflowTraceEventType.STEP_COMPLETED),
        ]

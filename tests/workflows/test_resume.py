"""Resume tests for relate.workflows.runner.WorkflowRunner.

Covers accepting a valid completed prefix, and rejecting every invalid
variant: changed workflow name/version, changed run identity, reordered or
gapped prefixes, unknown or wrong-version steps, tampered commitments, and
blocked records presented as completed.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relate.workflows.errors import WorkflowDefinitionError, WorkflowResumeError
from relate.workflows.models import (
    StepExecutionRecord,
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
        identity={"protocol": "abc"},
        inputs={},
    )
    base.update(overrides)
    return WorkflowContext(**base)


class _CountingStep:
    def __init__(self, name: str, version: str = "1") -> None:
        self.name = name
        self.version = version
        self.call_count = 0

    def execute(self, context, previous_results):
        self.call_count += 1
        return StepResult.completed(
            output={"from": self.name}, commitment_payload={"from": self.name}
        )


def _run_prefix(context: WorkflowContext, names: list[str]) -> WorkflowCheckpoint:
    steps = [_CountingStep(name) for name in names]
    definition = WorkflowDefinition(name="demo", version="1", steps=tuple(steps))
    result = WorkflowRunner(definition).run(context)
    return result.completed_checkpoint()


class TestValidResume:
    def test_valid_completed_prefix_accepted_and_next_step_executes(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        step_a, step_b = _CountingStep("a"), _CountingStep("b")
        definition = WorkflowDefinition(name="demo", version="1", steps=(step_a, step_b))
        result = WorkflowRunner(definition).run(context, resume_from=checkpoint)
        assert result.status is WorkflowRunStatus.COMPLETED
        assert step_a.call_count == 0  # resumed, not re-executed
        assert step_b.call_count == 1
        assert [r.step_name for r in result.records] == ["a", "b"]

    def test_full_completed_prefix_returns_completed_without_re_execution(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a", "b"])
        step_a, step_b = _CountingStep("a"), _CountingStep("b")
        definition = WorkflowDefinition(name="demo", version="1", steps=(step_a, step_b))
        result = WorkflowRunner(definition).run(context, resume_from=checkpoint)
        assert result.status is WorkflowRunStatus.COMPLETED
        assert step_a.call_count == 0
        assert step_b.call_count == 0
        assert len(result.records) == 2


class TestRejectedResume:
    def test_changed_workflow_name_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        tampered = replace(checkpoint, workflow_name="other")
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=tampered)

    def test_changed_workflow_version_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        tampered = replace(checkpoint, workflow_version="2")
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=tampered)

    def test_changed_run_identity_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        other_context = _context(run_id="run-2")
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(other_context, resume_from=checkpoint)

    def test_changed_step_version_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a", version="2"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=checkpoint)

    def test_reordered_prefix_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a", "b"])
        reordered = replace(checkpoint, completed_steps=tuple(reversed(checkpoint.completed_steps)))
        definition = WorkflowDefinition(
            name="demo",
            version="1",
            steps=(_CountingStep("a"), _CountingStep("b"), _CountingStep("c")),
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=reordered)

    def test_gap_in_prefix_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a", "b", "c"])
        # Keep positions 0 and 2 but drop position 1 — position 1 in the
        # resulting checkpoint now holds the record that used to be at
        # position 2, which does not match the declared step at index 1.
        gapped = replace(
            checkpoint,
            completed_steps=(checkpoint.completed_steps[0], checkpoint.completed_steps[2]),
        )
        definition = WorkflowDefinition(
            name="demo",
            version="1",
            steps=(_CountingStep("a"), _CountingStep("b"), _CountingStep("c")),
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=gapped)

    def test_unknown_step_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("not_a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=checkpoint)

    def test_checkpoint_longer_than_workflow_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a", "b"])
        definition = WorkflowDefinition(name="demo", version="1", steps=(_CountingStep("a"),))
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=checkpoint)

    def test_tampered_output_commitment_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        record = checkpoint.completed_steps[0]
        tampered_record = replace(record, output_commitment="0" * 64)
        tampered = replace(checkpoint, completed_steps=(tampered_record,))
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=tampered)

    def test_tampered_input_commitment_rejected(self) -> None:
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        record = checkpoint.completed_steps[0]
        tampered_record = replace(record, input_commitment="0" * 64)
        tampered = replace(checkpoint, completed_steps=(tampered_record,))
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=tampered)

    def test_tampered_result_payload_rejected(self) -> None:
        # Changing the underlying result's commitment payload without
        # updating output_commitment must be caught by recomputation.
        context = _context()
        checkpoint = _run_prefix(context, ["a"])
        record = checkpoint.completed_steps[0]
        tampered_result = StepResult.completed(
            output={"from": "a"}, commitment_payload={"from": "tampered"}
        )
        tampered_record = replace(record, result=tampered_result)
        tampered = replace(checkpoint, completed_steps=(tampered_record,))
        definition = WorkflowDefinition(
            name="demo", version="1", steps=(_CountingStep("a"), _CountingStep("b"))
        )
        with pytest.raises(WorkflowResumeError):
            WorkflowRunner(definition).run(context, resume_from=tampered)

    def test_blocked_record_rejected_as_completed_prefix(self) -> None:
        blocked_result = StepResult.blocked("manual review required")
        blocked_record = StepExecutionRecord(
            step_name="a",
            step_version="1",
            status=StepStatus.BLOCKED,
            input_commitment="in",
            output_commitment="out",
            result=blocked_result,
        )
        with pytest.raises(WorkflowDefinitionError):
            WorkflowCheckpoint(
                workflow_name="demo",
                workflow_version="1",
                run_id="run-1",
                completed_steps=(blocked_record,),
            )

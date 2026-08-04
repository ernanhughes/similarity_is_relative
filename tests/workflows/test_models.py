"""Model tests for relate.workflows.

Covers immutable context, defensive mapping copies, workflow-definition
validation, JSON-value validation, and StepResult completed/blocked
invariants.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from relate.workflows.errors import WorkflowCommitmentError, WorkflowDefinitionError
from relate.workflows.models import (
    StepResult,
    StepStatus,
    WorkflowContext,
    WorkflowDefinition,
    tuple_to_json_list,
    validate_json_value,
)


def _context(**overrides: object) -> WorkflowContext:
    base = dict(
        workflow_name="demo",
        workflow_version="1",
        run_id="run-1",
        repo_root=Path("."),
        work_dir=Path("."),
        allowed_roles=frozenset({"visible"}),
        identity={"k": "v"},
        inputs={"a": 1},
    )
    base.update(overrides)
    return WorkflowContext(**base)


class _Step:
    def __init__(self, name: str = "step", version: str = "1") -> None:
        self.name = name
        self.version = version

    def execute(self, context, previous_results):  # pragma: no cover - not exercised here
        return StepResult.completed(output=None, commitment_payload=None)


class TestImmutableContext:
    def test_fields_cannot_be_reassigned(self) -> None:
        context = _context()
        with pytest.raises(FrozenInstanceError):
            context.workflow_name = "other"  # type: ignore[misc]

    def test_identity_mapping_is_read_only(self) -> None:
        context = _context()
        with pytest.raises(TypeError):
            context.identity["new"] = "value"  # type: ignore[index]

    def test_inputs_mapping_is_read_only(self) -> None:
        context = _context()
        with pytest.raises(TypeError):
            context.inputs["new"] = "value"  # type: ignore[index]

    def test_mutating_original_dict_after_construction_does_not_leak(self) -> None:
        identity = {"k": "v"}
        context = _context(identity=identity)
        identity["k"] = "tampered"
        identity["extra"] = "leaked"
        assert dict(context.identity) == {"k": "v"}

    def test_allowed_roles_is_frozenset(self) -> None:
        context = _context(allowed_roles={"visible", "protected"})
        assert context.allowed_roles == frozenset({"visible", "protected"})
        assert isinstance(context.allowed_roles, frozenset)


class TestContextValidation:
    def test_empty_workflow_name_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            _context(workflow_name="")

    def test_empty_workflow_version_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            _context(workflow_version="")

    def test_empty_run_id_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            _context(run_id="")

    def test_empty_allowed_roles_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            _context(allowed_roles=frozenset())

    def test_non_string_identity_value_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            _context(identity={"k": 1})

    def test_non_json_input_rejected(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            _context(inputs={"path": Path(".")})


class TestWorkflowDefinition:
    def test_valid_definition(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"), _Step("b")))
        assert [s.name for s in definition.steps] == ["a", "b"]

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(name="", version="1", steps=(_Step(),))

    def test_empty_version_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(name="demo", version="", steps=(_Step(),))

    def test_no_steps_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(name="demo", version="1", steps=())

    def test_duplicate_step_names_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(name="demo", version="1", steps=(_Step("a"), _Step("a")))

    def test_empty_step_name_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(name="demo", version="1", steps=(_Step(""),))

    def test_empty_step_version_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            WorkflowDefinition(name="demo", version="1", steps=(_Step("a", ""),))


class TestJsonValueValidation:
    def test_accepts_nested_valid_value(self) -> None:
        value = {"a": [1, 2.5, "x", True, None, {"b": "c"}]}
        assert validate_json_value(value) == value

    def test_rejects_tuple(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            validate_json_value((1, 2))

    def test_rejects_path(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            validate_json_value(Path("."))

    def test_rejects_nan(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            validate_json_value(math.nan)

    def test_rejects_infinity(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            validate_json_value(math.inf)

    def test_rejects_non_string_key(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            validate_json_value({1: "a"})

    def test_rejects_arbitrary_object(self) -> None:
        class Thing:
            pass

        with pytest.raises(WorkflowCommitmentError):
            validate_json_value(Thing())

    def test_tuple_to_json_list_converts_explicitly(self) -> None:
        assert tuple_to_json_list((1, "a", None)) == [1, "a", None]

    def test_tuple_to_json_list_still_validates_elements(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            tuple_to_json_list((1, Path(".")))


class TestStepResultInvariants:
    def test_completed_result_accepted(self) -> None:
        result = StepResult.completed(output={"x": 1}, commitment_payload={"x": 1})
        assert result.status is StepStatus.COMPLETED
        assert result.blocked_reason is None

    def test_completed_result_with_blocked_reason_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            StepResult(
                status=StepStatus.COMPLETED,
                output=None,
                commitment_payload=None,
                blocked_reason="should not be here",
            )

    def test_blocked_result_accepted(self) -> None:
        result = StepResult.blocked("manual review required")
        assert result.status is StepStatus.BLOCKED
        assert result.blocked_reason == "manual review required"

    def test_blocked_result_requires_nonempty_reason(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            StepResult(
                status=StepStatus.BLOCKED,
                output=None,
                commitment_payload=None,
                blocked_reason="",
            )

    def test_blocked_result_requires_non_whitespace_reason(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            StepResult(
                status=StepStatus.BLOCKED,
                output=None,
                commitment_payload=None,
                blocked_reason="   ",
            )

    def test_blocked_result_reason_is_bounded(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            StepResult(
                status=StepStatus.BLOCKED,
                output=None,
                commitment_payload=None,
                blocked_reason="x" * 501,
            )

    def test_unsupported_status_rejected(self) -> None:
        with pytest.raises(WorkflowDefinitionError):
            StepResult(status="COMPLETE", output=None, commitment_payload=None)  # type: ignore[arg-type]

    def test_result_metadata_is_read_only(self) -> None:
        result = StepResult.completed(output=None, commitment_payload=None, metadata={"k": "v"})
        with pytest.raises(TypeError):
            result.metadata["new"] = "value"  # type: ignore[index]

    def test_result_output_must_be_json_compatible(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            StepResult.completed(output=Path("."), commitment_payload=None)

    def test_result_commitment_payload_must_be_json_compatible(self) -> None:
        with pytest.raises(WorkflowCommitmentError):
            StepResult.completed(output=None, commitment_payload=math.nan)

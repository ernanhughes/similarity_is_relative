"""Commitment tests for relate.workflows.commitments.

Covers determinism, mapping-order independence, prior-step order and
version/identity/payload/blocked-reason sensitivity, timestamp
independence, Unicode behaviour, and rejection of unsupported/non-finite
values.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from relate.workflows.commitments import (
    run_identity_commitment,
    step_input_commitment,
    step_output_commitment,
)
from relate.workflows.errors import WorkflowCommitmentError
from relate.workflows.models import StepStatus, WorkflowContext


def _context(**overrides: object) -> WorkflowContext:
    base = dict(
        workflow_name="demo",
        workflow_version="1",
        run_id="run-1",
        repo_root=Path("."),
        work_dir=Path("."),
        allowed_roles=frozenset({"visible"}),
        identity={"a": "1", "b": "2"},
        inputs={},
    )
    base.update(overrides)
    return WorkflowContext(**base)


class TestRunIdentityCommitment:
    def test_deterministic_across_calls(self) -> None:
        context = _context()
        assert run_identity_commitment(context) == run_identity_commitment(context)

    def test_mapping_order_independence(self) -> None:
        context_a = _context(identity={"a": "1", "b": "2"})
        context_b = _context(identity={"b": "2", "a": "1"})
        assert run_identity_commitment(context_a) == run_identity_commitment(context_b)

    def test_workflow_version_sensitivity(self) -> None:
        context_a = _context(workflow_version="1")
        context_b = _context(workflow_version="2")
        assert run_identity_commitment(context_a) != run_identity_commitment(context_b)

    def test_workflow_name_sensitivity(self) -> None:
        context_a = _context(workflow_name="demo")
        context_b = _context(workflow_name="other")
        assert run_identity_commitment(context_a) != run_identity_commitment(context_b)

    def test_run_id_sensitivity(self) -> None:
        context_a = _context(run_id="run-1")
        context_b = _context(run_id="run-2")
        assert run_identity_commitment(context_a) != run_identity_commitment(context_b)

    def test_identity_value_sensitivity(self) -> None:
        context_a = _context(identity={"a": "1"})
        context_b = _context(identity={"a": "2"})
        assert run_identity_commitment(context_a) != run_identity_commitment(context_b)

    def test_repo_root_and_work_dir_do_not_affect_commitment(self) -> None:
        context_a = _context(repo_root=Path("one"), work_dir=Path("one-work"))
        context_b = _context(repo_root=Path("two"), work_dir=Path("two-work"))
        assert run_identity_commitment(context_a) == run_identity_commitment(context_b)

    def test_allowed_roles_do_not_affect_commitment(self) -> None:
        context_a = _context(allowed_roles={"visible"})
        context_b = _context(allowed_roles={"visible", "protected"})
        assert run_identity_commitment(context_a) == run_identity_commitment(context_b)

    def test_unicode_identity_value_is_stable(self) -> None:
        context = _context(identity={"a": "café ☃"})
        first = run_identity_commitment(context)
        second = run_identity_commitment(_context(identity={"a": "café ☃"}))
        assert first == second


class TestStepInputCommitment:
    def test_deterministic(self) -> None:
        context = _context()
        first = step_input_commitment(
            context=context, step_name="a", step_version="1", prior_commitments=["x", "y"]
        )
        second = step_input_commitment(
            context=context, step_name="a", step_version="1", prior_commitments=["x", "y"]
        )
        assert first == second

    def test_prior_step_order_sensitivity(self) -> None:
        context = _context()
        forward = step_input_commitment(
            context=context, step_name="a", step_version="1", prior_commitments=["x", "y"]
        )
        backward = step_input_commitment(
            context=context, step_name="a", step_version="1", prior_commitments=["y", "x"]
        )
        assert forward != backward

    def test_step_name_sensitivity(self) -> None:
        context = _context()
        one = step_input_commitment(
            context=context, step_name="a", step_version="1", prior_commitments=[]
        )
        two = step_input_commitment(
            context=context, step_name="b", step_version="1", prior_commitments=[]
        )
        assert one != two

    def test_step_version_sensitivity(self) -> None:
        context = _context()
        one = step_input_commitment(
            context=context, step_name="a", step_version="1", prior_commitments=[]
        )
        two = step_input_commitment(
            context=context, step_name="a", step_version="2", prior_commitments=[]
        )
        assert one != two

    def test_workflow_version_sensitivity(self) -> None:
        context_a = _context(workflow_version="1")
        context_b = _context(workflow_version="2")
        one = step_input_commitment(
            context=context_a, step_name="a", step_version="1", prior_commitments=[]
        )
        two = step_input_commitment(
            context=context_b, step_name="a", step_version="1", prior_commitments=[]
        )
        assert one != two

    def test_identity_sensitivity(self) -> None:
        context_a = _context(identity={"a": "1"})
        context_b = _context(identity={"a": "2"})
        one = step_input_commitment(
            context=context_a, step_name="a", step_version="1", prior_commitments=[]
        )
        two = step_input_commitment(
            context=context_b, step_name="a", step_version="1", prior_commitments=[]
        )
        assert one != two


class TestStepOutputCommitment:
    def _base_kwargs(self) -> dict:
        return dict(
            step_name="a",
            step_version="1",
            input_commitment="input-commitment",
            status=StepStatus.COMPLETED,
            commitment_payload={"x": 1},
            blocked_reason=None,
        )

    def test_deterministic(self) -> None:
        kwargs = self._base_kwargs()
        assert step_output_commitment(**kwargs) == step_output_commitment(**kwargs)

    def test_payload_sensitivity(self) -> None:
        base = self._base_kwargs()
        one = step_output_commitment(**{**base, "commitment_payload": {"x": 1}})
        two = step_output_commitment(**{**base, "commitment_payload": {"x": 2}})
        assert one != two

    def test_input_commitment_sensitivity(self) -> None:
        base = self._base_kwargs()
        one = step_output_commitment(**{**base, "input_commitment": "aaa"})
        two = step_output_commitment(**{**base, "input_commitment": "bbb"})
        assert one != two

    def test_status_sensitivity(self) -> None:
        base = self._base_kwargs()
        completed = step_output_commitment(**base)
        blocked = step_output_commitment(
            **{**base, "status": StepStatus.BLOCKED, "blocked_reason": "manual review required"}
        )
        assert completed != blocked

    def test_blocked_reason_sensitivity(self) -> None:
        base = {**self._base_kwargs(), "status": StepStatus.BLOCKED}
        one = step_output_commitment(**{**base, "blocked_reason": "reason one"})
        two = step_output_commitment(**{**base, "blocked_reason": "reason two"})
        assert one != two

    def test_step_name_sensitivity(self) -> None:
        base = self._base_kwargs()
        one = step_output_commitment(**{**base, "step_name": "a"})
        two = step_output_commitment(**{**base, "step_name": "b"})
        assert one != two

    def test_step_version_sensitivity(self) -> None:
        base = self._base_kwargs()
        one = step_output_commitment(**{**base, "step_version": "1"})
        two = step_output_commitment(**{**base, "step_version": "2"})
        assert one != two

    def test_unicode_payload_is_stable(self) -> None:
        base = self._base_kwargs()
        one = step_output_commitment(**{**base, "commitment_payload": {"text": "café ☃"}})
        two = step_output_commitment(**{**base, "commitment_payload": {"text": "café ☃"}})
        assert one == two

    def test_rejects_non_finite_float_in_payload(self) -> None:
        base = self._base_kwargs()
        with pytest.raises(WorkflowCommitmentError):
            step_output_commitment(**{**base, "commitment_payload": {"x": math.inf}})

    def test_rejects_unsupported_value_in_payload(self) -> None:
        base = self._base_kwargs()
        with pytest.raises(WorkflowCommitmentError):
            step_output_commitment(**{**base, "commitment_payload": {"x": Path(".")}})

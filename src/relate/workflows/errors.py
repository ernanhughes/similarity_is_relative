"""Exceptions for the RELATE workflow kernel.

Unexpected failures during workflow execution must raise, not return a
successful-looking result. This module defines the explicit error taxonomy
the kernel uses instead of swallowing exceptions or inventing implicit
statuses.

This module must not import from relate.experiments or relate.family, and
must not import relate.workflows.models (to avoid a circular import — models
raises these errors).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from relate.workflows.models import StepExecutionRecord


class WorkflowError(Exception):
    """Base class for all relate.workflows errors."""


class WorkflowDefinitionError(WorkflowError):
    """A workflow, step, or result object violates its structural contract.

    Raised for things like an empty workflow name, a duplicate step name, a
    completed StepResult carrying a blocked reason, or a WorkflowCheckpoint
    containing a non-completed step record.
    """


class WorkflowCommitmentError(WorkflowError):
    """A value cannot be represented in a deterministic commitment.

    Raised for non-JSON-compatible values (arbitrary objects, Path,
    datetime, dataclasses, tuples passed without explicit conversion) and
    non-finite floats (NaN, Infinity).
    """


class WorkflowExecutionError(WorkflowError):
    """A step raised an unexpected exception during execution.

    Preserves the original cause (via ``raise ... from cause`` and the
    ``cause`` attribute) and the partial run record collected before the
    failure, so completed and blocked step records are never silently lost.
    """

    def __init__(
        self,
        message: str,
        *,
        partial_records: tuple[StepExecutionRecord, ...],
        failed_step_name: str,
        cause: BaseException,
    ) -> None:
        super().__init__(message)
        self.partial_records = partial_records
        self.failed_step_name = failed_step_name
        self.cause = cause


class WorkflowResumeError(WorkflowError):
    """A supplied checkpoint fails resume validation against the current
    workflow definition and run context.

    Raised for mismatched workflow name/version, mismatched run identity,
    reordered or gapped step prefixes, unknown or wrong-version steps,
    non-completed records presented as a completed prefix, and tampered
    input/output commitments.
    """

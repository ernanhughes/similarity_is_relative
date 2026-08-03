"""Core data model for the RELATE workflow kernel.

Defines the JSON-compatible value type, the immutable run context, workflow
and step result shapes, execution records, and the resumable checkpoint
contract. This module contains no scientific logic and no persistence; it is
domain-neutral orchestration vocabulary only.

This module must not import from relate.experiments, relate.family, or
relate.cli.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from relate.workflows.errors import WorkflowCommitmentError, WorkflowDefinitionError

if TYPE_CHECKING:
    from relate.workflows.step import WorkflowStep

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_MAX_BLOCKED_REASON_LENGTH = 500


def validate_json_value(value: object, *, path: str = "$") -> JsonValue:
    """Recursively validate that *value* is JSON-compatible.

    Rejects tuples, non-finite floats, non-string dict keys, and arbitrary
    objects (Path, datetime, dataclasses, NumPy values, ...) rather than
    silently serializing them. Callers must convert such values explicitly
    before passing them in — see ``tuple_to_json_list``.
    """
    if value is None:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WorkflowCommitmentError(f"non-finite float is not commitment-safe at {path}")
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return [validate_json_value(item, path=f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, dict):
        validated: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise WorkflowCommitmentError(f"non-string mapping key at {path}: {key!r}")
            validated[key] = validate_json_value(item, path=f"{path}.{key}")
        return validated
    raise WorkflowCommitmentError(
        f"unsupported value type {type(value).__name__!r} at {path}; convert explicitly first"
    )


def tuple_to_json_list(values: Sequence[JsonValue]) -> list[JsonValue]:
    """Explicitly convert an ordered sequence (e.g. a tuple) into a validated JSON list."""
    return [validate_json_value(item) for item in values]


def generate_run_id() -> str:
    """Return a fresh opaque run identifier.

    This is a label, not a commitment input transform: callers who resume a
    run must supply the *same* run_id explicitly rather than regenerate one.
    """
    return uuid.uuid4().hex


@dataclass(frozen=True)
class WorkflowContext:
    """Immutable, explicit run-level context passed to every step.

    Mappings are defensively copied into read-only views on construction so
    no step can mutate context shared with other steps.
    """

    workflow_name: str
    workflow_version: str
    run_id: str
    repo_root: Path
    work_dir: Path
    allowed_roles: frozenset[str]
    identity: Mapping[str, str]
    inputs: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        if not self.workflow_name or not self.workflow_name.strip():
            raise WorkflowDefinitionError("workflow_name must be a nonempty string")
        if not self.workflow_version or not self.workflow_version.strip():
            raise WorkflowDefinitionError("workflow_version must be a nonempty string")
        if not self.run_id or not self.run_id.strip():
            raise WorkflowDefinitionError("run_id must be a nonempty string")
        roles = frozenset(self.allowed_roles)
        if not roles:
            raise WorkflowDefinitionError("allowed_roles must be a nonempty frozenset")
        for role in roles:
            if not isinstance(role, str) or not role.strip():
                raise WorkflowDefinitionError("allowed_roles values must be nonempty strings")
        identity = dict(self.identity)
        for key, value in identity.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise WorkflowDefinitionError("identity must be a str-to-str mapping")
        inputs = {key: validate_json_value(value) for key, value in self.inputs.items()}
        object.__setattr__(self, "allowed_roles", roles)
        object.__setattr__(self, "identity", MappingProxyType(identity))
        object.__setattr__(self, "inputs", MappingProxyType(inputs))


class StepStatus(StrEnum):
    """Outcome of one executed step. Intentionally minimal — see module docs
    in relate.workflows.step for why SKIPPED/WARNING/RETRY do not exist yet."""

    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class StepResult:
    """The result a step returns from ``execute``.

    ``output`` and ``commitment_payload`` must be JSON-compatible; they are
    validated on construction. A COMPLETED result must not carry a blocked
    reason; a BLOCKED result must carry a bounded, non-empty one.
    """

    status: StepStatus
    output: JsonValue
    commitment_payload: JsonValue
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, StepStatus):
            raise WorkflowDefinitionError(f"unsupported step status: {self.status!r}")
        output = validate_json_value(self.output)
        commitment_payload = validate_json_value(self.commitment_payload)
        metadata = {key: validate_json_value(value) for key, value in self.metadata.items()}
        object.__setattr__(self, "output", output)
        object.__setattr__(self, "commitment_payload", commitment_payload)
        object.__setattr__(self, "metadata", MappingProxyType(metadata))
        if self.status is StepStatus.COMPLETED:
            if self.blocked_reason is not None:
                raise WorkflowDefinitionError(
                    "a completed step result must not carry a blocked reason"
                )
        elif self.status is StepStatus.BLOCKED:
            if not self.blocked_reason or not self.blocked_reason.strip():
                raise WorkflowDefinitionError(
                    "a blocked step result requires a bounded, nonempty reason"
                )
            if len(self.blocked_reason) > _MAX_BLOCKED_REASON_LENGTH:
                raise WorkflowDefinitionError("blocked_reason exceeds the frozen length bound")

    @staticmethod
    def completed(
        output: JsonValue,
        commitment_payload: JsonValue,
        *,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> StepResult:
        return StepResult(
            status=StepStatus.COMPLETED,
            output=output,
            commitment_payload=commitment_payload,
            metadata=dict(metadata) if metadata is not None else {},
            blocked_reason=None,
        )

    @staticmethod
    def blocked(
        reason: str,
        *,
        output: JsonValue = None,
        commitment_payload: JsonValue = None,
        metadata: Mapping[str, JsonValue] | None = None,
    ) -> StepResult:
        return StepResult(
            status=StepStatus.BLOCKED,
            output=output,
            commitment_payload=commitment_payload,
            metadata=dict(metadata) if metadata is not None else {},
            blocked_reason=reason,
        )


@dataclass(frozen=True)
class StepExecutionRecord:
    """One step's execution outcome plus its commitment chain position."""

    step_name: str
    step_version: str
    status: StepStatus
    input_commitment: str
    output_commitment: str
    result: StepResult


class WorkflowRunStatus(StrEnum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class WorkflowRunResult:
    """The outcome of one ``WorkflowRunner.run`` call.

    Only COMPLETED and BLOCKED are ever returned directly; FAILED is used by
    ``WorkflowExecutionError`` to describe a partial run when a step raises.
    """

    workflow_name: str
    workflow_version: str
    run_id: str
    status: WorkflowRunStatus
    records: tuple[StepExecutionRecord, ...]
    blocked_step: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))

    def completed_checkpoint(self) -> WorkflowCheckpoint:
        """Return a checkpoint of this run's completed prefix.

        Safe to call on a BLOCKED run: the blocked step itself is never
        COMPLETED, so it is naturally excluded from the resulting checkpoint.
        """
        completed = tuple(
            record for record in self.records if record.status is StepStatus.COMPLETED
        )
        return WorkflowCheckpoint(
            workflow_name=self.workflow_name,
            workflow_version=self.workflow_version,
            run_id=self.run_id,
            completed_steps=completed,
        )


@dataclass(frozen=True)
class WorkflowCheckpoint:
    """A validated-shape snapshot of a completed step prefix for resume.

    Only COMPLETED records may appear here; this is enforced at
    construction, independent of any specific workflow or run context. The
    runner separately validates a checkpoint against a specific
    WorkflowDefinition and WorkflowContext when resuming (see
    relate.workflows.runner).
    """

    workflow_name: str
    workflow_version: str
    run_id: str
    completed_steps: tuple[StepExecutionRecord, ...]

    def __post_init__(self) -> None:
        steps = tuple(self.completed_steps)
        for record in steps:
            if record.status is not StepStatus.COMPLETED:
                raise WorkflowDefinitionError(
                    f"workflow checkpoint may only contain COMPLETED step records; "
                    f"{record.step_name!r} is {record.status.value}"
                )
        object.__setattr__(self, "completed_steps", steps)


@dataclass(frozen=True)
class WorkflowDefinition:
    """An explicit, ordered tuple of already-constructed step objects.

    Workflows are never loaded from YAML/JSON/TOML, entry points, dotted
    class paths, or environment variables, and steps are never dynamically
    imported. A caller constructs a WorkflowDefinition directly in Python.
    """

    name: str
    version: str
    steps: tuple[WorkflowStep, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise WorkflowDefinitionError("workflow name must be a nonempty string")
        if not self.version or not self.version.strip():
            raise WorkflowDefinitionError("workflow version must be a nonempty string")
        steps = tuple(self.steps)
        if not steps:
            raise WorkflowDefinitionError("a workflow must declare at least one step")
        seen: set[str] = set()
        for step in steps:
            step_name = getattr(step, "name", None)
            step_version = getattr(step, "version", None)
            if not isinstance(step_name, str) or not step_name.strip():
                raise WorkflowDefinitionError("every step must have a nonempty string name")
            if not isinstance(step_version, str) or not step_version.strip():
                raise WorkflowDefinitionError("every step must have a nonempty string version")
            if step_name in seen:
                raise WorkflowDefinitionError(f"duplicate step name: {step_name!r}")
            seen.add(step_name)
        object.__setattr__(self, "steps", steps)

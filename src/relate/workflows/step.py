"""The minimal step interface the workflow runner executes.

A step owns exactly one operation: given the immutable run context and the
results of previously completed steps, produce one StepResult. The runner
owns ordering, commitment chaining, trace recording, stop behaviour, and
resume-prefix validation — a step must not know about any of that.

Only two step outcomes exist today: COMPLETED and BLOCKED (see StepStatus in
relate.workflows.models). SKIPPED, WARNING, PARTIAL_SUCCESS, and RETRY are
deliberately not modelled in this stage; adding them is a future decision,
not an oversight.

Steps are constructed explicitly by the caller and passed into a
WorkflowDefinition. There is no decorator-based registration, no scanning of
function signatures, and no parameter-name-based injection.

This module must not import from relate.experiments, relate.family, or
relate.cli.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from relate.workflows.models import StepResult, WorkflowContext


@runtime_checkable
class WorkflowStep(Protocol):
    """Protocol for one workflow step.

    ``name`` and ``version`` are plain attributes (not methods) so a step's
    identity is visible without calling it. ``execute`` receives the full
    immutable context and a read-only view of every previously completed
    step's result, keyed by step name.
    """

    name: str
    version: str

    def execute(
        self,
        context: WorkflowContext,
        previous_results: Mapping[str, StepResult],
    ) -> StepResult: ...

"""Operational trace events for the workflow kernel, separate from commitments.

Trace records carry timestamps and latency for observability. They must
never influence deterministic commitments (see relate.workflows.commitments),
and by default they carry only bounded metadata and commitment hashes, not
entire step output payloads, to avoid accidental leakage of protected data
into logs.

The trace sink is injected, not hard-coded: this module provides an
in-memory sink for tests and a no-op sink for callers who do not need
tracing. No SQLite tables, logging-service integrations, telemetry
exporters, or network publication are introduced here.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class WorkflowTraceEventType(StrEnum):
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_BLOCKED = "STEP_BLOCKED"
    STEP_FAILED = "STEP_FAILED"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


@dataclass(frozen=True)
class WorkflowTraceEvent:
    """One operational trace record.

    ``timestamp`` and ``latency_seconds`` are informational only and must
    never be read back into a commitment computation.
    """

    event_type: WorkflowTraceEventType
    workflow_name: str
    workflow_version: str
    run_id: str
    step_name: str
    step_version: str
    timestamp: str
    input_commitment: str | None = None
    output_commitment: str | None = None
    latency_seconds: float | None = None
    blocked_reason: str | None = None
    failure_message: str | None = None


class WorkflowTraceSink(Protocol):
    def record(self, event: WorkflowTraceEvent) -> None: ...


class InMemoryTraceSink:
    """Test-oriented trace sink that retains events in arrival order."""

    def __init__(self) -> None:
        self._events: list[WorkflowTraceEvent] = []

    def record(self, event: WorkflowTraceEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[WorkflowTraceEvent, ...]:
        """Defensive copy: mutating the returned tuple never affects the sink."""
        return tuple(self._events)


class NullTraceSink:
    """A sink that discards every event. Useful when tracing is not needed."""

    def record(self, event: WorkflowTraceEvent) -> None:
        return None

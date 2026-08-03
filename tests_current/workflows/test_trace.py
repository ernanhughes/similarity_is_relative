"""Trace tests for relate.workflows.trace.

Covers timestamp/latency independence from commitments, start/finish event
delivery, commitment presence in trace records, absence of arbitrary output
payloads in traces by default, and defensive copies from the in-memory sink.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.workflows.models import StepResult, WorkflowContext, WorkflowDefinition
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


class _Step:
    def __init__(self, name: str) -> None:
        self.name = name
        self.version = "1"

    def execute(self, context, previous_results):
        return StepResult.completed(
            output={"secret_rows": "should not leak"}, commitment_payload={"from": self.name}
        )


class TestTimestampIndependence:
    def test_two_runs_produce_identical_commitments_despite_different_wall_clock_time(self) -> None:
        context = _context()
        definition_one = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        definition_two = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        result_one = WorkflowRunner(definition_one).run(context)
        result_two = WorkflowRunner(definition_two).run(context)
        assert result_one.records[0].input_commitment == result_two.records[0].input_commitment
        assert result_one.records[0].output_commitment == result_two.records[0].output_commitment


class TestTraceDelivery:
    def test_sink_receives_start_and_completed_events(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        WorkflowRunner(definition, trace_sink=sink).run(_context())
        types = [event.event_type for event in sink.events]
        assert types == [WorkflowTraceEventType.STEP_STARTED, WorkflowTraceEventType.STEP_COMPLETED]

    def test_trace_records_contain_commitments(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        result = WorkflowRunner(definition, trace_sink=sink).run(_context())
        record = result.records[0]
        started, completed = sink.events
        assert started.input_commitment == record.input_commitment
        assert completed.input_commitment == record.input_commitment
        assert completed.output_commitment == record.output_commitment

    def test_traces_omit_full_output_payload_by_default(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        WorkflowRunner(definition, trace_sink=sink).run(_context())
        for event in sink.events:
            assert not hasattr(event, "output")
            fields = ("input_commitment", "output_commitment", "blocked_reason", "failure_message")
            for field_name in fields:
                value = getattr(event, field_name)
                if value is not None:
                    assert "secret_rows" not in str(value)

    def test_trace_events_carry_latency_and_timestamp_but_not_in_commitments(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        WorkflowRunner(definition, trace_sink=sink).run(_context())
        _, completed = sink.events
        assert completed.timestamp
        assert completed.latency_seconds is not None
        assert completed.latency_seconds >= 0


class TestInMemoryTraceSinkDefensiveCopies:
    def test_events_property_returns_a_copy(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        WorkflowRunner(definition, trace_sink=sink).run(_context())
        first = sink.events
        mutable_attempt = list(first)
        mutable_attempt.clear()
        assert len(sink.events) == 2  # internal state unaffected

    def test_events_are_frozen_dataclasses(self) -> None:
        sink = InMemoryTraceSink()
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        WorkflowRunner(definition, trace_sink=sink).run(_context())
        event = sink.events[0]
        with pytest.raises(Exception):  # noqa: B017 - dataclasses.FrozenInstanceError
            event.step_name = "tampered"  # type: ignore[misc]


class TestNullTraceSink:
    def test_run_succeeds_without_a_trace_sink(self) -> None:
        definition = WorkflowDefinition(name="demo", version="1", steps=(_Step("a"),))
        result = WorkflowRunner(definition).run(_context())
        assert len(result.records) == 1

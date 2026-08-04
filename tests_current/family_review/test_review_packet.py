from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from relate.family.review import (
    FAMILY_REVIEW_PACKET_SCHEMA_ID,
    build_family_review_packet,
    family_review_packet_commitment,
)
from relate.workflows import WorkflowRunStatus


def test_completed_workflow_builds_deterministic_packet(completed_family_workflow) -> None:
    plan, result = completed_family_workflow
    packet = build_family_review_packet(plan=plan, result=result)
    again = build_family_review_packet(plan=plan, result=result)
    assert packet.as_record() == again.as_record()
    assert family_review_packet_commitment(packet) == family_review_packet_commitment(again)
    assert packet.as_record()["schema_id"] == FAMILY_REVIEW_PACKET_SCHEMA_ID


def test_packet_contains_only_bounded_facts_and_non_conclusions(
    completed_family_workflow,
) -> None:
    plan, result = completed_family_workflow
    record = build_family_review_packet(plan=plan, result=result).as_record()
    assert record["publication_scope"] == "BOUNDED_FAMILY_RESULT_ONLY"
    assert record["packet_contains"] == "BOUNDED_FAMILY_GRAPH_FACTS_ONLY"
    assert "MATERIAL_CONTAMINATION" in record["not_concluded"]
    assert record["downstream_decisions"]["reallocation_required"] == "NOT_AUTHORIZED"
    assert record["downstream_decisions"]["d2_authorization"] == "NOT_AUTHORIZED"


def test_blocked_result_rejected(completed_family_workflow) -> None:
    plan, result = completed_family_workflow
    blocked = replace(result, status=WorkflowRunStatus.BLOCKED, blocked_step="x")
    with pytest.raises(Exception, match="not completed"):
        build_family_review_packet(plan=plan, result=blocked)


def test_wrong_workflow_name_rejected(completed_family_workflow) -> None:
    plan, result = completed_family_workflow
    bad_definition = replace(plan.definition, name="wrong")
    bad_context = replace(plan.context, workflow_name="wrong")
    bad_plan = replace(plan, definition=bad_definition, context=bad_context)
    with pytest.raises(ValueError, match="workflow name"):
        build_family_review_packet(plan=bad_plan, result=result)


def test_tampered_workflow_commitment_rejected(completed_family_workflow) -> None:
    plan, result = completed_family_workflow
    first = result.records[0]
    tampered_record = replace(first, output_commitment="0" * 64)
    tampered = replace(result, records=(tampered_record, *result.records[1:]))
    with pytest.raises(Exception, match="output commitment|stale"):
        build_family_review_packet(plan=plan, result=tampered)


def test_tampered_durable_phase_rejected(completed_family_workflow) -> None:
    plan, result = completed_family_workflow
    with sqlite3.connect(plan.store_spec.path) as connection:
        connection.execute(
            "UPDATE phase_commitments SET commitment_sha256 = ? WHERE phase = ?",
            ("0" * 64, "family_components"),
        )
        connection.commit()
    with pytest.raises(ValueError, match="component phase"):
        build_family_review_packet(plan=plan, result=result)

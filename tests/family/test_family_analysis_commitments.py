"""Versioned scientific commitment tests for family analysis outputs."""

from __future__ import annotations

from relate.family.analysis import (
    RoleCrossingAnalysis,
    bounded_family_outcome_commitment,
    role_crossing_analysis_commitment,
)

PROTOCOL_SHA = "a" * 64


def _analysis() -> RoleCrossingAnalysis:
    return RoleCrossingAnalysis(
        cross_role_connecting_components=0,
        crossing_component_ids=(),
        crossing_components=(),
        role_pair_impacts=(),
        largest_crossing_component_repository_count=0,
        hard_or_exact_fit_iteration_crossing_observed=False,
    )


def test_role_crossing_commitment_is_deterministic_and_protocol_bound() -> None:
    analysis = _analysis()
    assert role_crossing_analysis_commitment(
        analysis, protocol_sha256=PROTOCOL_SHA
    ) == role_crossing_analysis_commitment(analysis, protocol_sha256=PROTOCOL_SHA)
    assert role_crossing_analysis_commitment(
        analysis, protocol_sha256=PROTOCOL_SHA
    ) != role_crossing_analysis_commitment(analysis, protocol_sha256="b" * 64)


def test_role_crossing_commitment_is_record_sensitive() -> None:
    assert role_crossing_analysis_commitment(
        _analysis(), protocol_sha256=PROTOCOL_SHA
    ) != role_crossing_analysis_commitment(
        RoleCrossingAnalysis(
            cross_role_connecting_components=1,
            crossing_component_ids=("x",),
            crossing_components=(),
            role_pair_impacts=(),
            largest_crossing_component_repository_count=1,
            hard_or_exact_fit_iteration_crossing_observed=True,
        ),
        protocol_sha256=PROTOCOL_SHA,
    )


def test_outcome_commitment_is_deterministic_and_protocol_bound() -> None:
    outcome = {"family_graph_outcome": "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"}
    assert bounded_family_outcome_commitment(
        outcome, protocol_sha256=PROTOCOL_SHA
    ) == bounded_family_outcome_commitment(outcome, protocol_sha256=PROTOCOL_SHA)
    assert bounded_family_outcome_commitment(
        outcome, protocol_sha256=PROTOCOL_SHA
    ) != bounded_family_outcome_commitment(outcome, protocol_sha256="b" * 64)

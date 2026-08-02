from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from relate.experiments.option_c0_data_firewall import register_candidate
from relate.experiments.option_c0_discovery_runner import (
    CANDIDATE_FAMILIES,
    CandidateRegistryMismatch,
    DiscoveryPlan,
    empirical_residual_mass_decision,
    fit_primitive_models,
    fit_query_transform,
    predict_primitives,
    split_fit_repositories,
    to_signed_margins,
    verify_registered_candidates,
)
from relate.experiments.option_c0_selective_baselines import QueryForm


def _query_forms() -> list[dict[str, object]]:
    primitives = [
        "cyclomatic_complexity",
        "max_control_depth",
        "distinct_call_sites",
    ]
    return [
        {
            "query_id": "all_primitives_above_fit_median",
            "operator": "all",
            "primitive_names": primitives,
            "k": None,
        },
        {
            "query_id": "any_primitive_above_fit_median",
            "operator": "any",
            "primitive_names": primitives,
            "k": None,
        },
        {
            "query_id": "two_of_three_primitives_above_fit_median",
            "operator": "k_of_n",
            "primitive_names": primitives,
            "k": 2,
        },
    ]


def _plan_mapping() -> dict[str, object]:
    candidates = []
    for family in CANDIDATE_FAMILIES:
        for query in _query_forms():
            query_id = str(query["query_id"])
            candidates.append(
                {
                    "candidate_id": f"{family}__{query_id}",
                    "version": "v1",
                    "family": family,
                    "query_id": query_id,
                    "support_object_definition": "fixture support object",
                    "propagation_rule": "fixture propagation rule",
                    "nonconformity_score": "fixture score",
                    "expected_failure_mode": "fixture failure",
                    "implementation_commit_sha": "a" * 40,
                }
            )
    return {
        "schema_id": "option-c0-initial-candidate-plan-v1",
        "status": "C0_INITIAL_CANDIDATE_PLAN_FROZEN",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_accessed": False,
        "c1_rows_selected": False,
        "primitives": [
            "cyclomatic_complexity",
            "max_control_depth",
            "distinct_call_sites",
        ],
        "query_forms": _query_forms(),
        "candidates": candidates,
        "alpha_grid": [0.01, 0.025, 0.05, 0.1, 0.2],
        "residual_mass_beta_grid": [0.01, 0.025, 0.05, 0.1, 0.2],
        "coverage_anchors": [0.25, 0.5, 0.75, 0.9, 1.0],
        "fit_calibration_fraction": 0.2,
        "ridge_alphas": [0.01, 0.1, 1.0, 10.0, 100.0],
        "ridge_folds": 5,
        "embedding_batch_size": 10,
    }


def _registry_payload(candidate, query):
    return {
        "candidate_id": candidate.candidate_id,
        "version": candidate.version,
        "commit_sha": candidate.implementation_commit_sha,
        "support_object_definition": candidate.support_object_definition,
        "propagation_rule": candidate.propagation_rule,
        "query_form": json.dumps(query.to_dict(), sort_keys=True),
        "confidence_score": candidate.nonconformity_score,
        "data_roles": ["C0_FIT", "C0_ITERATION"],
        "hyperparameters": {
            "fit_data_role": "C0_FIT",
            "calibration_data_role": "C0_FIT",
            "evaluation_data_role": "C0_ITERATION",
        },
        "expected_failure_mode": candidate.expected_failure_mode,
        "status": "active",
        "timestamp": "2026-08-02T15:30:00Z",
        "predecessor_version": None,
        "artifact_hashes": {"candidate_plan": "b" * 64},
    }


def test_plan_requires_two_families_across_all_three_queries():
    plan = DiscoveryPlan.from_mapping(_plan_mapping())
    assert len(plan.query_forms) == 3
    assert len(plan.candidates) == 6
    assert {item.family for item in plan.candidates} == set(CANDIDATE_FAMILIES)

    invalid = _plan_mapping()
    invalid["candidates"] = list(invalid["candidates"])[:-1]
    with pytest.raises(ValueError):
        DiscoveryPlan.from_mapping(invalid)


def test_fit_repository_partition_is_deterministic_and_disjoint():
    repositories = [f"repo-{index:03d}" for index in range(20)]
    first = split_fit_repositories(
        repositories,
        allocation_context_sha256="1" * 64,
        calibration_fraction=0.2,
    )
    second = split_fit_repositories(
        reversed(repositories),
        allocation_context_sha256="1" * 64,
        calibration_fraction=0.2,
    )
    assert first == second
    model_fit, calibration, commitment = first
    assert len(model_fit) == 16
    assert len(calibration) == 4
    assert model_fit.isdisjoint(calibration)
    assert len(commitment) == 64


def test_empirical_residual_mass_preserves_joint_residual_vectors():
    query = QueryForm(
        "two_of_three_primitives_above_fit_median",
        "k_of_n",
        (
            "cyclomatic_complexity",
            "max_control_depth",
            "distinct_call_sites",
        ),
        k=2,
    )
    prediction = np.asarray(
        [
            [1.0, 1.0, -0.2],
            [0.1, -0.1, 0.1],
        ],
        dtype=np.float64,
    )
    residuals = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [0.2, -0.2, 0.2],
            [-0.2, 0.2, -0.2],
            [0.1, 0.1, 0.1],
        ],
        dtype=np.float64,
    )
    decision = empirical_residual_mass_decision(
        prediction,
        residuals,
        query,
        beta=0.25,
        chunk_size=2,
    )
    assert decision.predictions.tolist() == [True, True]
    assert decision.accepted.tolist() == [True, False]


def test_query_transform_uses_fit_medians_and_iqr_floor():
    primitives = np.asarray(
        [
            [1.0, 0.0, 1.0],
            [2.0, 1.0, 2.0],
            [3.0, 2.0, 3.0],
            [4.0, 3.0, 4.0],
        ]
    )
    transform = fit_query_transform(primitives)
    np.testing.assert_allclose(transform.thresholds, [2.5, 1.5, 2.5])
    assert np.all(transform.scales >= 1.0)
    margins = to_signed_margins(primitives, transform)
    assert margins.shape == primitives.shape
    assert np.all(margins[:2] < margins[2:])


def test_grouped_ridge_models_are_deterministic():
    random = np.random.default_rng(8112026)
    embeddings = random.normal(size=(60, 8))
    repositories = tuple(f"repo-{index // 3:03d}" for index in range(60))
    weights = random.normal(size=(8, 3))
    primitives = embeddings @ weights + random.normal(scale=0.01, size=(60, 3))
    first = fit_primitive_models(
        embeddings,
        primitives,
        repositories,
        alphas=(0.01, 0.1, 1.0, 10.0, 100.0),
        folds=5,
    )
    second = fit_primitive_models(
        embeddings,
        primitives,
        repositories,
        alphas=(0.01, 0.1, 1.0, 10.0, 100.0),
        folds=5,
    )
    assert first.selected_alphas == second.selected_alphas
    np.testing.assert_allclose(
        predict_primitives(first, embeddings),
        predict_primitives(second, embeddings),
    )


def test_registry_must_exactly_match_candidate_plan(tmp_path: Path):
    plan = DiscoveryPlan.from_mapping(_plan_mapping())
    registry = tmp_path / "registry.jsonl"
    queries = {item.query_id: item for item in plan.query_forms}
    for candidate in plan.candidates:
        register_candidate(
            registry,
            _registry_payload(candidate, queries[candidate.query_id]),
        )
    events = verify_registered_candidates(plan, registry)
    assert len(events) == 6

    extra = _registry_payload(plan.candidates[0], queries[plan.candidates[0].query_id])
    extra["candidate_id"] = "unexpected"
    register_candidate(registry, extra)
    with pytest.raises(CandidateRegistryMismatch):
        verify_registered_candidates(plan, registry)

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from relate.experiments.option_c0_diagnostics import (
    primitive_interval_coverage,
    ranked_risk_coverage_curve,
    selective_diagnostics,
    stratified_selective_diagnostics,
)
from relate.experiments.option_c0_mechanism_harness import (
    CandidatePlan,
    CandidatePlanError,
    DevelopmentBatch,
    HarnessContract,
    HiddenRoleAccessError,
    load_visible_repository_assignments,
    require_c0_selection_unavailable,
    require_c1_evidence_unavailable,
    require_candidate_registered,
    validate_candidate_collection,
    validate_harness_setup,
)
from relate.experiments.option_c0_selective_baselines import (
    QueryForm,
    SelectiveDecision,
    direct_compound_conformal_decision,
    finite_sample_quantile,
    fit_direct_compound_conformal,
    fit_independent_primitive_calibration,
    fit_joint_max_residual_calibration,
    independent_primitive_conformal_decision,
    interval_query_decision,
    joint_box_support_decision,
    oracle_support_decision,
    query_truth,
    uncalibrated_confidence_decision,
)


def _contract() -> dict[str, object]:
    return {
        "schema_id": "option-c0-development-harness-contract-v1",
        "status": "C0_MECHANISM_HARNESS_CONTRACT_FROZEN",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "visible_roles": ["c0_fit", "c0_iteration"],
        "blocked_roles": ["c0_selection", "c1_reserve"],
        "query_operators": ["all", "any", "k_of_n"],
        "max_query_forms": 3,
        "required_baselines": [
            "independent_primitive_split_conformal",
            "direct_compound_split_conformal",
            "uncalibrated_confidence",
            "oracle_support_diagnostic",
        ],
        "development_alpha_grid": [0.01, 0.025, 0.05, 0.1, 0.2],
        "coverage_anchors": [0.25, 0.5, 0.75, 0.9, 1.0],
        "candidate_registration_required_before_iteration": True,
        "c0_selection_access": False,
        "c1_access": False,
    }


def _query(operator: str = "all", *, query_id: str = "q1", k: int | None = None):
    return QueryForm(query_id, operator, ("a", "b", "c"), k=k)


def _canonical_firewall(root: Path) -> Path:
    root.mkdir(parents=True)
    assignments = [
        {"role": "c0_fit", "repository": "fit-a", "row_count": 4},
        {"role": "c0_iteration", "repository": "iter-a", "row_count": 3},
        {"role": "c0_selection", "repository": "selection-a", "row_count": 2},
        {"role": "c1_reserve", "repository": "reserve-a", "row_count": 2},
    ]
    allocation = root / "option-c0-repository-allocation-v1.jsonl"
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in assignments
    )
    allocation.write_text(payload, encoding="utf-8", newline="\n")
    publication = {
        "status": "C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED_PENDING_REVIEW",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "counts": {"allocated_repositories": 4},
        "role_counts": {
            "c0_fit": {"repositories": 1},
            "c0_iteration": {"repositories": 1},
            "c0_selection": {"repositories": 1},
            "c1_reserve": {"repositories": 1},
        },
        "artifacts": {
            "option-c0-repository-allocation-v1.jsonl": {
                "path": str(allocation).replace("\\", "/"),
                "file_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            }
        },
    }
    (root / "option-c0-data-firewall-publication-v1.json").write_text(
        json.dumps(publication), encoding="utf-8"
    )
    return root


def test_contract_and_visible_role_guards(tmp_path: Path):
    contract = HarnessContract.from_mapping(_contract())
    assert contract.max_query_forms == 3
    canonical = _canonical_firewall(tmp_path / "firewall")
    rows = load_visible_repository_assignments(canonical)
    assert [row["repository"] for row in rows] == ["fit-a", "iter-a"]
    with pytest.raises(HiddenRoleAccessError):
        load_visible_repository_assignments(canonical, requested_roles=("c0_selection",))
    with pytest.raises(HiddenRoleAccessError):
        require_c0_selection_unavailable()
    with pytest.raises(HiddenRoleAccessError):
        require_c1_evidence_unavailable()


def test_three_query_operators_and_interval_logic():
    margins = np.asarray(((1, 1, -1), (1, 1, 1), (-1, -1, 1)), dtype=float)
    assert query_truth(margins, _query("all")).tolist() == [False, True, False]
    assert query_truth(margins, _query("any")).tolist() == [True, True, True]
    assert query_truth(margins, _query("k_of_n", k=2)).tolist() == [True, True, False]
    lower = np.asarray(((1, 1, 1), (-2, -1, -1), (-1, 1, 1)), dtype=float)
    upper = np.asarray(((2, 2, 2), (-1, 1, 1), (1, 2, 2)), dtype=float)
    decision = interval_query_decision(lower, upper, _query("all"))
    assert decision.accepted.tolist() == [True, True, False]
    assert decision.predictions.tolist() == [True, False, False]


def test_conformal_baselines_and_oracle():
    assert finite_sample_quantile(np.arange(1, 11, dtype=float), 0.2) == 9.0
    truth = np.asarray(((1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)))
    prediction = truth - 0.25
    independent = fit_independent_primitive_calibration(truth, prediction, alpha=0.25)
    query = QueryForm("and", "all", ("a", "b"))
    decision = independent_primitive_conformal_decision(
        np.asarray(((2.0, 2.0), (0.1, 2.0), (-2.0, 2.0))), independent, query
    )
    assert decision.accepted.tolist() == [True, False, True]
    joint = fit_joint_max_residual_calibration(truth, prediction, alpha=0.25)
    joint_decision = joint_box_support_decision(
        np.asarray(((2.0, 2.0), (0.1, 2.0))), joint, query
    )
    assert joint_decision.accepted.tolist() == [True, False]
    oracle = oracle_support_decision(np.asarray(((1.0, 1.0), (0.0, 2.0))), query)
    assert oracle.accepted.tolist() == [True, False]


def test_direct_compound_and_uncalibrated_baselines():
    fit_x = np.asarray(((-3.0,), (-2.0,), (-1.0,), (1.0,), (2.0,), (3.0,)))
    fit_y = np.asarray((False, False, False, True, True, True))
    calibration_x = np.asarray(((-2.5,), (-1.5,), (1.5,), (2.5,)))
    calibration_y = np.asarray((False, False, True, True))
    model = fit_direct_compound_conformal(
        fit_x, fit_y, calibration_x, calibration_y, alpha=0.25
    )
    decision = direct_compound_conformal_decision(model, np.asarray(((-3.0,), (0.0,), (3.0,))))
    assert decision.accepted[0] and decision.accepted[2]
    probabilities = np.asarray(((0.9, 0.1), (0.2, 0.8), (0.5, 0.5), (0.7, 0.3)))
    ranked = uncalibrated_confidence_decision(probabilities, target_coverage=0.5)
    assert ranked.accepted.tolist() == [True, True, False, False]


def test_diagnostics_cover_repository_regime_and_coverage_curves():
    decision = SelectiveDecision(
        np.asarray((True, False, True), dtype=np.bool_),
        np.asarray((True, True, False), dtype=np.bool_),
        np.asarray((0.9, 0.8, 0.1)),
        ("accepted", "accepted", "refused_fixture"),
    )
    report = selective_diagnostics(
        np.asarray((True, True, False)), decision, ("r1", "r1", "r2")
    )
    assert report["selective_risk"] == 0.5
    curve = ranked_risk_coverage_curve(
        np.asarray((True, False, True, False)),
        np.asarray((True, False, False, False)),
        np.asarray((0.9, 0.8, 0.7, 0.6)),
        ("r1", "r2", "r3", "r4"),
        (0.5, 1.0),
    )
    assert [point["accepted"] for point in curve] == [2, 4]
    coverage = primitive_interval_coverage(
        np.asarray(((1.0, 2.0), (2.0, 4.0))),
        np.asarray(((1.1, 1.8), (2.5, 4.0))),
        np.asarray((0.25, 0.25)),
    )
    assert coverage["joint_empirical_coverage"] == 0.5
    stratified = stratified_selective_diagnostics(
        np.asarray((True, False, False)),
        decision,
        ("r1", "r1", "r2"),
        ("supported", "weak", "shifted"),
    )
    assert stratified["supported"]["accepted"] == 1


def test_development_batch_and_candidate_plan_reject_hidden_evidence():
    query = QueryForm("and", "all", ("a", "b"))
    arrays = np.ones((2, 2))
    features = np.ones((2, 3))
    with pytest.raises(HiddenRoleAccessError):
        DevelopmentBatch("C0_SELECTION", query, arrays, arrays, features, ("r1", "r2"))
    batch = DevelopmentBatch(
        "C0_ITERATION", query, arrays, arrays, features, ("r1", "r2")
    )
    assert batch.labels.tolist() == [True, True]
    candidate = CandidatePlan(
        "candidate-q1",
        "v1",
        "a" * 40,
        "coordinate interval support",
        "logical interval propagation",
        query,
        "absolute primitive residual",
        hyperparameters={"alpha": 0.1},
        expected_failure_mode="correlated residuals",
    )
    payload = candidate.to_registry_payload(
        timestamp="2026-08-02T16:00:00Z",
        artifact_hashes={"spec": "b" * 64},
    )
    assert payload["hyperparameters"]["calibration_data_role"] == "C0_FIT"
    with pytest.raises(HiddenRoleAccessError):
        CandidatePlan(
            "bad",
            "v1",
            "a" * 40,
            "support",
            "rule",
            QueryForm("q", "all", ("a",)),
            "score",
            evaluation_data_role="C0_SELECTION",
            expected_failure_mode="failure",
        )


def _candidate(query_id: str) -> CandidatePlan:
    return CandidatePlan(
        f"candidate-{query_id}",
        "v1",
        "a" * 40,
        "support",
        "rule",
        QueryForm(query_id, "all", ("a",)),
        "score",
        expected_failure_mode="failure",
    )


def test_candidate_collection_and_registration_gate(tmp_path: Path):
    validate_candidate_collection([_candidate("q1"), _candidate("q2"), _candidate("q3")])
    with pytest.raises(CandidatePlanError):
        validate_candidate_collection(
            [_candidate("q1"), _candidate("q2"), _candidate("q3"), _candidate("q4")]
        )
    with pytest.raises(CandidatePlanError):
        require_candidate_registered(
            tmp_path / "empty-registry.jsonl", candidate_id="c", version="v1"
        )


def test_harness_setup_validation_observes_no_result(tmp_path: Path):
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps(_contract()), encoding="utf-8")
    report = validate_harness_setup(contract, _canonical_firewall(tmp_path / "setup"))
    assert report["visible_repository_counts"] == {"c0_fit": 1, "c0_iteration": 1}
    assert report["mechanism_result_observed"] is False
    assert report["c0_selection_accessed"] is False

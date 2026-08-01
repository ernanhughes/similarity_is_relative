from __future__ import annotations

import inspect

import numpy as np
import pytest

from relate.experiments.option_b_predicted_executor import (
    PredictedPrimitiveVectors,
    deterministic_fold_assignment,
    fit_predicted_executor_contract,
    predicted_executor_distance,
    stable_key_sequence_hash,
)
from relate.experiments.option_b_real_code import array_hash


def _fixture():
    train_x = np.eye(10, dtype=np.float64)
    train_y = np.column_stack(
        (
            np.arange(10, dtype=np.float64),
            np.arange(10, dtype=np.float64) * 2.0 + 1.0,
            np.arange(10, dtype=np.float64) ** 2,
        )
    )
    validation_x = np.vstack((np.full(10, 0.1), np.full(10, 0.2)))
    validation_y = np.asarray(((2.5, 6.0, 8.0), (4.5, 10.0, 22.0)), dtype=np.float64)
    test_x = np.vstack((np.full(10, 0.15), np.full(10, 0.25)))
    return {
        "train_x": train_x,
        "train_true_primitives": train_y,
        "validation_x": validation_x,
        "validation_true_primitives": validation_y,
        "test_x": test_x,
        "train_stable_keys": [f"train-{index}" for index in range(10)],
        "validation_stable_keys": ["validation-0", "validation-1"],
        "test_stable_keys": ["test-0", "test-1"],
        "alphas": (0.1, 1.0, 10.0),
        "folds": 5,
    }


def test_fold_assignment_is_balanced_and_key_deterministic() -> None:
    keys = [f"key-{index}" for index in range(20)]
    assignment = deterministic_fold_assignment(keys, folds=5)
    reversed_assignment = deterministic_fold_assignment(list(reversed(keys)), folds=5)
    by_key = dict(zip(keys, assignment, strict=True))
    reversed_by_key = dict(zip(reversed(keys), reversed_assignment, strict=True))
    assert by_key == reversed_by_key
    assert np.bincount(assignment).tolist() == [4, 4, 4, 4, 4]


def test_test_labels_are_absent_from_fitting_api() -> None:
    signature = inspect.signature(fit_predicted_executor_contract)
    assert "test_true_primitives" not in signature.parameters
    with pytest.raises(TypeError):
        fit_predicted_executor_contract(**_fixture(), test_true_primitives=np.zeros((2, 3)))


def test_contract_produces_oof_candidates_and_hash_addressed_outputs() -> None:
    fixture = _fixture()
    artifacts = fit_predicted_executor_contract(**fixture)

    assert artifacts.report["candidate_prediction_protocol"] == (
        "deterministic balanced out-of-fold"
    )
    assert artifacts.report["prediction_rounding"] == "forbidden"
    assert artifacts.report["canonical_probe_fitting_performed"] is False
    assert artifacts.train_candidates.values.dtype == np.float64
    assert artifacts.validation_rows.values.dtype == np.float64
    assert artifacts.test_queries.values.dtype == np.float64
    assert np.any(artifacts.test_queries.values != np.round(artifacts.test_queries.values))

    assert artifacts.train_candidates.row_order_sha256 == stable_key_sequence_hash(
        fixture["train_stable_keys"]
    )
    assert artifacts.train_candidates.prediction_sha256 == array_hash(
        artifacts.train_candidates.values
    )
    assert artifacts.report["fold_assignment_sha256"]
    for primitive in artifacts.report["primitives"].values():
        assert primitive["refit_policy"] == "refit selected alpha on all training rows"
        assert primitive["alpha_tie_break"] == (
            "largest alpha among equal validation MAE values"
        )
        assert len(primitive["out_of_fold_models"]) == 5


def test_candidate_predictions_are_not_full_train_in_sample_predictions() -> None:
    fixture = _fixture()
    artifacts = fit_predicted_executor_contract(**fixture)
    train_y = fixture["train_true_primitives"]
    median = np.median(train_y, axis=0)
    q25, q75 = np.percentile(train_y, (25, 75), axis=0)
    scaled = (train_y - median) / np.maximum(q75 - q25, 1.0)
    assert not np.allclose(artifacts.train_candidates.values, scaled)


def test_executor_requires_predicted_roles_on_both_sides() -> None:
    artifacts = fit_predicted_executor_contract(**_fixture())
    distances = predicted_executor_distance(
        artifacts.test_queries, artifacts.train_candidates
    )
    assert distances.shape == (2, 10)

    with pytest.raises(TypeError):
        predicted_executor_distance(
            artifacts.test_queries.values, artifacts.train_candidates  # type: ignore[arg-type]
        )

    oracle_candidates = PredictedPrimitiveVectors(
        values=artifacts.train_candidates.values,
        role="oracle_candidates",
        row_order_sha256=artifacts.train_candidates.row_order_sha256,
        prediction_sha256=artifacts.train_candidates.prediction_sha256,
        bundle_sha256=artifacts.train_candidates.bundle_sha256,
    )
    with pytest.raises(ValueError, match="train-candidate prediction role"):
        predicted_executor_distance(artifacts.test_queries, oracle_candidates)


def test_query_and_candidate_predictions_must_share_a_bundle() -> None:
    artifacts = fit_predicted_executor_contract(**_fixture())
    foreign = PredictedPrimitiveVectors(
        values=artifacts.train_candidates.values.copy(),
        role=artifacts.train_candidates.role,
        row_order_sha256=artifacts.train_candidates.row_order_sha256,
        prediction_sha256=artifacts.train_candidates.prediction_sha256,
        bundle_sha256="0" * 64,
    )
    with pytest.raises(ValueError, match="same fitted bundle"):
        predicted_executor_distance(artifacts.test_queries, foreign)

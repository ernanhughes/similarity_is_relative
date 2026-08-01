"""Freeze Option B predicted-executor semantics without fitting canonical probes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

from relate.experiments.option_b_real_code import (
    ALPHAS,
    PRIMITIVES,
    array_hash,
    robust_scale,
    robust_scale_fit,
)

DEFAULT_FOLDS = 5
TRAIN_CANDIDATE_ROLE = "train_candidates"
VALIDATION_ROLE = "validation_rows"
TEST_QUERY_ROLE = "test_queries"


def stable_key_sequence_hash(stable_keys: Sequence[str]) -> str:
    """Hash an ordered stable-key sequence with an unambiguous JSON encoding."""
    payload = json.dumps(list(stable_keys), separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def deterministic_fold_assignment(
    stable_keys: Sequence[str], *, folds: int = DEFAULT_FOLDS
) -> np.ndarray:
    """Assign balanced folds by stable-key hash, independent of input ordering."""
    if folds < 2:
        raise ValueError("at least two folds are required")
    if len(stable_keys) < folds:
        raise ValueError("number of training rows must be at least the fold count")
    if len(set(stable_keys)) != len(stable_keys):
        raise ValueError("training stable keys must be unique")

    ranked = sorted(
        range(len(stable_keys)),
        key=lambda index: (
            hashlib.sha256(stable_keys[index].encode()).hexdigest(),
            stable_keys[index],
        ),
    )
    assignments = np.empty(len(stable_keys), dtype=np.int64)
    for rank, index in enumerate(ranked):
        assignments[index] = rank % folds
    return assignments


@dataclass(frozen=True)
class PredictedPrimitiveVectors:
    """Hash-addressed predictions with an explicit executor role."""

    values: np.ndarray
    role: str
    row_order_sha256: str
    prediction_sha256: str
    bundle_sha256: str

    def __post_init__(self) -> None:
        array = np.asarray(self.values)
        if array.dtype != np.float64:
            raise ValueError("predicted primitive vectors must be float64")
        if array.ndim != 2 or array.shape[1] != len(PRIMITIVES):
            raise ValueError("predicted primitive vectors must have one column per primitive")
        if not np.isfinite(array).all():
            raise ValueError("predicted primitive vectors must be finite")
        if array_hash(array) != self.prediction_sha256:
            raise ValueError("prediction hash does not match values")


@dataclass(frozen=True)
class PredictedExecutorArtifacts:
    """All prediction surfaces required by the frozen executor contract."""

    train_candidates: PredictedPrimitiveVectors
    validation_rows: PredictedPrimitiveVectors
    test_queries: PredictedPrimitiveVectors
    report: dict[str, Any]


def _matrix(name: str, value: np.ndarray, *, rows: int | None = None) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional matrix")
    if rows is not None and len(array) != rows:
        raise ValueError(f"{name} row count does not match its stable keys")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    return array


def _stable_keys(name: str, values: Sequence[str], rows: int) -> tuple[str, ...]:
    keys = tuple(values)
    if len(keys) != rows:
        raise ValueError(f"{name} stable-key count does not match its matrix")
    if len(set(keys)) != len(keys):
        raise ValueError(f"{name} stable keys must be unique")
    return keys


def _parameter_hash(value: np.ndarray | float) -> str:
    return array_hash(np.asarray(value, dtype=np.float64))


def fit_predicted_executor_contract(
    *,
    train_x: np.ndarray,
    train_true_primitives: np.ndarray,
    validation_x: np.ndarray,
    validation_true_primitives: np.ndarray,
    test_x: np.ndarray,
    train_stable_keys: Sequence[str],
    validation_stable_keys: Sequence[str],
    test_stable_keys: Sequence[str],
    alphas: tuple[float, ...] = ALPHAS,
    folds: int = DEFAULT_FOLDS,
) -> PredictedExecutorArtifacts:
    """Fit the prospectively frozen prediction protocol.

    Test primitive labels are intentionally absent. Train candidates receive
    deterministic out-of-fold predictions. Validation and test rows receive
    predictions from a final model refit on all training rows after alpha is
    selected using validation MAE. Predictions are never rounded.
    """
    train_x = _matrix("train_x", train_x)
    validation_x = _matrix("validation_x", validation_x)
    test_x = _matrix("test_x", test_x)
    train_y = _matrix("train_true_primitives", train_true_primitives, rows=len(train_x))
    validation_y = _matrix(
        "validation_true_primitives", validation_true_primitives, rows=len(validation_x)
    )
    if train_y.shape[1] != len(PRIMITIVES) or validation_y.shape[1] != len(PRIMITIVES):
        raise ValueError("primitive matrices must have one column per registered primitive")
    if train_x.shape[1] != validation_x.shape[1] or train_x.shape[1] != test_x.shape[1]:
        raise ValueError("embedding dimensions must match across splits")
    if not alphas or any(alpha <= 0 for alpha in alphas):
        raise ValueError("ridge alphas must be positive")

    train_keys = _stable_keys("train", train_stable_keys, len(train_x))
    validation_keys = _stable_keys("validation", validation_stable_keys, len(validation_x))
    test_keys = _stable_keys("test", test_stable_keys, len(test_x))

    median, scale = robust_scale_fit(train_y)
    scaled_train_y = robust_scale(train_y, median, scale)
    scaled_validation_y = robust_scale(validation_y, median, scale)
    fold_assignment = deterministic_fold_assignment(train_keys, folds=folds)

    train_predictions = np.empty_like(scaled_train_y, dtype=np.float64)
    validation_predictions = np.empty_like(scaled_validation_y, dtype=np.float64)
    test_predictions = np.empty((len(test_x), len(PRIMITIVES)), dtype=np.float64)
    primitive_report: dict[str, Any] = {}

    for primitive_index, primitive_name in enumerate(PRIMITIVES):
        alpha_trials: list[tuple[float, float, float]] = []
        for alpha in sorted(set(float(value) for value in alphas)):
            model = Ridge(alpha=alpha).fit(train_x, scaled_train_y[:, primitive_index])
            prediction = model.predict(validation_x)
            validation_mae = float(
                mean_absolute_error(scaled_validation_y[:, primitive_index], prediction)
            )
            alpha_trials.append((validation_mae, -alpha, alpha))
        selected_mae, _, selected_alpha = min(alpha_trials)

        fold_models: list[dict[str, Any]] = []
        for fold in range(folds):
            held_out = fold_assignment == fold
            training = ~held_out
            model = Ridge(alpha=selected_alpha).fit(
                train_x[training], scaled_train_y[training, primitive_index]
            )
            train_predictions[held_out, primitive_index] = model.predict(train_x[held_out])
            fold_models.append(
                {
                    "fold": fold,
                    "training_rows": int(training.sum()),
                    "held_out_rows": int(held_out.sum()),
                    "coefficient_sha256": _parameter_hash(model.coef_),
                    "intercept_sha256": _parameter_hash(float(model.intercept_)),
                }
            )

        final_model = Ridge(alpha=selected_alpha).fit(
            train_x, scaled_train_y[:, primitive_index]
        )
        validation_predictions[:, primitive_index] = final_model.predict(validation_x)
        test_predictions[:, primitive_index] = final_model.predict(test_x)
        primitive_report[primitive_name] = {
            "selected_alpha": selected_alpha,
            "alpha_tie_break": "largest alpha among equal validation MAE values",
            "validation_mae": selected_mae,
            "refit_policy": "refit selected alpha on all training rows",
            "final_coefficient_sha256": _parameter_hash(final_model.coef_),
            "final_intercept_sha256": _parameter_hash(float(final_model.intercept_)),
            "out_of_fold_models": fold_models,
        }

    prediction_hashes = {
        TRAIN_CANDIDATE_ROLE: array_hash(train_predictions),
        VALIDATION_ROLE: array_hash(validation_predictions),
        TEST_QUERY_ROLE: array_hash(test_predictions),
    }
    row_order_hashes = {
        TRAIN_CANDIDATE_ROLE: stable_key_sequence_hash(train_keys),
        VALIDATION_ROLE: stable_key_sequence_hash(validation_keys),
        TEST_QUERY_ROLE: stable_key_sequence_hash(test_keys),
    }
    bundle_payload = {
        "contract": "option-b-predicted-executor-v1",
        "folds": folds,
        "fold_assignment_sha256": array_hash(fold_assignment),
        "row_order_sha256": row_order_hashes,
        "prediction_sha256": prediction_hashes,
        "scaler_median_sha256": array_hash(median),
        "scaler_scale_sha256": array_hash(scale),
        "primitives": primitive_report,
    }
    bundle_sha256 = hashlib.sha256(
        json.dumps(bundle_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    report = {
        **bundle_payload,
        "bundle_sha256": bundle_sha256,
        "status": "PREDICTED_EXECUTOR_CONTRACT_COMPLETE",
        "scientific_result_observed": False,
        "true_primitive_usage": [
            "train-only robust scaler fitting",
            "train-only ridge fitting",
            "validation-only alpha selection",
            "later oracle distance and hard-negative construction",
        ],
        "forbidden_executor_input": "true candidate primitives",
        "candidate_prediction_protocol": "deterministic balanced out-of-fold",
        "prediction_rounding": "forbidden",
        "next_allowed_action": "EMBEDDING_IDENTITY_V2",
        "canonical_probe_fitting_performed": False,
    }

    def vectors(values: np.ndarray, role: str) -> PredictedPrimitiveVectors:
        return PredictedPrimitiveVectors(
            values=values,
            role=role,
            row_order_sha256=row_order_hashes[role],
            prediction_sha256=prediction_hashes[role],
            bundle_sha256=bundle_sha256,
        )

    return PredictedExecutorArtifacts(
        train_candidates=vectors(train_predictions, TRAIN_CANDIDATE_ROLE),
        validation_rows=vectors(validation_predictions, VALIDATION_ROLE),
        test_queries=vectors(test_predictions, TEST_QUERY_ROLE),
        report=report,
    )


def predicted_executor_distance(
    queries: PredictedPrimitiveVectors,
    candidates: PredictedPrimitiveVectors,
) -> np.ndarray:
    """Compute the registered executor geometry using predictions on both sides."""
    if not isinstance(queries, PredictedPrimitiveVectors) or not isinstance(
        candidates, PredictedPrimitiveVectors
    ):
        raise TypeError("predicted executor accepts only PredictedPrimitiveVectors")
    if queries.role != TEST_QUERY_ROLE:
        raise ValueError("query vectors must have the test-query prediction role")
    if candidates.role != TRAIN_CANDIDATE_ROLE:
        raise ValueError("candidate vectors must have the train-candidate prediction role")
    if queries.bundle_sha256 != candidates.bundle_sha256:
        raise ValueError("query and candidate predictions must come from the same fitted bundle")
    return np.max(
        np.abs(queries.values[:, None, :] - candidates.values[None, :, :]), axis=2
    )

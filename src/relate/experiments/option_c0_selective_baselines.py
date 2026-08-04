"""Development-only query and baseline primitives for Option C0."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from sklearn.linear_model import LogisticRegression

QUERY_OPERATORS: Final = ("all", "any", "k_of_n")


@dataclass(frozen=True)
class QueryForm:
    query_id: str
    operator: str
    primitive_names: tuple[str, ...]
    k: int | None = None

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("query_id must be non-empty")
        if self.operator not in QUERY_OPERATORS:
            raise ValueError(f"unsupported query operator: {self.operator}")
        if not self.primitive_names or len(set(self.primitive_names)) != len(
            self.primitive_names
        ):
            raise ValueError("primitive_names must be non-empty and unique")
        if self.operator == "k_of_n":
            if self.k is None or not 1 <= self.k <= len(self.primitive_names):
                raise ValueError("k_of_n requires 1 <= k <= primitive count")
        elif self.k is not None:
            raise ValueError("k is only valid for k_of_n queries")

    def to_dict(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "operator": self.operator,
            "primitive_names": list(self.primitive_names),
            "k": self.k,
            "boundary_rule": "primitive condition is true iff signed margin > 0",
        }


def query_truth(margins: np.ndarray, query: QueryForm) -> np.ndarray:
    values = np.asarray(margins, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != len(query.primitive_names):
        raise ValueError("margin matrix shape does not match the query form")
    if not np.all(np.isfinite(values)):
        raise ValueError("query margins must be finite")
    positive = values > 0.0
    if query.operator == "all":
        return np.all(positive, axis=1)
    if query.operator == "any":
        return np.any(positive, axis=1)
    assert query.k is not None
    return np.sum(positive, axis=1) >= query.k


@dataclass(frozen=True)
class SelectiveDecision:
    predictions: np.ndarray
    accepted: np.ndarray
    scores: np.ndarray
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        predictions = np.asarray(self.predictions)
        accepted = np.asarray(self.accepted)
        scores = np.asarray(self.scores, dtype=np.float64)
        if predictions.ndim != 1 or accepted.shape != predictions.shape:
            raise ValueError("predictions and accepted must be aligned vectors")
        if scores.shape != predictions.shape or len(self.reasons) != len(predictions):
            raise ValueError("scores and reasons must align with predictions")
        if predictions.dtype != np.bool_ or accepted.dtype != np.bool_:
            raise ValueError("predictions and accepted must be boolean")
        if not np.all(np.isfinite(scores)):
            raise ValueError("decision scores must be finite")


def interval_query_decision(
    lower: np.ndarray,
    upper: np.ndarray,
    query: QueryForm,
) -> SelectiveDecision:
    low = np.asarray(lower, dtype=np.float64)
    high = np.asarray(upper, dtype=np.float64)
    if low.shape != high.shape or low.ndim != 2:
        raise ValueError("support bounds must be aligned matrices")
    if low.shape[1] != len(query.primitive_names):
        raise ValueError("support bounds do not match query primitives")
    if np.any(low > high):
        raise ValueError("support lower bounds cannot exceed upper bounds")
    true = low > 0.0
    false = high <= 0.0
    uncertain = ~(true | false)
    if query.operator == "all":
        positive = np.all(true, axis=1)
        negative = np.any(false, axis=1)
    elif query.operator == "any":
        positive = np.any(true, axis=1)
        negative = np.all(false, axis=1)
    else:
        assert query.k is not None
        true_count = np.sum(true, axis=1)
        uncertain_count = np.sum(uncertain, axis=1)
        positive = true_count >= query.k
        negative = true_count + uncertain_count < query.k
    accepted = (positive | negative).astype(np.bool_)
    predictions = positive.astype(np.bool_)
    scores = np.min(np.minimum(np.abs(low), np.abs(high)), axis=1)
    reasons = tuple(
        "accepted_supported_true"
        if is_positive
        else "accepted_supported_false"
        if is_negative
        else "refused_primitive_support_overlap"
        for is_positive, is_negative in zip(positive, negative, strict=True)
    )
    return SelectiveDecision(predictions, accepted, scores, reasons)


def finite_sample_quantile(scores: np.ndarray, alpha: float) -> float:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("conformal scores must be a non-empty finite vector")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    rank = min(len(values), math.ceil((len(values) + 1) * (1.0 - alpha)))
    return float(np.partition(values, rank - 1)[rank - 1])


@dataclass(frozen=True)
class IndependentPrimitiveCalibration:
    alpha: float
    quantiles: np.ndarray


def fit_independent_primitive_calibration(
    truth: np.ndarray,
    prediction: np.ndarray,
    *,
    alpha: float,
) -> IndependentPrimitiveCalibration:
    true_values = np.asarray(truth, dtype=np.float64)
    predicted_values = np.asarray(prediction, dtype=np.float64)
    if true_values.ndim != 2 or predicted_values.shape != true_values.shape:
        raise ValueError("calibration primitive arrays must be aligned matrices")
    residuals = np.abs(true_values - predicted_values)
    quantiles = np.asarray(
        [finite_sample_quantile(residuals[:, index], alpha) for index in range(residuals.shape[1])]
    )
    return IndependentPrimitiveCalibration(alpha, quantiles)


def independent_primitive_conformal_decision(
    predicted_margins: np.ndarray,
    calibration: IndependentPrimitiveCalibration,
    query: QueryForm,
) -> SelectiveDecision:
    predicted = np.asarray(predicted_margins, dtype=np.float64)
    if predicted.ndim != 2 or predicted.shape[1] != len(calibration.quantiles):
        raise ValueError("predicted primitive matrix does not match calibration")
    return interval_query_decision(
        predicted - calibration.quantiles,
        predicted + calibration.quantiles,
        query,
    )


@dataclass(frozen=True)
class JointMaxResidualCalibration:
    alpha: float
    scales: np.ndarray
    quantile: float


def fit_joint_max_residual_calibration(
    truth: np.ndarray,
    prediction: np.ndarray,
    *,
    alpha: float,
    minimum_scale: float = 1e-12,
) -> JointMaxResidualCalibration:
    true_values = np.asarray(truth, dtype=np.float64)
    predicted_values = np.asarray(prediction, dtype=np.float64)
    if true_values.ndim != 2 or predicted_values.shape != true_values.shape:
        raise ValueError("joint calibration arrays must be aligned matrices")
    residuals = np.abs(true_values - predicted_values)
    scales = np.maximum(np.median(residuals, axis=0), minimum_scale)
    quantile = finite_sample_quantile(np.max(residuals / scales, axis=1), alpha)
    return JointMaxResidualCalibration(alpha, scales, quantile)


def joint_box_support_decision(
    predicted_margins: np.ndarray,
    calibration: JointMaxResidualCalibration,
    query: QueryForm,
) -> SelectiveDecision:
    predicted = np.asarray(predicted_margins, dtype=np.float64)
    if predicted.ndim != 2 or predicted.shape[1] != len(calibration.scales):
        raise ValueError("predicted primitive matrix does not match calibration")
    radius = calibration.quantile * calibration.scales
    return interval_query_decision(predicted - radius, predicted + radius, query)


@dataclass(frozen=True)
class DirectCompoundConformalModel:
    estimator: LogisticRegression
    alpha: float
    quantile: float
    feature_count: int


def fit_direct_compound_conformal(
    fit_features: np.ndarray,
    fit_labels: np.ndarray,
    calibration_features: np.ndarray,
    calibration_labels: np.ndarray,
    *,
    alpha: float,
    random_seed: int = 8_112_026,
) -> DirectCompoundConformalModel:
    fit_x = np.asarray(fit_features, dtype=np.float64)
    fit_y = np.asarray(fit_labels, dtype=np.bool_)
    calibration_x = np.asarray(calibration_features, dtype=np.float64)
    calibration_y = np.asarray(calibration_labels, dtype=np.bool_)
    if fit_x.ndim != 2 or calibration_x.ndim != 2:
        raise ValueError("direct compound features must be matrices")
    if fit_x.shape[1] != calibration_x.shape[1]:
        raise ValueError("fit and calibration feature dimensions must match")
    if fit_y.shape != (len(fit_x),) or calibration_y.shape != (len(calibration_x),):
        raise ValueError("direct compound labels must align with feature rows")
    if len(np.unique(fit_y)) != 2:
        raise ValueError("direct compound fit labels must contain both classes")
    estimator = LogisticRegression(
        random_state=random_seed,
        solver="lbfgs",
        max_iter=2_000,
    ).fit(fit_x, fit_y.astype(np.int64))
    probabilities = estimator.predict_proba(calibration_x)
    scores = 1.0 - probabilities[
        np.arange(len(calibration_y)), calibration_y.astype(np.int64)
    ]
    return DirectCompoundConformalModel(
        estimator,
        alpha,
        finite_sample_quantile(scores, alpha),
        fit_x.shape[1],
    )


def direct_compound_conformal_decision(
    model: DirectCompoundConformalModel,
    features: np.ndarray,
) -> SelectiveDecision:
    values = np.asarray(features, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != model.feature_count:
        raise ValueError("direct compound feature matrix has the wrong shape")
    probabilities = model.estimator.predict_proba(values)
    included = (1.0 - probabilities) <= model.quantile
    cardinality = np.sum(included, axis=1)
    accepted = (cardinality == 1).astype(np.bool_)
    predictions = included[:, 1].astype(np.bool_)
    reasons = tuple(
        "accepted_singleton_prediction_set"
        if count == 1
        else "refused_empty_prediction_set"
        if count == 0
        else "refused_ambiguous_prediction_set"
        for count in cardinality
    )
    return SelectiveDecision(predictions, accepted, np.max(probabilities, axis=1), reasons)


def uncalibrated_confidence_decision(
    probabilities: np.ndarray,
    *,
    target_coverage: float,
) -> SelectiveDecision:
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise ValueError("probabilities must have shape (n, 2)")
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("probabilities must be finite and non-negative")
    if not np.allclose(np.sum(values, axis=1), 1.0, atol=1e-12, rtol=0.0):
        raise ValueError("probability rows must sum to one")
    if not 0.0 <= target_coverage <= 1.0:
        raise ValueError("target coverage must lie in [0, 1]")
    confidence = np.max(values, axis=1)
    predictions = (values[:, 1] > values[:, 0]).astype(np.bool_)
    accepted = np.zeros(len(values), dtype=np.bool_)
    count = len(values) if target_coverage == 1.0 else int(
        math.floor(len(values) * target_coverage)
    )
    if count:
        order = np.lexsort((np.arange(len(values)), -confidence))
        accepted[order[:count]] = True
    reasons = tuple(
        "accepted_confidence_rank" if item else "refused_confidence_rank"
        for item in accepted
    )
    return SelectiveDecision(predictions, accepted, confidence, reasons)


def oracle_support_decision(
    true_margins: np.ndarray,
    query: QueryForm,
    *,
    minimum_boundary_distance: float = 0.0,
) -> SelectiveDecision:
    values = np.asarray(true_margins, dtype=np.float64)
    if minimum_boundary_distance < 0.0:
        raise ValueError("minimum boundary distance must be non-negative")
    predictions = query_truth(values, query).astype(np.bool_)
    scores = np.min(np.abs(values), axis=1)
    accepted = (scores > minimum_boundary_distance).astype(np.bool_)
    reasons = tuple(
        "accepted_oracle_support" if item else "refused_oracle_boundary"
        for item in accepted
    )
    return SelectiveDecision(predictions, accepted, scores, reasons)

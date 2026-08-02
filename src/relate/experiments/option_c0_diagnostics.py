"""Exploratory diagnostics for Option C0 selective prediction."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from typing import Any, Final

import numpy as np

from relate.experiments.option_c0_selective_baselines import SelectiveDecision

REGIME_LABELS: Final = ("supported", "weak", "absent", "shifted")


def selective_diagnostics(
    labels: np.ndarray,
    decision: SelectiveDecision,
    repositories: Sequence[str],
) -> dict[str, Any]:
    truth = np.asarray(labels, dtype=np.bool_)
    if truth.shape != decision.predictions.shape or len(repositories) != len(truth):
        raise ValueError("labels, decisions, and repositories must align")
    accepted_indices = np.flatnonzero(decision.accepted)
    errors = decision.predictions != truth
    accepted_count = len(accepted_indices)
    accepted_errors = int(np.sum(errors[accepted_indices])) if accepted_count else 0
    by_repository: dict[str, list[int]] = defaultdict(list)
    for index in accepted_indices:
        repository = str(repositories[int(index)])
        if not repository:
            raise ValueError("repository identities must be non-empty")
        by_repository[repository].append(int(index))
    risks = [
        float(np.mean(errors[np.asarray(indices, dtype=np.int64)]))
        for indices in by_repository.values()
    ]
    dispersion = {
        "repositories_with_acceptance": len(risks),
        "mean_risk": float(np.mean(risks)) if risks else None,
        "std_risk": float(np.std(risks)) if risks else None,
        "min_risk": float(np.min(risks)) if risks else None,
        "max_risk": float(np.max(risks)) if risks else None,
    }
    return {
        "rows": len(truth),
        "accepted": accepted_count,
        "refused": len(truth) - accepted_count,
        "errors": accepted_errors,
        "coverage": accepted_count / len(truth) if len(truth) else 0.0,
        "selective_risk": accepted_errors / accepted_count if accepted_count else None,
        "refusal_reasons": dict(
            sorted(
                Counter(
                    reason
                    for reason, accepted in zip(
                        decision.reasons, decision.accepted, strict=True
                    )
                    if not accepted
                ).items()
            )
        ),
        "repository_dispersion": dispersion,
    }


def ranked_risk_coverage_curve(
    labels: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
    repositories: Sequence[str],
    coverage_anchors: Iterable[float],
) -> list[dict[str, Any]]:
    truth = np.asarray(labels, dtype=np.bool_)
    predicted = np.asarray(predictions, dtype=np.bool_)
    confidence = np.asarray(scores, dtype=np.float64)
    if truth.shape != predicted.shape or confidence.shape != truth.shape:
        raise ValueError("ranked curve arrays must be aligned")
    if not np.all(np.isfinite(confidence)):
        raise ValueError("ranked curve scores must be finite")
    anchors = tuple(float(item) for item in coverage_anchors)
    if not anchors or any(not 0.0 <= item <= 1.0 for item in anchors):
        raise ValueError("coverage anchors must lie in [0, 1]")
    curve: list[dict[str, Any]] = []
    for anchor in anchors:
        accepted = np.zeros(len(truth), dtype=np.bool_)
        count = len(truth) if anchor == 1.0 else int(math.floor(len(truth) * anchor))
        if count:
            order = np.lexsort((np.arange(len(truth)), -confidence))
            accepted[order[:count]] = True
        decision = SelectiveDecision(
            predicted,
            accepted,
            confidence,
            tuple(
                "accepted_score_rank" if item else "refused_score_rank"
                for item in accepted
            ),
        )
        point = selective_diagnostics(truth, decision, repositories)
        point["target_coverage"] = anchor
        curve.append(point)
    return curve


def primitive_interval_coverage(
    truth: np.ndarray,
    prediction: np.ndarray,
    quantiles: np.ndarray,
) -> dict[str, Any]:
    true_values = np.asarray(truth, dtype=np.float64)
    predicted_values = np.asarray(prediction, dtype=np.float64)
    radii = np.asarray(quantiles, dtype=np.float64)
    if true_values.ndim != 2 or predicted_values.shape != true_values.shape:
        raise ValueError("primitive coverage arrays must be aligned matrices")
    if radii.shape != (true_values.shape[1],) or np.any(radii < 0.0):
        raise ValueError("primitive coverage radii must match the primitive dimension")
    covered = np.abs(true_values - predicted_values) <= radii
    return {
        "rows": len(true_values),
        "per_primitive_empirical_coverage": [
            float(np.mean(covered[:, index])) for index in range(covered.shape[1])
        ],
        "joint_empirical_coverage": float(np.mean(np.all(covered, axis=1))),
    }


def stratified_selective_diagnostics(
    labels: np.ndarray,
    decision: SelectiveDecision,
    repositories: Sequence[str],
    regimes: Sequence[str],
) -> dict[str, Any]:
    if len(regimes) != len(labels):
        raise ValueError("regime labels must align with evaluated rows")
    invalid = sorted(set(regimes) - set(REGIME_LABELS))
    if invalid:
        raise ValueError(f"unknown C0 regime labels: {invalid}")
    labels_array = np.asarray(labels, dtype=np.bool_)
    result: dict[str, Any] = {}
    for regime in REGIME_LABELS:
        indices = np.asarray(
            [index for index, value in enumerate(regimes) if value == regime],
            dtype=np.int64,
        )
        if not len(indices):
            result[regime] = {"rows": 0}
            continue
        subset = SelectiveDecision(
            decision.predictions[indices],
            decision.accepted[indices],
            decision.scores[indices],
            tuple(decision.reasons[int(index)] for index in indices),
        )
        result[regime] = selective_diagnostics(
            labels_array[indices],
            subset,
            tuple(repositories[int(index)] for index in indices),
        )
    return result

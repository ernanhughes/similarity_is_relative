from __future__ import annotations

import numpy as np

from relate.experiments.e00_certification import (
    _average_precision_scores,
    _bootstrap_difference,
    _bootstrap_interval,
    _triplet_scores,
)


def test_triplet_scores_are_perfect_for_oracle_distances() -> None:
    candidates = np.arange(8, dtype=float)
    queries = np.array([1.5, 5.5])
    distances = np.abs(queries[:, None] - candidates[None, :])
    scores = _triplet_scores(distances, candidates, queries)
    assert np.allclose(scores, 1.0)


def test_binary_average_precision_is_perfect_for_class_distance() -> None:
    candidates = np.array([0, 1, 0, 1, 0, 1], dtype=float)
    queries = np.array([0, 1], dtype=float)
    distances = np.abs(queries[:, None] - candidates[None, :])
    scores = _average_precision_scores(distances, candidates, queries)
    assert np.allclose(scores, 1.0)


def test_bootstrap_is_deterministic_for_fixed_rng() -> None:
    values = np.linspace(0.6, 0.9, 20)
    first = _bootstrap_interval(values, np.random.default_rng(17), 200, 0.95)
    second = _bootstrap_interval(values, np.random.default_rng(17), 200, 0.95)
    assert first == second


def test_bootstrap_difference_preserves_large_gap() -> None:
    left = np.full(30, 0.9)
    right = np.full(30, 0.2)
    interval = _bootstrap_difference(left, right, np.random.default_rng(17), 200, 0.95)
    assert interval["lower"] > 0.6

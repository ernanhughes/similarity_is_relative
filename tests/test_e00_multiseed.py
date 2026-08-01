from __future__ import annotations

import numpy as np
import pytest

from relate.experiments.e00_multiseed import (
    CONFIRMATORY_SEEDS,
    HISTORICAL_SEED,
    MultiSeedConfig,
    _candidate_models,
    _seed_interval,
)


def test_confirmatory_seeds_are_frozen_and_exclude_history() -> None:
    assert CONFIRMATORY_SEEDS == (23, 41, 59, 83, 101)
    assert HISTORICAL_SEED == 17
    assert HISTORICAL_SEED not in CONFIRMATORY_SEEDS
    assert MultiSeedConfig().seeds == CONFIRMATORY_SEEDS


def test_candidate_grid_is_frozen_and_deterministic() -> None:
    identifiers = [identifier for identifier, _ in _candidate_models(23)]
    assert identifiers == [
        "poly2-logistic-c0.1",
        "poly2-logistic-c1",
        "poly2-logistic-c10",
        "mlp-16-alpha0.0001",
        "mlp-16-alpha0.001",
        "mlp-16-alpha0.01",
        "mlp-32-alpha0.0001",
        "mlp-32-alpha0.001",
        "mlp-32-alpha0.01",
        "mlp-32x16-alpha0.0001",
        "mlp-32x16-alpha0.001",
        "mlp-32x16-alpha0.01",
    ]


def test_seed_bootstrap_resamples_seed_values() -> None:
    interval = _seed_interval([0.8, 0.9, 1.0, 0.7, 0.6], np.random.default_rng(7), 100)
    assert interval["values"] == [0.8, 0.9, 1.0, 0.7, 0.6]
    assert interval["mean"] == pytest.approx(0.8)
    assert interval["minimum"] == pytest.approx(0.6)
    assert interval["maximum"] == pytest.approx(1.0)
    assert interval["lower"] <= interval["mean"] <= interval["upper"]

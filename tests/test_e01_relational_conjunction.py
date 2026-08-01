from pathlib import Path

import numpy as np

from relate.experiments.e01_relational_conjunction import (
    COMPOUNDS,
    PRIMITIVES,
    RelationalConjunctionConfig,
    _decision,
    _generate,
    _scalar_collapse_distance,
    _weighted_relational_distance,
    run,
)


def test_contract_is_frozen() -> None:
    assert PRIMITIVES == ("a", "b", "c")
    assert COMPOUNDS == {
        "a2_b": (2.0, 1.0, 0.0),
        "a3_c": (3.0, 0.0, 1.0),
        "b2_c": (0.0, 2.0, 1.0),
        "a_b2_c3": (1.0, 2.0, 3.0),
    }
    assert RelationalConjunctionConfig().seed == 307


def test_generation_is_deterministic() -> None:
    config = RelationalConjunctionConfig(samples=128, dimensions=8)
    left = _generate(config)
    right = _generate(config)
    assert np.array_equal(left["x"], right["x"])
    assert np.array_equal(left["targets"], right["targets"])


def test_relational_geometry_prevents_scalar_cancellation() -> None:
    values = np.asarray([[0.0, 0.0], [1.0, -1.0], [0.0, 0.0]])
    candidates = np.asarray([1, 2])
    queries = np.asarray([0])
    weights = np.asarray([1.0, 1.0])
    relational = _weighted_relational_distance(values, candidates, queries, weights)
    collapsed = _scalar_collapse_distance(values, candidates, queries, weights)
    assert relational[0, 0] > relational[0, 1]
    assert collapsed[0, 0] == collapsed[0, 1]


def test_decision_thresholds() -> None:
    controls = [
        {"triplet_accuracy": 0.70},
        {"triplet_accuracy": 0.72},
    ]
    assert _decision({"triplet_accuracy": 0.90}, controls) == "SUPPORTED_POINT_ESTIMATE"
    assert _decision({"triplet_accuracy": 0.65}, controls) == "UNSUPPORTED_AT_THRESHOLD"


def test_small_run_writes_complete_result(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        RelationalConjunctionConfig(samples=256, dimensions=12, retrieval_ks=(10, 25)),
    )
    assert result["experiment_id"] == "e01-relational-conjunction"
    assert len(result["compounds"]) == 4
    assert len(result["decisions"]) == 4
    assert result["gate"]["claim_promotion_allowed"] is False
    assert (tmp_path / "relational-conjunction-result.json").exists()
    assert (tmp_path / "relational-conjunction-result-with-hash.json").exists()

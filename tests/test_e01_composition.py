from pathlib import Path

import numpy as np

from relate.experiments.e01_composition import (
    COMPOUNDS,
    PRIMITIVES,
    CompositionConfig,
    _decision,
    _generate,
    _scalar_distances,
    run,
)


def test_contract_is_frozen() -> None:
    assert PRIMITIVES == ("a", "b", "c")
    assert COMPOUNDS == {
        "a_plus_b": (1.0, 1.0, 0.0),
        "a_plus_c": (1.0, 0.0, 1.0),
        "b_plus_c": (0.0, 1.0, 1.0),
        "a_plus_2b_minus_c": (1.0, 2.0, -1.0),
    }
    assert CompositionConfig().seed == 211


def test_generation_is_deterministic() -> None:
    config = CompositionConfig(samples=128, dimensions=8)
    left = _generate(config)
    right = _generate(config)
    assert np.array_equal(left["x"], right["x"])
    assert np.array_equal(left["primitive_targets"], right["primitive_targets"])
    assert all(
        np.array_equal(left["splits"][name], right["splits"][name])
        for name in ("train", "validation", "test")
    )


def test_rotation_preserves_pairwise_distances() -> None:
    generated = _generate(CompositionConfig(samples=64, dimensions=8))
    x = generated["x"]
    rotation = generated["rotation"]
    recovered = x @ rotation.T
    assert np.allclose(
        np.linalg.norm(x[0] - x[1]),
        np.linalg.norm(recovered[0] - recovered[1]),
    )


def test_scalar_distances_are_absolute_differences() -> None:
    values = np.asarray([0.0, 2.0, 5.0])
    observed = _scalar_distances(values, np.asarray([0, 2]), np.asarray([1]))
    assert np.array_equal(observed, np.asarray([[2.0, 3.0]]))


def test_decision_thresholds() -> None:
    supported = {"triplet_accuracy": 0.90}
    oracle = {"triplet_accuracy": 0.93}
    controls = [{"triplet_accuracy": 0.60}, {"triplet_accuracy": 0.65}]
    assert _decision(supported, oracle, controls) == "SUPPORTED_POINT_ESTIMATE"
    assert (
        _decision({"triplet_accuracy": 0.60}, oracle, controls)
        == "UNSUPPORTED_AT_THRESHOLD"
    )


def test_small_run_writes_complete_result(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        CompositionConfig(samples=256, dimensions=12, retrieval_ks=(10, 25)),
    )
    assert result["experiment_id"] == "e01-unseen-composition"
    assert len(result["compounds"]) == 4
    assert len(result["decisions"]) == 4
    assert result["gate"]["claim_promotion_allowed"] is False
    assert (tmp_path / "composition-result.json").exists()
    assert (tmp_path / "composition-result-with-hash.json").exists()

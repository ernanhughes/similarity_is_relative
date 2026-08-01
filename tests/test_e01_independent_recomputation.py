from pathlib import Path

import numpy as np

from relate.audits.e01_independent_recomputation import (
    AuditConfig,
    NON_IDENTITY_PERMUTATIONS,
    WEIGHT_GRID,
    _distance,
    _original_status,
    run,
)


def test_distance_matches_direct_broadcast() -> None:
    values = np.asarray([[0.0, 1.0], [2.0, 3.0], [1.0, -1.0]])
    candidates = np.asarray([0, 1])
    queries = np.asarray([2])
    weights = np.asarray([2.0, 0.5])
    observed = _distance(values, candidates, queries, weights)
    delta = values[queries, None, :] - values[candidates][None, :, :]
    expected = np.sqrt(np.sum(delta * delta * weights[None, None, :], axis=2))
    assert np.allclose(observed, expected)


def test_original_rule_requires_point_one_margin() -> None:
    assert _original_status(0.92, [0.81, 0.80]) == "SUPPORTED_POINT_ESTIMATE"
    assert _original_status(0.92, [0.83, 0.80]) == "INSUFFICIENT_EVIDENCE"


def test_frozen_control_contract() -> None:
    assert len(NON_IDENTITY_PERMUTATIONS) == 5
    assert tuple(WEIGHT_GRID) == (
        "equal",
        "near_equal",
        "moderate",
        "registered",
        "separated",
    )


def test_small_audit_writes_result(tmp_path: Path) -> None:
    config = AuditConfig(
        seeds=(401,),
        samples=192,
        dimensions=8,
        retrieval_ks=(5, 10),
        triplets_per_query=8,
    )
    result = run(tmp_path, config)
    assert result["verification_class"] == "INDEPENDENT_RECOMPUTATION"
    assert result["claim_promotion_allowed"] is False
    assert "e01_1_exhaustive_control" in result["decisions"]
    assert (tmp_path / "e01-independent-recomputation-with-hash.json").exists()

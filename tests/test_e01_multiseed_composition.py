from pathlib import Path

import numpy as np

from relate.experiments.e01_multiseed_composition import (
    NON_IDENTITY_PERMUTATIONS,
    SEEDS,
    MultiSeedCompositionConfig,
    _manifest,
    run,
)


def test_frozen_seed_and_permutation_contract() -> None:
    assert SEEDS == (401, 433, 467, 503, 557)
    assert len(NON_IDENTITY_PERMUTATIONS) == 5
    assert (0, 1, 2) not in NON_IDENTITY_PERMUTATIONS


def test_manifest_is_deterministic_and_explicit() -> None:
    queries = np.asarray([10, 11])
    candidates = np.asarray([1, 2, 3, 4])
    left = _manifest(99, queries, candidates, 8)
    right = _manifest(99, queries, candidates, 8)
    assert np.array_equal(left, right)
    assert left.shape == (16, 3)
    assert set(left[:, 0]) == {10, 11}


def test_small_multiseed_run_writes_result(tmp_path: Path) -> None:
    config = MultiSeedCompositionConfig(
        seeds=(401,),
        samples=192,
        dimensions=8,
        triplets_per_query=8,
        bootstrap_repetitions=20,
    )
    result = run(tmp_path, config)
    assert result["stage"] == "E01.2a"
    assert len(result["seeds"]) == 1
    assert len(result["aggregate"]) == 4
    assert result["gate"]["claim_promotion_allowed"] is False
    assert (tmp_path / "multiseed-composition-result-with-hash.json").exists()

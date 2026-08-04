from pathlib import Path

import numpy as np

from relate.experiments.e00 import Config
from relate.experiments.e00 import run as run_e00
from relate.experiments.e00_operator_matrix import (
    OperatorConfig,
    _pairwise_cosine,
    _pairwise_euclidean,
    frozen_splits,
)
from relate.experiments.e00_operator_matrix import (
    run as run_operator_matrix,
)
from relate.verification.e00_operator_matrix import verify


def test_exact_distance_helpers() -> None:
    candidates = np.array([[1.0, 0.0], [0.0, 1.0]])
    queries = np.array([[1.0, 0.0]])
    euclidean = _pairwise_euclidean(queries, candidates)
    cosine = _pairwise_cosine(queries, candidates)
    assert np.allclose(euclidean, [[0.0, np.sqrt(2.0)]])
    assert np.allclose(cosine, [[0.0, 1.0]])


def test_frozen_splits_match_e00_rng_contract() -> None:
    config = Config(seed=17, samples=256, dimensions=8)
    first = frozen_splits(config)
    second = frozen_splits(config)
    assert all(np.array_equal(first[name], second[name]) for name in first)


def test_operator_matrix_consumes_and_verifies_frozen_e00(tmp_path: Path) -> None:
    source = tmp_path / "source"
    operators = tmp_path / "operators"
    run_e00(
        Config(
            seed=17,
            samples=192,
            dimensions=8,
            retrieval_k=5,
            retrieval_ks=(5, 10, 25),
        ),
        source,
    )
    result = run_operator_matrix(
        source,
        operators,
        OperatorConfig(retrieval_ks=(5, 10, 25), pls_ranks=(2, 4)),
    )

    assert result["source_manifest_sha256"]
    assert set(result["regimes"]["axis_linear"]["methods"]) == {
        "raw_euclidean",
        "raw_cosine",
        "ridge_predicted_distance",
        "diagonal_ridge_metric",
        "rank1_ridge_projection",
        "pls_projection_rank2",
        "pls_projection_rank4",
    }
    report = verify(source, operators)
    assert report["status"] == "PASS"
    assert report["verified_regimes"] == 6

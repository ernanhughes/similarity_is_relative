from pathlib import Path

import numpy as np

from relate.experiments.e00 import (
    Config,
    array_hash,
    evaluate_scalar_retrieval,
    orthogonal_matrix,
    run,
)
from relate.verification.e00 import verify


def test_rotation_is_orthogonal() -> None:
    rng = np.random.default_rng(17)
    rotation = orthogonal_matrix(rng, 16)
    assert np.allclose(rotation.T @ rotation, np.eye(16), atol=1e-10)


def test_array_hash_includes_shape() -> None:
    values = np.arange(8, dtype=np.float64)
    assert array_hash(values) != array_hash(values.reshape(2, 4))


def test_perfect_scalar_predictions_score_perfectly() -> None:
    candidates = np.linspace(-2.0, 2.0, 101)
    queries = np.array([-1.25, -0.1, 0.75, 1.6])
    metrics = evaluate_scalar_retrieval(
        candidate_values=candidates,
        query_values=queries,
        predicted_candidates=candidates.copy(),
        predicted_queries=queries.copy(),
        k=10,
        ks=(10, 25, 50),
    )

    assert metrics["spearman"] == 1.0
    assert metrics["triplet_accuracy"] == 1.0
    assert metrics["oracle_neighbor_predicted_rank_median"] <= 10
    assert metrics["oracle_neighbor_predicted_rank_p90"] <= 10
    for value in ("10", "25", "50"):
        assert metrics["recall_at"][value] == 1.0
        assert np.isclose(metrics["relative_neighbor_error_at"][value], 1.0)
        assert np.isclose(metrics["ndcg_at"][value], 1.0)


def test_metrics_report_near_miss_quality_beyond_exact_overlap() -> None:
    candidates = np.linspace(0.0, 1.0, 200)
    queries = np.array([0.2, 0.5, 0.8])
    shifted_predictions = candidates + 0.015
    metrics = evaluate_scalar_retrieval(
        candidate_values=candidates,
        query_values=queries,
        predicted_candidates=shifted_predictions,
        predicted_queries=queries,
        k=10,
        ks=(10, 25),
    )

    assert 0.0 < metrics["recall_at"]["10"] < 1.0
    assert metrics["ndcg_at"]["10"] > metrics["recall_at"]["10"]
    assert metrics["relative_neighbor_error_at"]["10"] >= 1.0
    assert metrics["triplet_accuracy"] > 0.9


def test_e00_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    config = Config(
        seed=17,
        samples=256,
        dimensions=8,
        retrieval_k=5,
        retrieval_ks=(5, 10, 25),
    )
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    result_a = run(config, run_a)
    result_b = run(config, run_b)

    assert result_a["rotation_sha256"] == result_b["rotation_sha256"]
    assert result_a["split_hashes"] == result_b["split_hashes"]
    assert {
        key: value["x_sha256"] for key, value in result_a["regimes"].items()
    } == {
        key: value["x_sha256"] for key, value in result_b["regimes"].items()
    }
    assert result_a["regimes"] == result_b["regimes"]
    assert verify(run_a)["status"] == "PASS"

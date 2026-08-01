from pathlib import Path

import numpy as np

from relate.experiments.e00 import Config, array_hash, orthogonal_matrix, run
from relate.verification.e00 import verify


def test_rotation_is_orthogonal() -> None:
    rng = np.random.default_rng(17)
    rotation = orthogonal_matrix(rng, 16)
    assert np.allclose(rotation.T @ rotation, np.eye(16), atol=1e-10)


def test_array_hash_includes_shape() -> None:
    values = np.arange(8, dtype=np.float64)
    assert array_hash(values) != array_hash(values.reshape(2, 4))


def test_e00_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    config = Config(seed=17, samples=256, dimensions=8, retrieval_k=5)
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
    assert verify(run_a)["status"] == "PASS"

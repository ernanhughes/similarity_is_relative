from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from relate.experiments.option_b_cache import OptionBCache
from relate.experiments.option_b_embeddings import extract_split


def test_code_cache_validates_all_immutable_inputs(tmp_path: Path) -> None:
    code = "def example():\n    return 1\n"
    code_sha = hashlib.sha256(code.encode()).hexdigest()
    database = tmp_path / "cache.sqlite3"

    with OptionBCache(database) as cache:
        cache.put_code(
            stable_key="stable",
            split="train",
            code_sha256=code_sha,
            code=code,
            dataset_revision="dataset-a",
            selection_manifest_sha256="manifest-a",
        )
        cache.commit()

        assert (
            cache.get_code(
                stable_key="stable",
                code_sha256=code_sha,
                dataset_revision="dataset-a",
                selection_manifest_sha256="manifest-a",
            )
            == code
        )
        assert (
            cache.get_code(
                stable_key="stable",
                code_sha256=code_sha,
                dataset_revision="dataset-b",
                selection_manifest_sha256="manifest-a",
            )
            is None
        )


def test_embedding_cache_reuses_vectors_across_output_directories(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def embed(batch: list[str]) -> np.ndarray:
        calls.append(batch)
        return np.asarray([[float(len(value)), 1.0] for value in batch], dtype=np.float32)

    codes = ["a", "bb", "ccc"]
    keys = ["one", "two", "three"]
    database = tmp_path / "cache.sqlite3"

    with OptionBCache(database) as cache:
        first = extract_split(
            "test",
            codes,
            tmp_path / "first",
            embed,
            batch_size=2,
            stable_keys=keys,
            cache=cache,
            model_revision="model",
            pooling_sha256="pooling",
        )
        assert len(calls) == 2
        assert first["sqlite_cache_hits"] == 0
        assert first["sqlite_cache_misses"] == 3

    calls.clear()
    with OptionBCache(database) as cache:
        second = extract_split(
            "test",
            codes,
            tmp_path / "second",
            embed,
            batch_size=2,
            stable_keys=keys,
            cache=cache,
            model_revision="model",
            pooling_sha256="pooling",
        )

    assert calls == []
    assert second["sqlite_cache_hits"] == 3
    assert second["sqlite_cache_misses"] == 0
    assert first["array_sha256"] == second["array_sha256"]


def test_refresh_mode_ignores_existing_embeddings_and_replaces_them(tmp_path: Path) -> None:
    database = tmp_path / "cache.sqlite3"
    first_vector = np.asarray([1.0, 2.0], dtype=np.float32)
    replacement = np.asarray([3.0, 4.0], dtype=np.float32)

    with OptionBCache(database) as cache:
        cache.put_embedding(
            stable_key="stable",
            model_id="model",
            model_revision="revision",
            pooling_sha256="pooling",
            max_length=256,
            vector=first_vector,
        )

    with OptionBCache(database, "refresh") as cache:
        assert (
            cache.get_embedding(
                stable_key="stable",
                model_id="model",
                model_revision="revision",
                pooling_sha256="pooling",
                max_length=256,
            )
            is None
        )
        cache.put_embedding(
            stable_key="stable",
            model_id="model",
            model_revision="revision",
            pooling_sha256="pooling",
            max_length=256,
            vector=replacement,
        )

    with OptionBCache(database) as cache:
        actual = cache.get_embedding(
            stable_key="stable",
            model_id="model",
            model_revision="revision",
            pooling_sha256="pooling",
            max_length=256,
        )

    np.testing.assert_array_equal(actual, replacement)

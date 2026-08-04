from __future__ import annotations

import hashlib
import io

import numpy as np

from relate.experiments.option_b_real_code import FunctionRecord
from relate.experiments.option_c0_embedding_cache import (
    EmbeddingFingerprint,
    OptionC0EmbeddingCache,
)
from relate.experiments.option_c0_recovery_entrypoint import (
    ProgressReporter,
    embed_partition_with_cache,
    embedding_fingerprint,
)


def _record(index: int) -> FunctionRecord:
    code = str(index)
    return FunctionRecord(
        split="train",
        repository=f"repo-{index // 2}",
        path=f"module-{index}.py",
        function_id=f"function-{index}",
        code=code,
        code_sha256=hashlib.sha256(code.encode()).hexdigest(),
        normalized_ast_sha256=hashlib.sha256(f"ast-{index}".encode()).hexdigest(),
        token_count=32,
        cyclomatic_complexity=float(index + 1),
        max_control_depth=float(index % 3),
        distinct_call_sites=float(index % 5),
    )


def _fingerprint() -> EmbeddingFingerprint:
    return EmbeddingFingerprint.from_payload(
        {
            "schema": "option-c0-embedding-fingerprint-v1",
            "source_identity_sha256": "1" * 64,
            "embedding_identity_sha256": "2" * 64,
            "model_id": "model",
            "model_revision": "revision",
            "dataset_revision": "dataset",
            "embedding_implementation_sha256": "3" * 64,
            "tokenization_config_sha256": "4" * 64,
            "max_length": 256,
            "output_dtype": "float32",
            "device": "cuda",
            "fixed_batch_size": 3,
            "identity_variant": "test",
        }
    )


def test_embedding_cache_round_trip_and_payload_verification(tmp_path):
    path = tmp_path / "cache.sqlite3"
    fingerprint = _fingerprint()
    vector = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)

    with OptionC0EmbeddingCache(path) as cache:
        cache.register_fingerprint(fingerprint)
        cache.put(
            stable_key="stable",
            code_sha256="a" * 64,
            fingerprint_sha256=fingerprint.sha256,
            vector=vector,
        )
        cache.commit()
        loaded = cache.get(
            stable_key="stable",
            code_sha256="a" * 64,
            fingerprint_sha256=fingerprint.sha256,
        )
        assert loaded is not None
        assert np.array_equal(loaded, vector)
        assert cache.count(fingerprint.sha256) == 1

        cache.connection.execute(
            "UPDATE embeddings SET vector = ? WHERE stable_key = ?",
            (b"corrupt", "stable"),
        )
        cache.commit()
        assert (
            cache.get(
                stable_key="stable",
                code_sha256="a" * 64,
                fingerprint_sha256=fingerprint.sha256,
            )
            is None
        )


def test_embedding_fingerprint_changes_with_execution_identity():
    lineage = {
        "source_identity_sha256": "1" * 64,
        "embedding_identity_sha256": "2" * 64,
    }
    identity = {
        "model": {"repo_id": "model", "revision": "revision"},
        "dataset": {"revision": "dataset"},
        "embedding_implementation_sha256": "3" * 64,
        "tokenization_config_sha256": "4" * 64,
        "identity_variant": "gpu-fixed-batch10-amendment-v1",
    }

    cuda_10 = embedding_fingerprint(
        lineage=lineage,
        embedding_identity=identity,
        device="cuda",
        batch_size=10,
    )
    cuda_8 = embedding_fingerprint(
        lineage=lineage,
        embedding_identity=identity,
        device="cuda",
        batch_size=8,
    )
    cpu_10 = embedding_fingerprint(
        lineage=lineage,
        embedding_identity=identity,
        device="cpu",
        batch_size=10,
    )

    assert cuda_10.sha256 != cuda_8.sha256
    assert cuda_10.sha256 != cpu_10.sha256


def test_partition_cache_commits_batches_and_reuses_exact_vectors(tmp_path):
    records = [_record(index) for index in range(5)]
    fingerprint = _fingerprint()
    calls: list[list[str]] = []
    stream = io.StringIO()
    reporter = ProgressReporter(stream)

    def embed_batch(codes: list[str]) -> np.ndarray:
        calls.append(list(codes))
        return np.asarray(
            [[float(code), float(code) + 0.5] for code in codes],
            dtype=np.float32,
        )

    with OptionC0EmbeddingCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_fingerprint(fingerprint)
        first = records[0]
        cache.put(
            stable_key=first.stable_key,
            code_sha256=first.code_sha256,
            fingerprint_sha256=fingerprint.sha256,
            vector=np.asarray([0.0, 0.5], dtype=np.float32),
        )
        cache.commit()

        matrix, stats = embed_partition_with_cache(
            records,
            partition="iteration",
            cache=cache,
            fingerprint=fingerprint,
            embed_batch=embed_batch,
            batch_size=3,
            reporter=reporter,
        )

        assert calls == [["1", "2", "3"], ["4", "4", "4"]]
        assert matrix.tolist() == [
            [0.0, 0.5],
            [1.0, 1.5],
            [2.0, 2.5],
            [3.0, 3.5],
            [4.0, 4.5],
        ]
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 4
        assert stats["vectors_generated"] == 4
        assert stats["padded_rows"] == 2
        assert cache.count(fingerprint.sha256) == 5

        calls.clear()
        second, second_stats = embed_partition_with_cache(
            records,
            partition="iteration",
            cache=cache,
            fingerprint=fingerprint,
            embed_batch=embed_batch,
            batch_size=3,
            reporter=reporter,
        )

    assert calls == []
    assert np.array_equal(second, matrix)
    assert second_stats["cache_hits"] == 5
    assert second_stats["cache_misses"] == 0
    output = stream.getvalue()
    assert "cache iteration: 1 hit/4 miss" in output
    assert "5/5 (100.0%)" in output
    assert "eta=" in output

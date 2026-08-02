from __future__ import annotations

import hashlib
import io

import numpy as np

from relate.experiments.option_b_real_code import FunctionRecord
from relate.experiments.option_c0_canonical_recovery_entrypoint import (
    embed_partition_in_canonical_batches,
)
from relate.experiments.option_c0_embedding_cache import (
    EmbeddingFingerprint,
    OptionC0EmbeddingCache,
)
from relate.experiments.option_c0_recovery_entrypoint import ProgressReporter


def _record(index: int) -> FunctionRecord:
    code = str(index)
    return FunctionRecord(
        split="train",
        repository="repo",
        path=f"module-{index}.py",
        function_id=f"function-{index}",
        code=code,
        code_sha256=hashlib.sha256(code.encode()).hexdigest(),
        normalized_ast_sha256=hashlib.sha256(f"ast-{index}".encode()).hexdigest(),
        token_count=32,
        cyclomatic_complexity=1.0,
        max_control_depth=0.0,
        distinct_call_sites=0.0,
    )


def _fingerprint() -> EmbeddingFingerprint:
    return EmbeddingFingerprint.from_payload(
        {
            "schema": "option-c0-embedding-fingerprint-v1",
            "identity": "canonical-batch-test",
        }
    )


def test_partial_cache_recomputes_original_batches_and_verifies_hits(tmp_path):
    records = [_record(index) for index in range(5)]
    fingerprint = _fingerprint()
    calls: list[list[str]] = []

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

        matrix, stats = embed_partition_in_canonical_batches(
            records,
            partition="iteration",
            cache=cache,
            fingerprint=fingerprint,
            embed_batch=embed_batch,
            batch_size=3,
            reporter=ProgressReporter(io.StringIO()),
        )

    assert calls == [["0", "1", "2"], ["3", "4", "4"]]
    assert matrix.tolist() == [
        [0.0, 0.5],
        [1.0, 1.5],
        [2.0, 2.5],
        [3.0, 3.5],
        [4.0, 4.5],
    ]
    assert stats["cache_hits"] == 1
    assert stats["cache_misses"] == 4
    assert stats["canonical_rows_recomputed"] == 5
    assert stats["cached_vectors_reverified"] == 1
    assert stats["padded_rows"] == 1


def test_complete_cache_performs_no_model_calls(tmp_path):
    records = [_record(index) for index in range(4)]
    fingerprint = _fingerprint()
    calls: list[list[str]] = []

    def embed_batch(codes: list[str]) -> np.ndarray:
        calls.append(list(codes))
        raise AssertionError("complete cache must not invoke the embedding backend")

    with OptionC0EmbeddingCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_fingerprint(fingerprint)
        for record in records:
            value = float(record.code)
            cache.put(
                stable_key=record.stable_key,
                code_sha256=record.code_sha256,
                fingerprint_sha256=fingerprint.sha256,
                vector=np.asarray([value, value + 0.5], dtype=np.float32),
            )
        cache.commit()

        matrix, stats = embed_partition_in_canonical_batches(
            records,
            partition="fit_model",
            cache=cache,
            fingerprint=fingerprint,
            embed_batch=embed_batch,
            batch_size=3,
            reporter=ProgressReporter(io.StringIO()),
        )

    assert calls == []
    assert matrix.shape == (4, 2)
    assert stats["cache_hits"] == 4
    assert stats["cache_misses"] == 0
    assert stats["canonical_rows_recomputed"] == 0

"""Preserve frozen batch composition while resuming Option C0 embeddings."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from relate.experiments import option_c0_recovery_entrypoint as recovery
from relate.experiments.option_b_real_code import FunctionRecord, array_hash
from relate.experiments.option_c0_embedding_cache import (
    EmbeddingFingerprint,
    OptionC0EmbeddingCache,
)


def embed_partition_in_canonical_batches(
    records: Sequence[FunctionRecord],
    *,
    partition: str,
    cache: OptionC0EmbeddingCache,
    fingerprint: EmbeddingFingerprint,
    embed_batch: Callable[[list[str]], np.ndarray],
    batch_size: int,
    reporter: recovery.ProgressReporter,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Resume only at frozen original batch boundaries and row positions."""

    if not records:
        raise ValueError(f"Option C0 partition is empty: {partition}")
    if batch_size <= 0:
        raise ValueError("embedding batch size must be positive")

    started = time.perf_counter()
    vectors: list[np.ndarray | None] = [None] * len(records)
    hits = 0
    for index, record in enumerate(records):
        if hashlib.sha256(record.code.encode()).hexdigest() != record.code_sha256:
            raise ValueError(f"source code hash mismatch in {partition} row {index}")
        vector = cache.get(
            stable_key=record.stable_key,
            code_sha256=record.code_sha256,
            fingerprint_sha256=fingerprint.sha256,
        )
        if vector is not None:
            vectors[index] = vector
            hits += 1

    misses = len(records) - hits
    reporter.message(
        f"cache {partition}: {hits:,} hit/{misses:,} miss "
        f"| total={len(records):,} | fingerprint={fingerprint.sha256[:12]}"
    )

    generated = 0
    canonical_rows_recomputed = 0
    cached_vectors_reverified = 0
    padded_rows = 0
    progress_stride = max(batch_size, 250)
    next_progress = progress_stride

    for start in range(0, len(records), batch_size):
        indices = list(range(start, min(start + batch_size, len(records))))
        missing_indices = [index for index in indices if vectors[index] is None]
        if not missing_indices:
            continue

        real_count = len(indices)
        codes = [records[index].code for index in indices]
        if real_count < batch_size:
            padded_rows += batch_size - real_count
            codes.extend([codes[-1]] * (batch_size - real_count))
        matrix = np.asarray(embed_batch(codes), dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != batch_size:
            raise ValueError("embedding backend returned an invalid fixed-batch matrix")
        if not np.isfinite(matrix).all():
            raise ValueError("embedding backend returned non-finite values")

        canonical_rows_recomputed += real_count
        missing_set = set(missing_indices)
        for offset, record_index in enumerate(indices):
            computed = np.ascontiguousarray(matrix[offset], dtype=np.float32)
            cached = vectors[record_index]
            if record_index not in missing_set:
                assert cached is not None
                if not np.array_equal(cached, computed):
                    raise ValueError(
                        f"cached embedding disagrees with canonical recomputation: "
                        f"{partition} row {record_index}"
                    )
                cached_vectors_reverified += 1
                continue

            record = records[record_index]
            cache.put(
                stable_key=record.stable_key,
                code_sha256=record.code_sha256,
                fingerprint_sha256=fingerprint.sha256,
                vector=computed,
            )
            vectors[record_index] = computed
            generated += 1
        cache.commit()

        if generated >= next_progress or generated == misses:
            reporter.rows(
                partition,
                hits + generated,
                len(records),
                started=started,
                cache_hits=hits,
                cache_misses=misses,
            )
            while next_progress <= generated:
                next_progress += progress_stride

    if misses == 0:
        reporter.rows(
            partition,
            len(records),
            len(records),
            started=started,
            cache_hits=hits,
            cache_misses=0,
        )

    if any(vector is None for vector in vectors):
        raise RuntimeError(f"Option C0 cache assembly is incomplete: {partition}")
    assembled = np.stack([vector for vector in vectors if vector is not None]).astype(
        np.float32,
        copy=False,
    )
    if assembled.shape[0] != len(records) or not np.isfinite(assembled).all():
        raise ValueError(f"assembled Option C0 embedding matrix is invalid: {partition}")

    return assembled, {
        "rows": len(records),
        "cache_hits": hits,
        "cache_misses": misses,
        "vectors_generated": generated,
        "canonical_rows_recomputed": canonical_rows_recomputed,
        "cached_vectors_reverified": cached_vectors_reverified,
        "padded_rows": padded_rows,
        "dimensions": int(assembled.shape[1]),
        "dtype": str(assembled.dtype),
        "array_sha256": array_hash(assembled),
        "seconds": time.perf_counter() - started,
        "recovery_batch_policy": "preserve original partition order and fixed batch boundaries",
    }


def main() -> None:
    original = recovery.embed_partition_with_cache
    recovery.embed_partition_with_cache = embed_partition_in_canonical_batches
    try:
        recovery.main()
    finally:
        recovery.embed_partition_with_cache = original


if __name__ == "__main__":
    main()

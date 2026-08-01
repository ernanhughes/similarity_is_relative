from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from relate.experiments.option_b_cache import OptionBCache
from relate.experiments.option_b_embeddings_hardened import (
    CHUNK_SCHEMA,
    extract_split,
    extraction_fingerprint_payload,
    extraction_fingerprint_sha256,
)


def _identity() -> dict[str, object]:
    return {
        "identity_id": "option-b-embedding-identity-v2",
        "model": {
            "repo_id": "microsoft/codebert-base",
            "revision": "model-revision",
        },
        "embedding_implementation_sha256": "implementation",
        "tokenization_config_sha256": "tokenization",
    }


def _fingerprint(
    *,
    manifest: str = "manifest",
    batch_size: int = 2,
    device: str = "cpu",
) -> dict[str, object]:
    return extraction_fingerprint_payload(
        identity_file_sha256="identity-file",
        identity=_identity(),
        split="test",
        split_manifest_sha256=manifest,
        stable_keys=("one", "two", "three"),
        source_sha256=("source-one", "source-two", "source-three"),
        batch_size=batch_size,
        runtime={"device": device, "torch": "test"},
    )


def _run(
    tmp_path: Path,
    calls: list[list[str]],
    *,
    cache_mode: str = "read-write",
    fingerprint: dict[str, object] | None = None,
):
    def embed(batch: list[str]) -> np.ndarray:
        calls.append(batch)
        return np.asarray(
            [[float(len(value)), 1.0] for value in batch],
            dtype=np.float32,
        )

    database = tmp_path / "cache.sqlite3"
    with OptionBCache(database, cache_mode) as cache:
        return extract_split(
            "test",
            ("a", "bb", "ccc"),
            tmp_path,
            embed,
            batch_size=2,
            stable_keys=("one", "two", "three"),
            source_sha256=tuple(
                hashlib.sha256(code.encode()).hexdigest()
                for code in ("a", "bb", "ccc")
            ),
            fingerprint_payload=fingerprint or _fingerprint(),
            cache=cache,
            cache_mode=cache_mode,
        )


def test_fingerprint_changes_for_material_inputs() -> None:
    baseline = extraction_fingerprint_sha256(_fingerprint())

    assert extraction_fingerprint_sha256(_fingerprint(manifest="other")) != baseline
    assert extraction_fingerprint_sha256(_fingerprint(batch_size=1)) != baseline
    assert extraction_fingerprint_sha256(_fingerprint(device="cuda")) != baseline


def test_only_verified_fingerprinted_chunks_are_resumed(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    first = _run(tmp_path, calls)

    assert len(calls) == 2
    assert first["verified_chunks_resumed"] == 0
    assert first["chunks_recomputed"] == 2

    calls.clear()
    second = _run(tmp_path, calls)

    assert calls == []
    assert second["verified_chunks_resumed"] == 2
    assert second["chunks_recomputed"] == 0
    assert second["array_sha256"] == first["array_sha256"]

    fingerprint = second["extraction_fingerprint_sha256"]
    sidecar = next((tmp_path / "chunks" / fingerprint / "test").glob("*.json"))
    value = json.loads(sidecar.read_text(encoding="utf-8"))
    assert value["schema"] == CHUNK_SCHEMA
    assert value["stable_key_sequence_sha256"]
    assert value["source_sequence_sha256"]
    assert value["file_sha256"]
    assert value["array_sha256"]


def test_tampered_sidecar_is_not_reused(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    first = _run(tmp_path, calls)
    fingerprint = first["extraction_fingerprint_sha256"]
    sidecar = next((tmp_path / "chunks" / fingerprint / "test").glob("*.json"))
    value = json.loads(sidecar.read_text(encoding="utf-8"))
    value["rows"] = 999
    sidecar.write_text(json.dumps(value), encoding="utf-8")

    calls.clear()
    result = _run(tmp_path, calls)

    assert result["verified_chunks_resumed"] == 1
    assert result["chunks_recomputed"] == 1
    assert result["chunk_rejection_reasons"]["identity-mismatch:rows"] == 1


def test_refresh_and_off_bypass_valid_chunks_and_cache_reads(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    _run(tmp_path, calls)

    calls.clear()
    refreshed = _run(tmp_path, calls, cache_mode="refresh")
    assert len(calls) == 2
    assert refreshed["verified_chunks_resumed"] == 0
    assert refreshed["sqlite_cache_hits"] == 0
    assert refreshed["sqlite_cache_misses"] == 3

    calls.clear()
    disabled = _run(tmp_path, calls, cache_mode="off")
    assert len(calls) == 2
    assert disabled["verified_chunks_resumed"] == 0
    assert disabled["sqlite_cache_hits"] == 0
    assert disabled["sqlite_cache_misses"] == 3


def test_legacy_unfingerprinted_chunk_is_ignored(tmp_path: Path) -> None:
    legacy = tmp_path / "chunks" / "test"
    legacy.mkdir(parents=True)
    np.save(legacy / "000000-000002.npy", np.ones((2, 2), dtype=np.float32))

    calls: list[list[str]] = []
    result = _run(tmp_path, calls)

    assert len(calls) == 2
    assert result["verified_chunks_resumed"] == 0
    assert result["chunks_recomputed"] == 2


def test_corrupt_v2_cache_row_is_recomputed(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    first = _run(tmp_path, calls)
    fingerprint = first["extraction_fingerprint_sha256"]

    import shutil
    import sqlite3

    shutil.rmtree(tmp_path / "chunks")
    database = tmp_path / "cache.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            UPDATE embeddings_v2
            SET embedding = ?
            WHERE stable_key = ?
              AND extraction_fingerprint_sha256 = ?
            """,
            (b"corrupt", "one", fingerprint),
        )
        connection.commit()

    calls.clear()
    result = _run(tmp_path, calls)

    assert calls == [["a"]]
    assert result["sqlite_cache_hits"] == 2
    assert result["sqlite_cache_misses"] == 1

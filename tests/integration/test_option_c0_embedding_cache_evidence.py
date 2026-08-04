"""Integration tests: OptionC0EmbeddingCache uses evidence SQLite helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from relate.experiments.option_c0_embedding_cache import (
    EmbeddingFingerprint,
    OptionC0EmbeddingCache,
)


def _make_fingerprint(schema_version: str = "v1") -> EmbeddingFingerprint:
    return EmbeddingFingerprint.from_payload(
        {
            "schema": "option-c0-embedding-fingerprint-v1",
            "model": "test-model",
            "schema_version": schema_version,
        }
    )


class TestOptionC0EmbeddingCacheWalPragmas:
    def test_new_database_has_wal_pragmas(self, tmp_path: Path) -> None:
        with OptionC0EmbeddingCache(tmp_path / "embeddings.sqlite3") as cache:
            conn = cache.connection
            journal = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            synchronous = int(conn.execute("PRAGMA synchronous").fetchone()[0])
            foreign_keys = int(conn.execute("PRAGMA foreign_keys").fetchone()[0])
        assert journal == "wal"
        assert synchronous == 2  # FULL
        assert foreign_keys == 1


class TestOptionC0EmbeddingCacheSchema:
    def test_schema_tables_present(self, tmp_path: Path) -> None:
        expected_tables = {"fingerprints", "embeddings"}
        with OptionC0EmbeddingCache(tmp_path / "embeddings.sqlite3") as cache:
            rows = cache.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        actual = {row[0] for row in rows}
        assert expected_tables.issubset(actual)


class TestOptionC0EmbeddingCacheRoundtrip:
    def test_put_and_get_roundtrip(self, tmp_path: Path) -> None:
        fp = _make_fingerprint()
        vector = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        stable_key = "test_repo::test_fn"
        code_sha256 = "a" * 64

        with OptionC0EmbeddingCache(tmp_path / "embeddings.sqlite3") as cache:
            cache.register_fingerprint(fp)
            cache.put(
                stable_key=stable_key,
                code_sha256=code_sha256,
                fingerprint_sha256=fp.sha256,
                vector=vector,
            )
            cache.commit()
            result = cache.get(
                stable_key=stable_key,
                code_sha256=code_sha256,
                fingerprint_sha256=fp.sha256,
            )

        assert result is not None
        np.testing.assert_array_equal(result, vector)

    def test_get_returns_none_for_unknown_key(self, tmp_path: Path) -> None:
        fp = _make_fingerprint()
        with OptionC0EmbeddingCache(tmp_path / "embeddings.sqlite3") as cache:
            cache.register_fingerprint(fp)
            result = cache.get(
                stable_key="unknown::fn",
                code_sha256="b" * 64,
                fingerprint_sha256=fp.sha256,
            )
        assert result is None

    def test_count_returns_correct_value(self, tmp_path: Path) -> None:
        fp = _make_fingerprint()
        vector = np.array([1.0, 2.0], dtype=np.float32)
        with OptionC0EmbeddingCache(tmp_path / "embeddings.sqlite3") as cache:
            cache.register_fingerprint(fp)
            assert cache.count(fp.sha256) == 0
            cache.put(
                stable_key="repo::fn",
                code_sha256="c" * 64,
                fingerprint_sha256=fp.sha256,
                vector=vector,
            )
            cache.commit()
            assert cache.count(fp.sha256) == 1

    def test_foreign_key_enforced(self, tmp_path: Path) -> None:
        """Inserting an embedding with an unregistered fingerprint must fail."""
        import sqlite3

        fp = _make_fingerprint()
        vector = np.array([1.0], dtype=np.float32)
        with OptionC0EmbeddingCache(tmp_path / "embeddings.sqlite3") as cache:
            # Do NOT register fingerprint first.
            with pytest.raises(sqlite3.IntegrityError):
                cache.put(
                    stable_key="repo::fn",
                    code_sha256="d" * 64,
                    fingerprint_sha256=fp.sha256,
                    vector=vector,
                )
                cache.commit()

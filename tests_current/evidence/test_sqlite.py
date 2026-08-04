"""Tests for relate.evidence.sqlite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from relate.evidence.sqlite import bind_cache_identity, enforce_wal_pragmas, verify_wal_pragmas


def _make_identity_table(conn: sqlite3.Connection, table: str = "cache_identity") -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _make_data_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_rows (
            id INTEGER PRIMARY KEY,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()


class TestEnforceWalPragmas:
    def test_pragmas_set(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        try:
            enforce_wal_pragmas(conn)
            journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
            synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
            foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert str(journal).lower() == "wal"
            assert int(synchronous) == 2  # FULL
            assert int(foreign_keys) == 1
        finally:
            conn.close()


class TestVerifyWalPragmas:
    def test_returns_dict_after_enforce(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        try:
            enforce_wal_pragmas(conn)
            result = verify_wal_pragmas(conn)
            assert result["journal_mode"] == "wal"
            assert result["synchronous"] == 2
            assert result["foreign_keys"] == 1
            assert result["synchronous_full"] is True
        finally:
            conn.close()

    def test_raises_without_enforce(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "fresh.sqlite3")
        try:
            # Default SQLite connection does not have WAL or foreign_keys.
            with pytest.raises(ValueError, match="not enforced"):
                verify_wal_pragmas(conn)
        finally:
            conn.close()


class TestBindCacheIdentity:
    def test_fresh_cache_inserts_identity(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        _make_identity_table(conn)
        expected = {"schema": "test-v1", "version": "1"}
        bind_cache_identity(conn, "cache_identity", expected, lambda: False)
        rows = dict(conn.execute("SELECT key, value FROM cache_identity"))
        assert rows == expected

    def test_existing_matching_identity_accepted(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        _make_identity_table(conn)
        expected = {"schema": "test-v1", "version": "1"}
        bind_cache_identity(conn, "cache_identity", expected, lambda: False)
        # Call again — should not raise.
        bind_cache_identity(conn, "cache_identity", expected, lambda: False)

    def test_key_set_mismatch_raises(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        _make_identity_table(conn)
        first = {"schema": "test-v1", "version": "1"}
        bind_cache_identity(conn, "cache_identity", first, lambda: False)
        different_keys = {"schema": "test-v1", "extra": "unexpected"}
        with pytest.raises(ValueError, match="mismatch"):
            bind_cache_identity(conn, "cache_identity", different_keys, lambda: False)

    def test_value_mismatch_raises(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        _make_identity_table(conn)
        first = {"schema": "test-v1", "version": "1"}
        bind_cache_identity(conn, "cache_identity", first, lambda: False)
        wrong_value = {"schema": "test-v1", "version": "2"}
        with pytest.raises(ValueError, match="mismatch"):
            bind_cache_identity(conn, "cache_identity", wrong_value, lambda: False)

    def test_data_without_identity_raises(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        _make_identity_table(conn)
        _make_data_table(conn)
        conn.execute("INSERT INTO data_rows(payload) VALUES ('row')")
        conn.commit()
        expected = {"schema": "test-v1"}
        with pytest.raises(ValueError, match="without identity"):
            bind_cache_identity(conn, "cache_identity", expected, lambda: True)

    def test_empty_identity_and_no_data_is_allowed(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.sqlite3")
        _make_identity_table(conn)
        bind_cache_identity(conn, "cache_identity", {}, lambda: False)
        rows = list(conn.execute("SELECT key, value FROM cache_identity"))
        assert rows == []

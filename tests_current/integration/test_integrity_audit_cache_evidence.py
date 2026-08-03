"""Integration tests: IntegrityAuditCache uses evidence SQLite helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from relate.experiments.option_c0_d1_integrity_audit import IntegrityAuditCache


class TestIntegrityAuditCacheWalPragmas:
    def test_new_database_has_wal_pragmas(self, tmp_path: Path) -> None:
        with IntegrityAuditCache(tmp_path / "audit.sqlite3") as cache:
            conn = cache.connection
            journal = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            synchronous = int(conn.execute("PRAGMA synchronous").fetchone()[0])
            foreign_keys = int(conn.execute("PRAGMA foreign_keys").fetchone()[0])
        assert journal == "wal"
        assert synchronous == 2  # FULL
        assert foreign_keys == 1

    def test_verify_pragmas_returns_dict(self, tmp_path: Path) -> None:
        with IntegrityAuditCache(tmp_path / "audit.sqlite3") as cache:
            result = cache.verify_pragmas()
        assert result["journal_mode"] == "wal"
        assert result["synchronous"] == 2
        assert result["foreign_keys"] == 1
        assert result["synchronous_full"] is True

    def test_verify_pragmas_raises_value_error_on_bad_connection(self, tmp_path: Path) -> None:
        """verify_pragmas must raise ValueError (not RuntimeError)."""
        cache = IntegrityAuditCache.__new__(IntegrityAuditCache)
        cache.path = tmp_path / "bad.sqlite3"
        (tmp_path / "bad.sqlite3").touch()
        cache.connection = sqlite3.connect(tmp_path / "bad.sqlite3")
        try:
            with pytest.raises(ValueError, match="integrity cache.*not enforced"):
                cache.verify_pragmas()
        finally:
            cache.connection.close()

    def test_verify_pragmas_preserves_original_message(self, tmp_path: Path) -> None:
        cache = IntegrityAuditCache.__new__(IntegrityAuditCache)
        cache.path = tmp_path / "bad.sqlite3"
        (tmp_path / "bad.sqlite3").touch()
        cache.connection = sqlite3.connect(tmp_path / "bad.sqlite3")
        try:
            with pytest.raises(ValueError, match="integrity cache SQLite pragmas are not enforced"):
                cache.verify_pragmas()
        finally:
            cache.connection.close()


class TestIntegrityAuditCacheSchema:
    def test_schema_tables_present(self, tmp_path: Path) -> None:
        expected_tables = {
            "contexts",
            "visible_rows",
            "near_pairs",
            "candidate_pairs",
            "phase_checkpoints",
            "phases",
        }
        with IntegrityAuditCache(tmp_path / "audit.sqlite3") as cache:
            rows = cache.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        actual = {row[0] for row in rows}
        assert expected_tables.issubset(actual)

    def test_schema_unchanged_after_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "audit.sqlite3"
        with IntegrityAuditCache(db) as cache:
            before = set(
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            )
        with IntegrityAuditCache(db) as cache:
            after = set(
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            )
        assert before == after

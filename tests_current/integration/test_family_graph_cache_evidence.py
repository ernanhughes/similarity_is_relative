"""Integration tests: FamilyGraphCache uses evidence SQLite helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from relate.experiments.option_c0_family_connected_protocol import (
    FamilyGraphCache,
    FamilyGraphCacheIdentity,
)


def _make_identity(override: dict[str, str] | None = None) -> FamilyGraphCacheIdentity:
    """Return a minimal FamilyGraphCacheIdentity with all fields set."""
    base = dict(
        family_protocol_sha256="a" * 64,
        allocation_manifest_sha256="b" * 64,
        allocation_context_sha256="c" * 64,
        d1_audit_result_sha256="d" * 64,
        d1_1_classification_sha256="e" * 64,
        cache_schema_version="test-schema-v0",
        family_runner_source_identity="f" * 64,
    )
    if override:
        base.update(override)
    return FamilyGraphCacheIdentity(**base)


class TestFamilyGraphCacheWalPragmas:
    def test_new_database_has_wal_pragmas(self, tmp_path: Path) -> None:
        identity = _make_identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            conn = cache.connection
            journal = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            synchronous = int(conn.execute("PRAGMA synchronous").fetchone()[0])
            foreign_keys = int(conn.execute("PRAGMA foreign_keys").fetchone()[0])
        assert journal == "wal"
        assert synchronous == 2  # FULL
        assert foreign_keys == 1

    def test_verify_pragmas_raises_runtime_error_on_bad_connection(self, tmp_path: Path) -> None:
        """_verify_pragmas must raise RuntimeError (not ValueError)."""
        identity = _make_identity()
        cache = FamilyGraphCache.__new__(FamilyGraphCache)
        cache.path = tmp_path / "bad.sqlite3"
        cache.identity = identity
        (tmp_path / "bad.sqlite3").touch()
        cache.connection = sqlite3.connect(tmp_path / "bad.sqlite3")
        try:
            with pytest.raises(RuntimeError, match="pragmas are not enforced"):
                cache._verify_pragmas()
        finally:
            cache.connection.close()


class TestFamilyGraphCacheIdentityBinding:
    def test_fresh_cache_inserts_identity(self, tmp_path: Path) -> None:
        identity = _make_identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            rows = dict(cache.connection.execute("SELECT key, value FROM cache_identity"))
        assert rows == identity.as_mapping()

    def test_identical_identity_accepted_on_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _make_identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        # Reopen — should not raise.
        with FamilyGraphCache(db, identity=identity):
            pass

    def test_mismatched_identity_rejected(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _make_identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        different = _make_identity({"allocation_manifest_sha256": "0" * 64})
        with pytest.raises(ValueError):
            FamilyGraphCache(db, identity=different).close()

    def test_mismatched_key_set_rejected(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _make_identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        # Modify the identity so that it has a different set of keys.
        truncated = FamilyGraphCacheIdentity(
            family_protocol_sha256="a" * 64,
            allocation_manifest_sha256="b" * 64,
            allocation_context_sha256="c" * 64,
            d1_audit_result_sha256="d" * 64,
            d1_1_classification_sha256="e" * 64,
            cache_schema_version="test-schema-v0",
            family_runner_source_identity="f" * 64,
        )
        # Inject a bogus extra key directly to simulate key-set mismatch.
        conn = sqlite3.connect(db)
        try:
            conn.execute("INSERT INTO cache_identity(key, value) VALUES ('extra_key', 'x')")
            conn.commit()
        finally:
            conn.close()
        with pytest.raises(ValueError):
            FamilyGraphCache(db, identity=truncated).close()


class TestFamilyGraphCacheSchema:
    def test_schema_tables_present(self, tmp_path: Path) -> None:
        identity = _make_identity()
        expected_tables = {
            "cache_identity",
            "allocation_repositories",
            "repository_metadata_snapshots",
            "source_records",
            "typed_evidence_edges",
            "evidence_candidates",
            "manual_review_dispositions",
            "component_memberships",
            "phase_commitments",
        }
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            rows = cache.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        actual = {row[0] for row in rows}
        assert expected_tables.issubset(actual)

    def test_schema_unchanged_after_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _make_identity()
        with FamilyGraphCache(db, identity=identity) as cache:
            before = set(
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            )
        with FamilyGraphCache(db, identity=identity) as cache:
            after = set(
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            )
        assert before == after

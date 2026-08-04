"""Schema tests for relate.family.store.FamilyGraphCache.

Covers exact table set, key columns, primary/unique/foreign keys, WAL pragma
enforcement, and schema version stability.
"""

from __future__ import annotations

from pathlib import Path

from relate.family.store import CACHE_SCHEMA_ID, FamilyGraphCache, make_cache_identity

EXPECTED_TABLES = {
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


def _identity() -> object:
    return make_cache_identity(
        family_protocol_sha256="a" * 64,
        allocation_manifest_sha256="b" * 64,
        allocation_context_sha256="c" * 64,
        d1_audit_result_sha256="d" * 64,
        d1_1_classification_sha256="e" * 64,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity="f" * 64,
    )


class TestTableSet:
    def test_exact_table_set(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            rows = cache.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        actual = {row[0] for row in rows}
        assert actual == EXPECTED_TABLES

    def test_schema_stable_across_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity) as cache:
            before = {
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        with FamilyGraphCache(db, identity=identity) as cache:
            after = {
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert before == after


class TestColumnsAndConstraints:
    def _columns(self, cache: FamilyGraphCache, table: str) -> dict[str, str]:
        rows = cache.connection.execute(f"PRAGMA table_info({table})").fetchall()
        return {row[1]: row[2] for row in rows}

    def test_cache_identity_columns(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            columns = self._columns(cache, "cache_identity")
        assert columns == {"key": "TEXT", "value": "TEXT"}

    def test_allocation_repositories_primary_key(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            rows = cache.connection.execute("PRAGMA table_info(allocation_repositories)").fetchall()
        pk_columns = [row[1] for row in rows if row[5]]
        assert pk_columns == ["repository"]

    def test_manual_review_dispositions_unique_candidate(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            indexes = cache.connection.execute(
                "PRAGMA index_list(manual_review_dispositions)"
            ).fetchall()
        assert any(index[2] for index in indexes)  # at least one UNIQUE index

    def test_component_memberships_composite_primary_key(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            rows = cache.connection.execute("PRAGMA table_info(component_memberships)").fetchall()
        pk_columns = {row[1] for row in rows if row[5]}
        assert pk_columns == {"component_id", "repository"}

    def test_typed_evidence_edges_foreign_keys(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            fks = cache.connection.execute(
                "PRAGMA foreign_key_list(typed_evidence_edges)"
            ).fetchall()
        referenced_tables = {fk[2] for fk in fks}
        assert referenced_tables == {
            "evidence_candidates",
            "manual_review_dispositions",
            "allocation_repositories",
        }

    def test_phase_commitments_columns(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            columns = self._columns(cache, "phase_commitments")
        assert set(columns) == {"phase", "status", "commitment_sha256", "metadata_json"}


class TestPragmas:
    def test_wal_journal_mode(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            journal = str(cache.connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        assert journal == "wal"

    def test_synchronous_full(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            synchronous = int(cache.connection.execute("PRAGMA synchronous").fetchone()[0])
        assert synchronous == 2

    def test_foreign_keys_enforced(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            foreign_keys = int(cache.connection.execute("PRAGMA foreign_keys").fetchone()[0])
        assert foreign_keys == 1


class TestSchemaVersionConstant:
    def test_cache_schema_id_value(self) -> None:
        assert CACHE_SCHEMA_ID == "option-c0-family-graph-cache-v1"

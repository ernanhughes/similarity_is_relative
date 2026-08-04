"""Compatibility tests: relate.family.store vs. the historical facade.

Verifies that FamilyGraphCache, FamilyGraphCacheIdentity and CACHE_SCHEMA_ID
resolve to the same objects through both import paths, and that
representative operations produce identical schema, stored JSON, retrieved
domain records, exceptions and protocol identity through either path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
import relate.family.store as store
from relate.family.sources import make_source_record

TIMESTAMP = "2026-08-02T00:00:00+00:00"


def _identity_kwargs() -> dict[str, str]:
    return dict(
        family_protocol_sha256="a" * 64,
        allocation_manifest_sha256="b" * 64,
        allocation_context_sha256="c" * 64,
        d1_audit_result_sha256="d" * 64,
        d1_1_classification_sha256="e" * 64,
        cache_schema_version=store.CACHE_SCHEMA_ID,
        family_runner_source_identity="f" * 64,
    )


class TestObjectIdentity:
    def test_family_graph_cache_is_same_class(self) -> None:
        assert historical.FamilyGraphCache is store.FamilyGraphCache

    def test_family_graph_cache_identity_is_same_class(self) -> None:
        assert historical.FamilyGraphCacheIdentity is store.FamilyGraphCacheIdentity

    def test_cache_schema_id_is_same_value(self) -> None:
        assert historical.CACHE_SCHEMA_ID == store.CACHE_SCHEMA_ID

    def test_make_cache_identity_is_same_function(self) -> None:
        assert historical.make_cache_identity is store.make_cache_identity


class TestSchemaEquivalence:
    def test_same_table_set_through_both_paths(self, tmp_path: Path) -> None:
        identity = store.make_cache_identity(**_identity_kwargs())
        with historical.FamilyGraphCache(tmp_path / "hist.sqlite3", identity=identity) as cache:
            hist_tables = {
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        with store.FamilyGraphCache(tmp_path / "clean.sqlite3", identity=identity) as cache:
            clean_tables = {
                row[0]
                for row in cache.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert hist_tables == clean_tables


class TestRecordEquivalence:
    def test_same_stored_json_and_retrieved_record(self, tmp_path: Path) -> None:
        identity = store.make_cache_identity(**_identity_kwargs())
        record = make_source_record("fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP})
        with historical.FamilyGraphCache(tmp_path / "hist.sqlite3", identity=identity) as cache:
            cache.put_source_record(record)
            hist_json = cache.connection.execute(
                "SELECT record_json FROM source_records WHERE source_type = ? "
                "AND source_identity = ?",
                (record.source_type, record.source_identity),
            ).fetchone()[0]
            hist_fetched = cache.get_source_record(record.source_type, record.source_identity)
        with store.FamilyGraphCache(tmp_path / "clean.sqlite3", identity=identity) as cache:
            cache.put_source_record(record)
            clean_json = cache.connection.execute(
                "SELECT record_json FROM source_records WHERE source_type = ? "
                "AND source_identity = ?",
                (record.source_type, record.source_identity),
            ).fetchone()[0]
            clean_fetched = cache.get_source_record(record.source_type, record.source_identity)
        assert hist_json == clean_json
        assert hist_fetched == clean_fetched
        assert type(hist_fetched) is type(clean_fetched)


class TestExceptionEquivalence:
    def test_same_exception_for_mismatched_identity(self, tmp_path: Path) -> None:
        identity = store.make_cache_identity(**_identity_kwargs())
        db = tmp_path / "family.sqlite3"
        with historical.FamilyGraphCache(db, identity=identity):
            pass
        mismatched = store.make_cache_identity(
            **{**_identity_kwargs(), "family_protocol_sha256": "0" * 64}
        )
        with pytest.raises(ValueError, match="family graph cache") as hist_exc:
            historical.FamilyGraphCache(db, identity=mismatched).close()
        db2 = tmp_path / "family2.sqlite3"
        with store.FamilyGraphCache(db2, identity=identity):
            pass
        with pytest.raises(ValueError, match="family graph cache") as clean_exc:
            store.FamilyGraphCache(db2, identity=mismatched).close()
        assert type(hist_exc.value) is type(clean_exc.value)

    def test_same_exception_type_for_bad_pragmas(self, tmp_path: Path) -> None:
        import sqlite3

        identity = store.make_cache_identity(**_identity_kwargs())
        for module, name in ((historical, "hist"), (store, "clean")):
            path = tmp_path / f"{name}.sqlite3"
            path.touch()
            cache = module.FamilyGraphCache.__new__(module.FamilyGraphCache)
            cache.path = path
            cache.identity = identity
            cache.connection = sqlite3.connect(path)
            try:
                with pytest.raises(RuntimeError, match="pragmas are not enforced"):
                    cache._verify_pragmas()
            finally:
                cache.connection.close()


class TestProtocolIdentityUnaffected:
    def test_protocol_sha_unchanged_by_extraction(self) -> None:
        contract = historical.protocol_contract()
        assert (
            contract["protocol_sha256"]
            == "a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08"
        )

    def test_cache_schema_identity_fields_from_moved_class(self) -> None:
        contract = historical.protocol_contract()
        assert contract["cache_schema"]["identity_fields"] == list(
            store.FamilyGraphCacheIdentity.__annotations__
        )

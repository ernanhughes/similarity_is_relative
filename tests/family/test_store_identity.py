"""Tests for FamilyGraphCacheIdentity and make_cache_identity.

Covers exact identity mapping, empty-cache insertion, reopen acceptance,
mismatch rejection, and the explicit clean constructor vs. the historical
source-sensitive default wrapper.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.evidence.hashing import sha256_file
from relate.family.store import FamilyGraphCache, FamilyGraphCacheIdentity, make_cache_identity


def _identity(**overrides: str) -> FamilyGraphCacheIdentity:
    base = dict(
        family_protocol_sha256="a" * 64,
        allocation_manifest_sha256="b" * 64,
        allocation_context_sha256="c" * 64,
        d1_audit_result_sha256="d" * 64,
        d1_1_classification_sha256="e" * 64,
        cache_schema_version="test-schema-v0",
        family_runner_source_identity="f" * 64,
    )
    base.update(overrides)
    return make_cache_identity(**base)


class TestExplicitConstructor:
    def test_returns_frozen_dataclass_instance(self) -> None:
        identity = _identity()
        assert isinstance(identity, FamilyGraphCacheIdentity)

    def test_as_mapping_has_exact_keys_and_values(self) -> None:
        identity = _identity()
        assert identity.as_mapping() == {
            "family_protocol_sha256": "a" * 64,
            "allocation_manifest_sha256": "b" * 64,
            "allocation_context_sha256": "c" * 64,
            "d1_audit_result_sha256": "d" * 64,
            "d1_1_classification_sha256": "e" * 64,
            "cache_schema_version": "test-schema-v0",
            "family_runner_source_identity": "f" * 64,
        }

    def test_field_order_matches_annotations(self) -> None:
        assert list(FamilyGraphCacheIdentity.__annotations__) == [
            "family_protocol_sha256",
            "allocation_manifest_sha256",
            "allocation_context_sha256",
            "d1_audit_result_sha256",
            "d1_1_classification_sha256",
            "cache_schema_version",
            "family_runner_source_identity",
        ]

    def test_is_frozen(self) -> None:
        identity = _identity()
        with pytest.raises(Exception):  # noqa: B017 - dataclasses.FrozenInstanceError
            identity.family_protocol_sha256 = "0" * 64  # type: ignore[misc]


class TestCacheIdentityBinding:
    def test_fresh_cache_inserts_identity(self, tmp_path: Path) -> None:
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            rows = dict(cache.connection.execute("SELECT key, value FROM cache_identity"))
        assert rows == identity.as_mapping()

    def test_identical_identity_accepted_on_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        with FamilyGraphCache(db, identity=identity):
            pass

    @pytest.mark.parametrize(
        "field",
        [
            "family_protocol_sha256",
            "allocation_manifest_sha256",
            "allocation_context_sha256",
            "d1_audit_result_sha256",
            "d1_1_classification_sha256",
            "cache_schema_version",
            "family_runner_source_identity",
        ],
    )
    def test_changed_value_is_rejected(self, tmp_path: Path, field: str) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        changed = replace(identity, **{field: "0" * 64})
        with pytest.raises(ValueError):
            FamilyGraphCache(db, identity=changed).close()

    def test_missing_identity_key_is_rejected(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        with sqlite3.connect(db) as connection:
            connection.execute("DELETE FROM cache_identity WHERE key = 'd1_audit_result_sha256'")
            connection.commit()
        with pytest.raises(ValueError, match="identity key set"):
            FamilyGraphCache(db, identity=identity)

    def test_extra_identity_key_is_rejected(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        with sqlite3.connect(db) as connection:
            connection.execute("INSERT INTO cache_identity(key, value) VALUES ('extra_key', 'x')")
            connection.commit()
        with pytest.raises(ValueError, match="identity key set"):
            FamilyGraphCache(db, identity=identity)

    def test_data_without_identity_is_rejected(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.connection.execute(
                "INSERT INTO source_records(source_type, source_identity, record_json, "
                "record_sha256, status) VALUES ('fixture', 'x', '{}', 'y', 'COMPLETE')"
            )
            cache.connection.commit()
            cache.connection.execute("DELETE FROM cache_identity")
            cache.connection.commit()
        with pytest.raises(ValueError, match="data without identity"):
            FamilyGraphCache(db, identity=identity)

    def test_empty_cache_identity_is_allowed_and_recorded(self, tmp_path: Path) -> None:
        # An identity with real values still binds cleanly against a brand-new,
        # data-free database file (the "empty cache" case).
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            count = cache.connection.execute(
                "SELECT COUNT(*) FROM allocation_repositories"
            ).fetchone()[0]
        assert count == 0


class TestHistoricalDefaultWrapper:
    """default_cache_identity remains in the historical module and binds
    family_runner_source_identity to sha256_file(__file__) of that module,
    not of relate.family.store."""

    def test_default_identity_uses_historical_module_source_hash(self) -> None:
        identity = historical.default_cache_identity("a" * 64)
        historical_path = Path(historical.__file__)
        assert identity.family_runner_source_identity == sha256_file(historical_path)

    def test_default_identity_does_not_use_store_module_source_hash(self) -> None:
        import relate.family.store as store_module

        identity = historical.default_cache_identity("a" * 64)
        store_path = Path(store_module.__file__)
        assert identity.family_runner_source_identity != sha256_file(store_path)

    def test_default_identity_binds_frozen_protocol_constants(self) -> None:
        identity = historical.default_cache_identity("a" * 64)
        assert identity.allocation_manifest_sha256 == historical.ALLOCATION_MANIFEST_SHA256
        assert identity.allocation_context_sha256 == historical.ALLOCATION_CONTEXT_SHA256
        assert identity.d1_audit_result_sha256 == historical.D1_RESULT_SHA256
        assert identity.d1_1_classification_sha256 == historical.D1_1_CLASSIFICATION_SHA256
        assert identity.cache_schema_version == historical.CACHE_SCHEMA_ID

    def test_default_identity_is_same_type_as_clean_constructor_output(self) -> None:
        hist_identity = historical.default_cache_identity("a" * 64)
        clean_identity = make_cache_identity(
            family_protocol_sha256="a" * 64,
            allocation_manifest_sha256=historical.ALLOCATION_MANIFEST_SHA256,
            allocation_context_sha256=historical.ALLOCATION_CONTEXT_SHA256,
            d1_audit_result_sha256=historical.D1_RESULT_SHA256,
            d1_1_classification_sha256=historical.D1_1_CLASSIFICATION_SHA256,
            cache_schema_version=historical.CACHE_SCHEMA_ID,
            family_runner_source_identity=hist_identity.family_runner_source_identity,
        )
        assert hist_identity == clean_identity
        assert type(hist_identity) is type(clean_identity)
        assert type(hist_identity) is FamilyGraphCacheIdentity

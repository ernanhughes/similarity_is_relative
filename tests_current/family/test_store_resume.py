"""Resume tests for relate.family.store.FamilyGraphCache.

Covers close/reopen, exact identity enforcement across reopen, phase
commitments surviving reopen, replay safety across reopen, and distinguishing
partially populated state from complete state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.family.sources import make_source_record
from relate.family.store import CACHE_SCHEMA_ID, FamilyGraphCache, make_cache_identity

TIMESTAMP = "2026-08-02T00:00:00+00:00"


def _identity(**overrides: str) -> object:
    base = dict(
        family_protocol_sha256="a" * 64,
        allocation_manifest_sha256="b" * 64,
        allocation_context_sha256="c" * 64,
        d1_audit_result_sha256="d" * 64,
        d1_1_classification_sha256="e" * 64,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity="f" * 64,
    )
    base.update(overrides)
    return make_cache_identity(**base)


class TestCloseAndReopen:
    def test_records_survive_close_and_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        record = make_source_record("fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP})
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.put_source_record(record)
        with FamilyGraphCache(db, identity=identity) as cache:
            fetched = cache.get_source_record(record.source_type, record.source_identity)
        assert fetched == record

    def test_reopen_requires_exact_identity(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity):
            pass
        different = _identity(family_protocol_sha256="0" * 64)
        with pytest.raises(ValueError):
            FamilyGraphCache(db, identity=different).close()


class TestPhaseCommitmentResume:
    def test_completed_phase_commitment_available_after_reopen(self, tmp_path: Path) -> None:
        # Only the "initial_allocation" phase is currently committed
        # automatically by put_allocation_repositories; there is no generic
        # put/get phase-commitment API today (documented as a known gap in
        # docs/architecture/capability-continuity.md). This test exercises the
        # phase_commitments table's resume durability directly, which is the
        # capability this stage moved unchanged.
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.connection.execute(
                "INSERT INTO phase_commitments(phase, status, commitment_sha256, metadata_json) "
                "VALUES ('synthetic_phase', 'COMPLETE', ?, '{}')",
                ("1" * 64,),
            )
            cache.connection.commit()
        with FamilyGraphCache(db, identity=identity) as cache:
            row = cache.connection.execute(
                "SELECT phase, status, commitment_sha256 FROM phase_commitments "
                "WHERE phase = 'synthetic_phase'"
            ).fetchone()
        assert row == ("synthetic_phase", "COMPLETE", "1" * 64)


class TestReplaySafetyAcrossReopen:
    def test_identical_source_record_replay_is_accepted(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        record = make_source_record("fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP})
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.put_source_record(record)
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.put_source_record(record)  # identical replay must not raise

    def test_conflicting_source_record_replay_is_rejected(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        record = make_source_record("fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP})
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.put_source_record(record)
            cache.connection.execute(
                "UPDATE source_records SET record_json = '{}' "
                "WHERE source_type = ? AND source_identity = ?",
                (record.source_type, record.source_identity),
            )
            cache.connection.commit()
        with FamilyGraphCache(db, identity=identity) as cache:
            with pytest.raises(ValueError, match="conflicting source record content"):
                cache.put_source_record(record)


class TestPartialStateIsInspectable:
    def test_partial_state_is_distinguishable_from_complete(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        record = make_source_record("fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP})
        with FamilyGraphCache(db, identity=identity) as cache:
            cache.put_source_record(record)
            source_count = cache.connection.execute(
                "SELECT COUNT(*) FROM source_records"
            ).fetchone()[0]
            allocation_count = cache.connection.execute(
                "SELECT COUNT(*) FROM allocation_repositories"
            ).fetchone()[0]
            phase_count = cache.connection.execute(
                "SELECT COUNT(*) FROM phase_commitments"
            ).fetchone()[0]
        assert source_count == 1
        assert allocation_count == 0
        assert phase_count == 0

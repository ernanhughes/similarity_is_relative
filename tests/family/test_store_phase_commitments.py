"""Phase-commitment persistence tests for relate.family.store.

Covers the new general-purpose put/get/list_phase_commitment(s) API,
which is separate from the existing implicit "initial_allocation" write
inside put_allocation_repositories (left unchanged) and separate from the
Stage 2C relate.workflows.WorkflowCheckpoint concept (never persisted here).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.evidence.hashing import sha256_file
from relate.family.repositories import ALLOCATION_REPOSITORY_COMMITMENT_SHA256
from relate.family.store import CACHE_SCHEMA_ID, FamilyGraphCache, make_cache_identity

CANONICAL_ALLOCATION = Path(
    "artifacts/canonical/option-c0/data-firewall-v1/option-c0-repository-allocation-v1.jsonl"
)


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


class TestPhaseCommitmentInsertion:
    def test_insertion_and_retrieval(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.put_phase_commitment(
                "graph_built",
                status="COMPLETE",
                commitment_sha256="1" * 64,
                metadata={"components": 3},
            )
            record = cache.get_phase_commitment("graph_built")
        assert record is not None
        assert record.phase == "graph_built"
        assert record.status == "COMPLETE"
        assert record.commitment_sha256 == "1" * 64
        assert dict(record.metadata) == {"components": 3}

    def test_identical_replay_is_accepted(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.put_phase_commitment(
                "phase_x", status="COMPLETE", commitment_sha256="2" * 64, metadata={}
            )
            cache.put_phase_commitment(
                "phase_x", status="COMPLETE", commitment_sha256="2" * 64, metadata={}
            )

    def test_conflicting_replay_is_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.put_phase_commitment(
                "phase_x", status="COMPLETE", commitment_sha256="2" * 64, metadata={}
            )
            with pytest.raises(ValueError, match="conflicting phase commitment"):
                cache.put_phase_commitment(
                    "phase_x", status="COMPLETE", commitment_sha256="3" * 64, metadata={}
                )

    def test_conflicting_status_is_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.put_phase_commitment(
                "phase_x", status="COMPLETE", commitment_sha256="2" * 64, metadata={}
            )
            with pytest.raises(ValueError, match="conflicting phase commitment"):
                cache.put_phase_commitment(
                    "phase_x", status="INCOMPLETE", commitment_sha256="2" * 64, metadata={}
                )

    def test_malformed_hash_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            with pytest.raises(ValueError, match="SHA-256"):
                cache.put_phase_commitment(
                    "phase_x", status="COMPLETE", commitment_sha256="not-a-hash", metadata={}
                )

    def test_empty_phase_name_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            with pytest.raises(ValueError, match="phase must be a nonempty string"):
                cache.put_phase_commitment(
                    "", status="COMPLETE", commitment_sha256="2" * 64, metadata={}
                )

    def test_deterministic_metadata_serialization(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.put_phase_commitment(
                "phase_a", status="COMPLETE", commitment_sha256="4" * 64, metadata={"b": 1, "a": 2}
            )
            # Same logical metadata with keys inserted in a different order
            # must serialize identically and therefore replay as identical.
            cache.put_phase_commitment(
                "phase_a", status="COMPLETE", commitment_sha256="4" * 64, metadata={"a": 2, "b": 1}
            )

    def test_get_missing_phase_returns_none(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            assert cache.get_phase_commitment("does_not_exist") is None


class TestListPhaseCommitments:
    def test_list_ordering(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.put_phase_commitment(
                "zeta", status="COMPLETE", commitment_sha256="5" * 64, metadata={}
            )
            cache.put_phase_commitment(
                "alpha", status="COMPLETE", commitment_sha256="6" * 64, metadata={}
            )
            records = cache.list_phase_commitments()
        assert [record.phase for record in records] == ["alpha", "zeta"]

    @pytest.mark.skipif(
        not CANONICAL_ALLOCATION.exists(), reason="canonical allocation manifest not available"
    )
    def test_compatible_with_existing_implicit_initial_allocation_record(
        self, tmp_path: Path
    ) -> None:
        identity = _identity(allocation_manifest_sha256=sha256_file(CANONICAL_ALLOCATION))
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
            cache.put_phase_commitment(
                "graph_built", status="COMPLETE", commitment_sha256="7" * 64, metadata={}
            )
            records = cache.list_phase_commitments()
        phases = {record.phase: record for record in records}
        assert "initial_allocation" in phases
        assert "graph_built" in phases
        assert phases["initial_allocation"].status == "COMPLETE"
        assert (
            phases["initial_allocation"].commitment_sha256
            == ALLOCATION_REPOSITORY_COMMITMENT_SHA256
        )
        assert [record.phase for record in records] == sorted(phases)

    def test_initial_allocation_upsert_path_is_unchanged(self, tmp_path: Path) -> None:
        # The implicit write inside put_allocation_repositories uses
        # INSERT ... ON CONFLICT DO UPDATE, not reject-on-conflict. This
        # test only documents that put_phase_commitment (reject-on-conflict)
        # is a distinct method and does not alter that existing behaviour;
        # it does not call put_allocation_repositories directly since that
        # requires the full canonical allocation set.
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            cache.connection.execute(
                "INSERT INTO phase_commitments(phase, status, commitment_sha256, metadata_json) "
                "VALUES ('initial_allocation', 'COMPLETE', ?, '{}')",
                ("8" * 64,),
            )
            cache.connection.commit()
            record = cache.get_phase_commitment("initial_allocation")
        assert record is not None
        assert record.commitment_sha256 == "8" * 64

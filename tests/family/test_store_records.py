"""Record-level tests for relate.family.store.FamilyGraphCache.

Covers allocation registration/replay/conflict, source-record persistence,
evidence-candidate persistence, manual-review-disposition persistence, and
resolved-edge persistence. Uses synthetic evidence throughout; allocation
tests use the published (non-hidden) canonical allocation manifest, which
lists repository/role/row_count only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.evidence.hashing import sha256_file
from relate.family.edges import (
    make_evidence_candidate,
    make_manual_review_disposition,
    resolve_evidence_candidate,
)
from relate.family.models import AllocationEntry
from relate.family.repositories import ALLOCATION_REPOSITORY_COMMITMENT_SHA256
from relate.family.sources import make_source_record
from relate.family.store import CACHE_SCHEMA_ID, FamilyGraphCache, make_cache_identity

TIMESTAMP = "2026-08-02T00:00:00+00:00"
SOURCE_ID = "a" * 64
PROTOCOL_SHA = "b" * 64
LEFT = "owner/alpha"
RIGHT = "owner/beta"

CANONICAL_ALLOCATION = Path(
    "artifacts/canonical/option-c0/data-firewall-v1/option-c0-repository-allocation-v1.jsonl"
)


def _identity(**overrides: str) -> object:
    base = dict(
        family_protocol_sha256=PROTOCOL_SHA,
        allocation_manifest_sha256="c" * 64,
        allocation_context_sha256="d" * 64,
        d1_audit_result_sha256="e" * 64,
        d1_1_classification_sha256="f" * 64,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity="0" * 64,
    )
    base.update(overrides)
    return make_cache_identity(**base)


def _identity_for_allocation(path: Path) -> object:
    return _identity(allocation_manifest_sha256=sha256_file(path))


def _seed_repositories(
    cache: FamilyGraphCache, repositories: tuple[str, ...] = (LEFT, RIGHT)
) -> None:
    """Insert synthetic repositories directly to satisfy the foreign-key
    constraint on evidence_candidates/typed_evidence_edges, without going
    through the frozen canonical-allocation validation path."""
    cache.connection.executemany(
        "INSERT OR IGNORE INTO allocation_repositories(repository, role, row_count) "
        "VALUES (?, 'c0_fit', 1)",
        [(repo,) for repo in repositories],
    )
    cache.connection.commit()


def _fork_candidate():
    snap = make_source_record(
        "public_metadata_snapshot",
        payload={
            "fork": True,
            "child_full_name": LEFT,
            "parent_or_source_full_name": RIGHT,
            "left_repository_id": "1",
            "right_repository_id": "2",
        },
        provenance={},
    )
    evidence_sources = {
        "github_rest": snap.source_identity,
        "public_metadata_snapshot": snap.source_identity,
    }
    payload = {
        "left_repository_id": "1",
        "right_repository_id": "2",
        "child_full_name": LEFT,
        "parent_or_source_full_name": RIGHT,
        "fork": True,
        "metadata_snapshot_identity": snap.source_identity,
        "snapshot_status": "COMPLETE",
    }
    candidate = make_evidence_candidate(
        LEFT,
        RIGHT,
        "DECLARED_GITHUB_FORK",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    return snap, candidate


def _succession_candidate():
    snap = make_source_record(
        "public_metadata_snapshot",
        payload={"predecessor": LEFT, "successor": RIGHT},
        provenance={},
    )
    evidence_sources = {"public_metadata_snapshot": snap.source_identity}
    payload = {
        "predecessor_repository": LEFT,
        "successor_repository": RIGHT,
        "direction": "predecessor_to_successor",
        "public_succession_record": "public rename notice",
        "record_snapshot_hash": snap.source_identity,
    }
    candidate = make_evidence_candidate(
        LEFT,
        RIGHT,
        "VERIFIED_REPOSITORY_SUCCESSION",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    return snap, candidate


class TestAllocationRegistration:
    def test_noncanonical_entries_rejected_without_touching_files(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            with pytest.raises(ValueError, match="noncanonical"):
                cache.put_allocation_repositories(
                    [AllocationEntry(repository="owner/a", role="c0_fit", row_count=1)]
                )

    @pytest.mark.skipif(
        not CANONICAL_ALLOCATION.exists(), reason="canonical allocation manifest not available"
    )
    def test_canonical_allocation_manifest_registers_rows(self, tmp_path: Path) -> None:
        identity = _identity_for_allocation(CANONICAL_ALLOCATION)
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            commitment = cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
            assert commitment == ALLOCATION_REPOSITORY_COMMITMENT_SHA256
            count = cache.connection.execute(
                "SELECT COUNT(*) FROM allocation_repositories"
            ).fetchone()[0]
            assert count == 5324

    @pytest.mark.skipif(
        not CANONICAL_ALLOCATION.exists(), reason="canonical allocation manifest not available"
    )
    def test_identical_allocation_replay_is_accepted(self, tmp_path: Path) -> None:
        identity = _identity_for_allocation(CANONICAL_ALLOCATION)
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
            cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)

    @pytest.mark.skipif(
        not CANONICAL_ALLOCATION.exists(), reason="canonical allocation manifest not available"
    )
    def test_conflicting_allocation_rows_rejected(self, tmp_path: Path) -> None:
        identity = _identity_for_allocation(CANONICAL_ALLOCATION)
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
            cache.connection.execute(
                "UPDATE allocation_repositories SET role = 'c0_iteration' WHERE repository = "
                "(SELECT repository FROM allocation_repositories WHERE role = 'c0_fit' LIMIT 1)"
            )
            cache.connection.commit()
            with pytest.raises(ValueError, match="allocation repositories differ"):
                cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)

    @pytest.mark.skipif(
        not CANONICAL_ALLOCATION.exists(), reason="canonical allocation manifest not available"
    )
    def test_phase_commitment_recorded_after_allocation(self, tmp_path: Path) -> None:
        identity = _identity_for_allocation(CANONICAL_ALLOCATION)
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
            row = cache.connection.execute(
                "SELECT phase, status FROM phase_commitments WHERE phase = 'initial_allocation'"
            ).fetchone()
        assert row == ("initial_allocation", "COMPLETE")


class TestSourceRecordPersistence:
    def test_insertion_and_retrieval(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            record = make_source_record(
                "fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP}
            )
            cache.put_source_record(record)
            fetched = cache.get_source_record(record.source_type, record.source_identity)
            assert fetched == record

    def test_identical_replay_is_accepted(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            record = make_source_record(
                "fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP}
            )
            cache.put_source_record(record)
            cache.put_source_record(record)

    def test_tampered_source_record_conflict_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            record = make_source_record(
                "fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP}
            )
            cache.put_source_record(record)
            cache.connection.execute(
                "UPDATE source_records SET record_json = '{}' "
                "WHERE source_type = ? AND source_identity = ?",
                (record.source_type, record.source_identity),
            )
            cache.connection.commit()
            with pytest.raises(ValueError, match="conflicting source record content"):
                cache.put_source_record(record)


class TestEvidenceCandidatePersistence:
    def test_insertion_and_retrieval(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _, candidate = _fork_candidate()
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            fetched = cache.get_evidence_candidate(candidate.candidate_id)
            assert fetched == candidate

    def test_identical_replay_is_accepted(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _, candidate = _fork_candidate()
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            cache.put_evidence_candidate(candidate)

    def test_conflicting_candidate_content_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _, candidate = _fork_candidate()
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            cache.connection.execute(
                "UPDATE evidence_candidates SET candidate_json = '{}' WHERE candidate_id = ?",
                (candidate.candidate_id,),
            )
            cache.connection.commit()
            with pytest.raises(ValueError, match="conflicting evidence candidate content"):
                cache.put_evidence_candidate(candidate)

    def test_not_found_raises(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            with pytest.raises(ValueError, match="evidence candidate not found"):
                cache.get_evidence_candidate("0" * 64)


class TestManualReviewDispositionPersistence:
    def test_insertion_and_retrieval(self, tmp_path: Path) -> None:
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            _, candidate = _succession_candidate()
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            disposition = make_manual_review_disposition(
                edge_candidate_id=candidate.candidate_id,
                protocol_sha256=PROTOCOL_SHA,
                evidence_commitment=candidate.evidence_commitment,
                disposition="APPROVED",
                reviewer_identity=SOURCE_ID,
                review_timestamp=TIMESTAMP,
                bounded_reason="test review",
            )
            cache.put_manual_review_disposition(disposition)
            fetched = cache.get_manual_review_disposition(disposition.disposition_id)
            assert fetched == disposition
            assert cache.get_final_disposition_for_candidate(candidate.candidate_id) == disposition

    def test_conflicting_final_disposition_rejected(self, tmp_path: Path) -> None:
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            _, candidate = _succession_candidate()
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            approved = make_manual_review_disposition(
                edge_candidate_id=candidate.candidate_id,
                protocol_sha256=PROTOCOL_SHA,
                evidence_commitment=candidate.evidence_commitment,
                disposition="APPROVED",
                reviewer_identity=SOURCE_ID,
                review_timestamp=TIMESTAMP,
                bounded_reason="test review",
            )
            cache.put_manual_review_disposition(approved)
            rejected = make_manual_review_disposition(
                edge_candidate_id=candidate.candidate_id,
                protocol_sha256=PROTOCOL_SHA,
                evidence_commitment=candidate.evidence_commitment,
                disposition="REJECTED",
                reviewer_identity=SOURCE_ID,
                review_timestamp=TIMESTAMP,
                bounded_reason="different reviewer decision",
            )
            with pytest.raises(ValueError, match="conflicting final disposition"):
                cache.put_manual_review_disposition(rejected)


class TestResolvedEdgePersistence:
    def test_insertion_and_retrieval(self, tmp_path: Path) -> None:
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            snap, candidate = _fork_candidate()
            cache.put_source_record(snap)
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            edge = resolve_evidence_candidate(
                candidate, None, protocol_sha256=identity.family_protocol_sha256
            )
            cache.put_resolved_edge(edge)
            fetched = cache.get_resolved_edge(edge.edge_id)
            assert fetched == edge

    def test_identical_replay_is_accepted(self, tmp_path: Path) -> None:
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            snap, candidate = _fork_candidate()
            cache.put_source_record(snap)
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            edge = resolve_evidence_candidate(
                candidate, None, protocol_sha256=identity.family_protocol_sha256
            )
            cache.put_resolved_edge(edge)
            cache.put_resolved_edge(edge)

    def test_conflicting_resolved_edge_rejected(self, tmp_path: Path) -> None:
        identity = _identity()
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            snap, candidate = _fork_candidate()
            cache.put_source_record(snap)
            _seed_repositories(cache)
            cache.put_evidence_candidate(candidate)
            edge = resolve_evidence_candidate(
                candidate, None, protocol_sha256=identity.family_protocol_sha256
            )
            cache.put_resolved_edge(edge)
            cache.connection.execute(
                "UPDATE typed_evidence_edges SET edge_json = '{}' WHERE edge_id = ?",
                (edge.edge_id,),
            )
            cache.connection.commit()
            with pytest.raises(ValueError, match="conflicting resolved edge content"):
                cache.put_resolved_edge(edge)

    def test_resolved_edge_requires_stored_candidate(self, tmp_path: Path) -> None:
        identity = _identity()
        _, candidate = _fork_candidate()
        edge = resolve_evidence_candidate(
            candidate, None, protocol_sha256=identity.family_protocol_sha256
        )
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
            # Candidate was never inserted into this cache instance.
            with pytest.raises(ValueError, match="evidence candidate not found"):
                cache.put_resolved_edge(edge)

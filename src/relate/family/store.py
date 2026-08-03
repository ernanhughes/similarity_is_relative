"""Family-graph SQLite persistence.

Moved from ``relate.experiments.option_c0_family_connected_protocol`` (Stage 2B).

Contains ``FamilyGraphCacheIdentity``, ``FamilyGraphCache`` and the explicit
identity constructor ``make_cache_identity``.  This module owns the family
cache's SQLite schema, connection lifecycle, identity binding, and record
persistence/retrieval.  It validates records through ``relate.family.edges``,
``relate.family.repositories`` and ``relate.family.sources`` rather than
reimplementing family-science validation.

No database access, CLI parsing, file publication or workflow orchestration
beyond what the cache itself owns.  This module must not import
``relate.experiments``.

Source-identity note
---------------------
The historical ``default_cache_identity`` in the experiment module derives
``family_runner_source_identity`` from ``sha256_file(Path(__file__))`` of the
*experiment* module.  That is deliberately not reproduced here: this module
has no opinion on which executing source produced a given run.  Callers
supply ``family_runner_source_identity`` explicitly to ``make_cache_identity``.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.sqlite import bind_cache_identity, enforce_wal_pragmas, verify_wal_pragmas
from relate.family.edges import (
    evidence_candidate_from_record,
    evidence_edge_from_record,
    manual_review_disposition_from_record,
    validate_evidence_candidate,
    validate_manual_review_disposition,
    validate_resolved_edge,
)
from relate.family.models import (
    AllocationEntry,
    EvidenceCandidate,
    EvidenceEdge,
    ManualReviewDisposition,
    SourceEvidenceRecord,
)
from relate.family.repositories import (
    ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
    ALLOCATION_REPOSITORY_COUNT,
    ALLOCATION_ROLE_REPOSITORY_COUNTS,
    ALLOCATION_ROLE_ROW_COUNTS,
    load_allocation_manifest,
    normalize_repository,
    validate_canonical_allocation_entries,
)
from relate.family.sources import HASH_PATTERN, source_record_from_record, validate_source_record

CACHE_SCHEMA_ID: Final = "option-c0-family-graph-cache-v1"


@dataclass(frozen=True)
class FamilyGraphCacheIdentity:
    family_protocol_sha256: str
    allocation_manifest_sha256: str
    allocation_context_sha256: str
    d1_audit_result_sha256: str
    d1_1_classification_sha256: str
    cache_schema_version: str
    family_runner_source_identity: str

    def as_mapping(self) -> dict[str, str]:
        return {
            "family_protocol_sha256": self.family_protocol_sha256,
            "allocation_manifest_sha256": self.allocation_manifest_sha256,
            "allocation_context_sha256": self.allocation_context_sha256,
            "d1_audit_result_sha256": self.d1_audit_result_sha256,
            "d1_1_classification_sha256": self.d1_1_classification_sha256,
            "cache_schema_version": self.cache_schema_version,
            "family_runner_source_identity": self.family_runner_source_identity,
        }


def make_cache_identity(
    *,
    family_protocol_sha256: str,
    allocation_manifest_sha256: str,
    allocation_context_sha256: str,
    d1_audit_result_sha256: str,
    d1_1_classification_sha256: str,
    cache_schema_version: str,
    family_runner_source_identity: str,
) -> FamilyGraphCacheIdentity:
    """Explicit cache-identity constructor.

    Unlike the historical ``default_cache_identity``, this constructor takes
    every field explicitly, including ``family_runner_source_identity``. It
    has no opinion on how a caller derives that value; a workflow step must
    supply its own executing-source identity rather than inheriting the
    identity of the historical experiment module.
    """
    return FamilyGraphCacheIdentity(
        family_protocol_sha256=family_protocol_sha256,
        allocation_manifest_sha256=allocation_manifest_sha256,
        allocation_context_sha256=allocation_context_sha256,
        d1_audit_result_sha256=d1_audit_result_sha256,
        d1_1_classification_sha256=d1_1_classification_sha256,
        cache_schema_version=cache_schema_version,
        family_runner_source_identity=family_runner_source_identity,
    )


@dataclass(frozen=True)
class PhaseCommitmentRecord:
    """A single row from the ``phase_commitments`` table.

    ``metadata`` is defensively copied into a read-only mapping so callers
    cannot mutate cached state through a returned record.
    """

    phase: str
    status: str
    commitment_sha256: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class FamilyGraphCache:
    def __init__(self, path: Path, *, identity: FamilyGraphCacheIdentity) -> None:
        self.path = path
        self.identity = identity
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        enforce_wal_pragmas(self.connection)
        self._create_schema()
        self._verify_pragmas()
        self._bind_identity()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> FamilyGraphCache:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _verify_pragmas(self) -> None:
        try:
            verify_wal_pragmas(self.connection)
        except ValueError as exc:
            raise RuntimeError("family graph cache SQLite pragmas are not enforced") from exc

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cache_identity (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS allocation_repositories (
                repository TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                row_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repository_metadata_snapshots (
                repository TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                snapshot_sha256 TEXT NOT NULL,
                FOREIGN KEY(repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS source_records (
                source_type TEXT NOT NULL,
                source_identity TEXT NOT NULL,
                record_json TEXT NOT NULL,
                record_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY(source_type, source_identity)
            );
            CREATE TABLE IF NOT EXISTS typed_evidence_edges (
                edge_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                disposition_id TEXT,
                left_repository TEXT NOT NULL,
                right_repository TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                connecting INTEGER NOT NULL,
                edge_json TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES evidence_candidates(candidate_id),
                FOREIGN KEY(disposition_id) REFERENCES manual_review_dispositions(disposition_id),
                FOREIGN KEY(left_repository) REFERENCES allocation_repositories(repository),
                FOREIGN KEY(right_repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS evidence_candidates (
                candidate_id TEXT PRIMARY KEY,
                left_repository TEXT NOT NULL,
                right_repository TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                candidate_json TEXT NOT NULL,
                evidence_commitment TEXT NOT NULL,
                FOREIGN KEY(left_repository) REFERENCES allocation_repositories(repository),
                FOREIGN KEY(right_repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS manual_review_dispositions (
                disposition_id TEXT PRIMARY KEY,
                edge_candidate_id TEXT NOT NULL,
                protocol_sha256 TEXT NOT NULL,
                evidence_commitment TEXT NOT NULL,
                disposition TEXT NOT NULL,
                reviewer_identity TEXT NOT NULL,
                review_timestamp TEXT NOT NULL,
                bounded_reason TEXT NOT NULL,
                FOREIGN KEY(edge_candidate_id) REFERENCES evidence_candidates(candidate_id),
                UNIQUE(edge_candidate_id)
            );
            CREATE TABLE IF NOT EXISTS component_memberships (
                component_id TEXT NOT NULL,
                repository TEXT NOT NULL,
                PRIMARY KEY(component_id, repository),
                FOREIGN KEY(repository) REFERENCES allocation_repositories(repository)
            );
            CREATE TABLE IF NOT EXISTS phase_commitments (
                phase TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                commitment_sha256 TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def _bind_identity(self) -> None:
        expected = self.identity.as_mapping()
        try:
            bind_cache_identity(self.connection, "cache_identity", expected, self._has_data_rows)
        except ValueError as exc:
            msg = str(exc)
            if "key set mismatch" in msg:
                raise ValueError("family graph cache identity key set mismatch") from exc
            if "contains data rows without identity" in msg:
                raise ValueError("family graph cache contains data without identity") from exc
            # Value mismatch: extract the key name from the neutral message.
            raise ValueError(str(exc).replace("cache_identity", "family graph cache")) from exc

    def _has_data_rows(self) -> bool:
        for table in (
            "allocation_repositories",
            "repository_metadata_snapshots",
            "source_records",
            "evidence_candidates",
            "typed_evidence_edges",
            "manual_review_dispositions",
            "component_memberships",
            "phase_commitments",
        ):
            row = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            if int(row[0]):
                return True
        return False

    def put_allocation_repositories(self, entries: Sequence[AllocationEntry]) -> None:
        commitment = validate_canonical_allocation_entries(entries)
        existing = {
            str(repository): (str(role), int(row_count))
            for repository, role, row_count in self.connection.execute(
                "SELECT repository, role, row_count FROM allocation_repositories"
            )
        }
        incoming = {entry.repository: (entry.role, entry.row_count) for entry in entries}
        if existing and existing != incoming:
            raise ValueError("allocation repositories differ under the same cache identity")
        self.connection.executemany(
            """
            INSERT INTO allocation_repositories(repository, role, row_count)
            VALUES (?, ?, ?)
            ON CONFLICT(repository) DO NOTHING
            """,
            [(entry.repository, entry.role, entry.row_count) for entry in entries],
        )
        self.connection.commit()
        self.connection.execute(
            """
            INSERT INTO phase_commitments(phase, status, commitment_sha256, metadata_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phase) DO UPDATE SET
                status = excluded.status,
                commitment_sha256 = excluded.commitment_sha256,
                metadata_json = excluded.metadata_json
            """,
            (
                "initial_allocation",
                "COMPLETE",
                commitment,
                canonical_json(
                    {
                        "repository_count": ALLOCATION_REPOSITORY_COUNT,
                        "role_repository_counts": ALLOCATION_ROLE_REPOSITORY_COUNTS,
                        "role_row_counts": ALLOCATION_ROLE_ROW_COUNTS,
                    }
                ),
            ),
        )
        self.connection.commit()

    def put_canonical_allocation_manifest(self, canonical_path: Path) -> str:
        entries = load_allocation_manifest(
            canonical_path,
            expected_sha256=self.identity.allocation_manifest_sha256,
        )
        self.put_allocation_repositories(entries)
        return ALLOCATION_REPOSITORY_COMMITMENT_SHA256

    def put_evidence_candidate(self, candidate: EvidenceCandidate) -> None:
        validate_evidence_candidate(candidate)
        record_json = canonical_json(candidate.as_record())
        existing = self.connection.execute(
            "SELECT candidate_json FROM evidence_candidates WHERE candidate_id = ?",
            (candidate.candidate_id,),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != record_json:
                raise ValueError("conflicting evidence candidate content")
            return
        self.connection.execute(
            """
            INSERT INTO evidence_candidates(
                candidate_id, left_repository, right_repository, edge_type,
                candidate_json, evidence_commitment
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.candidate_id,
                candidate.left_repository,
                candidate.right_repository,
                candidate.edge_type,
                record_json,
                candidate.evidence_commitment,
            ),
        )
        self.connection.commit()

    def put_manual_review_disposition(self, disposition: ManualReviewDisposition) -> None:
        candidate = self.get_evidence_candidate(disposition.edge_candidate_id)
        validate_manual_review_disposition(
            disposition,
            candidate,
            protocol_sha256=self.identity.family_protocol_sha256,
        )
        existing = self.get_final_disposition_for_candidate(disposition.edge_candidate_id)
        if existing is not None:
            if existing != disposition:
                raise ValueError("conflicting final disposition for candidate")
            return
        self.connection.execute(
            """
            INSERT INTO manual_review_dispositions(
                disposition_id, edge_candidate_id, protocol_sha256, evidence_commitment,
                disposition, reviewer_identity, review_timestamp, bounded_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                disposition.disposition_id,
                disposition.edge_candidate_id,
                disposition.protocol_sha256,
                disposition.evidence_commitment,
                disposition.disposition,
                disposition.reviewer_identity,
                disposition.review_timestamp,
                disposition.bounded_reason,
            ),
        )
        self.connection.commit()

    def put_resolved_edge(self, edge: EvidenceEdge) -> None:
        candidate = self.get_evidence_candidate(edge.candidate_id)
        disposition = (
            self.get_manual_review_disposition(edge.disposition_id)
            if edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=self.identity.family_protocol_sha256,
            source_records=self.get_source_registry(),
        )
        record_json = canonical_json(edge.as_record())
        existing = self.connection.execute(
            "SELECT edge_json FROM typed_evidence_edges WHERE edge_id = ?",
            (edge.edge_id,),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != record_json:
                raise ValueError("conflicting resolved edge content")
            return
        self.connection.execute(
            """
            INSERT INTO typed_evidence_edges(
                edge_id, candidate_id, disposition_id, left_repository, right_repository,
                edge_type, connecting, edge_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge.edge_id,
                edge.candidate_id,
                edge.disposition_id,
                edge.left_repository,
                edge.right_repository,
                edge.edge_type,
                int(edge.connecting),
                record_json,
            ),
        )
        self.connection.commit()

    def put_source_record(self, record: SourceEvidenceRecord) -> None:
        validate_source_record(record)
        record_json = canonical_json(record.as_record())
        existing = self.connection.execute(
            """
            SELECT record_json FROM source_records
            WHERE source_type = ? AND source_identity = ?
            """,
            (record.source_type, record.source_identity),
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != record_json:
                raise ValueError("conflicting source record content")
            return
        self.connection.execute(
            """
            INSERT INTO source_records(
                source_type, source_identity, record_json, record_sha256, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.source_type,
                record.source_identity,
                record_json,
                record.record_sha256,
                record.status,
            ),
        )
        self.connection.commit()

    def get_source_record(self, source_type: str, source_identity: str) -> SourceEvidenceRecord:
        row = self.connection.execute(
            """
            SELECT record_json FROM source_records
            WHERE source_type = ? AND source_identity = ?
            """,
            (source_type, source_identity),
        ).fetchone()
        if row is None:
            raise ValueError("source record not found")
        record = source_record_from_record(json.loads(str(row[0])))
        validate_source_record(record)
        if record.source_type != source_type or record.source_identity != source_identity:
            raise ValueError("source record type or identity mismatch")
        return record

    def get_source_registry(self) -> dict[tuple[str, str], SourceEvidenceRecord]:
        registry: dict[tuple[str, str], SourceEvidenceRecord] = {}
        for source_type, source_identity in self.connection.execute(
            "SELECT source_type, source_identity FROM source_records"
        ):
            record = self.get_source_record(str(source_type), str(source_identity))
            registry[(record.source_type, record.source_identity)] = record
        return registry

    def get_evidence_candidate(self, candidate_id: str) -> EvidenceCandidate:
        row = self.connection.execute(
            "SELECT candidate_json FROM evidence_candidates WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            raise ValueError("evidence candidate not found")
        candidate = evidence_candidate_from_record(json.loads(str(row[0])))
        validate_evidence_candidate(candidate)
        return candidate

    def get_manual_review_disposition(self, disposition_id: str | None) -> ManualReviewDisposition:
        if disposition_id is None:
            raise ValueError("manual disposition not found")
        row = self.connection.execute(
            """
            SELECT disposition_id, edge_candidate_id, protocol_sha256, evidence_commitment,
                   disposition, reviewer_identity, review_timestamp, bounded_reason
            FROM manual_review_dispositions WHERE disposition_id = ?
            """,
            (disposition_id,),
        ).fetchone()
        if row is None:
            raise ValueError("manual disposition not found")
        disposition = manual_review_disposition_from_record(
            {
                "disposition_id": row[0],
                "edge_candidate_id": row[1],
                "protocol_sha256": row[2],
                "evidence_commitment": row[3],
                "disposition": row[4],
                "reviewer_identity": row[5],
                "review_timestamp": row[6],
                "bounded_reason": row[7],
            }
        )
        candidate = self.get_evidence_candidate(disposition.edge_candidate_id)
        validate_manual_review_disposition(
            disposition,
            candidate,
            protocol_sha256=self.identity.family_protocol_sha256,
        )
        return disposition

    def get_final_disposition_for_candidate(
        self,
        candidate_id: str,
    ) -> ManualReviewDisposition | None:
        row = self.connection.execute(
            "SELECT disposition_id FROM manual_review_dispositions WHERE edge_candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        return self.get_manual_review_disposition(str(row[0]))

    def get_resolved_edge(self, edge_id: str) -> EvidenceEdge:
        row = self.connection.execute(
            "SELECT edge_json FROM typed_evidence_edges WHERE edge_id = ?",
            (edge_id,),
        ).fetchone()
        if row is None:
            raise ValueError("resolved edge not found")
        edge = evidence_edge_from_record(json.loads(str(row[0])))
        candidate = self.get_evidence_candidate(edge.candidate_id)
        disposition = (
            self.get_manual_review_disposition(edge.disposition_id)
            if edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=self.identity.family_protocol_sha256,
            source_records=self.get_source_registry(),
        )
        return edge

    # --- Component memberships ---
    # component_memberships table exists since Stage 2B (schema only); these
    # methods add the first public persistence API for it (Stage 2D).

    def put_component_memberships(self, components: Sequence[Mapping[str, Any]]) -> None:
        """Persist a complete connected-component membership snapshot.

        *components* must be the shape produced by
        ``relate.family.graph.build_components``: each item a mapping with
        ``component_id``, ``repositories`` (an iterable of repository
        names), and ``repository_count``.

        This is a whole-graph operation: it compares the complete existing
        membership set against the complete incoming set before writing
        anything. An empty or byte-identical existing set is accepted
        (idempotent replay); any other existing set is rejected outright,
        never partially overwritten, so a mixed old/new graph can never be
        observed.
        """
        normalized: list[tuple[str, str]] = []
        seen_repositories: set[str] = set()
        for component in components:
            component_id = str(component.get("component_id", ""))
            if not component_id.strip():
                raise ValueError("component_id must be a nonempty string")
            repositories = list(component.get("repositories") or [])
            if not repositories:
                raise ValueError(f"component has no repositories: {component_id!r}")
            for repository in repositories:
                repo = normalize_repository(str(repository))
                if repo in seen_repositories:
                    raise ValueError(f"repository appears in multiple components: {repo}")
                seen_repositories.add(repo)
                normalized.append((component_id, repo))
        normalized.sort()

        known_repositories = {
            str(row[0])
            for row in self.connection.execute("SELECT repository FROM allocation_repositories")
        }
        unknown = seen_repositories - known_repositories
        if unknown:
            raise ValueError(
                f"component membership references unknown repositories: {sorted(unknown)}"
            )

        existing = sorted(
            (str(row[0]), str(row[1]))
            for row in self.connection.execute(
                "SELECT component_id, repository FROM component_memberships"
            )
        )
        if existing:
            if existing != normalized:
                raise ValueError("component memberships differ from the existing stored graph")
            return
        if not normalized:
            return
        self.connection.executemany(
            "INSERT INTO component_memberships(component_id, repository) VALUES (?, ?)",
            normalized,
        )
        self.connection.commit()

    def get_component_memberships(self) -> tuple[dict[str, Any], ...]:
        """Return stored components in the same shape as
        ``relate.family.graph.build_components``' output, ordered
        deterministically by ``component_id``."""
        rows = self.connection.execute(
            "SELECT component_id, repository FROM component_memberships "
            "ORDER BY component_id, repository"
        ).fetchall()
        grouped: dict[str, list[str]] = {}
        for component_id, repository in rows:
            grouped.setdefault(str(component_id), []).append(str(repository))
        return tuple(
            {
                "component_id": component_id,
                "repositories": tuple(repositories),
                "repository_count": len(repositories),
            }
            for component_id, repositories in sorted(grouped.items())
        )

    # --- Phase commitments ---
    # phase_commitments table exists since Stage 2B; put_allocation_repositories
    # already writes one implicit row ("initial_allocation") using
    # INSERT ... ON CONFLICT DO UPDATE. That transaction path is left exactly
    # as-is. The methods below add a *separate*, general-purpose API for any
    # other phase, using reject-on-conflict semantics consistent with every
    # other put_* method in this store. This is not a generic workflow
    # checkpoint store — relate.workflows.WorkflowCheckpoint is a distinct,
    # unrelated concept and is never persisted here.

    def put_phase_commitment(
        self,
        phase: str,
        *,
        status: str,
        commitment_sha256: str,
        metadata: Mapping[str, Any],
    ) -> None:
        if not phase.strip():
            raise ValueError("phase must be a nonempty string")
        if not status.strip():
            raise ValueError("status must be a nonempty string")
        if not HASH_PATTERN.fullmatch(commitment_sha256):
            raise ValueError("commitment_sha256 must be a SHA-256 hex digest")
        metadata_json = canonical_json(dict(metadata))
        existing = self.connection.execute(
            "SELECT status, commitment_sha256, metadata_json FROM phase_commitments "
            "WHERE phase = ?",
            (phase,),
        ).fetchone()
        if existing is not None:
            if (str(existing[0]), str(existing[1]), str(existing[2])) != (
                status,
                commitment_sha256,
                metadata_json,
            ):
                raise ValueError(f"conflicting phase commitment for phase: {phase}")
            return
        self.connection.execute(
            """
            INSERT INTO phase_commitments(phase, status, commitment_sha256, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (phase, status, commitment_sha256, metadata_json),
        )
        self.connection.commit()

    def get_phase_commitment(self, phase: str) -> PhaseCommitmentRecord | None:
        row = self.connection.execute(
            "SELECT phase, status, commitment_sha256, metadata_json FROM phase_commitments "
            "WHERE phase = ?",
            (phase,),
        ).fetchone()
        if row is None:
            return None
        return PhaseCommitmentRecord(
            phase=str(row[0]),
            status=str(row[1]),
            commitment_sha256=str(row[2]),
            metadata=json.loads(str(row[3])),
        )

    def list_phase_commitments(self) -> tuple[PhaseCommitmentRecord, ...]:
        rows = self.connection.execute(
            "SELECT phase, status, commitment_sha256, metadata_json FROM phase_commitments "
            "ORDER BY phase"
        ).fetchall()
        return tuple(
            PhaseCommitmentRecord(
                phase=str(row[0]),
                status=str(row[1]),
                commitment_sha256=str(row[2]),
                metadata=json.loads(str(row[3])),
            )
            for row in rows
        )

    # --- Deterministic readers for graph/outcome inputs ---
    # These expose already-persisted data so a future graph or outcome
    # workflow step never needs store.connection.execute(...) directly.

    def list_allocation_repositories(self) -> tuple[AllocationEntry, ...]:
        rows = self.connection.execute(
            "SELECT repository, role, row_count FROM allocation_repositories ORDER BY repository"
        ).fetchall()
        return tuple(
            AllocationEntry(repository=str(row[0]), role=str(row[1]), row_count=int(row[2]))
            for row in rows
        )

    def list_evidence_candidates(self) -> tuple[EvidenceCandidate, ...]:
        rows = self.connection.execute(
            "SELECT candidate_id FROM evidence_candidates ORDER BY candidate_id"
        ).fetchall()
        return tuple(self.get_evidence_candidate(str(row[0])) for row in rows)

    def list_resolved_edges(self) -> tuple[EvidenceEdge, ...]:
        rows = self.connection.execute(
            "SELECT edge_id FROM typed_evidence_edges ORDER BY edge_id"
        ).fetchall()
        return tuple(self.get_resolved_edge(str(row[0])) for row in rows)

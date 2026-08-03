"""Frozen Option C0 family-connected allocation protocol primitives."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.evidence.sqlite import bind_cache_identity, enforce_wal_pragmas, verify_wal_pragmas
from relate.family.edges import (
    PROTOCOL_VERSION,
    REVIEW_DISPOSITIONS,
    derive_edge_id,
    evidence_candidate_from_record,
    evidence_edge_from_record,
    make_evidence_candidate,
    make_manual_review_disposition,
    manual_review_disposition_from_record,
    resolve_evidence_candidate,
    validate_evidence_candidate,
    validate_evidence_edge,
    validate_manual_review_disposition,
    validate_resolved_edge,
    validate_rule_payload,
    validate_rule_semantics,
    validate_source_payload_binding,
)

# --- Compatibility re-exports from relate.family ---
# These names are imported explicitly so that callers using the historical
# module path continue to resolve the same objects.  All imports in this
# section are intentional re-exports; F401 is suppressed for this file in
# pyproject.toml.
from relate.family.models import (
    EDGE_SCHEMA_ID,
    AllocationEntry,
    EdgeRule,
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
    REPOSITORY_PATTERN,
    ROLE_ORDER,
    allocation_repository_commitment,
    load_allocation_manifest,
    normalize_repository,
    repository_owner,
    validate_canonical_allocation_entries,
)
from relate.family.rules import (
    ALL_EDGE_TYPES,
    CONDITIONAL_CONNECTING_EDGE_TYPES,
    CONNECTING_EDGE_TYPES,
    EDGE_RULES,
    HARD_CONNECTING_EDGE_TYPES,
    NONCONNECTING_EDGE_TYPES,
    edge_rules_contract,
)
from relate.family.sources import (
    ALLOWED_EVIDENCE_SOURCES,
    FORBIDDEN_PAYLOAD_PATTERNS,
    HASH_PATTERN,
    LOCATOR_PATTERN,
    MAX_EVIDENCE_STRING_LENGTH,
    METADATA_STATUSES,
    PUBLIC_METADATA_FIELDS,
    make_source_record,
    parse_timestamp,
    payload_hash,
    public_metadata_snapshot,
    source_bundle_commitment,
    source_record_from_record,
    validate_evidence_source_bundle,
    validate_payload_firewall,
    validate_source_identity,
    validate_source_record,
    validate_source_registry,
)

# --- Historical-only schema constants ---

SCHEMA_ID: Final = "option-c0-family-connected-allocation-contract-v1"
CACHE_SCHEMA_ID: Final = "option-c0-family-graph-cache-v1"
D1_RESULT_SHA256: Final = "a19c042f725fb20a0a87fa902d2071f30c66d5ee8f96bfde1cd056cba5123420"
D1_1_CLASSIFICATION_SHA256: Final = (
    "64787803c775193335c98dfef7ccdd23989c54d0a110efb0284f7960640c5be4"
)
ALLOCATION_MANIFEST_SHA256: Final = (
    "41e48447171ac2f0553b795f2b3e50dfc5ac389b68fb30607b7d1c496bdb5bfc"
)
ALLOCATION_CONTEXT_SHA256: Final = (
    "a3ae0b5dcbef0ae8e5056900ba44eeb53b4fd53a20f7cea8d842f67197ab02ed"
)


# --- make_evidence_edge compatibility wrapper ---
# The clean relate.family.edges version accepts protocol_sha256 explicitly.
# This wrapper calls protocol_contract() to supply the canonical value so that
# callers of the historical module path see the same behaviour as before.


def make_evidence_edge(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
    evidence_sources: Mapping[str, str] | None = None,
    evidence_source: str | None = None,
    evidence_source_identity: str | None = None,
    retrieval_timestamp: str | None = None,
    evidence_payload: Mapping[str, Any],
    reason: str | None = None,
    rule_version: str = PROTOCOL_VERSION,
) -> EvidenceEdge:
    from relate.family.edges import make_evidence_edge as _clean_make_evidence_edge

    return _clean_make_evidence_edge(
        left_repository,
        right_repository,
        edge_type,
        protocol_sha256=protocol_contract()["protocol_sha256"],
        evidence_sources=evidence_sources,
        evidence_source=evidence_source,
        evidence_source_identity=evidence_source_identity,
        retrieval_timestamp=retrieval_timestamp,
        evidence_payload=evidence_payload,
        reason=reason,
        rule_version=rule_version,
    )


# --- FamilyGraphCacheIdentity ---
# Kept here with FamilyGraphCache during this PR.
# FamilyGraphCacheIdentity.family_runner_source_identity is set from sha256_file(__file__)
# in default_cache_identity, making it source-hash sensitive.
# Moving it to relate.family would change the default runner identity.
# Scheduled for Stage 2B (family persistence extraction).


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


def default_cache_identity(family_protocol_sha256: str) -> FamilyGraphCacheIdentity:
    return FamilyGraphCacheIdentity(
        family_protocol_sha256=family_protocol_sha256,
        allocation_manifest_sha256=ALLOCATION_MANIFEST_SHA256,
        allocation_context_sha256=ALLOCATION_CONTEXT_SHA256,
        d1_audit_result_sha256=D1_RESULT_SHA256,
        d1_1_classification_sha256=D1_1_CLASSIFICATION_SHA256,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity=sha256_file(Path(__file__)),
    )


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
            expected_sha256=ALLOCATION_MANIFEST_SHA256,
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


def validate_frozen_protocol_inputs(repo_root: Path) -> dict[str, Any]:
    allocation = repo_root / (
        "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-repository-allocation-v1.jsonl"
    )
    firewall = repo_root / (
        "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-data-firewall-publication-v1.json"
    )
    d1 = repo_root / (
        "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-integrity-audit-v1.json"
    )
    d11 = repo_root / (
        "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-overlap-classification-v1.json"
    )
    if sha256_file(allocation) != ALLOCATION_MANIFEST_SHA256:
        raise ValueError("canonical allocation manifest hash mismatch")
    if sha256_file(d1) != D1_RESULT_SHA256:
        raise ValueError("canonical D1 result hash mismatch")
    if sha256_file(d11) != D1_1_CLASSIFICATION_SHA256:
        raise ValueError("canonical D1.1 classification hash mismatch")
    firewall_data = json.loads(firewall.read_text(encoding="utf-8"))
    d1_data = json.loads(d1.read_text(encoding="utf-8"))
    d11_data = json.loads(d11.read_text(encoding="utf-8"))
    for artifact in (firewall_data, d1_data, d11_data):
        if not isinstance(artifact, dict):
            raise ValueError("canonical protocol input must be a JSON object")
    if firewall_data.get("allocation_context_sha256") != ALLOCATION_CONTEXT_SHA256:
        raise ValueError("allocation context SHA-256 mismatch")
    classification = d11_data.get("classification", {})
    if classification.get("overall_outcome") != "D1_CLASSIFICATION_INCONCLUSIVE":
        raise ValueError("D1.1 outcome is not inconclusive")
    if classification.get("family_identity_rule_status") != "NOT_FROZEN":
        raise ValueError("D1.1 family identity rule status is not frozen as NOT_FROZEN")
    common_firewall_keys = (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c0_selection_rows_accessed",
        "c1_rows_accessed",
        "hidden_row_content_accessed",
    )
    d11_firewall_keys = (
        *common_firewall_keys,
        "c0_selection_row_content_accessed",
        "c1_row_content_accessed",
    )
    d11_firewall_booleans = d11_data.get("firewall_booleans", {})
    for key in d11_firewall_keys:
        if key not in d11_firewall_booleans or d11_firewall_booleans[key] is not False:
            raise ValueError(f"hidden-row firewall field is true: {key}")
    d1_firewall = d1_data.get("firewall_booleans", d1_data)
    for key in common_firewall_keys:
        if key not in d1_firewall or d1_firewall[key] is not False:
            raise ValueError(f"D1 hidden-row firewall field is not exactly false: {key}")
    return {
        "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
        "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
        "allocation_repository_commitment_sha256": ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
    }


def validate_firewall_booleans(d1_data: Mapping[str, Any], d11_data: Mapping[str, Any]) -> None:
    common_firewall_keys = (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c0_selection_rows_accessed",
        "c1_rows_accessed",
        "hidden_row_content_accessed",
    )
    d11_firewall_keys = (
        *common_firewall_keys,
        "c0_selection_row_content_accessed",
        "c1_row_content_accessed",
    )
    d11_firewall_booleans = d11_data.get("firewall_booleans", {})
    for key in d11_firewall_keys:
        if key not in d11_firewall_booleans or d11_firewall_booleans[key] is not False:
            raise ValueError(f"hidden-row firewall field is true: {key}")
    d1_firewall = d1_data.get("firewall_booleans", d1_data)
    for key in common_firewall_keys:
        if key not in d1_firewall or d1_firewall[key] is not False:
            raise ValueError(f"D1 hidden-row firewall field is not exactly false: {key}")


class UnionFind:
    def __init__(self, nodes: Sequence[str]) -> None:
        self.parent = {node: node for node in sorted(set(nodes))}

    def find(self, node: str) -> str:
        parent = self.parent[node]
        if parent != node:
            self.parent[node] = self.find(parent)
        return self.parent[node]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            first, second = sorted((left_root, right_root))
            self.parent[second] = first


def component_id(members: Sequence[str], protocol_sha256: str) -> str:
    return sha256_text(
        canonical_json({"members": sorted(members), "protocol_sha256": protocol_sha256})
    )


def _reject_duplicate_edges(edges: Sequence[EvidenceEdge]) -> None:
    seen: set[str] = set()
    for edge in edges:
        if edge.edge_id in seen:
            raise ValueError("duplicate edge ID")
        seen.add(edge.edge_id)


def build_components(
    repositories: Sequence[str],
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str,
    candidates: Mapping[str, EvidenceCandidate] | None = None,
    dispositions: Mapping[str, ManualReviewDisposition] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> list[dict[str, Any]]:
    normalized = sorted({normalize_repository(repository) for repository in repositories})
    allocation_set = set(normalized)
    _reject_duplicate_edges(edges)
    uf = UnionFind(normalized)
    for edge in sorted(edges, key=lambda item: item.edge_id):
        candidate = candidates.get(edge.candidate_id) if candidates is not None else None
        disposition = (
            dispositions.get(edge.disposition_id)
            if dispositions is not None and edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=protocol_sha256,
            allocation_repositories=allocation_set,
            source_records=source_records,
        )
        if edge.connecting:
            uf.union(edge.left_repository, edge.right_repository)
    by_root: dict[str, list[str]] = {}
    for repository in normalized:
        by_root.setdefault(uf.find(repository), []).append(repository)
    components = [
        {
            "component_id": component_id(members, protocol_sha256),
            "repositories": sorted(members),
            "repository_count": len(members),
        }
        for members in by_root.values()
    ]
    return sorted(components, key=lambda item: item["component_id"])


def component_commitment(components: Sequence[Mapping[str, Any]]) -> str:
    protocol_sha256 = protocol_contract()["protocol_sha256"]
    normalized = []
    for component in components:
        repositories = sorted(normalize_repository(item) for item in component["repositories"])
        if int(component["repository_count"]) != len(repositories):
            raise ValueError("component repository_count is malformed")
        expected_id = component_id(repositories, protocol_sha256)
        if component["component_id"] != expected_id:
            raise ValueError("component_id does not match members")
        normalized.append(
            {
                "component_id": expected_id,
                "repositories": repositories,
                "repository_count": len(repositories),
            }
        )
    normalized = sorted(normalized, key=canonical_json)
    return sha256_text(canonical_json({"components": normalized}))


def edge_commitment(
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str | None = None,
    candidates: Mapping[str, EvidenceCandidate] | None = None,
    dispositions: Mapping[str, ManualReviewDisposition] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> str:
    _reject_duplicate_edges(edges)
    active_protocol = protocol_sha256 or protocol_contract()["protocol_sha256"]
    for edge in edges:
        candidate = candidates.get(edge.candidate_id) if candidates is not None else None
        disposition = (
            dispositions.get(edge.disposition_id)
            if dispositions is not None and edge.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            edge,
            candidate,
            disposition,
            protocol_sha256=active_protocol,
            source_records=source_records,
        )
    records = [edge.as_record() for edge in sorted(edges, key=lambda item: item.edge_id)]
    return sha256_text(canonical_json({"edges": records}))


def family_graph_outcome(summary: Mapping[str, Any]) -> dict[str, Any]:
    incomplete_metadata = int(summary.get("incomplete_metadata_records", 0))
    unresolved = int(summary.get("unresolved_connecting_candidate_edges", 0))
    approved = int(summary.get("approved_connecting_edges", 0))
    cross_role_components = int(summary.get("cross_role_connecting_components", 0))
    hard_or_exact = bool(summary.get("hard_or_exact_fit_iteration_crossing_observed", False))
    if incomplete_metadata:
        outcome = "FAMILY_GRAPH_INCOMPLETE_METADATA"
    elif unresolved:
        outcome = "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"
    elif cross_role_components:
        outcome = "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED"
    else:
        outcome = "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"
    return {
        "family_graph_outcome": outcome,
        "family_crossing_observed": cross_role_components > 0,
        "allocation_family_disjointness_violated": cross_role_components > 0,
        "hard_or_exact_fit_iteration_crossing_observed": hard_or_exact,
        "approved_connecting_edges": approved,
        "unresolved_connecting_candidate_edges": unresolved,
        "rejected_connecting_candidates": int(summary.get("rejected_connecting_candidates", 0)),
        "nonconnecting_review_evidence_edges": int(
            summary.get("nonconnecting_review_evidence_edges", 0)
        ),
        "incomplete_metadata_records": incomplete_metadata,
        "material_contamination_established": False,
        "reallocation_required": None,
        "automatic_reallocation_decision_permitted": False,
    }


def protocol_contract() -> dict[str, Any]:
    contract = {
        "schema_id": SCHEMA_ID,
        "schema_version": "v1",
        "source_allocation_identity": {
            "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
            "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
            "allocation_repository_commitment_sha256": ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
            "repository_count": ALLOCATION_REPOSITORY_COUNT,
            "role_repository_counts": ALLOCATION_ROLE_REPOSITORY_COUNTS,
            "role_row_counts": ALLOCATION_ROLE_ROW_COUNTS,
        },
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
        "repository_normalization_rule": {
            "case": "lowercase",
            "trim_python_unicode_whitespace": True,
            "required_shape": "owner/repository",
            "allowed_pattern": REPOSITORY_PATTERN.pattern,
        },
        "edge_rules": edge_rules_contract(),
        "edge_taxonomy": {
            "hard_connecting": list(HARD_CONNECTING_EDGE_TYPES),
            "conditional_connecting": list(CONDITIONAL_CONNECTING_EDGE_TYPES),
            "nonconnecting_review_evidence": list(NONCONNECTING_EDGE_TYPES),
        },
        "component_algorithm": {
            "sort_connecting_edges": "by immutable edge_id",
            "duplicate_edge_ids": "rejected before counts, commitments, publication, and union",
            "union_find_uses_connecting_edges_only": True,
            "reviewed_edges_require_validated_candidate_and_disposition_before_union": True,
            "component_id": "sha256(canonical_json(sorted members + protocol sha256))",
            "transitivity": "applies only through connecting edges",
        },
        "resolved_edge_validation": {
            "approved_required_edges_validate_against_candidate_and_disposition": True,
            "recompute_fields": [
                "canonical endpoint order",
                "edge_id",
                "candidate_id",
                "payload hash",
                "source-bundle hash",
                "evidence commitment",
                "review disposition identity",
                "connecting status",
                "review status",
                "confidence category",
                "human-review requirement",
                "rule version",
                "frozen reason",
            ],
        },
        "evidence_source_binding": {
            "source_requirements_are_conjunctive": True,
            "payload_evidence_identities_must_match_source_bundle_identities": True,
        },
        "public_metadata_policy": {
            "snapshot_and_hash_public_metadata": True,
            "allowed_statuses": list(METADATA_STATUSES),
            "live_api_responses_not_silent_dependencies": True,
        },
        "cache_schema": {
            "schema_id": CACHE_SCHEMA_ID,
            "path": ".writer/option-c0/cache/option-c0-family-graph-v1.sqlite3",
            "identity_fields": list(FamilyGraphCacheIdentity.__annotations__),
            "tables": [
                "cache_identity",
                "allocation_repositories",
                "repository_metadata_snapshots",
                "source_records",
                "evidence_candidates",
                "typed_evidence_edges",
                "manual_review_dispositions",
                "component_memberships",
                "phase_commitments",
            ],
            "sqlite_pragmas": {"journal_mode": "WAL", "synchronous": "FULL", "foreign_keys": "ON"},
            "resolved_edge_foreign_keys": {
                "candidate_id": "evidence_candidates(candidate_id)",
                "disposition_id": "manual_review_dispositions(disposition_id)",
            },
            "final_disposition_uniqueness": "one final disposition per candidate",
        },
        "progress_contract": {
            "fields": [
                "phase",
                "completed",
                "total",
                "percentage",
                "cache_hits",
                "cache_misses",
                "request_rate",
                "elapsed_time",
                "ETA",
            ],
            "checkpoint_cadence": "after every durable phase transition and bounded request batch",
            "phase_status_enum": ["PENDING", "IN_PROGRESS", "COMPLETE", "INCOMPLETE", "FAILED"],
            "resume_cursor_requirements": [
                "cursor value",
                "cursor input identity",
                "phase commitment before cursor",
            ],
            "phase_commitment_requirements": [
                "phase name",
                "status",
                "input identities",
                "ordered output commitment",
                "cache identity",
            ],
        },
        "decision_rules": {
            "allowed_outcomes": [
                "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS",
                "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED",
                "FAMILY_GRAPH_INCOMPLETE_METADATA",
                "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED",
            ],
            "family_crossing_observed": "true when a connecting component spans roles",
            "allocation_family_disjointness_violated": (
                "true when any connecting component spans roles"
            ),
            "material_contamination_established": "false in automatic run pending human review",
            "reallocation_required": "null in automatic run pending human review",
            "automatic_reallocation_from_crossing": False,
            "materiality_inputs": [
                "number of connecting family components crossing roles",
                "repositories affected by role pair",
                "rows affected by role pair",
                "largest component",
                "fraction of c0_fit rows affected",
                "fraction of c0_iteration rows affected",
                "hard-edge crossing count",
                "conditional-edge crossing count",
                "whether a valid family-disjoint allocation remains feasible",
            ],
            "materiality_threshold": "no automatic materiality threshold in v1",
            "explicit_human_review_required": True,
        },
        "permitted_inputs": [
            "published repository names",
            "published role assignments",
            "published aggregate row counts",
            "D1 visible-row hashes and bounded metadata",
            "public repository metadata",
        ],
        "prohibited_actions": [
            "canonical family graph execution in this PR",
            "allocation changes",
            "model refits",
            "C0 replay",
            "C0 selection row-content access",
            "C1 reserve row-content access",
            "D2 execution",
        ],
        "firewall_booleans": {
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
            "hidden_row_content_accessed": False,
        },
    }
    contract["protocol_sha256"] = sha256_text(canonical_json(contract))
    return contract


def verify_protocol_contract(contract: Mapping[str, Any]) -> bool:
    expected = dict(contract)
    observed = expected.pop("protocol_sha256", None)
    return observed == sha256_text(canonical_json(expected))


def write_protocol_contract(path: Path, *, overwrite: bool = False) -> dict[str, Any]:
    if path.exists() and not overwrite:
        raise FileExistsError("protocol contract refuses overwrite")
    contract = protocol_contract()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(canonical_json(contract) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)
    return contract


def graph_completeness(
    items: Sequence[EvidenceEdge | EvidenceCandidate],
    *,
    protocol_sha256: str,
    candidates: Mapping[str, EvidenceCandidate],
    dispositions: Mapping[str, ManualReviewDisposition],
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord],
    incomplete_metadata_records: int = 0,
) -> dict[str, int]:
    unresolved = 0
    approved = 0
    review_only = 0
    rejected = 0
    for item in items:
        if isinstance(item, EvidenceCandidate):
            validate_evidence_candidate(item)
            validate_source_registry(
                EDGE_RULES[item.edge_type],
                item.left_repository,
                item.right_repository,
                item.evidence_payload,
                item.evidence_sources,
                source_records,
            )
            rule = EDGE_RULES[item.edge_type]
            if rule.is_connecting_candidate and rule.review_requirement == "APPROVED_REQUIRED":
                unresolved += 1
            elif not rule.is_connecting_candidate:
                review_only += 1
            continue
        candidate = candidates.get(item.candidate_id)
        if candidate is None:
            raise ValueError("graph completeness missing candidate")
        disposition = (
            dispositions.get(item.disposition_id)
            if item.disposition_id is not None
            else None
        )
        validate_resolved_edge(
            item,
            candidate,
            disposition,
            protocol_sha256=protocol_sha256,
            source_records=source_records,
        )
        rule = EDGE_RULES[item.edge_type]
        if rule.is_connecting_candidate and item.review_status == "UNRESOLVED":
            unresolved += 1
        elif item.connecting:
            approved += 1
        elif rule.is_connecting_candidate and item.review_status == "REJECTED":
            rejected += 1
        elif not rule.is_connecting_candidate:
            review_only += 1
    return {
        "unresolved_connecting_candidate_edges": unresolved,
        "approved_connecting_edges": approved,
        "rejected_connecting_candidates": rejected,
        "nonconnecting_review_evidence_edges": review_only,
        "incomplete_metadata_records": incomplete_metadata_records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the frozen Option C0 family-connected protocol contract."
    )
    parser.add_argument("--write-contract", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if args.write_contract:
        write_protocol_contract(args.write_contract, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

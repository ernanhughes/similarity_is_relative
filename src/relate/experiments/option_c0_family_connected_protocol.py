"""Frozen Option C0 family-connected allocation protocol primitives."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

SCHEMA_ID: Final = "option-c0-family-connected-allocation-contract-v1"
EDGE_SCHEMA_ID: Final = "option-c0-family-evidence-edge-v1"
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
ROLE_ORDER: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
REPOSITORY_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_.-]*/[a-z0-9][a-z0-9_.-]*$")
HARD_CONNECTING_EDGE_TYPES: Final = (
    "DECLARED_GITHUB_FORK",
    "VERIFIED_REPOSITORY_SUCCESSION",
    "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
    "VERIFIED_SHARED_PACKAGE_LINEAGE",
)
CONDITIONAL_CONNECTING_EDGE_TYPES: Final = (
    "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
    "SAME_MODULE_LINEAGE_WITH_CORROBORATION",
    "EXPLICIT_COPY_OR_EXTRACTION_HISTORY",
)
NONCONNECTING_EDGE_TYPES: Final = (
    "SAME_OWNER_PROXY",
    "SIMILAR_REPOSITORY_NAME",
    "SUFFIX_STRIPPED_NAME_MATCH",
    "SIMHASH_NEAR_FUNCTION",
    "COMMON_FRAMEWORK_OR_BOILERPLATE",
    "SHARED_LANGUAGE_OR_TOPIC",
)
CONNECTING_EDGE_TYPES: Final = HARD_CONNECTING_EDGE_TYPES + CONDITIONAL_CONNECTING_EDGE_TYPES
ALL_EDGE_TYPES: Final = CONNECTING_EDGE_TYPES + NONCONNECTING_EDGE_TYPES


def canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_repository(repository: str) -> str:
    value = repository.strip().lower()
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise ValueError(f"malformed repository identity: {repository!r}")
    return value


def repository_owner(repository: str) -> str:
    return normalize_repository(repository).split("/", 1)[0]


@dataclass(frozen=True)
class AllocationEntry:
    repository: str
    role: str
    row_count: int


def load_allocation_manifest(path: Path) -> tuple[AllocationEntry, ...]:
    entries: list[AllocationEntry] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        repository = normalize_repository(str(item.get("repository", "")))
        role = str(item.get("role", ""))
        if role not in ROLE_ORDER:
            raise ValueError(f"invalid role at allocation line {line_number}: {role}")
        if repository in seen:
            raise ValueError(f"duplicate allocation repository: {repository}")
        seen.add(repository)
        entries.append(
            AllocationEntry(
                repository=repository,
                role=role,
                row_count=int(item.get("row_count", 0)),
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.repository))


def payload_hash(payload: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(payload))


def condition_complete(edge_type: str, payload: Mapping[str, Any]) -> bool:
    if edge_type == "EXACT_AST_WITH_CORROBORATING_PROVENANCE":
        return all(
            bool(payload.get(field))
            for field in (
                "same_normalized_ast",
                "same_function_identity",
                "same_path_suffix",
                "compatible_repository_dates",
                "public_shared_package_history",
            )
        )
    if edge_type == "SAME_MODULE_LINEAGE_WITH_CORROBORATION":
        return all(
            bool(payload.get(field))
            for field in (
                "same_module_lineage",
                "public_shared_package_history",
                "compatible_repository_dates",
            )
        )
    if edge_type == "EXPLICIT_COPY_OR_EXTRACTION_HISTORY":
        return all(
            bool(payload.get(field))
            for field in ("public_copy_or_extraction_record", "compatible_repository_dates")
        )
    return False


@dataclass(frozen=True)
class EvidenceEdge:
    left_repository: str
    right_repository: str
    edge_type: str
    connecting: bool
    evidence_source: str
    evidence_source_identity: str
    retrieval_timestamp: str
    evidence_payload_hash: str
    rule_version: str
    confidence_category: str
    human_review_required: bool
    reason: str
    evidence_payload: Mapping[str, Any]

    def as_record(self) -> dict[str, Any]:
        return {
            "schema_id": EDGE_SCHEMA_ID,
            "left_repository": self.left_repository,
            "right_repository": self.right_repository,
            "edge_type": self.edge_type,
            "connecting": self.connecting,
            "evidence_source": self.evidence_source,
            "evidence_source_identity": self.evidence_source_identity,
            "retrieval_timestamp": self.retrieval_timestamp,
            "evidence_payload_hash": self.evidence_payload_hash,
            "rule_version": self.rule_version,
            "confidence_category": self.confidence_category,
            "human_review_required": self.human_review_required,
            "reason": self.reason,
            "evidence_payload": dict(self.evidence_payload),
        }


def make_evidence_edge(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
    evidence_source: str,
    evidence_source_identity: str,
    retrieval_timestamp: str,
    evidence_payload: Mapping[str, Any],
    confidence_category: str,
    human_review_required: bool,
    reason: str,
    rule_version: str = "family-protocol-v1",
) -> EvidenceEdge:
    left = normalize_repository(left_repository)
    right = normalize_repository(right_repository)
    if left == right:
        raise ValueError("family evidence edge must connect two distinct repositories")
    if left > right:
        left, right = right, left
    if edge_type not in ALL_EDGE_TYPES:
        raise ValueError(f"unknown family evidence edge type: {edge_type}")
    connecting = False
    if edge_type in HARD_CONNECTING_EDGE_TYPES:
        connecting = bool(evidence_payload.get("required_evidence_complete"))
    elif edge_type in CONDITIONAL_CONNECTING_EDGE_TYPES:
        connecting = condition_complete(edge_type, evidence_payload)
    evidence_hash = payload_hash(evidence_payload)
    return EvidenceEdge(
        left_repository=left,
        right_repository=right,
        edge_type=edge_type,
        connecting=connecting,
        evidence_source=evidence_source,
        evidence_source_identity=evidence_source_identity,
        retrieval_timestamp=retrieval_timestamp,
        evidence_payload_hash=evidence_hash,
        rule_version=rule_version,
        confidence_category=confidence_category,
        human_review_required=human_review_required,
        reason=reason,
        evidence_payload=evidence_payload,
    )


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
        if left_root == right_root:
            return
        first, second = sorted((left_root, right_root))
        self.parent[second] = first


def component_id(members: Sequence[str], protocol_sha256: str) -> str:
    return sha256_text(
        canonical_json({"members": sorted(members), "protocol_sha256": protocol_sha256})
    )


def build_components(
    repositories: Sequence[str],
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str,
) -> list[dict[str, Any]]:
    normalized = sorted({normalize_repository(repository) for repository in repositories})
    uf = UnionFind(normalized)
    for edge in sorted(
        edges,
        key=lambda item: (item.left_repository, item.right_repository, item.edge_type),
    ):
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
    return sha256_text(canonical_json({"components": list(components)}))


def edge_commitment(edges: Sequence[EvidenceEdge]) -> str:
    records = [
        edge.as_record()
        for edge in sorted(
            edges,
            key=lambda item: (item.left_repository, item.right_repository, item.edge_type),
        )
    ]
    return sha256_text(canonical_json({"edges": records}))


def public_metadata_snapshot(
    repository: str,
    status: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "repository": normalize_repository(repository),
        "status": status,
        "snapshot_timestamp": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "payload_hash": payload_hash(payload),
        "payload": dict(payload),
    }


def family_graph_outcome(summary: Mapping[str, Any]) -> dict[str, Any]:
    cross_role_components = int(summary.get("cross_role_connecting_components", 0))
    incomplete_metadata = int(summary.get("incomplete_metadata_records", 0))
    review_required = int(summary.get("manual_review_required_edges", 0))
    exact_or_hard_fit_iteration = bool(summary.get("exact_or_hard_edges_cross_fit_iteration"))
    if incomplete_metadata:
        outcome = "FAMILY_GRAPH_INCOMPLETE_METADATA"
    elif review_required:
        outcome = "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"
    elif cross_role_components:
        outcome = "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED"
    else:
        outcome = "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"
    return {
        "family_graph_outcome": outcome,
        "family_crossing_observed": cross_role_components > 0,
        "allocation_independence_violated": cross_role_components > 0
        and exact_or_hard_fit_iteration,
        "material_contamination_established": False,
        "reallocation_required": None,
        "automatic_reallocation_decision_permitted": False,
        "decision_rule": (
            "cross-role components are observations; material contamination and "
            "reallocation require explicit human review under the frozen protocol"
        ),
    }


def protocol_contract() -> dict[str, Any]:
    contract = {
        "schema_id": SCHEMA_ID,
        "schema_version": "v1",
        "source_allocation_identity": {
            "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
            "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
        },
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
        "repository_normalization_rule": {
            "case": "lowercase",
            "trim_ascii_whitespace": True,
            "required_shape": "owner/repository",
            "allowed_pattern": REPOSITORY_PATTERN.pattern,
        },
        "edge_taxonomy": {
            "hard_connecting": list(HARD_CONNECTING_EDGE_TYPES),
            "conditional_connecting": list(CONDITIONAL_CONNECTING_EDGE_TYPES),
            "nonconnecting_review_evidence": list(NONCONNECTING_EDGE_TYPES),
        },
        "connecting_rules": {
            "hard_edges": "connect only when required_evidence_complete is true",
            "conditional_edges": {
                "EXACT_AST_WITH_CORROBORATING_PROVENANCE": [
                    "same_normalized_ast",
                    "same_function_identity",
                    "same_path_suffix",
                    "compatible_repository_dates",
                    "public_shared_package_history",
                ],
                "SAME_MODULE_LINEAGE_WITH_CORROBORATION": [
                    "same_module_lineage",
                    "public_shared_package_history",
                    "compatible_repository_dates",
                ],
                "EXPLICIT_COPY_OR_EXTRACTION_HISTORY": [
                    "public_copy_or_extraction_record",
                    "compatible_repository_dates",
                ],
            },
            "nonconnecting_edges": "retained for review and never union components",
            "same_owner_alone": "nonconnecting proxy observation",
            "simhash_near_alone": "nonconnecting heuristic observation",
            "transitivity": "applies only through connecting edges",
        },
        "metadata_fields": [
            "left_repository",
            "right_repository",
            "edge_type",
            "connecting",
            "evidence_source",
            "evidence_source_identity",
            "retrieval_timestamp",
            "evidence_payload_hash",
            "rule_version",
            "confidence_category",
            "human_review_required",
            "reason",
        ],
        "component_algorithm": {
            "sort_connecting_edges": True,
            "union_find_uses_connecting_edges_only": True,
            "component_id": "sha256(canonical_json(sorted members + protocol sha256))",
        },
        "public_metadata_policy": {
            "snapshot_and_hash_public_metadata": True,
            "record_unavailable_deleted_renamed_archived_rate_limited": True,
            "live_api_responses_not_silent_dependencies": True,
        },
        "cache_schema": {
            "schema_id": CACHE_SCHEMA_ID,
            "path": ".writer/option-c0/cache/option-c0-family-graph-v1.sqlite3",
            "identity_fields": [
                "family_protocol_sha256",
                "allocation_manifest_sha256",
                "d1_audit_result_sha256",
                "d1_1_classification_sha256",
            ],
            "tables": [
                "cache_identity",
                "repository_metadata_snapshots",
                "typed_evidence_edges",
                "manual_review_dispositions",
                "component_memberships",
                "phase_commitments",
            ],
            "sqlite_pragmas": {
                "journal_mode": "WAL",
                "synchronous": "FULL",
                "foreign_keys": "ON",
            },
        },
        "progress_contract": [
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
        "decision_rules": {
            "allowed_outcomes": [
                "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS",
                "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED",
                "FAMILY_GRAPH_INCOMPLETE_METADATA",
                "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED",
            ],
            "distinctions": [
                "family crossing observed",
                "allocation independence violated",
                "material contamination established",
                "reallocation required",
            ],
            "automatic_reallocation_from_crossing": False,
            "materiality_inputs": [
                "number of connecting family components crossing roles",
                "repositories affected",
                "rows affected by role pair",
                "largest component",
                "fraction of fit rows affected",
                "fraction of iteration rows affected",
                "whether exact or hard edges cross fit and iteration",
                "whether a valid family-disjoint allocation remains feasible",
            ],
            "materiality_threshold": "no automatic threshold in v1; explicit human review required",
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


def write_protocol_contract(path: Path) -> dict[str, Any]:
    contract = protocol_contract()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(contract) + "\n", encoding="utf-8")
    return contract


class FamilyGraphCache:
    def __init__(self, path: Path, *, protocol_sha256: str) -> None:
        self.path = path
        self.protocol_sha256 = protocol_sha256
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self._create_schema()
        self._bind_identity()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> FamilyGraphCache:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cache_identity (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repository_metadata_snapshots (
                repository TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS typed_evidence_edges (
                edge_id TEXT PRIMARY KEY,
                left_repository TEXT NOT NULL,
                right_repository TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                connecting INTEGER NOT NULL,
                edge_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manual_review_dispositions (
                edge_id TEXT PRIMARY KEY,
                disposition TEXT NOT NULL,
                reviewer_note TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS component_memberships (
                component_id TEXT NOT NULL,
                repository TEXT NOT NULL,
                PRIMARY KEY(component_id, repository)
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
        row = self.connection.execute(
            "SELECT value FROM cache_identity WHERE key = 'family_protocol_sha256'"
        ).fetchone()
        if row is not None and row[0] != self.protocol_sha256:
            raise ValueError("family graph cache is bound to a different protocol identity")
        self.connection.execute(
            """
            INSERT INTO cache_identity(key, value)
            VALUES ('family_protocol_sha256', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (self.protocol_sha256,),
        )
        self.connection.commit()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the frozen Option C0 family-connected protocol contract."
    )
    parser.add_argument("--write-contract", type=Path)
    args = parser.parse_args(argv)
    if args.write_contract:
        write_protocol_contract(args.write_contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

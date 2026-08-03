"""Pure connected-component graph construction over resolved family edges.

No database access, CLI parsing, file publication, or workflow
orchestration. Receives validated domain objects (repository names,
``EvidenceEdge`` records) and returns plain component records; it never
reads canonical artifact files or protected row contents.

This module must not import from relate.experiments, relate.workflows, or
relate.cli.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.edges import validate_resolved_edge
from relate.family.models import (
    EvidenceCandidate,
    EvidenceEdge,
    ManualReviewDisposition,
    SourceEvidenceRecord,
)
from relate.family.repositories import normalize_repository


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

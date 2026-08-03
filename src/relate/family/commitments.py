"""Deterministic graph-specific commitments: components and edges.

These bind *scientific graph records* (resolved edges, connected
components) to a SHA-256 identity. This is a distinct concept from the
Stage 2C workflow commitment chain in ``relate.workflows.commitments``,
which binds *execution steps and results*. The two must not be conflated:
a family graph commitment has no notion of a workflow run, and a workflow
step commitment has no notion of family edge types or components.

No database access, CLI parsing, file publication, or workflow
orchestration. This module must not import from relate.experiments,
relate.workflows, or relate.cli.

Source-identity note
---------------------
The historical ``component_commitment`` and ``edge_commitment`` read the
protocol SHA-256 from the historical module's own ``protocol_contract()``
when a caller does not supply one. That is deliberately not reproduced
here: reaching into ``relate.experiments`` would violate this module's
dependency boundary. Both functions here require ``protocol_sha256``
explicitly; the historical module keeps thin wrappers that supply
``protocol_contract()["protocol_sha256"]`` as the default, exactly as
``relate.family.edges.make_evidence_edge`` was wrapped in Stage 2A.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.edges import validate_resolved_edge
from relate.family.graph import _reject_duplicate_edges, component_id
from relate.family.models import (
    EvidenceCandidate,
    EvidenceEdge,
    ManualReviewDisposition,
    SourceEvidenceRecord,
)
from relate.family.repositories import normalize_repository


def component_commitment(
    components: Sequence[Mapping[str, Any]],
    *,
    protocol_sha256: str,
) -> str:
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
    protocol_sha256: str,
    candidates: Mapping[str, EvidenceCandidate] | None = None,
    dispositions: Mapping[str, ManualReviewDisposition] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> str:
    _reject_duplicate_edges(edges)
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
            protocol_sha256=protocol_sha256,
            source_records=source_records,
        )
    records = [edge.as_record() for edge in sorted(edges, key=lambda item: item.edge_id)]
    return sha256_text(canonical_json({"edges": records}))

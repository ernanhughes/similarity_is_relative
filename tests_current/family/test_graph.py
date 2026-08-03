"""Graph-construction tests for relate.family.graph.

Covers UnionFind, component_id determinism, and build_components: isolated
repositories, connecting/nonconnecting/rejected edges, transitive closure,
input-order independence, deterministic ordering, duplicate and unknown
endpoint handling, and full allocation coverage.
"""

from __future__ import annotations

import pytest

from relate.family.edges import (
    make_evidence_candidate,
    make_manual_review_disposition,
    resolve_evidence_candidate,
)
from relate.family.graph import UnionFind, build_components, component_id

TIMESTAMP = "2026-08-02T00:00:00+00:00"
PROTOCOL_SHA = "a" * 64


def _fork_edge(left: str, right: str):
    snapshot_id = "b" * 64
    evidence_sources = {"github_rest": snapshot_id, "public_metadata_snapshot": snapshot_id}
    payload = {
        "left_repository_id": "1",
        "right_repository_id": "2",
        "child_full_name": left,
        "parent_or_source_full_name": right,
        "fork": True,
        "metadata_snapshot_identity": snapshot_id,
        "snapshot_status": "COMPLETE",
    }
    candidate = make_evidence_candidate(
        left,
        right,
        "DECLARED_GITHUB_FORK",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    return resolve_evidence_candidate(candidate, None, protocol_sha256=PROTOCOL_SHA)


def _same_owner_edge(left: str, right: str):
    owner = left.split("/", 1)[0]
    evidence_sources = {"allocation_manifest": "allocation:manifest-v1"}
    payload = {"same_owner": True, "owner": owner}
    candidate = make_evidence_candidate(
        left, right, "SAME_OWNER_PROXY", evidence_sources=evidence_sources, evidence_payload=payload
    )
    return resolve_evidence_candidate(candidate, None, protocol_sha256=PROTOCOL_SHA)


def _succession_edge(left: str, right: str, disposition_outcome: str):
    """Return (edge, dispositions_mapping). Callers must pass the mapping
    through to build_components/graph_completeness for APPROVED_REQUIRED
    edges, exactly as a real caller with a persisted disposition would."""
    snapshot_id = "c" * 64
    evidence_sources = {"public_metadata_snapshot": snapshot_id}
    payload = {
        "predecessor_repository": left,
        "successor_repository": right,
        "direction": "predecessor_to_successor",
        "public_succession_record": "public rename notice",
        "record_snapshot_hash": snapshot_id,
    }
    candidate = make_evidence_candidate(
        left,
        right,
        "VERIFIED_REPOSITORY_SUCCESSION",
        evidence_sources=evidence_sources,
        evidence_payload=payload,
    )
    disposition = make_manual_review_disposition(
        edge_candidate_id=candidate.candidate_id,
        protocol_sha256=PROTOCOL_SHA,
        evidence_commitment=candidate.evidence_commitment,
        disposition=disposition_outcome,
        reviewer_identity="d" * 64,
        review_timestamp=TIMESTAMP,
        bounded_reason="test review",
    )
    edge = resolve_evidence_candidate(candidate, disposition, protocol_sha256=PROTOCOL_SHA)
    return edge, {disposition.disposition_id: disposition}


class TestUnionFind:
    def test_starts_disjoint(self) -> None:
        uf = UnionFind(["owner/a", "owner/b", "owner/c"])
        assert uf.find("owner/a") != uf.find("owner/b")

    def test_union_merges_roots(self) -> None:
        uf = UnionFind(["owner/a", "owner/b"])
        uf.union("owner/a", "owner/b")
        assert uf.find("owner/a") == uf.find("owner/b")

    def test_union_is_transitive(self) -> None:
        uf = UnionFind(["owner/a", "owner/b", "owner/c"])
        uf.union("owner/a", "owner/b")
        uf.union("owner/b", "owner/c")
        assert uf.find("owner/a") == uf.find("owner/c")


class TestComponentId:
    def test_deterministic(self) -> None:
        assert component_id(["owner/a", "owner/b"], PROTOCOL_SHA) == component_id(
            ["owner/a", "owner/b"], PROTOCOL_SHA
        )

    def test_member_order_independent(self) -> None:
        assert component_id(["owner/a", "owner/b"], PROTOCOL_SHA) == component_id(
            ["owner/b", "owner/a"], PROTOCOL_SHA
        )

    def test_protocol_sensitivity(self) -> None:
        assert component_id(["owner/a"], PROTOCOL_SHA) != component_id(["owner/a"], "0" * 64)

    def test_membership_sensitivity(self) -> None:
        assert component_id(["owner/a"], PROTOCOL_SHA) != component_id(
            ["owner/a", "owner/b"], PROTOCOL_SHA
        )


class TestBuildComponentsBasics:
    def test_no_repositories(self) -> None:
        assert build_components([], [], protocol_sha256=PROTOCOL_SHA) == []

    def test_one_isolated_repository(self) -> None:
        components = build_components(["owner/a"], [], protocol_sha256=PROTOCOL_SHA)
        assert len(components) == 1
        assert components[0]["repositories"] == ["owner/a"]
        assert components[0]["repository_count"] == 1

    def test_multiple_isolated_repositories(self) -> None:
        components = build_components(
            ["owner/a", "owner/b", "owner/c"], [], protocol_sha256=PROTOCOL_SHA
        )
        assert len(components) == 3
        assert sorted(c["repository_count"] for c in components) == [1, 1, 1]

    def test_one_connecting_pair(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        components = build_components(["owner/a", "owner/b"], [edge], protocol_sha256=PROTOCOL_SHA)
        assert len(components) == 1
        assert components[0]["repositories"] == ["owner/a", "owner/b"]

    def test_transitive_three_repository_family(self) -> None:
        edge_ab = _fork_edge("owner/a", "owner/b")
        edge_bc, dispositions = _succession_edge("owner/b", "owner/c", "APPROVED")
        components = build_components(
            ["owner/a", "owner/b", "owner/c"],
            [edge_ab, edge_bc],
            protocol_sha256=PROTOCOL_SHA,
            dispositions=dispositions,
        )
        assert len(components) == 1
        assert components[0]["repositories"] == ["owner/a", "owner/b", "owner/c"]

    def test_multiple_disconnected_families(self) -> None:
        edge_ab = _fork_edge("owner/a", "owner/b")
        edge_cd = _fork_edge("owner/c", "owner/d")
        components = build_components(
            ["owner/a", "owner/b", "owner/c", "owner/d", "owner/e"],
            [edge_ab, edge_cd],
            protocol_sha256=PROTOCOL_SHA,
        )
        sizes = sorted(c["repository_count"] for c in components)
        assert sizes == [1, 2, 2]


class TestEdgeParticipation:
    def test_nonconnecting_edge_ignored(self) -> None:
        edge = _same_owner_edge("owner/a", "owner/b")
        components = build_components(["owner/a", "owner/b"], [edge], protocol_sha256=PROTOCOL_SHA)
        assert sorted(c["repository_count"] for c in components) == [1, 1]

    def test_reviewed_rejected_edge_ignored(self) -> None:
        edge, dispositions = _succession_edge("owner/a", "owner/b", "REJECTED")
        assert edge.connecting is False
        components = build_components(
            ["owner/a", "owner/b"], [edge], protocol_sha256=PROTOCOL_SHA, dispositions=dispositions
        )
        assert sorted(c["repository_count"] for c in components) == [1, 1]

    def test_connecting_edge_included(self) -> None:
        edge, dispositions = _succession_edge("owner/a", "owner/b", "APPROVED")
        assert edge.connecting is True
        components = build_components(
            ["owner/a", "owner/b"], [edge], protocol_sha256=PROTOCOL_SHA, dispositions=dispositions
        )
        assert len(components) == 1


class TestDeterminism:
    def test_input_order_independence(self) -> None:
        edge_ab = _fork_edge("owner/a", "owner/b")
        edge_cd = _fork_edge("owner/c", "owner/d")
        forward = build_components(
            ["owner/a", "owner/b", "owner/c", "owner/d"],
            [edge_ab, edge_cd],
            protocol_sha256=PROTOCOL_SHA,
        )
        backward = build_components(
            ["owner/d", "owner/c", "owner/b", "owner/a"],
            [edge_cd, edge_ab],
            protocol_sha256=PROTOCOL_SHA,
        )
        assert forward == backward

    def test_deterministic_component_ordering(self) -> None:
        edge_ab = _fork_edge("owner/a", "owner/b")
        edge_cd = _fork_edge("owner/c", "owner/d")
        components = build_components(
            ["owner/a", "owner/b", "owner/c", "owner/d"],
            [edge_ab, edge_cd],
            protocol_sha256=PROTOCOL_SHA,
        )
        ids = [c["component_id"] for c in components]
        assert ids == sorted(ids)

    def test_deterministic_member_ordering(self) -> None:
        edge = _fork_edge("owner/b", "owner/a")
        components = build_components(["owner/b", "owner/a"], [edge], protocol_sha256=PROTOCOL_SHA)
        assert components[0]["repositories"] == sorted(components[0]["repositories"])

    def test_duplicate_repository_input_is_deduplicated(self) -> None:
        components = build_components(
            ["owner/a", "owner/a", "OWNER/A"], [], protocol_sha256=PROTOCOL_SHA
        )
        assert len(components) == 1
        assert components[0]["repositories"] == ["owner/a"]


class TestValidationAndRejection:
    def test_duplicate_edge_id_rejected(self) -> None:
        edge = _fork_edge("owner/a", "owner/b")
        with pytest.raises(ValueError, match="duplicate edge ID"):
            build_components(["owner/a", "owner/b"], [edge, edge], protocol_sha256=PROTOCOL_SHA)

    def test_unknown_endpoint_rejected(self) -> None:
        edge = _fork_edge("owner/a", "owner/z")
        with pytest.raises(ValueError, match="outside the allocation repository set"):
            build_components(["owner/a", "owner/b"], [edge], protocol_sha256=PROTOCOL_SHA)


class TestFullCoverage:
    def test_every_repository_represented_exactly_once(self) -> None:
        edge_ab = _fork_edge("owner/a", "owner/b")
        repositories = ["owner/a", "owner/b", "owner/c", "owner/d", "owner/e"]
        components = build_components(repositories, [edge_ab], protocol_sha256=PROTOCOL_SHA)
        all_members = [repo for component in components for repo in component["repositories"]]
        assert sorted(all_members) == sorted(repositories)
        assert len(all_members) == len(set(all_members))

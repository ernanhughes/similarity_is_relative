"""Compatibility tests: relate.family.graph/commitments/outcome vs. the
historical facade.

Verifies object identity for symbols with no wrapper, equal behaviour for
the two wrapped commitment functions, and that the protocol payload and SHA
are unaffected by this extraction.
"""

from __future__ import annotations

import relate.experiments.option_c0_family_connected_protocol as historical
import relate.family.commitments as clean_commitments
import relate.family.graph as clean_graph
import relate.family.outcome as clean_outcome

CANONICAL_PROTOCOL_SHA = "a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08"


class TestObjectIdentity:
    def test_union_find_is_same_class(self) -> None:
        assert historical.UnionFind is clean_graph.UnionFind

    def test_build_components_is_same_function(self) -> None:
        assert historical.build_components is clean_graph.build_components

    def test_component_id_is_same_function(self) -> None:
        assert historical.component_id is clean_graph.component_id

    def test_family_graph_outcome_is_same_function(self) -> None:
        assert historical.family_graph_outcome is clean_outcome.family_graph_outcome

    def test_graph_completeness_is_same_function(self) -> None:
        assert historical.graph_completeness is clean_outcome.graph_completeness


class TestGraphBehaviourEquivalence:
    def test_same_components_for_synthetic_input(self) -> None:
        protocol_sha256 = "a" * 64
        via_historical = historical.build_components(
            ["owner/a", "owner/b"], [], protocol_sha256=protocol_sha256
        )
        via_clean = clean_graph.build_components(
            ["owner/a", "owner/b"], [], protocol_sha256=protocol_sha256
        )
        assert via_historical == via_clean

    def test_same_outcome_for_synthetic_summary(self) -> None:
        summary = {"cross_role_connecting_components": 1}
        assert historical.family_graph_outcome(summary) == clean_outcome.family_graph_outcome(
            summary
        )

    def test_same_exception_for_duplicate_edge_id(self) -> None:
        from relate.family.edges import make_evidence_candidate, resolve_evidence_candidate

        snapshot_id = "b" * 64
        evidence_sources = {"github_rest": snapshot_id, "public_metadata_snapshot": snapshot_id}
        payload = {
            "left_repository_id": "1",
            "right_repository_id": "2",
            "child_full_name": "owner/a",
            "parent_or_source_full_name": "owner/b",
            "fork": True,
            "metadata_snapshot_identity": snapshot_id,
            "snapshot_status": "COMPLETE",
        }
        candidate = make_evidence_candidate(
            "owner/a",
            "owner/b",
            "DECLARED_GITHUB_FORK",
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )
        edge = resolve_evidence_candidate(candidate, None, protocol_sha256="a" * 64)
        try:
            historical.build_components(
                ["owner/a", "owner/b"], [edge, edge], protocol_sha256="a" * 64
            )
        except ValueError as hist_exc:
            try:
                clean_graph.build_components(
                    ["owner/a", "owner/b"], [edge, edge], protocol_sha256="a" * 64
                )
            except ValueError as clean_exc:
                assert str(hist_exc) == str(clean_exc)
            else:
                raise AssertionError("clean build_components did not raise")
        else:
            raise AssertionError("historical build_components did not raise")


class TestCommitmentWrapperEquivalence:
    def test_component_commitment_wrapper_matches_clean_with_explicit_sha(self) -> None:
        components = historical.build_components(
            ["owner/a"], [], protocol_sha256=historical.protocol_contract()["protocol_sha256"]
        )
        wrapped = historical.component_commitment(components)
        explicit = clean_commitments.component_commitment(
            components, protocol_sha256=historical.protocol_contract()["protocol_sha256"]
        )
        assert wrapped == explicit

    def test_edge_commitment_wrapper_matches_clean_with_explicit_sha(self) -> None:
        wrapped = historical.edge_commitment([])
        explicit = clean_commitments.edge_commitment(
            [], protocol_sha256=historical.protocol_contract()["protocol_sha256"]
        )
        assert wrapped == explicit


class TestProtocolUnaffected:
    def test_protocol_sha_matches_canonical(self) -> None:
        contract = historical.protocol_contract()
        assert contract["protocol_sha256"] == CANONICAL_PROTOCOL_SHA

    def test_protocol_contract_is_deterministic(self) -> None:
        assert historical.protocol_contract() == historical.protocol_contract()


class TestDependencyDirection:
    def test_family_graph_does_not_import_experiments_or_workflows(self) -> None:
        _assert_no_forbidden_imports(clean_graph)

    def test_family_commitments_does_not_import_experiments_or_workflows(self) -> None:
        _assert_no_forbidden_imports(clean_commitments)

    def test_family_outcome_does_not_import_experiments_or_workflows(self) -> None:
        _assert_no_forbidden_imports(clean_outcome)


def _assert_no_forbidden_imports(module) -> None:
    for name, obj in vars(module).items():
        mod = getattr(obj, "__module__", None) or ""
        if "relate.experiments" in mod or "relate.workflows" in mod:
            raise AssertionError(f"{module.__name__}.{name} is from {mod} (forbidden)")

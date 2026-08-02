from __future__ import annotations

import json
from pathlib import Path

import pytest

from relate.experiments import option_c0_family_connected_protocol as protocol

TIMESTAMP = "2026-08-02T00:00:00+00:00"


def edge(
    left: str,
    right: str,
    edge_type: str,
    payload: dict[str, object] | None = None,
) -> protocol.EvidenceEdge:
    return protocol.make_evidence_edge(
        left,
        right,
        edge_type,
        evidence_source="fixture",
        evidence_source_identity="fixture-sha",
        retrieval_timestamp=TIMESTAMP,
        evidence_payload=payload or {"required_evidence_complete": True},
        confidence_category="high",
        human_review_required=False,
        reason="fixture",
    )


def test_repository_normalization_is_deterministic() -> None:
    assert protocol.normalize_repository(" Sarugaku/Vistir ") == "sarugaku/vistir"
    assert protocol.normalize_repository("sarugaku/vistir") == "sarugaku/vistir"


def test_malformed_repository_identities_are_refused() -> None:
    for value in ("missing-slash", "/repo", "owner/", "UP SPACE/repo"):
        with pytest.raises(ValueError, match="malformed repository"):
            protocol.normalize_repository(value)


def test_declared_forks_form_connecting_edges() -> None:
    item = edge("owner/a", "owner/b", "DECLARED_GITHUB_FORK")
    assert item.connecting is True


def test_exact_source_identity_forms_connecting_edge() -> None:
    item = edge("owner/a", "other/b", "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY")
    assert item.connecting is True


def test_exact_ast_alone_does_not_connect() -> None:
    item = edge(
        "owner/a",
        "owner/b",
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        {"same_normalized_ast": True},
    )
    assert item.connecting is False


def test_same_owner_alone_does_not_connect() -> None:
    item = edge("owner/a", "owner/b", "SAME_OWNER_PROXY", {"same_owner": True})
    assert item.connecting is False


def test_simhash_near_alone_does_not_connect() -> None:
    item = edge("owner/a", "other/b", "SIMHASH_NEAR_FUNCTION", {"hamming_distance": 0})
    assert item.connecting is False


def test_conditional_edges_require_every_frozen_condition() -> None:
    missing = edge(
        "owner/a",
        "owner/b",
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        {
            "same_normalized_ast": True,
            "same_function_identity": True,
            "same_path_suffix": True,
            "compatible_repository_dates": True,
        },
    )
    complete = edge(
        "owner/a",
        "owner/b",
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        {
            "same_normalized_ast": True,
            "same_function_identity": True,
            "same_path_suffix": True,
            "compatible_repository_dates": True,
            "public_shared_package_history": True,
        },
    )
    assert missing.connecting is False
    assert complete.connecting is True


def test_nonconnecting_edges_never_affect_components() -> None:
    contract = protocol.protocol_contract()
    components = protocol.build_components(
        ["owner/a", "owner/b"],
        [edge("owner/a", "owner/b", "SAME_OWNER_PROXY", {"same_owner": True})],
        protocol_sha256=contract["protocol_sha256"],
    )
    assert sorted(component["repository_count"] for component in components) == [1, 1]


def test_connecting_edge_transitivity_is_deterministic() -> None:
    contract = protocol.protocol_contract()
    components = protocol.build_components(
        ["owner/c", "owner/b", "owner/a"],
        [
            edge("owner/b", "owner/c", "DECLARED_GITHUB_FORK"),
            edge("owner/a", "owner/b", "VERIFIED_REPOSITORY_SUCCESSION"),
        ],
        protocol_sha256=contract["protocol_sha256"],
    )
    assert len(components) == 1
    assert components[0]["repositories"] == ["owner/a", "owner/b", "owner/c"]


def test_stable_component_ids_are_order_independent() -> None:
    contract = protocol.protocol_contract()
    first = protocol.build_components(
        ["owner/a", "owner/b"],
        [edge("owner/a", "owner/b", "DECLARED_GITHUB_FORK")],
        protocol_sha256=contract["protocol_sha256"],
    )
    second = protocol.build_components(
        ["OWNER/B", "OWNER/A"],
        [edge("OWNER/B", "OWNER/A", "DECLARED_GITHUB_FORK")],
        protocol_sha256=contract["protocol_sha256"],
    )
    assert first == second


def test_protocol_changes_alter_protocol_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    original = protocol.protocol_contract()["protocol_sha256"]
    monkeypatch.setattr(
        protocol,
        "NONCONNECTING_EDGE_TYPES",
        protocol.NONCONNECTING_EDGE_TYPES + ("NEW_REVIEW_ONLY_EDGE",),
    )
    changed = protocol.protocol_contract()["protocol_sha256"]
    assert changed != original


def test_evidence_payloads_are_hashed() -> None:
    item = edge("owner/a", "owner/b", "DECLARED_GITHUB_FORK", {"required_evidence_complete": True})
    assert item.evidence_payload_hash == protocol.payload_hash({"required_evidence_complete": True})


def test_unavailable_public_metadata_remains_explicit() -> None:
    snapshot = protocol.public_metadata_snapshot(
        "owner/repo",
        "UNAVAILABLE",
        {"http_status": 404, "reason": "deleted"},
    )
    assert snapshot["status"] == "UNAVAILABLE"
    assert snapshot["payload_hash"] == protocol.payload_hash(
        {"http_status": 404, "reason": "deleted"}
    )


def test_cached_metadata_is_bound_to_protocol_identity(tmp_path: Path) -> None:
    cache = tmp_path / "family.sqlite3"
    with protocol.FamilyGraphCache(cache, protocol_sha256="a" * 64):
        pass
    with pytest.raises(ValueError, match="different protocol identity"):
        protocol.FamilyGraphCache(cache, protocol_sha256="b" * 64)


def test_hidden_role_row_contents_are_never_requested() -> None:
    contract = protocol.protocol_contract()
    assert "published aggregate row counts" in contract["permitted_inputs"]
    assert "C0 selection row-content access" in contract["prohibited_actions"]
    assert contract["firewall_booleans"]["c0_selection_row_content_accessed"] is False
    assert contract["firewall_booleans"]["c1_row_content_accessed"] is False


def test_cross_role_components_do_not_automatically_imply_material_contamination() -> None:
    decision = protocol.family_graph_outcome(
        {
            "cross_role_connecting_components": 1,
            "exact_or_hard_edges_cross_fit_iteration": True,
        }
    )
    assert decision["family_crossing_observed"] is True
    assert decision["allocation_independence_violated"] is True
    assert decision["material_contamination_established"] is False


def test_contamination_does_not_automatically_imply_reallocation() -> None:
    decision = protocol.family_graph_outcome(
        {
            "cross_role_connecting_components": 1,
            "exact_or_hard_edges_cross_fit_iteration": True,
        }
    )
    assert decision["reallocation_required"] is None
    assert decision["automatic_reallocation_decision_permitted"] is False


def test_known_sarugaku_fixture_is_not_hard_coded() -> None:
    contract = protocol.protocol_contract()
    encoded = json.dumps(contract, sort_keys=True)
    assert "sarugaku" not in encoded
    assert "shellingham" not in encoded
    assert "vistir" not in encoded


def test_no_canonical_family_graph_is_executed_or_published(tmp_path: Path) -> None:
    output = tmp_path / "contract.json"
    written = protocol.write_protocol_contract(output)
    assert output.exists()
    assert written["prohibited_actions"][0] == "canonical family graph execution in this PR"
    assert not (tmp_path / "option-c0-family-graph-v1.json").exists()


def test_allocation_manifest_rejects_duplicates_and_malformed_entries(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.jsonl"
    malformed.write_text(
        json.dumps({"repository": "owner/repo", "role": "c0_fit", "row_count": 1})
        + "\n"
        + json.dumps({"repository": "OWNER/REPO", "role": "c0_iteration", "row_count": 1})
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate allocation repository"):
        protocol.load_allocation_manifest(malformed)


def test_contract_contains_required_taxonomy_and_cache_policy() -> None:
    contract = protocol.protocol_contract()
    assert contract["edge_taxonomy"]["hard_connecting"] == list(
        protocol.HARD_CONNECTING_EDGE_TYPES
    )
    assert contract["edge_taxonomy"]["nonconnecting_review_evidence"] == list(
        protocol.NONCONNECTING_EDGE_TYPES
    )
    assert contract["cache_schema"]["sqlite_pragmas"] == {
        "journal_mode": "WAL",
        "synchronous": "FULL",
        "foreign_keys": "ON",
    }

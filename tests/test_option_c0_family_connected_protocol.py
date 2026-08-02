from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from relate.experiments import option_c0_family_connected_protocol as protocol

TIMESTAMP = "2026-08-02T00:00:00+00:00"
SOURCE_ID = "a" * 64


def payload(edge_type: str) -> dict[str, object]:
    values: dict[str, dict[str, object]] = {
        "DECLARED_GITHUB_FORK": {
            "left_repository_id": "1",
            "right_repository_id": "2",
            "child_full_name": "owner/a",
            "parent_or_source_full_name": "owner/b",
            "fork": True,
            "parent_or_source_endpoint_equals_other_endpoint": True,
            "metadata_snapshot_identity": "b" * 64,
            "snapshot_status": "COMPLETE",
        },
        "VERIFIED_REPOSITORY_SUCCESSION": {
            "predecessor_repository": "owner/a",
            "successor_repository": "owner/b",
            "direction": "predecessor_to_successor",
            "public_succession_record": "public rename notice",
            "record_snapshot_hash": "c" * 64,
            "review_disposition": "APPROVED",
            "review_disposition_protocol_sha256": protocol.protocol_contract()["protocol_sha256"],
            "review_disposition_evidence_hash": "d" * 64,
        },
        "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY": {
            "identity_scope": "approved_non_generated_module",
            "matching_content_sha256": "e" * 64,
            "left_scope_identity": "f" * 64,
            "right_scope_identity": "1" * 64,
            "source_identity_provenance": "bounded visible source identity",
            "generated_vendor_boilerplate_exclusion": True,
            "complete_evidence_status": "COMPLETE",
        },
        "VERIFIED_SHARED_PACKAGE_LINEAGE": {
            "lineage_record_type": "continuation",
            "approved_lineage_record": "public package continuation",
            "evidence_snapshot_hash": "2" * 64,
            "review_disposition": "APPROVED",
            "review_disposition_protocol_sha256": protocol.protocol_contract()["protocol_sha256"],
            "review_disposition_evidence_hash": "3" * 64,
        },
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE": {
            "same_normalized_ast": True,
            "same_function_identity": True,
            "same_path_suffix": True,
            "compatible_repository_dates": True,
            "public_shared_package_history": True,
            "review_disposition": "APPROVED",
            "review_disposition_protocol_sha256": protocol.protocol_contract()["protocol_sha256"],
            "review_disposition_evidence_hash": "4" * 64,
        },
        "SAME_MODULE_LINEAGE_WITH_CORROBORATION": {
            "same_module_lineage": True,
            "public_shared_package_history": True,
            "compatible_repository_dates": True,
            "review_disposition": "APPROVED",
            "review_disposition_protocol_sha256": protocol.protocol_contract()["protocol_sha256"],
            "review_disposition_evidence_hash": "5" * 64,
        },
        "EXPLICIT_COPY_OR_EXTRACTION_HISTORY": {
            "public_copy_or_extraction_record": "public copy notice",
            "compatible_repository_dates": True,
            "review_disposition": "APPROVED",
            "review_disposition_protocol_sha256": protocol.protocol_contract()["protocol_sha256"],
            "review_disposition_evidence_hash": "6" * 64,
        },
        "EXACT_FUNCTION_SOURCE_MATCH": {
            "left_stable_key": "left",
            "right_stable_key": "right",
            "code_sha256": "7" * 64,
            "visible_role_left": "c0_fit",
            "visible_role_right": "c0_iteration",
        },
        "SAME_OWNER_PROXY": {"same_owner": True, "owner": "owner"},
        "SIMHASH_NEAR_FUNCTION": {
            "left_stable_key": "left",
            "right_stable_key": "right",
            "hamming_distance": 0,
        },
        "SIMILAR_REPOSITORY_NAME": {"similarity_method": "jaro", "score": 0.9},
        "SUFFIX_STRIPPED_NAME_MATCH": {"normalized_family_token": "pkg"},
        "COMMON_FRAMEWORK_OR_BOILERPLATE": {"framework_or_boilerplate_name": "django"},
        "SHARED_LANGUAGE_OR_TOPIC": {"topic_or_language": "python"},
    }
    return dict(values[edge_type])


def source(edge_type: str) -> str:
    rule = protocol.EDGE_RULES[edge_type]
    return rule.evidence_source_requirements[0]


def edge(edge_type: str, evidence_payload: dict[str, object] | None = None):
    return protocol.make_evidence_edge(
        "owner/a",
        "owner/b",
        edge_type,
        evidence_source=source(edge_type),
        evidence_source_identity=SOURCE_ID,
        retrieval_timestamp=TIMESTAMP,
        evidence_payload=evidence_payload or payload(edge_type),
    )


def test_repository_normalization_is_deterministic() -> None:
    assert protocol.normalize_repository(" Sarugaku/Vistir ") == "sarugaku/vistir"


def test_malformed_repository_identities_are_refused() -> None:
    with pytest.raises(ValueError, match="malformed repository"):
        protocol.normalize_repository("missing-slash")


def test_hard_edge_with_only_generic_completeness_is_rejected() -> None:
    with pytest.raises(ValueError, match="unexpected|missing"):
        edge("DECLARED_GITHUB_FORK", {"required_evidence_complete": True})


@pytest.mark.parametrize("value", ["true", "false", 1, [], {}])
def test_non_boolean_values_do_not_satisfy_true_condition(value: object) -> None:
    item = payload("DECLARED_GITHUB_FORK")
    item["fork"] = value
    with pytest.raises(ValueError, match="must be exactly true"):
        edge("DECLARED_GITHUB_FORK", item)


def test_caller_cannot_force_connecting_true() -> None:
    item = edge("SAME_OWNER_PROXY")
    tampered = replace(item, connecting=True)
    with pytest.raises(ValueError, match="connecting"):
        protocol.validate_evidence_edge(
            tampered,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
            allocation_repositories={"owner/a", "owner/b"},
        )


def test_caller_cannot_suppress_required_human_review() -> None:
    item = edge("EXACT_AST_WITH_CORROBORATING_PROVENANCE")
    tampered = replace(item, human_review_required=False)
    with pytest.raises(ValueError, match="human_review_required"):
        protocol.validate_evidence_edge(
            tampered,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
            allocation_repositories={"owner/a", "owner/b"},
        )


def test_one_exact_function_does_not_hard_connect_repositories() -> None:
    assert edge("EXACT_FUNCTION_SOURCE_MATCH").connecting is False


def test_common_dependency_does_not_establish_shared_package_lineage() -> None:
    item = payload("VERIFIED_SHARED_PACKAGE_LINEAGE")
    item["common_dependency_only"] = True
    with pytest.raises(ValueError, match="unexpected|forbidden"):
        edge("VERIFIED_SHARED_PACKAGE_LINEAGE", item)


@pytest.mark.parametrize("field", ["source_body", "hidden_row_content", "raw_embedding"])
def test_forbidden_payload_content_is_rejected_before_hashing(field: str) -> None:
    item = payload("SIMHASH_NEAR_FUNCTION")
    item[field] = "secret"
    with pytest.raises(ValueError, match="forbidden evidence payload field"):
        edge("SIMHASH_NEAR_FUNCTION", item)


def test_tampered_payload_hash_is_rejected() -> None:
    item = edge("DECLARED_GITHUB_FORK")
    tampered = replace(item, evidence_payload_hash="0" * 64)
    with pytest.raises(ValueError, match="evidence_payload_hash"):
        protocol.validate_evidence_edge(
            tampered,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
            allocation_repositories={"owner/a", "owner/b"},
        )


def test_wrong_rule_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="wrong family edge rule version"):
        protocol.make_evidence_edge(
            "owner/a",
            "owner/b",
            "DECLARED_GITHUB_FORK",
            evidence_source="github_rest",
            evidence_source_identity=SOURCE_ID,
            retrieval_timestamp=TIMESTAMP,
            evidence_payload=payload("DECLARED_GITHUB_FORK"),
            rule_version="other",
        )


def test_edge_endpoint_outside_allocation_is_rejected() -> None:
    item = edge("DECLARED_GITHUB_FORK")
    with pytest.raises(ValueError, match="outside the allocation"):
        protocol.build_components(
            ["owner/a"],
            [item],
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_conflicting_duplicate_edge_ids_are_rejected() -> None:
    item = edge("DECLARED_GITHUB_FORK")
    tampered = replace(item, reason="different")
    with pytest.raises(ValueError, match="conflicting duplicate"):
        protocol.edge_commitment([item, tampered])


def test_edge_commitment_is_order_independent_and_material_changes_change_it() -> None:
    first = edge("DECLARED_GITHUB_FORK")
    second = edge("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY")
    assert protocol.edge_commitment([first, second]) == protocol.edge_commitment([second, first])
    changed_payload = payload("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY")
    changed_payload["matching_content_sha256"] = "9" * 64
    changed = edge("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY", changed_payload)
    assert protocol.edge_commitment([first, second]) != protocol.edge_commitment([first, changed])


def test_component_commitment_is_order_independent() -> None:
    contract = protocol.protocol_contract()
    components = protocol.build_components(
        ["owner/c", "owner/a", "owner/b"],
        [
            edge("DECLARED_GITHUB_FORK"),
            protocol.make_evidence_edge(
                "owner/b",
                "owner/c",
                "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
                evidence_source="d1_visible_cache",
                evidence_source_identity=SOURCE_ID,
                retrieval_timestamp=TIMESTAMP,
                evidence_payload=payload("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY"),
            ),
        ],
        protocol_sha256=contract["protocol_sha256"],
    )
    assert protocol.component_commitment(components) == protocol.component_commitment(
        list(reversed(components))
    )


def test_nonconnecting_edges_never_affect_components() -> None:
    components = protocol.build_components(
        ["owner/a", "owner/b"],
        [edge("SAME_OWNER_PROXY")],
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
    )
    assert sorted(component["repository_count"] for component in components) == [1, 1]


def test_conditional_connecting_cross_role_component_violates_family_disjointness() -> None:
    item = edge("EXACT_AST_WITH_CORROBORATING_PROVENANCE")
    assert item.connecting is True
    decision = protocol.family_graph_outcome(
        {
            "cross_role_connecting_components": 1,
            "approved_connecting_edges": 1,
            "hard_or_exact_fit_iteration_crossing_observed": False,
        }
    )
    assert decision["allocation_family_disjointness_violated"] is True
    assert decision["material_contamination_established"] is False
    assert decision["reallocation_required"] is None


def test_nonconnecting_review_evidence_does_not_make_graph_incomplete() -> None:
    completeness = protocol.graph_completeness([edge("SAME_OWNER_PROXY")])
    decision = protocol.family_graph_outcome(completeness)
    assert decision["family_graph_outcome"] == "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS"


def test_unresolved_connecting_candidate_makes_graph_incomplete() -> None:
    item = replace(
        edge("EXACT_AST_WITH_CORROBORATING_PROVENANCE"),
        review_status="UNRESOLVED",
        connecting=False,
    )
    completeness = protocol.graph_completeness([item])
    decision = protocol.family_graph_outcome(completeness)
    assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"


def test_stale_manual_disposition_is_rejected() -> None:
    item = edge("EXACT_AST_WITH_CORROBORATING_PROVENANCE")
    with pytest.raises(ValueError, match="stale"):
        protocol.validate_evidence_edge(
            item,
            protocol_sha256="0" * 64,
            allocation_repositories={"owner/a", "owner/b"},
        )


def test_metadata_snapshot_is_reproducible_and_requires_timestamp() -> None:
    first = protocol.public_metadata_snapshot(
        "owner/repo",
        "COMPLETE",
        TIMESTAMP,
        SOURCE_ID,
        {"fork": False},
    )
    second = protocol.public_metadata_snapshot(
        "OWNER/REPO",
        "COMPLETE",
        TIMESTAMP,
        SOURCE_ID,
        {"fork": False},
    )
    assert first["snapshot_sha256"] == second["snapshot_sha256"]
    with pytest.raises(ValueError, match="timezone-aware"):
        protocol.public_metadata_snapshot("owner/repo", "COMPLETE", "2026-08-02", SOURCE_ID, {})


def test_cache_identity_changes_are_rejected(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    path = tmp_path / "cache" / "family.sqlite3"
    with protocol.FamilyGraphCache(path, identity=identity):
        pass
    for field in identity.as_mapping():
        changed = replace(identity, **{field: "0" * 64})
        with pytest.raises(ValueError, match=field):
            protocol.FamilyGraphCache(path, identity=changed)


def test_sqlite_foreign_key_violation_fails(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    with protocol.FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
        with pytest.raises(sqlite3.IntegrityError):
            cache.connection.execute(
                """
                INSERT INTO repository_metadata_snapshots
                VALUES ('missing/repo', 'COMPLETE', '{}', ?)
                """,
                ("a" * 64,),
            )


def test_allocation_manifest_rejects_bad_row_counts_and_duplicates(tmp_path: Path) -> None:
    for row_count in (-1, True, 1.5, "1"):
        path = tmp_path / f"bad-{row_count}.jsonl"
        path.write_text(
            json.dumps({"repository": "owner/repo", "role": "c0_fit", "row_count": row_count}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="row_count"):
            protocol.load_allocation_manifest(path)
    dup = tmp_path / "dup.jsonl"
    dup.write_text(
        json.dumps({"repository": "owner/repo", "role": "c0_fit", "row_count": 1})
        + "\n"
        + json.dumps({"repository": "OWNER/REPO", "role": "c0_iteration", "row_count": 1}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        protocol.load_allocation_manifest(dup)


def test_actual_canonical_input_hashes_match_frozen_constants() -> None:
    result = protocol.validate_frozen_protocol_inputs(Path.cwd())
    assert result["allocation_manifest_sha256"] == protocol.ALLOCATION_MANIFEST_SHA256
    assert result["d1_audit_result_sha256"] == protocol.D1_RESULT_SHA256
    assert result["d1_1_classification_sha256"] == protocol.D1_1_CLASSIFICATION_SHA256


def test_committed_contract_equals_regenerated_contract_and_sha_verifies() -> None:
    path = Path(
        "artifacts/canonical/option-c0/review-v1/family-protocol-v1/"
        "option-c0-family-connected-allocation-contract-v1.json"
    )
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == protocol.protocol_contract()
    assert protocol.verify_protocol_contract(committed)
    assert committed["protocol_sha256"] == protocol.protocol_contract()["protocol_sha256"]


def test_contract_overwrite_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    protocol.write_protocol_contract(path)
    with pytest.raises(FileExistsError):
        protocol.write_protocol_contract(path)


def test_no_canonical_family_graph_is_executed_or_published(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    contract = protocol.write_protocol_contract(path)
    assert "canonical family graph execution in this PR" in contract["prohibited_actions"]
    assert not Path("artifacts/canonical/option-c0/review-v1/family-graph-v1").exists()

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from relate.experiments import option_c0_family_connected_protocol as protocol

TIMESTAMP = "2026-08-02T00:00:00+00:00"
SOURCE_ID = "a" * 64
PUBLIC_SOURCE_ID = "b" * 64
D1_SOURCE_ID = "e" * 64
CANONICAL_ALLOCATION = Path(
    "artifacts/canonical/option-c0/data-firewall-v1/"
    "option-c0-repository-allocation-v1.jsonl"
)


def payload(edge_type: str) -> dict[str, object]:
    values: dict[str, dict[str, object]] = {
        "DECLARED_GITHUB_FORK": {
            "left_repository_id": "1",
            "right_repository_id": "2",
            "child_full_name": "owner/a",
            "parent_or_source_full_name": "owner/b",
            "fork": True,
            "metadata_snapshot_identity": PUBLIC_SOURCE_ID,
            "snapshot_status": "COMPLETE",
        },
        "VERIFIED_REPOSITORY_SUCCESSION": {
            "predecessor_repository": "owner/a",
            "successor_repository": "owner/b",
            "direction": "predecessor_to_successor",
            "public_succession_record": "public rename notice",
            "record_snapshot_hash": PUBLIC_SOURCE_ID,
        },
        "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY": {
            "identity_scope": "approved_non_generated_module",
            "matching_content_sha256": D1_SOURCE_ID,
            "left_scope_identity": "f" * 64,
            "right_scope_identity": "1" * 64,
            "source_identity_provenance": "bounded visible source identity",
            "generated_vendor_boilerplate_exclusion": True,
            "complete_evidence_status": "COMPLETE",
        },
        "VERIFIED_SHARED_PACKAGE_LINEAGE": {
            "lineage_record_type": "continuation",
            "approved_lineage_record": "public package continuation",
            "evidence_snapshot_hash": PUBLIC_SOURCE_ID,
        },
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE": {
            "same_normalized_ast": True,
            "same_function_identity": True,
            "same_path_suffix": True,
            "compatible_repository_dates": True,
            "public_shared_package_history": True,
        },
        "SAME_MODULE_LINEAGE_WITH_CORROBORATION": {
            "same_module_lineage": True,
            "public_shared_package_history": True,
            "compatible_repository_dates": True,
        },
        "EXPLICIT_COPY_OR_EXTRACTION_HISTORY": {
            "public_copy_or_extraction_record": "public copy notice",
            "compatible_repository_dates": True,
        },
        "EXACT_FUNCTION_SOURCE_MATCH": {
            "left_stable_key": "left",
            "right_stable_key": "right",
            "code_sha256": "7" * 64,
            "d1_visible_evidence_identity": D1_SOURCE_ID,
            "visible_role_left": "c0_fit",
            "visible_role_right": "c0_iteration",
        },
        "SAME_OWNER_PROXY": {"same_owner": True, "owner": "owner"},
        "SIMHASH_NEAR_FUNCTION": {
            "left_stable_key": "left",
            "right_stable_key": "right",
            "hamming_distance": 0,
            "d1_visible_evidence_identity": D1_SOURCE_ID,
        },
        "SIMILAR_REPOSITORY_NAME": {"similarity_method": "jaro", "score": 0.9},
        "SUFFIX_STRIPPED_NAME_MATCH": {"normalized_family_token": "pkg"},
        "COMMON_FRAMEWORK_OR_BOILERPLATE": {"framework_or_boilerplate_name": "django"},
        "SHARED_LANGUAGE_OR_TOPIC": {"topic_or_language": "python"},
    }
    return dict(values[edge_type])


def sources(edge_type: str) -> dict[str, str]:
    rule = protocol.EDGE_RULES[edge_type]
    values = {
        "github_rest": PUBLIC_SOURCE_ID,
        "public_metadata_snapshot": PUBLIC_SOURCE_ID,
        "d1_visible_cache": D1_SOURCE_ID,
        "allocation_manifest": SOURCE_ID,
        "manual_review_record": SOURCE_ID,
        "fixture": SOURCE_ID,
    }
    return {source: values[source] for source in rule.evidence_source_requirements}


def candidate(edge_type: str, evidence_payload: dict[str, object] | None = None):
    return protocol.make_evidence_candidate(
        "owner/a",
        "owner/b",
        edge_type,
        evidence_sources=sources(edge_type),
        evidence_payload=evidence_payload or payload(edge_type),
    )


def disposition(cand, value: str = "APPROVED"):
    return protocol.make_manual_review_disposition(
        edge_candidate_id=cand.candidate_id,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        evidence_commitment=cand.evidence_commitment,
        disposition=value,
        reviewer_identity="sha256:" + "0" * 64,
        review_timestamp=TIMESTAMP,
        bounded_reason="reviewed fixture",
    )


def edge(edge_type: str, evidence_payload: dict[str, object] | None = None):
    cand = candidate(edge_type, evidence_payload)
    disp = None
    if protocol.EDGE_RULES[edge_type].review_requirement == "APPROVED_REQUIRED":
        disp = disposition(cand)
    return protocol.resolve_evidence_candidate(
        cand,
        disp,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
    )


def reviewed_context(edge_type: str = "EXACT_AST_WITH_CORROBORATING_PROVENANCE"):
    cand = candidate(edge_type)
    disp = disposition(cand)
    item = protocol.resolve_evidence_candidate(
        cand,
        disp,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
    )
    return cand, disp, item


def canonical_pair() -> tuple[str, str]:
    entries = protocol.load_allocation_manifest(
        CANONICAL_ALLOCATION,
        expected_sha256=protocol.ALLOCATION_MANIFEST_SHA256,
    )
    return entries[0].repository, entries[1].repository


def reviewed_cache_context():
    left, right = canonical_pair()
    cand = protocol.make_evidence_candidate(
        left,
        right,
        "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        evidence_sources=sources("EXACT_AST_WITH_CORROBORATING_PROVENANCE"),
        evidence_payload=payload("EXACT_AST_WITH_CORROBORATING_PROVENANCE"),
    )
    disp = disposition(cand)
    item = protocol.resolve_evidence_candidate(
        cand,
        disp,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
    )
    return cand, disp, item


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
    cand, disp, item = reviewed_context()
    tampered = replace(item, human_review_required=False)
    with pytest.raises(ValueError, match="human_review_required"):
        protocol.validate_resolved_edge(
            tampered,
            cand,
            disp,
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
        protocol.make_evidence_candidate(
            "owner/a",
            "owner/b",
            "DECLARED_GITHUB_FORK",
            evidence_sources=sources("DECLARED_GITHUB_FORK"),
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
    with pytest.raises(ValueError, match="duplicate edge ID"):
        protocol.edge_commitment([item, tampered])


def test_edge_commitment_is_order_independent_and_material_changes_change_it() -> None:
    first = edge("DECLARED_GITHUB_FORK")
    second = edge("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY")
    assert protocol.edge_commitment([first, second]) == protocol.edge_commitment([second, first])
    changed_payload = payload("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY")
    changed_payload["left_scope_identity"] = "9" * 64
    changed = edge("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY", changed_payload)
    assert protocol.edge_commitment([first, second]) != protocol.edge_commitment([first, changed])


def test_component_commitment_is_order_independent() -> None:
    contract = protocol.protocol_contract()
    components = protocol.build_components(
        ["owner/c", "owner/a", "owner/b"],
        [
            edge("DECLARED_GITHUB_FORK"),
            protocol.resolve_evidence_candidate(
                protocol.make_evidence_candidate(
                "owner/b",
                "owner/c",
                "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
                evidence_sources=sources("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY"),
                evidence_payload=payload("EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY"),
                ),
                None,
                protocol_sha256=contract["protocol_sha256"],
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
    item = candidate("EXACT_AST_WITH_CORROBORATING_PROVENANCE")
    completeness = protocol.graph_completeness([item])
    decision = protocol.family_graph_outcome(completeness)
    assert decision["family_graph_outcome"] == "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED"


def test_stale_manual_disposition_is_rejected() -> None:
    cand, disp, item = reviewed_context()
    with pytest.raises(ValueError, match="stale"):
        protocol.validate_resolved_edge(
            item,
            cand,
            disp,
            protocol_sha256="0" * 64,
            allocation_repositories={"owner/a", "owner/b"},
        )


def test_forged_approved_edge_with_arbitrary_disposition_id_is_rejected() -> None:
    cand, disp, item = reviewed_context()
    tampered = replace(
        item,
        disposition_id="9" * 64,
        review_disposition_identity="9" * 64,
    )
    with pytest.raises(ValueError, match="disposition_id|review_disposition_identity"):
        protocol.validate_resolved_edge(
            tampered,
            cand,
            disp,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_forged_approved_edge_with_arbitrary_edge_id_is_rejected() -> None:
    cand, disp, item = reviewed_context()
    with pytest.raises(ValueError, match="edge_id"):
        protocol.validate_resolved_edge(
            replace(item, edge_id="9" * 64),
            cand,
            disp,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_approved_edge_cannot_validate_without_disposition_record() -> None:
    cand, _disp, item = reviewed_context()
    with pytest.raises(ValueError, match="requires disposition record"):
        protocol.validate_resolved_edge(
            item,
            cand,
            None,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_approved_edge_cannot_validate_with_another_candidate_disposition() -> None:
    cand, _disp, item = reviewed_context()
    other = candidate("VERIFIED_REPOSITORY_SUCCESSION")
    other_disp = disposition(other)
    with pytest.raises(ValueError, match="another candidate|disposition_id"):
        protocol.validate_resolved_edge(
            item,
            cand,
            other_disp,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_approved_edge_cannot_validate_with_stale_evidence_commitment() -> None:
    cand, disp, item = reviewed_context()
    stale = replace(disp, evidence_commitment="9" * 64)
    with pytest.raises(ValueError, match="stale"):
        protocol.validate_resolved_edge(
            item,
            cand,
            stale,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_approved_edge_cannot_validate_with_another_protocol_disposition() -> None:
    cand, _disp, item = reviewed_context()
    stale = protocol.make_manual_review_disposition(
        edge_candidate_id=cand.candidate_id,
        protocol_sha256="9" * 64,
        evidence_commitment=cand.evidence_commitment,
        disposition="APPROVED",
        reviewer_identity="sha256:" + "0" * 64,
        review_timestamp=TIMESTAMP,
        bounded_reason="reviewed fixture",
    )
    with pytest.raises(ValueError, match="stale"):
        protocol.validate_resolved_edge(
            item,
            cand,
            stale,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_unresolved_edge_carrying_disposition_id_is_rejected() -> None:
    cand = candidate("EXACT_AST_WITH_CORROBORATING_PROVENANCE")
    item = protocol.resolve_evidence_candidate(
        cand,
        None,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
    )
    with pytest.raises(ValueError, match="must not carry disposition"):
        protocol.validate_resolved_edge(
            replace(item, disposition_id="9" * 64),
            cand,
            None,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
        )


def test_rejected_edge_remains_nonconnecting() -> None:
    cand = candidate("VERIFIED_REPOSITORY_SUCCESSION")
    disp = disposition(cand, "REJECTED")
    item = protocol.resolve_evidence_candidate(
        cand,
        disp,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
    )
    assert item.connecting is False
    protocol.validate_resolved_edge(
        item,
        cand,
        disp,
        protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
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


def test_incomplete_cache_identity_is_rejected(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    path = tmp_path / "family.sqlite3"
    with protocol.FamilyGraphCache(path, identity=identity):
        pass
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM cache_identity WHERE key = 'd1_audit_result_sha256'")
        connection.commit()
    with pytest.raises(ValueError, match="identity key set"):
        protocol.FamilyGraphCache(path, identity=identity)


def test_data_bearing_cache_with_empty_identity_is_rejected(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    path = tmp_path / "family.sqlite3"
    with protocol.FamilyGraphCache(path, identity=identity) as cache:
        cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
        cache.connection.execute("DELETE FROM cache_identity")
        cache.connection.commit()
    with pytest.raises(ValueError, match="data without identity"):
        protocol.FamilyGraphCache(path, identity=identity)


def test_allocation_rows_are_immutable_under_same_identity(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    with protocol.FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
        cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
        cache.connection.execute(
            "UPDATE allocation_repositories SET role = 'c0_iteration' WHERE repository = "
            "(SELECT repository FROM allocation_repositories WHERE role = 'c0_fit' LIMIT 1)"
        )
        cache.connection.commit()
        with pytest.raises(ValueError, match="allocation repositories differ"):
            cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)


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


def test_cache_disposition_insertion_validates_referenced_candidate(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    with protocol.FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
        cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
        cand, disp, _item = reviewed_cache_context()
        with pytest.raises(ValueError, match="candidate not found"):
            cache.put_manual_review_disposition(disp)
        cache.put_evidence_candidate(cand)
        cache.put_manual_review_disposition(disp)


def test_conflicting_final_dispositions_are_rejected(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    with protocol.FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
        cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
        cand, disp, _item = reviewed_cache_context()
        cache.put_evidence_candidate(cand)
        cache.put_manual_review_disposition(disp)
        conflict = protocol.make_manual_review_disposition(
            edge_candidate_id=cand.candidate_id,
            protocol_sha256=protocol.protocol_contract()["protocol_sha256"],
            evidence_commitment=cand.evidence_commitment,
            disposition="REJECTED",
            reviewer_identity="sha256:" + "1" * 64,
            review_timestamp=TIMESTAMP,
            bounded_reason="conflicting fixture",
        )
        with pytest.raises(ValueError, match="conflicting|UNIQUE"):
            cache.put_manual_review_disposition(conflict)


def test_cached_candidate_and_disposition_retrieval_revalidates_records(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    with protocol.FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
        cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
        cand, disp, _item = reviewed_cache_context()
        cache.put_evidence_candidate(cand)
        cache.put_manual_review_disposition(disp)
        assert cache.get_evidence_candidate(cand.candidate_id) == cand
        assert cache.get_manual_review_disposition(disp.disposition_id) == disp
        row = json.loads(
            cache.connection.execute(
                "SELECT candidate_json FROM evidence_candidates WHERE candidate_id = ?",
                (cand.candidate_id,),
            ).fetchone()[0]
        )
        row["evidence_commitment"] = "9" * 64
        cache.connection.execute(
            "UPDATE evidence_candidates SET candidate_json = ? WHERE candidate_id = ?",
            (json.dumps(row), cand.candidate_id),
        )
        cache.connection.commit()
        with pytest.raises(ValueError, match="tampered"):
            cache.get_evidence_candidate(cand.candidate_id)


def test_resolved_edge_cache_foreign_keys_are_enforced(tmp_path: Path) -> None:
    identity = protocol.default_cache_identity(protocol.protocol_contract()["protocol_sha256"])
    with protocol.FamilyGraphCache(tmp_path / "family.sqlite3", identity=identity) as cache:
        cache.put_canonical_allocation_manifest(CANONICAL_ALLOCATION)
        cand, disp, item = reviewed_cache_context()
        with pytest.raises(ValueError, match="candidate not found"):
            cache.put_resolved_edge(item)
        cache.put_evidence_candidate(cand)
        with pytest.raises(ValueError, match="manual disposition not found"):
            cache.put_resolved_edge(item)
        cache.put_manual_review_disposition(disp)
        cache.put_resolved_edge(item)
        assert cache.get_resolved_edge(item.edge_id) == item


def test_source_snapshot_identities_must_match_source_bundle() -> None:
    fork = payload("DECLARED_GITHUB_FORK")
    fork["metadata_snapshot_identity"] = "9" * 64
    with pytest.raises(ValueError, match="fork snapshot"):
        candidate("DECLARED_GITHUB_FORK", fork)
    succession = payload("VERIFIED_REPOSITORY_SUCCESSION")
    succession["record_snapshot_hash"] = "9" * 64
    with pytest.raises(ValueError, match="succession snapshot"):
        candidate("VERIFIED_REPOSITORY_SUCCESSION", succession)
    lineage = payload("VERIFIED_SHARED_PACKAGE_LINEAGE")
    lineage["evidence_snapshot_hash"] = "9" * 64
    with pytest.raises(ValueError, match="lineage snapshot"):
        candidate("VERIFIED_SHARED_PACKAGE_LINEAGE", lineage)


def test_noncanonical_initial_allocation_subset_is_rejected() -> None:
    with pytest.raises(ValueError, match="noncanonical allocation"):
        protocol.validate_canonical_allocation_entries(
            [protocol.AllocationEntry("owner/a", "c0_fit", 1)]
        )


def test_allocation_repository_commitment_matches_canonical_manifest() -> None:
    entries = protocol.load_allocation_manifest(
        CANONICAL_ALLOCATION,
        expected_sha256=protocol.ALLOCATION_MANIFEST_SHA256,
    )
    assert (
        protocol.allocation_repository_commitment(entries)
        == protocol.ALLOCATION_REPOSITORY_COMMITMENT_SHA256
    )


def test_identical_duplicate_edge_ids_are_rejected() -> None:
    item = edge("DECLARED_GITHUB_FORK")
    with pytest.raises(ValueError, match="duplicate edge ID"):
        protocol.edge_commitment([item, item])


def test_edge_commitment_rejects_tampered_edges() -> None:
    item = edge("DECLARED_GITHUB_FORK")
    with pytest.raises(ValueError, match="edge_id"):
        protocol.edge_commitment([replace(item, edge_id="9" * 64)])


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


def test_missing_d1_or_d11_firewall_keys_are_rejected() -> None:
    d1 = {
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_rows_accessed": False,
        "c1_rows_accessed": False,
        "hidden_row_content_accessed": False,
    }
    d11 = {
        "firewall_booleans": {
            **d1,
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
        }
    }
    missing_d1 = dict(d1)
    missing_d1.pop("scientific_result_observed")
    with pytest.raises(ValueError, match="scientific_result_observed"):
        protocol.validate_firewall_booleans(missing_d1, d11)
    missing_d11 = {"firewall_booleans": dict(d11["firewall_booleans"])}
    missing_d11["firewall_booleans"].pop("c1_row_content_accessed")
    with pytest.raises(ValueError, match="c1_row_content_accessed"):
        protocol.validate_firewall_booleans(d1, missing_d11)


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

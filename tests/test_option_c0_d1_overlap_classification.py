from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from relate.experiments import option_c0_d1_overlap_classification as d11


def write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")


def d1_result() -> dict[str, object]:
    return {
        "schema_id": "option-c0-d1-integrity-audit-v1",
        "status": d11.EXPECTED_D1_STATUS,
        "audit_context_sha256": d11.EXPECTED_AUDIT_CONTEXT_SHA256,
        "next_allowed_action": d11.EXPECTED_D1_NEXT_ACTION,
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_rows_accessed": False,
        "c1_rows_accessed": False,
        "hidden_row_content_accessed": False,
        "c0_selection_row_content_accessed": False,
        "c1_row_content_accessed": False,
        "execution_environment": {
            "git_head": d11.EXPECTED_D1_AUDIT_EXECUTION_GIT_COMMIT,
        },
        "visible_rows": {
            "rows": 2,
            "roles": {"c0_fit": 1, "c0_iteration": 1},
            "repositories": {"c0_fit": 1, "c0_iteration": 1},
        },
        "exact_code_overlap": {"cross_role_hashes": 0, "cross_role_rows": 0},
        "exact_ast_overlap": {
            "cross_role_hashes": 1,
            "cross_role_rows": 2,
            "cross_role_repositories": 2,
        },
        "near_duplicate_candidates": {
            "scan_complete": True,
            "comparison_truncated": False,
            "output_truncated": False,
            "candidate_pairs_generated": 1,
            "candidate_pairs_compared": 1,
            "near_pair_count": 1,
        },
    }


def init_cache(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE visible_rows (
            context_sha256 TEXT NOT NULL,
            role TEXT NOT NULL,
            repository TEXT NOT NULL,
            stable_key TEXT NOT NULL,
            source_split TEXT NOT NULL,
            path TEXT NOT NULL,
            function_id TEXT NOT NULL,
            code_sha256 TEXT NOT NULL,
            normalized_ast_sha256 TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            simhash_hex TEXT NOT NULL,
            PRIMARY KEY (context_sha256, stable_key)
        );
        CREATE TABLE near_pairs (
            context_sha256 TEXT NOT NULL,
            left_key TEXT NOT NULL,
            right_key TEXT NOT NULL,
            hamming_distance INTEGER NOT NULL,
            PRIMARY KEY (context_sha256, left_key, right_key)
        );
        """
    )
    return connection


def write_minimal_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "option-c0-d1-integrity-audit-v1.json"
    write_json(source, d1_result())
    cache_path = tmp_path / "cache.sqlite3"
    connection = init_cache(cache_path)
    keys = sorted(d11.EXACT_STABLE_KEYS)
    insert_row(connection, keys[0], role="c0_iteration", repository="sarugaku/vistir")
    insert_row(connection, keys[1], role="c0_fit", repository="sarugaku/shellingham")
    connection.execute(
        "INSERT INTO near_pairs VALUES (?, ?, ?, 0)",
        (d11.EXPECTED_AUDIT_CONTEXT_SHA256, keys[0], keys[1]),
    )
    connection.commit()
    allocation = tmp_path / "allocation.jsonl"
    allocation.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "repository": "sarugaku/vistir",
                        "role": "c0_iteration",
                        "row_count": 1,
                    }
                ),
                json.dumps(
                    {
                        "repository": "sarugaku/shellingham",
                        "role": "c0_fit",
                        "row_count": 1,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return source, cache_path, allocation


def insert_row(
    connection: sqlite3.Connection,
    stable_key: str,
    *,
    role: str,
    repository: str,
    token_count: int = 6,
    ast: str = d11.EXACT_AST_SHA256,
    simhash: str = "0000000000000000",
) -> None:
    connection.execute(
        """
        INSERT INTO visible_rows
        VALUES (?, ?, ?, ?, 'train', ?, ?, ?, ?, ?, ?)
        """,
        (
            d11.EXPECTED_AUDIT_CONTEXT_SHA256,
            role,
            repository,
            stable_key,
            f"pkg/{stable_key}.py",
            "same_name",
            f"code-{stable_key}".ljust(64, "0")[:64],
            ast,
            token_count,
            simhash,
        ),
    )


def test_immutable_d1_publication_and_overwrite_refusal(tmp_path: Path) -> None:
    source = tmp_path / "option-c0-d1-integrity-audit-v1.json"
    write_json(source, d1_result())
    output_dir = tmp_path / "published"

    publication = d11.publish_d1_result(
        source,
        output_dir,
        repo_root=Path.cwd(),
        expected_d1_result_sha256=d11.sha256_file(source),
    )

    copied = output_dir / source.name
    assert copied.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert publication["audit_result_sha256"] == d11.sha256_file(copied)
    assert (
        publication["d1_audit_execution_git_commit"]
        == d11.EXPECTED_D1_AUDIT_EXECUTION_GIT_COMMIT
    )
    with pytest.raises(FileExistsError, match="refuses overwrite"):
        d11.publish_d1_result(
            source,
            output_dir,
            repo_root=Path.cwd(),
            expected_d1_result_sha256=d11.sha256_file(source),
        )


def test_dirty_worktree_refuses_canonical_generation_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cache_path, allocation = write_minimal_inputs(tmp_path)
    monkeypatch.setattr(d11, "git_status_porcelain", lambda _repo_root: [" M dirty.py"])

    with pytest.raises(RuntimeError, match="git status --porcelain"):
        d11.build_classification(
            d1_result_path=source,
            cache_path=cache_path,
            allocation_path=allocation,
            output_dir=tmp_path / "out",
            docs_path=tmp_path / "report.md",
            repo_root=Path.cwd(),
            expected_d1_result_sha256=d11.sha256_file(source),
        )

    assert not (tmp_path / "out").exists()


def test_dirty_worktree_refuses_before_public_metadata_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cache_path, allocation = write_minimal_inputs(tmp_path)
    monkeypatch.setattr(d11, "git_status_porcelain", lambda _repo_root: ["?? new.py"])

    def fail_metadata(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("metadata should not be requested from a dirty worktree")

    monkeypatch.setattr(d11, "public_metadata_check", fail_metadata)
    with pytest.raises(RuntimeError, match="git status --porcelain"):
        d11.build_classification(
            d1_result_path=source,
            cache_path=cache_path,
            allocation_path=allocation,
            output_dir=tmp_path / "out",
            docs_path=tmp_path / "report.md",
            repo_root=Path.cwd(),
            expected_d1_result_sha256=d11.sha256_file(source),
        )


def test_clean_worktree_is_accepted_and_records_runtime_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cache_path, allocation = write_minimal_inputs(tmp_path)
    monkeypatch.setattr(d11, "git_status_porcelain", lambda _repo_root: [])
    monkeypatch.setattr(d11, "executing_git_commit", lambda _repo_root: "f" * 40)
    monkeypatch.setattr(d11, "current_git_branch", lambda _repo_root: "branch")
    monkeypatch.setattr(
        d11,
        "public_metadata_check",
        lambda *_args, **_kwargs: {"repositories": [], "public_metadata_only": True},
    )

    classification = d11.build_classification(
        d1_result_path=source,
        cache_path=cache_path,
        allocation_path=allocation,
        output_dir=tmp_path / "out",
        docs_path=tmp_path / "report.md",
        repo_root=Path.cwd(),
        expected_d1_result_sha256=d11.sha256_file(source),
    )
    publication = json.loads(
        (tmp_path / "out" / "option-c0-d1-integrity-audit-publication-v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert classification["generator_worktree_clean"] is True
    assert publication["generator_worktree_clean"] is True
    assert classification["d1_1_classification_generator_git_commit"] == "f" * 40
    assert publication["d1_result_publication_generator_git_commit"] == "f" * 40
    assert classification["generator_branch"] == "branch"


def test_test_fixture_override_can_bypass_dirty_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cache_path, allocation = write_minimal_inputs(tmp_path)
    monkeypatch.setattr(d11, "git_status_porcelain", lambda _repo_root: [" M dirty.py"])
    monkeypatch.setattr(
        d11,
        "public_metadata_check",
        lambda *_args, **_kwargs: {"repositories": [], "public_metadata_only": True},
    )

    classification = d11.build_classification(
        d1_result_path=source,
        cache_path=cache_path,
        allocation_path=allocation,
        output_dir=tmp_path / "out",
        docs_path=tmp_path / "report.md",
        repo_root=Path.cwd(),
        allow_dirty_test_fixture_override=True,
        expected_d1_result_sha256=d11.sha256_file(source),
    )
    assert classification["status"] == "D1_1_CLASSIFICATION_COMPLETE"


def test_d1_audit_execution_commit_is_read_from_immutable_result(tmp_path: Path) -> None:
    source = tmp_path / "option-c0-d1-integrity-audit-v1.json"
    write_json(source, d1_result())
    publication = d11.publish_d1_result(
        source,
        tmp_path / "published",
        repo_root=Path.cwd(),
        generator_commit="a" * 40,
        expected_d1_result_sha256=d11.sha256_file(source),
    )
    assert (
        publication["d1_audit_execution_git_commit"]
        == d11.EXPECTED_D1_AUDIT_EXECUTION_GIT_COMMIT
    )


def test_generator_source_manifest_contains_required_paths_and_hash_is_deterministic() -> None:
    first = d11.generator_source_manifest(Path.cwd())
    second = d11.generator_source_manifest(Path.cwd())
    assert set(d11.GENERATOR_SOURCE_PATHS) <= set(first["files"])
    assert first["manifest_sha256"] == second["manifest_sha256"]


def test_exact_stable_key_resolution_from_visible_rows(tmp_path: Path) -> None:
    connection = init_cache(tmp_path / "cache.sqlite3")
    keys = sorted(d11.EXACT_STABLE_KEYS)
    insert_row(connection, keys[0], role="c0_iteration", repository="sarugaku/vistir")
    insert_row(connection, keys[1], role="c0_fit", repository="sarugaku/shellingham")
    rows = d11.load_visible_rows(connection, d11.EXPECTED_AUDIT_CONTEXT_SHA256)

    resolved = d11.resolve_exact_pair(rows, keys)
    review = d11.exact_pair_review(resolved)

    assert {row["stable_key"] for row in resolved} == set(keys)
    assert review["same_normalized_ast"] is True
    assert review["same_source_code"] is False
    assert review["same_owner"] is True
    assert "not by itself proof" in review["owner_evidence_note"]


def test_hidden_stable_key_or_role_rejected(tmp_path: Path) -> None:
    connection = init_cache(tmp_path / "cache.sqlite3")
    key = sorted(d11.EXACT_STABLE_KEYS)[0]
    insert_row(connection, key, role="c0_selection", repository="hidden/repo")

    with pytest.raises(ValueError, match="non-visible"):
        d11.load_visible_rows(connection, d11.EXPECTED_AUDIT_CONTEXT_SHA256)


def test_owner_parsing_from_owner_repository() -> None:
    assert d11.parse_owner("Sarugaku/vistir") == "sarugaku"
    with pytest.raises(ValueError, match="owner/repository"):
        d11.parse_owner("not-a-full-name")


def test_owners_spanning_multiple_roles_and_names_only() -> None:
    analysis = d11.owner_role_analysis(
        [
            {"repository": "same/fit", "role": "c0_fit", "row_count": 3},
            {"repository": "same/iter", "role": "c0_iteration", "row_count": 4},
            {"repository": "same/sel", "role": "c0_selection", "row_count": 5},
            {"repository": "other/res", "role": "c1_reserve", "row_count": 2},
        ],
        sample_limit=2,
    )

    assert analysis["uses_published_repository_names_only"] is True
    assert analysis["c0_selection_row_content_accessed"] is False
    assert analysis["c1_row_content_accessed"] is False
    assert analysis["owners_appearing_in_more_than_one_allocation_role"] == 1
    assert analysis["owners_spanning_c0_fit_and_c0_iteration"] == 1
    assert analysis["owners_spanning_c0_fit_and_c0_selection"] == 1
    assert analysis["owners_spanning_three_or_four_roles"] == 1


def test_bounded_repository_samples() -> None:
    analysis = d11.owner_role_analysis(
        [
            {"repository": "same/a", "role": "c0_fit", "row_count": 1},
            {"repository": "same/b", "role": "c0_fit", "row_count": 1},
            {"repository": "same/c", "role": "c0_iteration", "row_count": 1},
        ],
        sample_limit=2,
    )

    group = analysis["cross_role_owner_groups"][0]
    assert len(group["repository_name_sample"]) == 2
    assert group["sample_truncated"] is True


def review_rows() -> dict[str, d11.ReviewRow]:
    return {
        "a": d11.ReviewRow(
            role="c0_fit",
            repository="same/pkg",
            stable_key="a",
            source_split="train",
            path="pkg/a.py",
            function_id="f",
            token_count=4,
            code_sha256="a" * 64,
            normalized_ast_sha256="1" * 64,
            simhash_hex="0" * 16,
        ),
        "b": d11.ReviewRow(
            role="c0_iteration",
            repository="same/pkg-core",
            stable_key="b",
            source_split="train",
            path="pkg/b.py",
            function_id="g",
            token_count=5,
            code_sha256="b" * 64,
            normalized_ast_sha256="2" * 64,
            simhash_hex="0" * 16,
        ),
        "c": d11.ReviewRow(
            role="c0_iteration",
            repository="different/other",
            stable_key="c",
            source_split="train",
            path="pkg/c.py",
            function_id="h",
            token_count=20,
            code_sha256="c" * 64,
            normalized_ast_sha256="3" * 64,
            simhash_hex="1" * 16,
        ),
    }


def test_near_pair_hamming_histogram_and_same_owner_counts() -> None:
    analysis = d11.near_pair_analysis(review_rows(), [("a", "b", 0), ("a", "c", 2)])

    assert analysis["hamming_distance_histogram"] == {"0": 1, "2": 1}
    assert analysis["same_owner_pair_count"] == 1
    assert analysis["different_owner_pair_count"] == 1
    assert analysis["same_suffix_stripped_family_count"] == 1


def test_connected_component_construction() -> None:
    components = d11.connected_components([("a", "b"), ("b", "c"), ("d", "e")])
    assert sorted(len(component) for component in components) == [2, 3]


def test_short_function_collision_classification() -> None:
    rows = review_rows()
    assert d11.classify_near_pair(rows["a"], rows["b"], 0) == "GENERIC_SHORT_FUNCTION_COLLISION"


def test_exact_pair_retained_separately_from_heuristic_pairs() -> None:
    keys = sorted(d11.EXACT_STABLE_KEYS)
    rows = {
        keys[0]: d11.ReviewRow(
            "c0_fit",
            "same/a",
            keys[0],
            "train",
            "a.py",
            "f",
            10,
            "a" * 64,
            d11.EXACT_AST_SHA256,
            "0" * 16,
        ),
        keys[1]: d11.ReviewRow(
            "c0_iteration",
            "same/b",
            keys[1],
            "train",
            "b.py",
            "g",
            12,
            "b" * 64,
            d11.EXACT_AST_SHA256,
            "0" * 16,
        ),
    }
    analysis = d11.near_pair_analysis(rows, [(keys[0], keys[1], 0)])
    assert analysis["pairs_involving_the_exact_ast_match"] == 1
    assert analysis["classification_counts"]["EXACT_AST_RELATED_OWNER"] == 1


def test_owner_crossings_alone_do_not_imply_reallocation() -> None:
    exact = {"same_owner": False}
    owner = {"owners_spanning_c0_fit_and_c0_iteration": 168}
    near = {"same_owner_pair_count": 0}
    decision = d11.classify_overall(exact, owner, near)
    assert decision["overall_outcome"] == "D1_CLASSIFICATION_INCONCLUSIVE"
    assert decision["reallocation_required"] is None
    assert decision["material_contamination_established"] is False


def test_same_owner_near_pairs_alone_do_not_imply_reallocation() -> None:
    exact = {"same_owner": True}
    owner = {"owners_spanning_c0_fit_and_c0_iteration": 0}
    near = {"same_owner_pair_count": 3}
    decision = d11.classify_overall(exact, owner, near)
    assert decision["overall_outcome"] == "D1_CLASSIFICATION_INCONCLUSIVE"
    assert decision["reallocation_required"] is None


def test_owner_crossings_plus_near_pairs_need_frozen_rule_for_reallocation() -> None:
    exact = {"same_owner": True}
    owner = {"owners_spanning_c0_fit_and_c0_iteration": 168}
    near = {"same_owner_pair_count": 3}
    decision = d11.classify_overall(exact, owner, near)
    assert decision["overall_outcome"] == "D1_CLASSIFICATION_INCONCLUSIVE"
    assert decision["next_allowed_action"] == "FREEZE_FAMILY_CONNECTED_REALLOCATION_PROTOCOL"
    assert decision["family_identity_rule_status"] == "NOT_FROZEN"
    assert decision["owner_proxy_crossings_observed"] == 168
    assert decision["confirmed_related_family_crossings"] is None
    assert decision["reallocation_required"] is None


def test_same_owner_exact_ast_is_possible_family_not_proven_leakage() -> None:
    exact = {"same_owner": True}
    owner = {"owners_spanning_c0_fit_and_c0_iteration": 168}
    near = {"same_owner_pair_count": 3}
    decision = d11.classify_overall(exact, owner, near)
    assert (
        decision["exact_pair_classification"]
        == "POSSIBLE_RELATED_REPOSITORY_FAMILY_LEAKAGE"
    )
    assert decision["exact_pair_classification"] != "RELATED_REPOSITORY_FAMILY_LEAKAGE"


def test_reallocation_cannot_be_emitted_when_family_rule_not_frozen() -> None:
    exact = {"same_owner": True}
    owner = {"owners_spanning_c0_fit_and_c0_iteration": 168}
    near = {"same_owner_pair_count": 3}
    decision = d11.classify_overall(
        exact,
        owner,
        near,
        family_identity_rule_status="NOT_FROZEN",
    )
    assert decision["overall_outcome"] != "D1_RELATED_REPOSITORY_REALLOCATION_REQUIRED"
    assert decision["reallocation_required"] is None


def test_all_hidden_row_firewall_booleans_remain_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cache_path, allocation = write_minimal_inputs(tmp_path)
    monkeypatch.setattr(
        d11,
        "public_metadata_check",
        lambda *_args, **_kwargs: {"repositories": [], "public_metadata_only": True},
    )

    classification = d11.build_classification(
        d1_result_path=source,
        cache_path=cache_path,
        allocation_path=allocation,
        output_dir=tmp_path / "out",
        docs_path=tmp_path / "report.md",
        repo_root=Path.cwd(),
        allow_dirty_test_fixture_override=True,
        expected_d1_result_sha256=d11.sha256_file(source),
    )

    assert all(value is False for value in classification["firewall_booleans"].values())


def test_canonical_result_and_publication_hashes_verify(tmp_path: Path) -> None:
    source = tmp_path / "option-c0-d1-integrity-audit-v1.json"
    write_json(source, d1_result())
    output_dir = tmp_path / "published"
    d11.publish_d1_result(
        source,
        output_dir,
        repo_root=Path.cwd(),
        expected_d1_result_sha256=d11.sha256_file(source),
    )
    assert d11.verify_publication_hashes(
        output_dir / source.name,
        output_dir / "option-c0-d1-integrity-audit-publication-v1.json",
    )

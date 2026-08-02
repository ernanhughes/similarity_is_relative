from __future__ import annotations

import json
from pathlib import Path

import pytest

from relate.experiments.option_c0_data_firewall import (
    ALLOCATION_SCHEMA,
    AppendOnlyViolation,
    AllocationConfig,
    C1SelectionForbidden,
    InsufficientRepositoriesError,
    allocate_repositories,
    append_discovery,
    change_candidate_status,
    delete_candidate,
    load_option_b_repository_exclusions,
    mutate_candidate,
    publish_allocation_bundle,
    read_candidate_registry,
    read_discovery_ledger,
    reconstruct_eligible_pool,
    record_candidate_evaluation,
    register_candidate,
    select_c1_rows,
    verify_allocation_bundle,
    verify_artifact_hashes,
    verify_role_disjointness,
)


def _rows(repository_count: int = 20, rows_per_repository: int = 2):
    rows = []
    for repository_index in range(repository_count):
        repository = f"repo-{repository_index:03d}"
        for row_index in range(rows_per_repository):
            identity = f"{repository}-{row_index}"
            rows.append(
                {
                    "repository": repository,
                    "stable_key": identity,
                    "source_split": ("train", "validation", "test")[
                        repository_index % 3
                    ],
                    "path": f"src/{identity}.py",
                    "function_id": identity,
                    "code_sha256": "a" * 64,
                    "normalized_ast_sha256": f"{repository_index:064x}",
                    "token_count": 64,
                }
            )
    return rows


def _allocation(rows=None, exclusions=(), identity="1" * 64):
    return allocate_repositories(
        rows or _rows(),
        exclusions,
        AllocationConfig(),
        source_identity_commitment=identity,
    )


def _candidate():
    return {
        "candidate_id": "fixture",
        "version": "v1",
        "commit_sha": "a" * 40,
        "support_object_definition": "fixture interval",
        "propagation_rule": "fixture intersection",
        "query_form": "fixture AND",
        "confidence_score": "fixture residual",
        "data_roles": ["C0_FIT", "C0_ITERATION"],
        "hyperparameters": {"fixture": 1},
        "expected_failure_mode": "fixture only",
        "status": "active",
        "timestamp": "2026-08-02T12:00:00Z",
        "predecessor_version": None,
        "artifact_hashes": {"fixture": "b" * 64},
    }


def _discovery():
    return {
        "discovery_id": "D-FIXTURE-001",
        "classification": "IMPLEMENTATION_OR_DATA_INTEGRITY_FINDING",
        "first_observed_timestamp": "2026-08-02T12:00:00Z",
        "first_observed_commit": "c" * 40,
        "first_observed_data_role": "C0_ITERATION",
        "anticipated": True,
        "observation": "fixture observation",
        "affected_candidates_or_assumptions": ["fixture"],
        "possible_explanations": ["fixture"],
        "action_taken": "fixture action",
        "c1_contract_relevance": False,
        "fresh_evidence_requirement": "fixture only",
        "artifact_hashes": {"fixture": "d" * 64},
    }


def test_repository_allocation_is_deterministic_and_disjoint():
    first = _allocation()
    second = _allocation()
    assert first == second
    verify_role_disjointness(first["assignments"])
    assert first["checks"]["pairwise_role_disjointness"] is True
    assert first["c1_rows_selected"] is False


def test_option_b_repositories_are_excluded_whole():
    result = _allocation(exclusions={"repo-002", "repo-009"})
    allocated = {item["repository"] for item in result["assignments"]}
    assert "repo-002" not in allocated
    assert "repo-009" not in allocated
    assert result["option_b_exclusion"]["excluded_eligible_rows"] == 4
    assert result["checks"]["option_b_repositories_excluded"] is True


def test_allocation_context_changes_with_source_identity_commitment():
    first = _allocation(identity="1" * 64)
    second = _allocation(identity="2" * 64)
    assert first["allocation_context_sha256"] != second["allocation_context_sha256"]
    first_keys = [item["repository_order_key"] for item in first["assignments"]]
    second_keys = [item["repository_order_key"] for item in second["assignments"]]
    assert first_keys != second_keys


def test_insufficient_roles_refuse_borrowing():
    config = AllocationConfig(minimum_repositories=(2, 2, 2, 2))
    with pytest.raises(InsufficientRepositoriesError):
        allocate_repositories(
            _rows(repository_count=7),
            (),
            config,
            source_identity_commitment="1" * 64,
        )


def test_c1_row_selection_is_unavailable():
    with pytest.raises(C1SelectionForbidden):
        select_c1_rows()


def test_allocation_publication_refuses_overwrite_and_verifies(tmp_path: Path):
    output = tmp_path / "allocation"
    allocation = _allocation()
    result = publish_allocation_bundle(output, allocation)
    assert result["status"] == "C0_DATA_FIREWALL_BUNDLE_VERIFIED"
    assert verify_allocation_bundle(output) == result
    with pytest.raises(FileExistsError):
        publish_allocation_bundle(output, allocation)


def test_candidate_registry_is_append_only_and_hash_chained(tmp_path: Path):
    path = tmp_path / "candidates.jsonl"
    registered = register_candidate(path, _candidate())
    assert registered["sequence"] == 0
    evaluated = record_candidate_evaluation(
        path,
        candidate_id="fixture",
        version="v1",
        commit_sha="e" * 40,
        timestamp="2026-08-02T12:01:00Z",
        artifact_hashes={"evaluation": "f" * 64},
    )
    assert evaluated["sequence"] == 1
    changed = change_candidate_status(
        path,
        candidate_id="fixture",
        version="v1",
        status="selected_for_c0_selection",
        commit_sha="e" * 40,
        timestamp="2026-08-02T12:02:00Z",
    )
    assert changed["sequence"] == 2
    events = read_candidate_registry(path)
    assert [event["event_type"] for event in events] == [
        "REGISTERED",
        "EVALUATED",
        "STATUS_CHANGED",
    ]


def test_evaluated_candidate_cannot_be_mutated_deleted_or_registered_again(tmp_path: Path):
    path = tmp_path / "candidates.jsonl"
    register_candidate(path, _candidate())
    record_candidate_evaluation(
        path,
        candidate_id="fixture",
        version="v1",
        commit_sha="e" * 40,
        timestamp="2026-08-02T12:01:00Z",
        artifact_hashes={"evaluation": "f" * 64},
    )
    with pytest.raises(AppendOnlyViolation):
        register_candidate(path, _candidate())
    with pytest.raises(AppendOnlyViolation):
        mutate_candidate(path, "fixture", "v1")
    with pytest.raises(AppendOnlyViolation):
        delete_candidate(path, "fixture", "v1")


def test_candidate_must_be_evaluated_before_selection(tmp_path: Path):
    path = tmp_path / "candidates.jsonl"
    register_candidate(path, _candidate())
    with pytest.raises(AppendOnlyViolation):
        change_candidate_status(
            path,
            candidate_id="fixture",
            version="v1",
            status="selected_for_c0_selection",
            commit_sha="e" * 40,
            timestamp="2026-08-02T12:02:00Z",
        )


def test_discovery_ledger_append_semantics(tmp_path: Path):
    path = tmp_path / "discoveries.jsonl"
    entry = append_discovery(path, _discovery())
    assert entry["sequence"] == 0
    assert read_discovery_ledger(path)[0]["discovery_id"] == "D-FIXTURE-001"
    with pytest.raises(AppendOnlyViolation):
        append_discovery(path, _discovery())


def test_discovery_classification_and_phase_are_enforced(tmp_path: Path):
    path = tmp_path / "discoveries.jsonl"
    invalid_classification = _discovery()
    invalid_classification["classification"] = "CONFIRMED_FINDING"
    with pytest.raises(ValueError):
        append_discovery(path, invalid_classification)

    invalid_phase = _discovery()
    invalid_phase["first_observed_data_role"] = "C1_TEST_RESERVE"
    with pytest.raises(ValueError):
        append_discovery(path, invalid_phase)


def test_artifact_hash_format_and_file_verification(tmp_path: Path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("evidence\n", encoding="utf-8", newline="\n")
    import hashlib

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    verify_artifact_hashes(tmp_path, {"artifact.txt": digest})
    with pytest.raises(ValueError):
        verify_artifact_hashes(tmp_path, {"artifact.txt": "0" * 64})

    candidate = _candidate()
    candidate["artifact_hashes"] = {"bad": "not-a-hash"}
    with pytest.raises(ValueError):
        register_candidate(tmp_path / "candidate.jsonl", candidate)


def test_chain_tampering_is_detected(tmp_path: Path):
    path = tmp_path / "discoveries.jsonl"
    append_discovery(path, _discovery())
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["payload"]["observation"] = "silently changed"
    path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
    with pytest.raises(AppendOnlyViolation):
        read_discovery_ledger(path)


def test_config_schema_and_roles_are_frozen():
    config = AllocationConfig.from_mapping(
        {
            "schema_id": ALLOCATION_SCHEMA,
            "domain": "fixture-domain",
            "role_weights": [5, 2, 1, 2],
            "minimum_repositories": [1, 1, 1, 1],
        }
    )
    assert config.to_dict()["role_names"] == [
        "c0_fit",
        "c0_iteration",
        "c0_selection",
        "c1_reserve",
    ]


class _Tokenizer:
    def __call__(self, code: str, **_: object):
        return {"input_ids": list(range(32))}


def test_eligible_pool_reconstruction_is_reproducible(tmp_path: Path):
    identity = tmp_path / "identity.json"
    identity.write_text(
        json.dumps(
            {
                "status": "IDENTITY_CAPTURE_COMPLETE",
                "model": {
                    "repo_id": "microsoft/codebert-base",
                    "revision": "model-revision",
                },
                "dataset": {
                    "repo_id": "code-search-net/code_search_net",
                    "revision": "dataset-revision",
                    "subset": "python",
                },
                "fixture": {"matrix_sha256": "fixture"},
                "pooling_implementation_sha256": "pooling",
            }
        ),
        encoding="utf-8",
    )
    dataset = {
        split: [
            {
                "repository_name": f"repo-{split}",
                "func_path_in_repository": f"src/{split}.py",
                "func_name": split,
                "whole_func_string": f"def {split}(x):\n    return x\n",
            }
        ]
        for split in ("train", "validation", "test")
    }
    first_rows, first_report = reconstruct_eligible_pool(
        identity, dataset_by_split=dataset, tokenizer=_Tokenizer()
    )
    second_rows, second_report = reconstruct_eligible_pool(
        identity, dataset_by_split=dataset, tokenizer=_Tokenizer()
    )
    assert first_rows == second_rows
    assert first_report == second_report
    assert first_report["eligible_rows"] == 3
    assert first_report["c1_rows_selected"] is False


def test_option_b_exclusion_loader_verifies_hashes(tmp_path: Path):
    import hashlib

    artifacts = {}
    for split in ("train", "validation", "test"):
        path = tmp_path / f"option-b-selected-{split}-v2.jsonl"
        payload = json.dumps(
            {"repository": f"repo-{split}", "stable_key": split},
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        path.write_text(payload, encoding="utf-8", newline="\n")
        artifacts[split] = {
            "selected_manifest": {
                "sha256": hashlib.sha256(payload.encode()).hexdigest(),
                "rows": 1,
            }
        }
    (tmp_path / "option-b-canonical-row-selection-v2.json").write_text(
        json.dumps(
            {
                "selection_id": "option-b-canonical-row-selection-v2",
                "artifacts": artifacts,
            }
        ),
        encoding="utf-8",
    )
    repositories, report = load_option_b_repository_exclusions(tmp_path)
    assert repositories == {"repo-train", "repo-validation", "repo-test"}
    assert report["repository_count"] == 3

    train_path = tmp_path / "option-b-selected-train-v2.jsonl"
    train_path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_option_b_repository_exclusions(tmp_path)

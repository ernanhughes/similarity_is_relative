from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from relate.experiments.option_b_hard_negative_manifest import (
    FrozenManifestConfig,
    assign_token_deciles,
    construct_query_manifest,
    generate_hard_negative_manifest,
    token_decile_boundaries,
)


def _scaled_rows(count: int) -> np.ndarray:
    values = np.arange(count, dtype=np.float64)
    return np.column_stack((values, values * 0.5, values * 0.25))


def test_generator_api_has_no_embedding_prediction_or_method_inputs() -> None:
    parameters = inspect.signature(generate_hard_negative_manifest).parameters
    assert set(parameters) == {
        "selection_dir",
        "probe_checkpoint_path",
        "output_dir",
    }


def test_token_deciles_use_candidate_boundaries_and_right_ties() -> None:
    counts = np.arange(10, 110, 10, dtype=np.int64)
    boundaries = token_decile_boundaries(counts, deciles=10)
    assigned = assign_token_deciles(
        np.asarray((10, boundaries[1], 100), dtype=np.float64),
        boundaries,
    )
    assert assigned.tolist() == [0, 1, 9]


def test_ties_are_excluded_and_zero_pair_query_is_retained() -> None:
    train = np.zeros((8, 3), dtype=np.float64)
    result = construct_query_manifest(
        query_index=0,
        query_stable_key="q",
        query_repository="repo",
        query_token_count=50,
        query_true_scaled=np.zeros(3),
        train_stable_keys=tuple(f"c-{index}" for index in range(8)),
        train_true_scaled=train,
        candidate_deciles=np.zeros(8, dtype=np.int64),
        query_decile=0,
        config=FrozenManifestConfig(
            min_rank_separation=1,
            max_rank_separation=2,
            max_pairs_per_query=4,
            sparse_pair_threshold=2,
        ),
    )
    assert result.pairs == ()
    assert result.summary["zero_informative_pairs"] is True
    assert result.summary["sparse"] is True
    assert result.summary["oracle_tie_exclusion_count"] > 0


def test_sparse_query_retains_every_eligible_pair() -> None:
    train = _scaled_rows(5)
    result = construct_query_manifest(
        query_index=2,
        query_stable_key="q",
        query_repository="repo",
        query_token_count=50,
        query_true_scaled=np.zeros(3),
        train_stable_keys=tuple(f"c-{index}" for index in range(5)),
        train_true_scaled=train,
        candidate_deciles=np.zeros(5, dtype=np.int64),
        query_decile=0,
        config=FrozenManifestConfig(
            min_rank_separation=1,
            max_rank_separation=1,
            max_pairs_per_query=128,
            sparse_pair_threshold=32,
        ),
    )
    assert result.summary["eligible_pair_count"] == 4
    assert result.summary["selected_pair_count"] == 4
    assert result.summary["sparse"] is True


def test_pair_cap_uses_ascending_sha_order() -> None:
    train = _scaled_rows(20)
    result = construct_query_manifest(
        query_index=0,
        query_stable_key="q",
        query_repository="repo",
        query_token_count=50,
        query_true_scaled=np.zeros(3),
        train_stable_keys=tuple(f"candidate-{index:02d}" for index in range(20)),
        train_true_scaled=train,
        candidate_deciles=np.zeros(20, dtype=np.int64),
        query_decile=0,
        config=FrozenManifestConfig(
            min_rank_separation=1,
            max_rank_separation=3,
            max_pairs_per_query=7,
            sparse_pair_threshold=2,
        ),
    )
    hashes = [row["selection_sha256"] for row in result.pairs]
    assert len(hashes) == 7
    assert hashes == sorted(hashes)
    assert [row["pair_order"] for row in result.pairs] == list(range(7))


def _write_json(path: Path, value: object) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")
    import hashlib

    return hashlib.sha256(payload.encode()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            handle.write(line)
            digest.update(line.encode())
    return digest.hexdigest()


def test_full_runner_writes_every_query_and_no_method_evidence(tmp_path: Path) -> None:
    selection = tmp_path / "selection"
    selection.mkdir()
    output = tmp_path / "out"
    checkpoint = tmp_path / "probe.json"

    _write_json(
        checkpoint,
        {
            "checkpoint_id": "option-b-primitive-probe-publication-v1",
            "status": "PRIMITIVE_PROBE_ARTIFACTS_PUBLISHED_PENDING_REVIEW",
            "scientific_result_observed": False,
            "next_allowed_action": "HARD_NEGATIVE_MANIFEST_IMPLEMENTATION_REVIEW",
            "source_fit": {"test_primitive_labels_loaded": False, "folds": 5},
        },
    )

    train_manifest = [
        {
            "stable_key": f"train-{index}",
            "repository": "train-repo",
            "token_count": 50 + index,
        }
        for index in range(12)
    ]
    test_manifest = [
        {
            "stable_key": f"test-{index}",
            "repository": "test-repo",
            "token_count": 51 + index,
        }
        for index in range(3)
    ]
    train_primitive = [
        {
            "stable_key": f"train-{index}",
            "cyclomatic_complexity": index,
            "max_control_depth": index / 2,
            "distinct_call_sites": index / 3,
        }
        for index in range(12)
    ]
    test_primitive = [
        {
            "stable_key": f"test-{index}",
            "cyclomatic_complexity": index,
            "max_control_depth": index / 2,
            "distinct_call_sites": index / 3,
        }
        for index in range(3)
    ]

    hashes = {}
    for split, manifest, primitive in (
        ("train", train_manifest, train_primitive),
        ("test", test_manifest, test_primitive),
    ):
        hashes[split] = {
            "selected_manifest": {
                "rows": len(manifest),
                "sha256": _write_jsonl(
                    selection / f"option-b-selected-{split}-v2.jsonl",
                    manifest,
                ),
            },
            "primitive_table": {
                "rows": len(primitive),
                "sha256": _write_jsonl(
                    selection / f"option-b-primitives-{split}-v2.jsonl",
                    primitive,
                ),
            },
        }

    _write_json(
        selection / "option-b-canonical-row-selection-v2.json",
        {
            "selection_id": "option-b-canonical-row-selection-v2",
            "status": "CANONICAL_ROW_SELECTION_V2_VERIFIED",
            "scientific_result_observed": False,
            "config": {
                "min_rank_separation": 5,
                "max_rank_separation": 25,
                "max_pairs_per_query": 128,
            },
            "artifacts": hashes,
        },
    )

    report = generate_hard_negative_manifest(
        selection_dir=selection,
        probe_checkpoint_path=checkpoint,
        output_dir=output,
    )
    assert report["artifacts"]["queries"]["rows"] == 3
    assert report["all_test_queries_represented"] is True
    assert report["construction_scope"]["embeddings_loaded"] is False
    assert report["construction_scope"]["probe_predictions_loaded"] is False
    query_lines = (
        output / "option-b-hard-negative-queries-v1.jsonl"
    ).read_text().splitlines()
    assert len(query_lines) == 3

    with pytest.raises(FileExistsError, match="already contains canonical files"):
        generate_hard_negative_manifest(
            selection_dir=selection,
            probe_checkpoint_path=checkpoint,
            output_dir=output,
        )

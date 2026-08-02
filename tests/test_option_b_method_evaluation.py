from __future__ import annotations

import inspect

import numpy as np
import pytest

from relate.experiments.option_b_method_evaluation import (
    METHOD_INDEX,
    METHODS,
    _deterministic_order,
    _repository_analysis,
    _score_pairs,
    decision_from_query_scores,
    run_method_evaluation,
)
from relate.experiments.option_b_method_evaluation_independent import (
    verify_method_evaluation,
)


def test_runner_apis_expose_paths_only() -> None:
    assert set(inspect.signature(run_method_evaluation).parameters) == {
        "selection_dir",
        "embedding_dir",
        "embedding_checkpoint_path",
        "probe_dir",
        "manifest_dir",
        "output_dir",
    }
    assert set(inspect.signature(verify_method_evaluation).parameters) == {
        "selection_dir",
        "embedding_dir",
        "embedding_checkpoint_path",
        "probe_dir",
        "manifest_dir",
        "result_dir",
    }


def test_method_distance_ties_score_half() -> None:
    scores, ties = _score_pairs(
        np.asarray((1.0, 2.0, 3.0)),
        np.asarray((2.0, 2.0, 1.0)),
    )
    assert scores.tolist() == [1.0, 0.5, 0.0]
    assert ties == 1


def test_decision_uses_query_equal_weighting_and_stronger_raw_baseline() -> None:
    scores = np.zeros((2, len(METHODS)), dtype=np.float64)
    scores[:, METHOD_INDEX["raw_cosine"]] = (0.60, 0.80)
    scores[:, METHOD_INDEX["raw_euclidean"]] = (0.70, 0.70)
    scores[:, METHOD_INDEX["predicted_executor"]] = (0.81, 0.81)
    scores[:, METHOD_INDEX["token_length"]] = (0.1, 0.1)
    scores[:, METHOD_INDEX["true_oracle"]] = (1.0, 1.0)
    result = decision_from_query_scores(scores, np.asarray((1, 100)))
    assert result["query_equal_weighted_accuracy"]["raw_cosine"] == 0.70
    assert result["raw_best"] == 0.70
    assert result["gap"] == pytest.approx(0.11)
    assert result["outcome"] == "REAL_PREMISE_SUPPORTED"


def test_threshold_is_inclusive_and_has_only_two_outcomes() -> None:
    scores = np.zeros((1, len(METHODS)), dtype=np.float64)
    scores[0, METHOD_INDEX["raw_cosine"]] = 0.0
    scores[0, METHOD_INDEX["raw_euclidean"]] = 0.0
    scores[0, METHOD_INDEX["predicted_executor"]] = 0.10
    scores[0, METHOD_INDEX["true_oracle"]] = 1.0
    supported = decision_from_query_scores(scores, np.asarray((1,)))
    assert supported["gap"] == 0.10
    assert supported["outcome"] == "REAL_PREMISE_SUPPORTED"

    scores[0, METHOD_INDEX["predicted_executor"]] = np.nextafter(0.10, 0.0)
    failed = decision_from_query_scores(scores, np.asarray((1,)))
    assert failed["gap"] < 0.10
    assert failed["outcome"] == "REAL_PREMISE_FAILED"


def test_candidate_distance_ties_use_stable_key_order() -> None:
    stable_ranks = np.asarray((2, 0, 1), dtype=np.int64)
    distances = np.ones(3, dtype=np.float64)
    assert _deterministic_order(distances, stable_ranks).tolist() == [1, 2, 0]


def test_repository_bootstrap_is_deterministic_and_descriptive() -> None:
    scores = np.zeros((8, len(METHODS)), dtype=np.float64)
    scores[:, METHOD_INDEX["raw_cosine"]] = np.linspace(0.4, 0.7, 8)
    scores[:, METHOD_INDEX["raw_euclidean"]] = np.linspace(0.5, 0.6, 8)
    scores[:, METHOD_INDEX["predicted_executor"]] = np.linspace(0.6, 0.9, 8)
    scores[:, METHOD_INDEX["true_oracle"]] = 1.0
    counts = np.full(8, 2, dtype=np.int64)
    repositories = ("a", "a", "b", "b", "c", "c", "d", "d")
    first = _repository_analysis(
        scores,
        counts,
        repositories,
        __import__(
            "relate.experiments.option_b_method_evaluation",
            fromlist=["FrozenEvaluationConfig"],
        ).FrozenEvaluationConfig(bootstrap_repetitions=20, min_repository_queries=2),
    )
    second = _repository_analysis(
        scores,
        counts,
        repositories,
        __import__(
            "relate.experiments.option_b_method_evaluation",
            fromlist=["FrozenEvaluationConfig"],
        ).FrozenEvaluationConfig(bootstrap_repetitions=20, min_repository_queries=2),
    )
    assert first == second
    assert first["bootstrap"]["descriptive_only"] is True


def _file_sha(path):
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _array_hash(value):
    import hashlib
    import json

    array = np.ascontiguousarray(value)
    payload = (
        json.dumps(
            {"dtype": str(array.dtype), "shape": list(array.shape)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + array.tobytes()
    )
    return hashlib.sha256(payload).hexdigest()


def _write_json(path, value):
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return _file_sha(path)


def _write_jsonl(path, rows):
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    return _file_sha(path)


def test_small_end_to_end_runner_and_independent_recomputation(tmp_path) -> None:
    import gzip
    import json

    from relate.experiments.option_b_method_evaluation import run_method_evaluation
    from relate.experiments.option_b_method_evaluation_independent import (
        verify_method_evaluation,
    )

    selection = tmp_path / "selection"
    embeddings = tmp_path / "embeddings"
    probes = tmp_path / "probes"
    manifest = tmp_path / "manifest"
    output = tmp_path / "result"
    for directory in (selection, embeddings, probes, manifest):
        directory.mkdir(parents=True)

    sizes = {"train": 60, "validation": 20, "test": 20}
    manifests = {}
    primitives = {}
    selection_artifacts = {}
    for split, count in sizes.items():
        manifests[split] = [
            {
                "stable_key": f"{split}-{index:04d}",
                "repository": f"repo-{index // 5}",
                "token_count": 32 + index,
            }
            for index in range(count)
        ]
        primitives[split] = [
            {
                "stable_key": f"{split}-{index:04d}",
                "cyclomatic_complexity": float(index + 1),
                "max_control_depth": float((index + 1) / 2),
                "distinct_call_sites": float((index + 1) / 3),
            }
            for index in range(count)
        ]
        manifest_path = selection / f"option-b-selected-{split}-v2.jsonl"
        primitive_path = selection / f"option-b-primitives-{split}-v2.jsonl"
        selection_artifacts[split] = {
            "selected_manifest": {
                "rows": count,
                "sha256": _write_jsonl(manifest_path, manifests[split]),
            },
            "primitive_table": {
                "rows": count,
                "sha256": _write_jsonl(primitive_path, primitives[split]),
            },
        }
    _write_json(
        selection / "option-b-canonical-row-selection-v2.json",
        {
            "selection_id": "option-b-canonical-row-selection-v2",
            "status": "CANONICAL_ROW_SELECTION_V2_VERIFIED",
            "scientific_result_observed": False,
            "artifacts": selection_artifacts,
        },
    )

    rng = np.random.default_rng(7)
    embedding_checkpoint = {
        "checkpoint_id": "option-b-independent-embedding-reproduction-v2",
        "status": "CANONICAL_EMBEDDINGS_V2_REPRODUCED",
        "scientific_result_observed": False,
        "splits": {},
    }
    embedding_values = {}
    for split, count in sizes.items():
        values = rng.normal(size=(count, 8)).astype(np.float32)
        embedding_values[split] = values
        path = embeddings / f"option-b-embeddings-{split}-v2.npy"
        np.save(path, values, allow_pickle=False)
        embedding_checkpoint["splits"][split] = {
            "dimensions": 8,
            "run_a_file_sha256": _file_sha(path),
            "array_sha256": _array_hash(values),
        }
    embedding_checkpoint_path = tmp_path / "embedding-checkpoint.json"
    _write_json(embedding_checkpoint_path, embedding_checkpoint)

    train_true = np.asarray(
        [
            [
                row[name]
                for name in (
                    "cyclomatic_complexity",
                    "max_control_depth",
                    "distinct_call_sites",
                )
            ]
            for row in primitives["train"]
        ],
        dtype=np.float64,
    )
    median = np.median(train_true, axis=0)
    q25, q75 = np.percentile(train_true, (25, 75), axis=0)
    scale = np.maximum(q75 - q25, 1.0)
    prediction_values = {}
    prediction_meta = {}
    role_data = {
        "train": ("train_candidates", "option-b-predicted-train-candidates-v1.npy"),
        "validation": ("validation_rows", "option-b-predicted-validation-rows-v1.npy"),
        "test": ("test_queries", "option-b-predicted-test-queries-v1.npy"),
    }
    for split, (role, filename) in role_data.items():
        true = np.asarray(
            [
                [
                    row[name]
                    for name in (
                        "cyclomatic_complexity",
                        "max_control_depth",
                        "distinct_call_sites",
                    )
                ]
                for row in primitives[split]
            ],
            dtype=np.float64,
        )
        values = (true - median) / scale
        prediction_values[split] = values
        path = probes / filename
        np.save(path, values, allow_pickle=False)
        sequence_payload = json.dumps(
            [row["stable_key"] for row in manifests[split]],
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
        import hashlib

        prediction_meta[role] = {
            "file_sha256": _file_sha(path),
            "array_sha256": _array_hash(values),
            "row_order_sha256": hashlib.sha256(sequence_payload).hexdigest(),
        }
    bundle_path = probes / "option-b-primitive-probe-bundle-v1.json"
    bundle = {
        "probe_bundle_id": "option-b-primitive-probe-bundle-v1",
        "contract": {
            "primitives": {
                name: {"selected_alpha": 1.0}
                for name in (
                    "cyclomatic_complexity",
                    "max_control_depth",
                    "distinct_call_sites",
                )
            }
        },
    }
    bundle_sha = _write_json(bundle_path, bundle)
    _write_json(
        probes / "option-b-primitive-probe-publication-v1.json",
        {
            "checkpoint_id": "option-b-primitive-probe-publication-v1",
            "status": "PRIMITIVE_PROBE_ARTIFACTS_PUBLISHED_PENDING_REVIEW",
            "scientific_result_observed": False,
            "source_fit": {
                "file_sha256": bundle_sha,
                "bundle_sha256": "bundle",
            },
            "predictions": prediction_meta,
        },
    )

    query_rows = []
    pair_rows = []
    for query_index in range(sizes["test"]):
        query_rows.append(
            {
                "query_index": query_index,
                "query_stable_key": manifests["test"][query_index]["stable_key"],
                "query_repository": manifests["test"][query_index]["repository"],
                "query_token_count": manifests["test"][query_index]["token_count"],
                "token_length_decile": query_index % 10,
                "selected_pair_count": 2,
            }
        )
        for pair_order, (closer, farther) in enumerate(
            ((query_index, query_index + 20), (query_index + 1, query_index + 21))
        ):
            pair_rows.append(
                {
                    "query_index": query_index,
                    "pair_order": pair_order,
                    "query_stable_key": manifests["test"][query_index]["stable_key"],
                    "closer_candidate_index": closer,
                    "closer_stable_key": manifests["train"][closer]["stable_key"],
                    "farther_candidate_index": farther,
                    "farther_stable_key": manifests["train"][farther]["stable_key"],
                }
            )
    query_path = manifest / "option-b-hard-negative-queries-v1.jsonl"
    query_sha = _write_jsonl(query_path, query_rows)
    raw_pair = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for row in pair_rows
    )
    pair_path = manifest / "option-b-hard-negative-pairs-v1.jsonl.gz"
    with pair_path.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as handle:
            handle.write(raw_pair)
    generation_path = manifest / "option-b-hard-negative-manifest-v1.json"
    generation_sha = _write_json(
        generation_path,
        {
            "scaling": {"median": median.tolist(), "scale": scale.tolist()},
        },
    )
    import hashlib

    _write_json(
        manifest / "option-b-hard-negative-manifest-publication-v1.json",
        {
            "checkpoint_id": "option-b-hard-negative-manifest-publication-v1",
            "status": "HARD_NEGATIVE_MANIFEST_PUBLISHED_PENDING_REVIEW",
            "scientific_result_observed": False,
            "next_allowed_action": "METHOD_EVALUATION_IMPLEMENTATION_REVIEW",
            "generation": {"file_sha256": generation_sha},
            "counts": {"pairs": len(pair_rows)},
            "artifacts": {
                "queries": {"file_sha256": query_sha},
                "pairs": {
                    "file_sha256": _file_sha(pair_path),
                    "uncompressed_file_sha256": hashlib.sha256(raw_pair).hexdigest(),
                },
            },
        },
    )

    result = run_method_evaluation(
        selection_dir=selection,
        embedding_dir=embeddings,
        embedding_checkpoint_path=embedding_checkpoint_path,
        probe_dir=probes,
        manifest_dir=manifest,
        output_dir=output,
    )
    assert result["scientific_result_observed"] is True
    assert result["primary_metric"]["uniform_pair_count_verified"] is True
    assert result["primary_metric"]["query_equal_weighted_accuracy"]["true_oracle"] == 1.0

    verification = verify_method_evaluation(
        selection_dir=selection,
        embedding_dir=embeddings,
        embedding_checkpoint_path=embedding_checkpoint_path,
        probe_dir=probes,
        manifest_dir=manifest,
        result_dir=output,
    )
    assert verification["status"] == "OPTION_B_PRIMARY_DECISION_INDEPENDENTLY_RECOMPUTED"
    assert verification["checks"]["query_scores_exactly_equal"] is True

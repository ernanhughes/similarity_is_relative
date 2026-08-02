from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from relate.experiments import option_b_probe_runner as runner
from relate.experiments.option_b_predicted_executor import PredictedPrimitiveVectors
from relate.experiments.option_b_real_code import PRIMITIVES, array_hash


def _write_json(path: Path, value: dict) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(payload.encode()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(payload.encode()).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save_npy(path: Path, value: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, value, allow_pickle=False)
    return _file_sha(path)


def _key_hash(keys: list[str]) -> str:
    payload = json.dumps(keys, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _fixture(tmp_path: Path) -> dict[str, Path]:
    selection = tmp_path / "selection"
    embedding_dir = tmp_path / "embeddings-a"
    reproduction = tmp_path / "reproduction"
    sizes = {"train": 10, "validation": 4, "test": 4}
    dimensions = 6

    artifacts = {}
    manifest_checkpoint = {}
    for split, count in sizes.items():
        keys = [f"{split}-{index}" for index in range(count)]
        manifest_rows = [
            {
                "split": split,
                "stable_key": key,
                "code_sha256": hashlib.sha256(key.encode()).hexdigest(),
            }
            for key in keys
        ]
        primitive_rows = [
            {
                "split": split,
                "stable_key": key,
                "cyclomatic_complexity": float(index + 1),
                "max_control_depth": float(index % 3),
                "distinct_call_sites": float(index * 2 + 1),
            }
            for index, key in enumerate(keys)
        ]
        manifest_path = selection / f"option-b-selected-{split}-v2.jsonl"
        primitive_path = selection / f"option-b-primitives-{split}-v2.jsonl"
        manifest_sha = _write_jsonl(manifest_path, manifest_rows)
        primitive_sha = _write_jsonl(primitive_path, primitive_rows)
        artifacts[split] = {
            "selected_manifest": {
                "path": str(manifest_path),
                "rows": count,
                "sha256": manifest_sha,
            },
            "primitive_table": {
                "path": str(primitive_path),
                "rows": count,
                "sha256": primitive_sha,
            },
        }
        manifest_checkpoint[split] = {
            "file_sha256": manifest_sha,
            "rows": count,
            "stable_key_sequence_sha256": _key_hash(keys),
        }

    selection_report = selection / runner.SELECTION_REPORT_NAME
    selection_report_sha = _write_json(
        selection_report,
        {
            "status": "CANONICAL_ROW_SELECTION_V2_VERIFIED",
            "artifacts": artifacts,
        },
    )

    matrices = {
        split: np.arange(count * dimensions, dtype=np.float32).reshape(count, dimensions)
        / 10.0
        for split, count in sizes.items()
    }
    report_artifacts = {}
    checkpoint_splits = {}
    for split, matrix in matrices.items():
        path = embedding_dir / f"option-b-embeddings-{split}-v2.npy"
        file_sha = _save_npy(path, matrix)
        fingerprint = hashlib.sha256(f"fingerprint:{split}".encode()).hexdigest()
        report_artifacts[split] = {
            "array_sha256": array_hash(matrix),
            "file_sha256": file_sha,
            "extraction_fingerprint_sha256": fingerprint,
        }
        checkpoint_splits[split] = {
            "rows": len(matrix),
            "dimensions": matrix.shape[1],
            "dtype": "float32",
            "array_sha256": array_hash(matrix),
            "exact_array_equal": True,
            "extraction_fingerprint_sha256": fingerprint,
            "run_a_file_sha256": file_sha,
            "run_b_file_sha256": file_sha,
        }

    identity_sha = "1" * 64
    embedding_report = reproduction / "run-a.json"
    embedding_report_sha = _write_json(
        embedding_report,
        {
            "embedding_id": "option-b-canonical-embeddings-v2",
            "status": "EMBEDDING_RUN_COMPLETE_PENDING_INDEPENDENT_REPRODUCTION",
            "scientific_result_observed": False,
            "identity": {"file_sha256": identity_sha},
            "artifacts": report_artifacts,
        },
    )

    checkpoint = reproduction / "checkpoint.json"
    _write_json(
        checkpoint,
        {
            "checkpoint_id": "option-b-independent-embedding-reproduction-v2",
            "status": "CANONICAL_EMBEDDINGS_V2_REPRODUCED",
            "scientific_result_observed": False,
            "next_allowed_action": "PRIMITIVE_PROBE_FITTING",
            "identity": {"file_sha256": identity_sha},
            "selection": {
                "report_file_sha256": selection_report_sha,
                "manifests": manifest_checkpoint,
            },
            "runs": {
                "a": {"report_file_sha256": embedding_report_sha},
                "b": {"report_file_sha256": "2" * 64},
            },
            "splits": checkpoint_splits,
        },
    )

    amendment = reproduction / "amendment.json"
    _write_json(
        amendment,
        {
            "checkpoint_id": "option-b-gpu-fixed-batch10-reproduction-v1",
            "status": "GPU_FIXED_BATCH_EMBEDDINGS_REPRODUCED_NOT_YET_CANONICAL",
            "scientific_result_observed": False,
            "gpu_identity": {"file_sha256": identity_sha},
            "protocol_amendment": {
                "frozen_execution": {
                    "device": "cuda",
                    "batch_size": 10,
                    "deterministic_algorithms": True,
                    "allow_tf32": False,
                    "cublas_workspace_config": ":4096:8",
                }
            },
            "splits": checkpoint_splits,
        },
    )

    return {
        "selection": selection,
        "embedding_dir": embedding_dir,
        "embedding_report": embedding_report,
        "checkpoint": checkpoint,
        "amendment": amendment,
    }


def _verify(paths: dict[str, Path]) -> runner.VerifiedProbeInputs:
    return runner.verify_probe_inputs(
        checkpoint_path=paths["checkpoint"],
        amendment_path=paths["amendment"],
        selection_dir=paths["selection"],
        embedding_report_path=paths["embedding_report"],
        embedding_dir=paths["embedding_dir"],
    )


def test_verify_inputs_loads_only_train_and_validation_primitive_labels(
    tmp_path: Path, monkeypatch
) -> None:
    paths = _fixture(tmp_path)
    called: list[str] = []
    original = runner._load_labeled_primitives

    def recording_loader(*args, **kwargs):
        split = args[1]
        called.append(split)
        return original(*args, **kwargs)

    monkeypatch.setattr(runner, "_load_labeled_primitives", recording_loader)
    inputs = _verify(paths)

    assert called == ["train", "validation"]
    assert inputs.evidence["test_primitive_labels_loaded"] is False
    assert inputs.train_y.shape == (10, len(PRIMITIVES))
    assert inputs.test_x.shape == (4, 6)


def test_test_primitive_labels_are_absent_from_runner_api() -> None:
    signature = inspect.signature(runner.run_probe_fit)
    assert "test_true_primitives" not in signature.parameters
    assert "test_primitive_path" not in signature.parameters


def test_verify_inputs_rejects_embedding_payload_tampering(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    matrix_path = paths["embedding_dir"] / "option-b-embeddings-test-v2.npy"
    matrix = np.load(matrix_path, allow_pickle=False)
    matrix[0, 0] += np.float32(1.0)
    np.save(matrix_path, matrix, allow_pickle=False)

    with pytest.raises(ValueError, match="test embedding logical array hash mismatch"):
        _verify(paths)


def test_verify_inputs_rejects_changed_gpu_batch_size(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    amendment = json.loads(paths["amendment"].read_text(encoding="utf-8"))
    amendment["protocol_amendment"]["frozen_execution"]["batch_size"] = 16
    _write_json(paths["amendment"], amendment)

    with pytest.raises(ValueError, match="batch_size=10"):
        _verify(paths)


def test_publish_probe_fit_writes_hash_addressed_float64_predictions(tmp_path: Path) -> None:
    inputs = SimpleNamespace(evidence={"test_primitive_labels_loaded": False})
    arrays = {
        "train_candidates": np.arange(30, dtype=np.float64).reshape(10, 3) / 7.0,
        "validation_rows": np.arange(12, dtype=np.float64).reshape(4, 3) / 9.0,
        "test_queries": np.arange(12, dtype=np.float64).reshape(4, 3) / 11.0,
    }

    def vector(role: str) -> PredictedPrimitiveVectors:
        values = arrays[role]
        return PredictedPrimitiveVectors(
            values=values,
            role=role,
            row_order_sha256="r" * 64,
            prediction_sha256=array_hash(values),
            bundle_sha256="b" * 64,
        )

    artifacts = SimpleNamespace(
        train_candidates=vector("train_candidates"),
        validation_rows=vector("validation_rows"),
        test_queries=vector("test_queries"),
        report={
            "contract": "option-b-predicted-executor-v1",
            "scientific_result_observed": False,
        },
    )

    report = runner.publish_probe_fit(inputs, artifacts, tmp_path / "output")

    assert report["status"] == "PRIMITIVE_PROBE_FIT_COMPLETE_PENDING_PUBLICATION_REVIEW"
    assert report["scientific_result_observed"] is False
    assert report["fit_scope"]["test_primitive_labels"].startswith("not parsed")
    for role, metadata in report["predictions"].items():
        values = np.load(metadata["path"], allow_pickle=False)
        assert values.dtype == np.float64
        assert array_hash(values) == metadata["array_sha256"]
        assert _file_sha(Path(metadata["path"])) == metadata["file_sha256"]
        assert values.shape == arrays[role].shape


def test_run_probe_fit_passes_no_test_labels_to_contract(tmp_path: Path, monkeypatch) -> None:
    paths = _fixture(tmp_path)
    captured = {}

    def fake_fit(**kwargs):
        captured.update(kwargs)
        arrays = {
            "train_candidates": np.zeros((10, 3), dtype=np.float64),
            "validation_rows": np.zeros((4, 3), dtype=np.float64),
            "test_queries": np.zeros((4, 3), dtype=np.float64),
        }

        def vector(role: str):
            values = arrays[role]
            return PredictedPrimitiveVectors(
                values=values,
                role=role,
                row_order_sha256="r" * 64,
                prediction_sha256=array_hash(values),
                bundle_sha256="b" * 64,
            )

        return SimpleNamespace(
            train_candidates=vector("train_candidates"),
            validation_rows=vector("validation_rows"),
            test_queries=vector("test_queries"),
            report={"contract": "option-b-predicted-executor-v1"},
        )

    monkeypatch.setattr(runner, "fit_predicted_executor_contract", fake_fit)
    report = runner.run_probe_fit(
        checkpoint_path=paths["checkpoint"],
        amendment_path=paths["amendment"],
        selection_dir=paths["selection"],
        embedding_report_path=paths["embedding_report"],
        embedding_dir=paths["embedding_dir"],
        output_dir=tmp_path / "probe-output",
    )

    assert "test_true_primitives" not in captured
    assert set(captured) >= {
        "train_true_primitives",
        "validation_true_primitives",
        "test_x",
    }
    assert report["next_allowed_action"] == "CANONICAL_PROBE_ARTIFACT_PUBLICATION"

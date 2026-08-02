"""Verify Option B probe inputs and fit the frozen predicted-executor bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

from relate.experiments.option_b_predicted_executor import (
    PredictedExecutorArtifacts,
    fit_predicted_executor_contract,
)
from relate.experiments.option_b_real_code import ALPHAS, PRIMITIVES, array_hash

SPLITS = ("train", "validation", "test")
LABELED_SPLITS = ("train", "validation")
DEFAULT_SELECTION_DIR = Path("artifacts/canonical/option-b/selection")
DEFAULT_REPRODUCTION_DIR = Path("artifacts/canonical/option-b/embedding-reproduction-v2")
DEFAULT_EMBEDDING_CHECKPOINT = (
    DEFAULT_REPRODUCTION_DIR / "option-b-independent-embedding-reproduction-v2.json"
)
DEFAULT_GPU_AMENDMENT = DEFAULT_REPRODUCTION_DIR / "option-b-gpu-fixed-batch10-reproduction-v1.json"
DEFAULT_EMBEDDING_REPORT = DEFAULT_REPRODUCTION_DIR / "option-b-canonical-embeddings-v2-run-a.json"
DEFAULT_EMBEDDING_DIR = Path("runs/option-b/gpu-fixed-batch-10/embeddings-a")
DEFAULT_OUTPUT_DIR = Path("runs/option-b/probes-v1")
SELECTION_REPORT_NAME = "option-b-canonical-row-selection-v2.json"
PREDICTION_FILENAMES = {
    "train_candidates": "option-b-predicted-train-candidates-v1.npy",
    "validation_rows": "option-b-predicted-validation-rows-v1.npy",
    "test_queries": "option-b-predicted-test-queries-v1.npy",
}


@dataclass(frozen=True)
class VerifiedProbeInputs:
    """Hash-verified inputs for one prospective canonical probe fit."""

    train_x: np.ndarray
    validation_x: np.ndarray
    test_x: np.ndarray
    train_y: np.ndarray
    validation_y: np.ndarray
    train_stable_keys: tuple[str, ...]
    validation_stable_keys: tuple[str, ...]
    test_stable_keys: tuple[str, ...]
    evidence: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _stable_key_hash(keys: tuple[str, ...]) -> str:
    payload = json.dumps(list(keys), separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _runtime_identity() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": _package_version("scipy"),
        "scikit_learn": _package_version("scikit-learn"),
        "thread_environment": {
            name: os.environ.get(name)
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_save_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        np.save(handle, value, allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _verify_reproduction_checkpoints(
    checkpoint_path: Path,
    amendment_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    checkpoint = _load_json(checkpoint_path)
    if checkpoint.get("checkpoint_id") != "option-b-independent-embedding-reproduction-v2":
        raise ValueError("unexpected embedding reproduction checkpoint id")
    if checkpoint.get("status") != "CANONICAL_EMBEDDINGS_V2_REPRODUCED":
        raise ValueError("independent embedding reproduction is incomplete")
    if checkpoint.get("scientific_result_observed") is not False:
        raise ValueError("embedding checkpoint crossed the scientific-result boundary")
    if checkpoint.get("next_allowed_action") != "PRIMITIVE_PROBE_FITTING":
        raise ValueError("embedding checkpoint does not permit primitive probe fitting")

    amendment = _load_json(amendment_path)
    if amendment.get("checkpoint_id") != "option-b-gpu-fixed-batch10-reproduction-v1":
        raise ValueError("unexpected GPU amendment checkpoint id")
    if amendment.get("status") != ("GPU_FIXED_BATCH_EMBEDDINGS_REPRODUCED_NOT_YET_CANONICAL"):
        raise ValueError("GPU fixed-batch reproduction checkpoint is incomplete")
    if amendment.get("scientific_result_observed") is not False:
        raise ValueError("GPU amendment crossed the scientific-result boundary")
    if amendment.get("gpu_identity", {}).get("file_sha256") != checkpoint.get("identity", {}).get(
        "file_sha256"
    ):
        raise ValueError("GPU amendment and independent checkpoint identity hashes differ")
    frozen = amendment.get("protocol_amendment", {}).get("frozen_execution", {})
    required = {
        "device": "cuda",
        "batch_size": 10,
        "deterministic_algorithms": True,
        "allow_tf32": False,
        "cublas_workspace_config": ":4096:8",
    }
    for key, expected in required.items():
        if frozen.get(key) != expected:
            raise ValueError(f"GPU amendment does not freeze {key}={expected!r}")
    for split in SPLITS:
        left = checkpoint.get("splits", {}).get(split, {})
        right = amendment.get("splits", {}).get(split, {})
        for key in ("rows", "dimensions", "dtype", "array_sha256"):
            if left.get(key) != right.get(key):
                raise ValueError(f"{split} checkpoint disagreement for {key}")
        if left.get("exact_array_equal") is not True:
            raise ValueError(f"{split} independent embeddings are not exactly equal")
    return checkpoint, amendment


def _verify_selection(
    selection_dir: Path,
    checkpoint: dict[str, Any],
) -> tuple[dict[str, tuple[str, ...]], dict[str, Any], dict[str, Any]]:
    report_path = selection_dir / SELECTION_REPORT_NAME
    report = _load_json(report_path)
    if report.get("status") != "CANONICAL_ROW_SELECTION_V2_VERIFIED":
        raise ValueError("canonical selection v2 is incomplete")
    expected_report_sha = checkpoint.get("selection", {}).get("report_file_sha256")
    if _sha256_file(report_path) != expected_report_sha:
        raise ValueError("selection report file hash does not match embedding checkpoint")

    keys_by_split: dict[str, tuple[str, ...]] = {}
    manifest_evidence: dict[str, Any] = {}
    primitive_evidence: dict[str, Any] = {}
    checkpoint_manifests = checkpoint.get("selection", {}).get("manifests", {})

    for split in SPLITS:
        manifest_path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
        expected_manifest = report["artifacts"][split]["selected_manifest"]
        checkpoint_manifest = checkpoint_manifests[split]
        actual_manifest_sha = _sha256_file(manifest_path)
        if actual_manifest_sha != expected_manifest["sha256"]:
            raise ValueError(f"{split} selected manifest does not match selection report")
        if actual_manifest_sha != checkpoint_manifest["file_sha256"]:
            raise ValueError(f"{split} selected manifest does not match embedding checkpoint")
        rows = _load_jsonl(manifest_path)
        keys = tuple(str(row["stable_key"]) for row in rows)
        if len(keys) != expected_manifest["rows"] or len(keys) != checkpoint_manifest["rows"]:
            raise ValueError(f"{split} selected manifest row count mismatch")
        if len(set(keys)) != len(keys):
            raise ValueError(f"{split} selected manifest stable keys are not unique")
        if _stable_key_hash(keys) != checkpoint_manifest["stable_key_sequence_sha256"]:
            raise ValueError(f"{split} selected manifest row order mismatch")
        keys_by_split[split] = keys
        manifest_evidence[split] = {
            "path": str(manifest_path).replace("\\", "/"),
            "rows": len(keys),
            "file_sha256": actual_manifest_sha,
            "stable_key_sequence_sha256": _stable_key_hash(keys),
        }

        primitive = report["artifacts"][split]["primitive_table"]
        primitive_path = selection_dir / f"option-b-primitives-{split}-v2.jsonl"
        actual_primitive_sha = _sha256_file(primitive_path)
        if actual_primitive_sha != primitive["sha256"]:
            raise ValueError(f"{split} primitive table does not match selection report")
        primitive_evidence[split] = {
            "path": str(primitive_path).replace("\\", "/"),
            "rows": primitive["rows"],
            "file_sha256": actual_primitive_sha,
        }

    return keys_by_split, manifest_evidence, primitive_evidence


def _load_labeled_primitives(
    selection_dir: Path,
    split: str,
    expected_keys: tuple[str, ...],
    expected_evidence: dict[str, Any],
) -> np.ndarray:
    if split not in LABELED_SPLITS:
        raise ValueError("test primitive labels are forbidden probe-fit inputs")
    path = selection_dir / f"option-b-primitives-{split}-v2.jsonl"
    if _sha256_file(path) != expected_evidence["file_sha256"]:
        raise ValueError(f"{split} primitive table changed after selection verification")
    rows = _load_jsonl(path)
    actual_keys = tuple(str(row["stable_key"]) for row in rows)
    if actual_keys != expected_keys:
        raise ValueError(f"{split} primitive table order does not match selected manifest")
    matrix = np.asarray(
        [[float(row[name]) for name in PRIMITIVES] for row in rows],
        dtype=np.float64,
    )
    if matrix.shape != (len(expected_keys), len(PRIMITIVES)):
        raise ValueError(f"{split} primitive table has an invalid shape")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{split} primitive table contains non-finite values")
    return matrix


def _verify_embedding_report(
    report_path: Path,
    checkpoint: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    report_sha = _sha256_file(report_path)
    matching_runs = [
        name
        for name, value in checkpoint.get("runs", {}).items()
        if value.get("report_file_sha256") == report_sha
    ]
    if len(matching_runs) != 1:
        raise ValueError("embedding report is not exactly one independently verified run")
    report = _load_json(report_path)
    if report.get("embedding_id") != "option-b-canonical-embeddings-v2":
        raise ValueError("unexpected embedding report id")
    if report.get("status") != "EMBEDDING_RUN_COMPLETE_PENDING_INDEPENDENT_REPRODUCTION":
        raise ValueError("embedding report is incomplete")
    if report.get("scientific_result_observed") is not False:
        raise ValueError("embedding report crossed the scientific-result boundary")
    if report.get("identity", {}).get("file_sha256") != checkpoint.get("identity", {}).get(
        "file_sha256"
    ):
        raise ValueError("embedding report identity differs from reproduction checkpoint")
    return report, matching_runs[0]


def _load_verified_embeddings(
    embedding_dir: Path,
    report: dict[str, Any],
    checkpoint: dict[str, Any],
    stable_keys: dict[str, tuple[str, ...]],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    matrices: dict[str, np.ndarray] = {}
    evidence: dict[str, Any] = {}
    for split in SPLITS:
        path = embedding_dir / f"option-b-embeddings-{split}-v2.npy"
        matrix = np.load(path, allow_pickle=False)
        expected = checkpoint["splits"][split]
        reported = report["artifacts"][split]
        if matrix.dtype != np.float32 or matrix.ndim != 2:
            raise ValueError(f"{split} embedding matrix must be two-dimensional float32")
        if matrix.shape != (expected["rows"], expected["dimensions"]):
            raise ValueError(f"{split} embedding matrix shape mismatch")
        if len(stable_keys[split]) != matrix.shape[0]:
            raise ValueError(f"{split} embedding row count does not match selected manifest")
        if not np.isfinite(matrix).all():
            raise ValueError(f"{split} embedding matrix contains non-finite values")
        logical_sha = array_hash(matrix)
        file_sha = _sha256_file(path)
        if logical_sha != expected["array_sha256"] or logical_sha != reported["array_sha256"]:
            raise ValueError(f"{split} embedding logical array hash mismatch")
        if file_sha != expected["run_a_file_sha256"]:
            raise ValueError(f"{split} embedding file hash is not the reproduced artifact")
        if file_sha != reported["file_sha256"]:
            raise ValueError(f"{split} embedding file hash differs from its run report")
        if reported["extraction_fingerprint_sha256"] != expected["extraction_fingerprint_sha256"]:
            raise ValueError(f"{split} extraction fingerprint mismatch")
        matrices[split] = matrix
        evidence[split] = {
            "path": str(path).replace("\\", "/"),
            "rows": int(matrix.shape[0]),
            "dimensions": int(matrix.shape[1]),
            "dtype": str(matrix.dtype),
            "array_sha256": logical_sha,
            "file_sha256": file_sha,
            "extraction_fingerprint_sha256": expected["extraction_fingerprint_sha256"],
        }
    return matrices, evidence


def verify_probe_inputs(
    *,
    checkpoint_path: Path = DEFAULT_EMBEDDING_CHECKPOINT,
    amendment_path: Path = DEFAULT_GPU_AMENDMENT,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    embedding_report_path: Path = DEFAULT_EMBEDDING_REPORT,
    embedding_dir: Path = DEFAULT_EMBEDDING_DIR,
) -> VerifiedProbeInputs:
    """Verify all inputs without parsing test primitive labels."""
    checkpoint, amendment = _verify_reproduction_checkpoints(checkpoint_path, amendment_path)
    stable_keys, manifest_evidence, primitive_evidence = _verify_selection(
        selection_dir, checkpoint
    )
    embedding_report, source_run = _verify_embedding_report(embedding_report_path, checkpoint)
    embeddings, embedding_evidence = _load_verified_embeddings(
        embedding_dir,
        embedding_report,
        checkpoint,
        stable_keys,
    )

    train_y = _load_labeled_primitives(
        selection_dir,
        "train",
        stable_keys["train"],
        primitive_evidence["train"],
    )
    validation_y = _load_labeled_primitives(
        selection_dir,
        "validation",
        stable_keys["validation"],
        primitive_evidence["validation"],
    )

    evidence = {
        "embedding_checkpoint": {
            "path": str(checkpoint_path).replace("\\", "/"),
            "file_sha256": _sha256_file(checkpoint_path),
            "checkpoint_id": checkpoint["checkpoint_id"],
            "status": checkpoint["status"],
        },
        "gpu_amendment": {
            "path": str(amendment_path).replace("\\", "/"),
            "file_sha256": _sha256_file(amendment_path),
            "checkpoint_id": amendment["checkpoint_id"],
            "status": amendment["status"],
        },
        "embedding_report": {
            "path": str(embedding_report_path).replace("\\", "/"),
            "file_sha256": _sha256_file(embedding_report_path),
            "source_run": source_run,
        },
        "selection_manifests": manifest_evidence,
        "primitive_tables": {
            "train": primitive_evidence["train"],
            "validation": primitive_evidence["validation"],
        },
        "test_primitive_labels_loaded": False,
        "embeddings": embedding_evidence,
    }
    return VerifiedProbeInputs(
        train_x=embeddings["train"],
        validation_x=embeddings["validation"],
        test_x=embeddings["test"],
        train_y=train_y,
        validation_y=validation_y,
        train_stable_keys=stable_keys["train"],
        validation_stable_keys=stable_keys["validation"],
        test_stable_keys=stable_keys["test"],
        evidence=evidence,
    )


def _prediction_metadata(path: Path, values: np.ndarray, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(path).replace("\\", "/"),
        "rows": int(values.shape[0]),
        "columns": int(values.shape[1]),
        "dtype": str(values.dtype),
        "array_sha256": array_hash(values),
        "file_sha256": _sha256_file(path),
    }


def publish_probe_fit(
    inputs: VerifiedProbeInputs,
    artifacts: PredictedExecutorArtifacts,
    output_dir: Path,
) -> dict[str, Any]:
    """Atomically publish predictions and the hash-complete probe-fit report."""
    values_by_role = {
        "train_candidates": artifacts.train_candidates.values,
        "validation_rows": artifacts.validation_rows.values,
        "test_queries": artifacts.test_queries.values,
    }
    predictions: dict[str, Any] = {}
    for role, values in values_by_role.items():
        if values.dtype != np.float64 or values.shape[1] != len(PRIMITIVES):
            raise ValueError(f"{role} predictions do not match the frozen contract")
        path = output_dir / PREDICTION_FILENAMES[role]
        _atomic_save_npy(path, values)
        predictions[role] = _prediction_metadata(path, values, role)

    report = {
        "probe_bundle_id": "option-b-primitive-probe-bundle-v1",
        "status": "PRIMITIVE_PROBE_FIT_COMPLETE_PENDING_PUBLICATION_REVIEW",
        "scientific_result_observed": False,
        "runtime": _runtime_identity(),
        "fit_scope": {
            "scaler": "train primitive labels only",
            "ridge_coefficients": "train embeddings and primitive labels only",
            "alpha_selection": "validation embeddings and primitive labels only",
            "test_primitive_labels": "not parsed or passed to fitting API",
        },
        "inputs": inputs.evidence,
        "contract": artifacts.report,
        "predictions": predictions,
        "next_allowed_action": "CANONICAL_PROBE_ARTIFACT_PUBLICATION",
        "prohibited_actions": [
            "hard-negative generation before probe artifact review",
            "scientific metric evaluation before hard-negative checkpoint",
            "test-label use in preprocessing, fitting, or model selection",
            "prediction rounding",
            "threshold, query, model, language, or canonical-row changes",
        ],
    }
    report_path = output_dir / "option-b-primitive-probe-bundle-v1.json"
    _atomic_write_json(report_path, report)
    report["report_file_sha256"] = _sha256_file(report_path)
    return report


def run_probe_fit(
    *,
    checkpoint_path: Path = DEFAULT_EMBEDDING_CHECKPOINT,
    amendment_path: Path = DEFAULT_GPU_AMENDMENT,
    selection_dir: Path = DEFAULT_SELECTION_DIR,
    embedding_report_path: Path = DEFAULT_EMBEDDING_REPORT,
    embedding_dir: Path = DEFAULT_EMBEDDING_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    alphas: tuple[float, ...] = ALPHAS,
    folds: int = 5,
) -> dict[str, Any]:
    """Fit the reviewed contract once inputs pass all evidence gates."""
    inputs = verify_probe_inputs(
        checkpoint_path=checkpoint_path,
        amendment_path=amendment_path,
        selection_dir=selection_dir,
        embedding_report_path=embedding_report_path,
        embedding_dir=embedding_dir,
    )
    artifacts = fit_predicted_executor_contract(
        train_x=inputs.train_x,
        train_true_primitives=inputs.train_y,
        validation_x=inputs.validation_x,
        validation_true_primitives=inputs.validation_y,
        test_x=inputs.test_x,
        train_stable_keys=inputs.train_stable_keys,
        validation_stable_keys=inputs.validation_stable_keys,
        test_stable_keys=inputs.test_stable_keys,
        alphas=alphas,
        folds=folds,
    )
    return publish_probe_fit(inputs, artifacts, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-checkpoint", type=Path, default=DEFAULT_EMBEDDING_CHECKPOINT)
    parser.add_argument("--gpu-amendment", type=Path, default=DEFAULT_GPU_AMENDMENT)
    parser.add_argument("--selection-dir", type=Path, default=DEFAULT_SELECTION_DIR)
    parser.add_argument("--embedding-report", type=Path, default=DEFAULT_EMBEDDING_REPORT)
    parser.add_argument("--embedding-dir", type=Path, default=DEFAULT_EMBEDDING_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()
    print(
        json.dumps(
            run_probe_fit(
                checkpoint_path=args.embedding_checkpoint,
                amendment_path=args.gpu_amendment,
                selection_dir=args.selection_dir,
                embedding_report_path=args.embedding_report,
                embedding_dir=args.embedding_dir,
                output_dir=args.output_dir,
                folds=args.folds,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

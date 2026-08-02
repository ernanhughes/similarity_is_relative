"""Independently verify two Option B embedding runs and publish a checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

SPLITS = ("train", "validation", "test")
EXPECTED_RUN_STATUS = "EMBEDDING_RUN_COMPLETE_PENDING_INDEPENDENT_REPRODUCTION"
CHECKPOINT_STATUS = "CANONICAL_EMBEDDINGS_V2_REPRODUCED"
FINGERPRINT_SCHEMA = "option-b-extraction-fingerprint-v1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _array_hash(value: np.ndarray) -> str:
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


def _sequence_hash(values: list[str]) -> str:
    return _sha256_json(values)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _verify_canonical_inputs(
    identity_path: Path,
    selection_dir: Path,
) -> dict[str, Any]:
    identity = _load_json(identity_path)
    if identity.get("status") != "EMBEDDING_IDENTITY_V2_COMPLETE":
        raise ValueError("canonical embedding identity v2 is incomplete")
    if identity.get("identity_id") != "option-b-embedding-identity-v2":
        raise ValueError("unexpected canonical embedding identity id")

    selection_report_path = selection_dir / "option-b-canonical-row-selection-v2.json"
    selection_report = _load_json(selection_report_path)
    if selection_report.get("status") != "CANONICAL_ROW_SELECTION_V2_VERIFIED":
        raise ValueError("canonical selection v2 is incomplete")

    manifests: dict[str, Any] = {}
    for split in SPLITS:
        path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
        expected = selection_report["artifacts"][split]["selected_manifest"]
        if _sha256_file(path) != expected["sha256"]:
            raise ValueError(f"{split} canonical manifest hash mismatch")
        rows = _load_manifest(path)
        if len(rows) != expected["rows"]:
            raise ValueError(f"{split} canonical manifest row count mismatch")
        manifests[split] = {
            "path": str(path).replace("\\", "/"),
            "file_sha256": expected["sha256"],
            "rows": len(rows),
            "stable_key_sequence_sha256": _sequence_hash([row["stable_key"] for row in rows]),
            "source_sequence_sha256": _sequence_hash([row["code_sha256"] for row in rows]),
        }
    return {
        "identity": identity,
        "identity_file_sha256": _sha256_file(identity_path),
        "selection_report_file_sha256": _sha256_file(selection_report_path),
        "manifests": manifests,
    }


def _verify_run(
    report_path: Path,
    *,
    canonical: dict[str, Any],
    required_device: str,
) -> dict[str, Any]:
    report = _load_json(report_path)
    if report.get("embedding_id") != "option-b-canonical-embeddings-v2":
        raise ValueError(f"{report_path}: unexpected embedding id")
    if report.get("status") != EXPECTED_RUN_STATUS:
        raise ValueError(f"{report_path}: run status is not complete")
    if report.get("scientific_result_observed") is not False:
        raise ValueError(f"{report_path}: scientific result boundary was violated")
    if report.get("fixture_preflight", {}).get("status") != (
        "EMBEDDING_FIXTURE_PREFLIGHT_VERIFIED"
    ):
        raise ValueError(f"{report_path}: fixture preflight was not verified")
    if report.get("next_allowed_action") != "INDEPENDENT_EMBEDDING_REPRODUCTION":
        raise ValueError(f"{report_path}: unexpected next action")

    identity = report.get("identity", {})
    if identity.get("identity_id") != canonical["identity"]["identity_id"]:
        raise ValueError(f"{report_path}: identity id mismatch")
    if identity.get("file_sha256") != canonical["identity_file_sha256"]:
        raise ValueError(f"{report_path}: identity file hash mismatch")

    runtime = report.get("runtime", {})
    device = str(runtime.get("device", ""))
    if required_device == "cuda":
        if not device.startswith("cuda"):
            raise ValueError(f"{report_path}: CUDA run required")
        if not runtime.get("gpu_name") or not runtime.get("cuda_runtime"):
            raise ValueError(f"{report_path}: incomplete CUDA runtime identity")
    elif device != "cpu":
        raise ValueError(f"{report_path}: CPU run required")

    cache = report.get("cache", {})
    if cache.get("mode") != "refresh":
        raise ValueError(f"{report_path}: independent runs must use refresh mode")
    if not cache.get("path"):
        raise ValueError(f"{report_path}: independent run requires a separate cache database")
    if cache.get("legacy_embedding_table_reused") is not False:
        raise ValueError(f"{report_path}: legacy embedding cache reuse is forbidden")

    recovery = report.get("recovery", {})
    if recovery.get("fingerprint_schema") != FINGERPRINT_SCHEMA:
        raise ValueError(f"{report_path}: unexpected fingerprint schema")
    if recovery.get("chunk_directory_is_fingerprint_scoped") is not True:
        raise ValueError(f"{report_path}: chunks are not fingerprint scoped")
    if recovery.get("refresh_and_off_bypass_chunk_reuse") is not True:
        raise ValueError(f"{report_path}: refresh bypass is not certified")
    if recovery.get("atomic_chunk_writes") is not True:
        raise ValueError(f"{report_path}: atomic chunk writes are not certified")

    verified_artifacts: dict[str, Any] = {}
    for split in SPLITS:
        artifact = report.get("artifacts", {}).get(split)
        if not isinstance(artifact, dict):
            raise ValueError(f"{report_path}: missing {split} artifact")
        canonical_manifest = canonical["manifests"][split]
        if report["selection_manifest_sha256"][split] != canonical_manifest["file_sha256"]:
            raise ValueError(f"{report_path}: {split} selection hash mismatch")

        expected_matrix_path = report_path.parent / f"option-b-embeddings-{split}-v2.npy"
        if Path(str(artifact.get("path", ""))).name != expected_matrix_path.name:
            raise ValueError(f"{report_path}: unexpected {split} matrix filename")
        matrix = np.load(expected_matrix_path, allow_pickle=False)
        if matrix.ndim != 2 or matrix.dtype != np.float32:
            raise ValueError(f"{report_path}: invalid {split} matrix shape or dtype")
        if not np.isfinite(matrix).all():
            raise ValueError(f"{report_path}: non-finite {split} matrix")
        if int(artifact.get("rows", -1)) != matrix.shape[0]:
            raise ValueError(f"{report_path}: {split} row count mismatch")
        if int(artifact.get("dimensions", -1)) != matrix.shape[1]:
            raise ValueError(f"{report_path}: {split} dimension mismatch")
        if artifact.get("dtype") != "float32":
            raise ValueError(f"{report_path}: {split} report dtype mismatch")
        if matrix.shape[0] != canonical_manifest["rows"]:
            raise ValueError(f"{report_path}: {split} canonical row count mismatch")
        actual_array_hash = _array_hash(matrix)
        actual_file_hash = _sha256_file(expected_matrix_path)
        if artifact.get("array_sha256") != actual_array_hash:
            raise ValueError(f"{report_path}: {split} logical array hash mismatch")
        if artifact.get("file_sha256") != actual_file_hash:
            raise ValueError(f"{report_path}: {split} file hash mismatch")
        if int(artifact.get("verified_chunks_resumed", -1)) != 0:
            raise ValueError(f"{report_path}: {split} resumed chunks in an independent run")
        if int(artifact.get("sqlite_cache_hits", -1)) != 0:
            raise ValueError(f"{report_path}: {split} reused cached embeddings")
        if int(artifact.get("sqlite_cache_misses", -1)) != matrix.shape[0]:
            raise ValueError(f"{report_path}: {split} did not recompute every row")

        fingerprint_payload = artifact.get("extraction_fingerprint")
        fingerprint_sha = artifact.get("extraction_fingerprint_sha256")
        if not isinstance(fingerprint_payload, dict):
            raise ValueError(f"{report_path}: missing {split} fingerprint payload")
        if fingerprint_payload.get("schema") != FINGERPRINT_SCHEMA:
            raise ValueError(f"{report_path}: invalid {split} fingerprint schema")
        if _sha256_json(fingerprint_payload) != fingerprint_sha:
            raise ValueError(f"{report_path}: invalid {split} fingerprint hash")
        identity_config = canonical["identity"]["tokenization_config"]
        expected_fingerprint_fields = {
            "identity_file_sha256": canonical["identity_file_sha256"],
            "identity_id": canonical["identity"]["identity_id"],
            "model": canonical["identity"]["model"],
            "embedding_implementation_sha256": canonical["identity"][
                "embedding_implementation_sha256"
            ],
            "tokenization_config_sha256": canonical["identity"]["tokenization_config_sha256"],
            "tokenization_config": identity_config,
            "pooling_policy": identity_config["pooling_policy"],
            "output_dtype": identity_config["output_dtype"],
            "max_length": identity_config["max_length"],
            "split": split,
            "split_manifest_sha256": canonical_manifest["file_sha256"],
            "stable_key_sequence_sha256": canonical_manifest["stable_key_sequence_sha256"],
            "source_sequence_sha256": canonical_manifest["source_sequence_sha256"],
            "rows": canonical_manifest["rows"],
            "runtime": runtime,
        }
        for key, expected in expected_fingerprint_fields.items():
            if fingerprint_payload.get(key) != expected:
                raise ValueError(f"{report_path}: {split} fingerprint mismatch for {key}")

        verified_artifacts[split] = {
            "matrix_path": str(expected_matrix_path).replace("\\", "/"),
            "rows": int(matrix.shape[0]),
            "dimensions": int(matrix.shape[1]),
            "dtype": str(matrix.dtype),
            "array_sha256": actual_array_hash,
            "file_sha256": actual_file_hash,
            "extraction_fingerprint_sha256": fingerprint_sha,
            "_matrix": matrix,
        }

    return {
        "report_path": str(report_path).replace("\\", "/"),
        "report_file_sha256": _sha256_file(report_path),
        "runtime": runtime,
        "cache_path": str(cache["path"]),
        "artifacts": verified_artifacts,
    }


def verify_independent_runs(
    run_a_report: Path,
    run_b_report: Path,
    *,
    identity_path: Path,
    selection_dir: Path,
    required_device: str = "cuda",
) -> dict[str, Any]:
    if run_a_report.resolve() == run_b_report.resolve():
        raise ValueError("run A and run B reports must be different files")
    if run_a_report.parent.resolve() == run_b_report.parent.resolve():
        raise ValueError("run A and run B must use different output directories")
    if required_device not in {"cuda", "cpu"}:
        raise ValueError("required device must be cuda or cpu")

    canonical = _verify_canonical_inputs(identity_path, selection_dir)
    run_a = _verify_run(
        run_a_report,
        canonical=canonical,
        required_device=required_device,
    )
    run_b = _verify_run(
        run_b_report,
        canonical=canonical,
        required_device=required_device,
    )
    if run_a["runtime"] != run_b["runtime"]:
        raise ValueError("run A and run B runtime identities differ")
    if Path(run_a["cache_path"]).resolve() == Path(run_b["cache_path"]).resolve():
        raise ValueError("run A and run B must use separate SQLite databases")

    split_results: dict[str, Any] = {}
    for split in SPLITS:
        a = run_a["artifacts"][split]
        b = run_b["artifacts"][split]
        if a["extraction_fingerprint_sha256"] != b["extraction_fingerprint_sha256"]:
            raise ValueError(f"{split} extraction fingerprints differ")
        if a["array_sha256"] != b["array_sha256"]:
            raise ValueError(f"{split} logical array hashes differ")
        if not np.array_equal(a["_matrix"], b["_matrix"]):
            raise ValueError(f"{split} embedding matrices are not exactly equal")
        split_results[split] = {
            "rows": a["rows"],
            "dimensions": a["dimensions"],
            "dtype": a["dtype"],
            "array_sha256": a["array_sha256"],
            "exact_array_equal": True,
            "extraction_fingerprint_sha256": a["extraction_fingerprint_sha256"],
            "run_a_file_sha256": a["file_sha256"],
            "run_b_file_sha256": b["file_sha256"],
            "file_sha256_equal": a["file_sha256"] == b["file_sha256"],
        }

    return {
        "checkpoint_id": "option-b-independent-embedding-reproduction-v2",
        "status": CHECKPOINT_STATUS,
        "scientific_result_observed": False,
        "required_device": required_device,
        "identity": {
            "path": str(identity_path).replace("\\", "/"),
            "file_sha256": canonical["identity_file_sha256"],
            "identity_id": canonical["identity"]["identity_id"],
        },
        "selection": {
            "directory": str(selection_dir).replace("\\", "/"),
            "report_file_sha256": canonical["selection_report_file_sha256"],
            "manifests": canonical["manifests"],
        },
        "runtime": run_a["runtime"],
        "runs": {
            "a": {
                "report_path": run_a["report_path"],
                "report_file_sha256": run_a["report_file_sha256"],
                "cache_path": run_a["cache_path"],
            },
            "b": {
                "report_path": run_b["report_path"],
                "report_file_sha256": run_b["report_file_sha256"],
                "cache_path": run_b["cache_path"],
            },
        },
        "splits": split_results,
        "next_allowed_action": "PRIMITIVE_PROBE_FITTING",
        "prohibited_actions": [
            "scientific metric evaluation before probe and hard-negative checkpoints",
            "threshold, query, model, language, or canonical-row changes",
        ],
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-a-report", type=Path, required=True)
    parser.add_argument("--run-b-report", type=Path, required=True)
    parser.add_argument(
        "--identity",
        type=Path,
        default=Path("artifacts/canonical/option-b/option-b-embedding-identity-v2.json"),
    )
    parser.add_argument(
        "--selection-dir",
        type=Path,
        default=Path("artifacts/canonical/option-b/selection"),
    )
    parser.add_argument(
        "--required-device",
        choices=("cuda", "cpu"),
        default="cuda",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "runs/option-b/embedding-reproduction/"
            "option-b-independent-embedding-reproduction-v2.json"
        ),
    )
    args = parser.parse_args()
    checkpoint = verify_independent_runs(
        args.run_a_report,
        args.run_b_report,
        identity_path=args.identity,
        selection_dir=args.selection_dir,
        required_device=args.required_device,
    )
    _atomic_write_json(args.output, checkpoint)
    print(json.dumps(checkpoint, indent=2, sort_keys=True))
    print(f"Written to: {args.output}")


if __name__ == "__main__":
    main()

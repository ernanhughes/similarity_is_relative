from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from relate.experiments.option_b_embedding_reproduction import (
    _array_hash,
    _sequence_hash,
    _sha256_file,
    _sha256_json,
    verify_independent_runs,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> str:
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256_file(path)


def _fixture(tmp_path: Path):
    identity_path = tmp_path / "identity.json"
    identity = {
        "identity_id": "option-b-embedding-identity-v2",
        "status": "EMBEDDING_IDENTITY_V2_COMPLETE",
    }
    _write_json(identity_path, identity)

    selection = tmp_path / "selection"
    artifacts = {}
    manifests = {}
    for split, rows in (("train", 4), ("validation", 2), ("test", 2)):
        values = [
            {"stable_key": f"{split}-{index}", "code_sha256": f"{index:064x}"}
            for index in range(rows)
        ]
        path = selection / f"option-b-selected-{split}-v2.jsonl"
        digest = _write_jsonl(path, values)
        artifacts[split] = {"selected_manifest": {"rows": rows, "sha256": digest}}
        manifests[split] = values
    _write_json(
        selection / "option-b-canonical-row-selection-v2.json",
        {"status": "CANONICAL_ROW_SELECTION_V2_VERIFIED", "artifacts": artifacts},
    )

    runtime = {
        "python": "3.11.4",
        "numpy": np.__version__,
        "torch": "test",
        "transformers": "test",
        "tokenizers": "test",
        "device": "cuda",
        "cuda_runtime": "12.8",
        "gpu_name": "Test GPU",
    }
    return identity_path, selection, manifests, runtime


def _write_run(
    directory: Path,
    *,
    identity_path: Path,
    selection: Path,
    manifests,
    runtime,
    cache_path: Path,
    mutate_split: str | None = None,
    cache_hits: int = 0,
):
    directory.mkdir(parents=True)
    selection_report = json.loads(
        (selection / "option-b-canonical-row-selection-v2.json").read_text()
    )
    run_artifacts = {}
    selection_hashes = {}
    for split, rows in manifests.items():
        matrix = np.arange(len(rows) * 3, dtype=np.float32).reshape(len(rows), 3)
        if split == mutate_split:
            matrix = matrix.copy()
            matrix[0, 0] += 1
        matrix_path = directory / f"option-b-embeddings-{split}-v2.npy"
        np.save(matrix_path, matrix, allow_pickle=False)
        manifest_hash = selection_report["artifacts"][split]["selected_manifest"]["sha256"]
        selection_hashes[split] = manifest_hash
        fingerprint = {
            "schema": "option-b-extraction-fingerprint-v1",
            "identity_file_sha256": _sha256_file(identity_path),
            "identity_id": "option-b-embedding-identity-v2",
            "model": {"repo_id": "microsoft/codebert-base", "revision": "rev"},
            "embedding_implementation_sha256": "a" * 64,
            "tokenization_config_sha256": "b" * 64,
            "tokenization_config": {"padding": "max_length"},
            "pooling_policy": "attention-mask mean pooling",
            "output_dtype": "float32",
            "max_length": 256,
            "split": split,
            "split_manifest_sha256": manifest_hash,
            "stable_key_sequence_sha256": _sequence_hash(
                [row["stable_key"] for row in rows]
            ),
            "source_sequence_sha256": _sequence_hash(
                [row["code_sha256"] for row in rows]
            ),
            "rows": len(rows),
            "batch_size": 2,
            "runtime": runtime,
        }
        run_artifacts[split] = {
            "path": str(matrix_path),
            "rows": len(rows),
            "dimensions": 3,
            "dtype": "float32",
            "array_sha256": _array_hash(matrix),
            "file_sha256": _sha256_file(matrix_path),
            "extraction_fingerprint_sha256": _sha256_json(fingerprint),
            "extraction_fingerprint": fingerprint,
            "verified_chunks_resumed": 0,
            "chunks_recomputed": (len(rows) + 1) // 2,
            "chunk_rejection_reasons": {"reuse-bypassed": (len(rows) + 1) // 2},
            "sqlite_cache_hits": cache_hits,
            "sqlite_cache_misses": len(rows) - cache_hits,
        }
    report = {
        "embedding_id": "option-b-canonical-embeddings-v2",
        "status": "EMBEDDING_RUN_COMPLETE_PENDING_INDEPENDENT_REPRODUCTION",
        "scientific_result_observed": False,
        "identity": {
            "path": str(identity_path),
            "file_sha256": _sha256_file(identity_path),
            "identity_id": "option-b-embedding-identity-v2",
        },
        "fixture_preflight": {"status": "EMBEDDING_FIXTURE_PREFLIGHT_VERIFIED"},
        "model": {},
        "selection_manifest_sha256": selection_hashes,
        "runtime": runtime,
        "cache": {
            "mode": "refresh",
            "path": str(cache_path),
            "schema": "embeddings_v2",
            "legacy_embedding_table_reused": False,
        },
        "recovery": {
            "fingerprint_schema": "option-b-extraction-fingerprint-v1",
            "chunk_schema": "option-b-embedding-chunk-v2",
            "chunk_directory_is_fingerprint_scoped": True,
            "refresh_and_off_bypass_chunk_reuse": True,
            "atomic_chunk_writes": True,
        },
        "artifacts": run_artifacts,
        "next_allowed_action": "INDEPENDENT_EMBEDDING_REPRODUCTION",
    }
    report_path = directory / "option-b-canonical-embeddings-v2.json"
    _write_json(report_path, report)
    return report_path


def test_independent_runs_publish_checkpoint(tmp_path: Path) -> None:
    identity, selection, manifests, runtime = _fixture(tmp_path)
    run_a = _write_run(
        tmp_path / "a",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "a.sqlite3",
    )
    run_b = _write_run(
        tmp_path / "b",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "b.sqlite3",
    )

    result = verify_independent_runs(
        run_a,
        run_b,
        identity_path=identity,
        selection_dir=selection,
        required_device="cuda",
    )

    assert result["status"] == "CANONICAL_EMBEDDINGS_V2_REPRODUCED"
    assert all(value["exact_array_equal"] for value in result["splits"].values())
    assert result["next_allowed_action"] == "PRIMITIVE_PROBE_FITTING"


def test_rejects_logically_different_arrays(tmp_path: Path) -> None:
    identity, selection, manifests, runtime = _fixture(tmp_path)
    run_a = _write_run(
        tmp_path / "a",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "a.sqlite3",
    )
    run_b = _write_run(
        tmp_path / "b",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "b.sqlite3",
        mutate_split="test",
    )

    with pytest.raises(ValueError, match="test logical array hashes differ"):
        verify_independent_runs(
            run_a,
            run_b,
            identity_path=identity,
            selection_dir=selection,
        )


def test_rejects_shared_cache_database(tmp_path: Path) -> None:
    identity, selection, manifests, runtime = _fixture(tmp_path)
    cache = tmp_path / "shared.sqlite3"
    run_a = _write_run(
        tmp_path / "a",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=cache,
    )
    run_b = _write_run(
        tmp_path / "b",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=cache,
    )

    with pytest.raises(ValueError, match="separate SQLite"):
        verify_independent_runs(
            run_a,
            run_b,
            identity_path=identity,
            selection_dir=selection,
        )


def test_rejects_cache_hits_in_refresh_run(tmp_path: Path) -> None:
    identity, selection, manifests, runtime = _fixture(tmp_path)
    run_a = _write_run(
        tmp_path / "a",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "a.sqlite3",
        cache_hits=1,
    )
    run_b = _write_run(
        tmp_path / "b",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "b.sqlite3",
    )

    with pytest.raises(ValueError, match="reused cached embeddings"):
        verify_independent_runs(
            run_a,
            run_b,
            identity_path=identity,
            selection_dir=selection,
        )


def test_rejects_runtime_difference(tmp_path: Path) -> None:
    identity, selection, manifests, runtime = _fixture(tmp_path)
    run_a = _write_run(
        tmp_path / "a",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=runtime,
        cache_path=tmp_path / "a.sqlite3",
    )
    changed = dict(runtime, torch="different")
    run_b = _write_run(
        tmp_path / "b",
        identity_path=identity,
        selection=selection,
        manifests=manifests,
        runtime=changed,
        cache_path=tmp_path / "b.sqlite3",
    )

    with pytest.raises(ValueError, match="runtime identities differ"):
        verify_independent_runs(
            run_a,
            run_b,
            identity_path=identity,
            selection_dir=selection,
        )

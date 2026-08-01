from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from relate.experiments.option_b_embeddings import extract_split, verify_inputs


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> str:
    import hashlib

    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def test_verify_inputs_checks_manifest_hashes(tmp_path: Path) -> None:
    identity = tmp_path / "identity.json"
    selection = tmp_path / "selection"
    _write_json(
        identity,
        {
            "status": "IDENTITY_CAPTURE_COMPLETE",
            "model": {"repo_id": "microsoft/codebert-base", "revision": "model"},
        },
    )
    artifacts = {}
    for split, count in (("train", 2), ("validation", 1), ("test", 1)):
        rows = [{"stable_key": f"{split}-{index}"} for index in range(count)]
        path = selection / f"option-b-selected-{split}-v1.jsonl"
        digest = _write_jsonl(path, rows)
        artifacts[split] = {"selected_manifest": {"rows": count, "sha256": digest}}
    _write_json(
        selection / "option-b-canonical-row-selection-v1.json",
        {"status": "CANONICAL_ROW_SELECTION_COMPLETE", "artifacts": artifacts},
    )

    loaded_identity, manifests = verify_inputs(identity, selection)

    assert loaded_identity["model"]["revision"] == "model"
    assert [row["stable_key"] for row in manifests["train"]] == ["train-0", "train-1"]


def test_extract_split_resumes_existing_chunks(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def embed(batch: list[str]) -> np.ndarray:
        calls.append(batch)
        return np.asarray([[float(len(value)), 1.0] for value in batch], dtype=np.float32)

    codes = ["a", "bb", "ccc"]
    first = extract_split("test", codes, tmp_path, embed, batch_size=2)
    assert len(calls) == 2

    calls.clear()
    second = extract_split("test", codes, tmp_path, embed, batch_size=2)

    assert calls == []
    assert first["array_sha256"] == second["array_sha256"]
    assert first["rows"] == 3
    assert first["dimensions"] == 2

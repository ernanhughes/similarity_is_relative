from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from relate.experiments import option_b_embeddings
from relate.experiments.option_b_embedding import (
    embedding_implementation_sha256,
    tokenization_config,
    tokenization_config_sha256,
)
from relate.experiments.option_b_embeddings import extract_split, verify_inputs


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> str:
    import hashlib

    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _checkpoint(tmp_path: Path) -> tuple[Path, Path]:
    identity = tmp_path / "identity.json"
    selection = tmp_path / "selection"
    _write_json(
        identity,
        {
            "identity_id": "option-b-embedding-identity-v2",
            "status": "EMBEDDING_IDENTITY_V2_COMPLETE",
            "model": {"repo_id": "microsoft/codebert-base", "revision": "model"},
            "embedding_implementation_sha256": embedding_implementation_sha256(),
            "tokenization_config": tokenization_config(),
            "tokenization_config_sha256": tokenization_config_sha256(),
            "fixture_preflight_required": True,
        },
    )
    artifacts = {}
    for split, count in (("train", 2), ("validation", 1), ("test", 1)):
        rows = [{"stable_key": f"{split}-{index}"} for index in range(count)]
        path = selection / f"option-b-selected-{split}-v2.jsonl"
        digest = _write_jsonl(path, rows)
        artifacts[split] = {"selected_manifest": {"rows": count, "sha256": digest}}
    _write_json(
        selection / "option-b-canonical-row-selection-v2.json",
        {"status": "CANONICAL_ROW_SELECTION_V2_VERIFIED", "artifacts": artifacts},
    )
    return identity, selection


def test_verify_inputs_checks_identity_v2_and_manifest_hashes(tmp_path: Path) -> None:
    identity, selection = _checkpoint(tmp_path)

    loaded_identity, manifests = verify_inputs(identity, selection)

    assert loaded_identity["model"]["revision"] == "model"
    assert [row["stable_key"] for row in manifests["train"]] == ["train-0", "train-1"]


def test_verify_inputs_rejects_manifest_byte_tampering(tmp_path: Path) -> None:
    identity, selection = _checkpoint(tmp_path)
    train = selection / "option-b-selected-train-v2.jsonl"
    train.write_bytes(train.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="train selected manifest hash does not match checkpoint"):
        verify_inputs(identity, selection)


def test_verify_inputs_rejects_stale_embedding_implementation(tmp_path: Path) -> None:
    identity, selection = _checkpoint(tmp_path)
    value = json.loads(identity.read_text(encoding="utf-8"))
    value["embedding_implementation_sha256"] = "0" * 64
    _write_json(identity, value)

    with pytest.raises(ValueError, match="does not certify"):
        verify_inputs(identity, selection)


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


def test_fixture_preflight_happens_before_dataset_reconstruction(monkeypatch, tmp_path) -> None:
    identity = {
        "model": {"revision": "model"},
        "embedding_implementation_sha256": embedding_implementation_sha256(),
    }
    monkeypatch.setattr(option_b_embeddings, "verify_inputs", lambda *_args: (identity, {}))
    monkeypatch.setattr(
        option_b_embeddings,
        "load_canonical_backend",
        lambda **_kwargs: (object(), object(), object()),
    )
    monkeypatch.setattr(
        option_b_embeddings,
        "verify_fixture_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("fixture failed")),
    )
    reconstructed = False

    def reconstruct(*_args, **_kwargs):
        nonlocal reconstructed
        reconstructed = True
        return {}

    monkeypatch.setattr(option_b_embeddings, "reconstruct_selected_code", reconstruct)

    with pytest.raises(ValueError, match="fixture failed"):
        option_b_embeddings.run_extraction(
            tmp_path / "identity.json",
            tmp_path / "selection",
            tmp_path / "output",
        )
    assert reconstructed is False

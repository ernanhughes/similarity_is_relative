from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from relate.experiments.option_c0_discovery_entrypoint import (
    CPU_EMBEDDING_IDENTITY,
    CUDA_EMBEDDING_IDENTITY,
    DiscoveryIdentityError,
    fixed_batch_embed,
    select_embedding_identity_path,
    verify_identity_pair,
)


def _write_json(path: Path, value: dict[str, object]) -> str:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_identity() -> dict[str, object]:
    return {
        "identity_id": "option-b-external-identity-v1",
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
    }


def _embedding_identity(source_sha256: str) -> dict[str, object]:
    return {
        "identity_id": "option-b-embedding-identity-v2",
        "identity_variant": "gpu-fixed-batch10-amendment-v1",
        "status": "EMBEDDING_IDENTITY_V2_COMPLETE",
        "model": {
            "repo_id": "microsoft/codebert-base",
            "revision": "model-revision",
        },
        "dataset": {
            "repo_id": "code-search-net/code_search_net",
            "revision": "dataset-revision",
            "subset": "python",
        },
        "predecessor": {
            "identity_id": "option-b-external-identity-v1",
            "file_sha256": source_sha256,
        },
        "protocol_amendment": {
            "frozen_execution": {
                "device": "cuda",
                "batch_size": 10,
            }
        },
    }


def test_select_embedding_identity_uses_device_specific_checkpoint():
    assert select_embedding_identity_path("cuda") == CUDA_EMBEDDING_IDENTITY
    assert select_embedding_identity_path("cuda:0") == CUDA_EMBEDDING_IDENTITY
    assert select_embedding_identity_path("cpu") == CPU_EMBEDDING_IDENTITY


def test_verify_identity_pair_separates_source_and_cuda_embedding_roles(tmp_path: Path):
    source_path = tmp_path / "source.json"
    source_sha = _write_json(source_path, _source_identity())
    embedding_path = tmp_path / "embedding.json"
    _write_json(embedding_path, _embedding_identity(source_sha))

    source, embedding, lineage = verify_identity_pair(
        source_path,
        embedding_path,
        device="cuda",
        batch_size=10,
    )

    assert source["identity_id"] == "option-b-external-identity-v1"
    assert embedding["identity_id"] == "option-b-embedding-identity-v2"
    assert lineage["source_identity_sha256"] == source_sha
    assert lineage["batch_size"] == 10


def test_verify_identity_pair_rejects_wrong_predecessor_hash(tmp_path: Path):
    source_path = tmp_path / "source.json"
    _write_json(source_path, _source_identity())
    embedding_path = tmp_path / "embedding.json"
    _write_json(embedding_path, _embedding_identity("0" * 64))

    with pytest.raises(DiscoveryIdentityError, match="predecessor hash"):
        verify_identity_pair(
            source_path,
            embedding_path,
            device="cuda",
            batch_size=10,
        )


def test_fixed_batch_embed_pads_only_the_final_model_call():
    calls: list[list[str]] = []

    def embed_batch(codes: list[str]) -> np.ndarray:
        calls.append(codes)
        return np.asarray([[float(code)] for code in codes], dtype=np.float32)

    matrix, padded_rows = fixed_batch_embed(
        ["1", "2", "3", "4", "5"],
        embed_batch,
        batch_size=3,
    )

    assert calls == [["1", "2", "3"], ["4", "5", "5"]]
    assert padded_rows == 1
    assert matrix[:, 0].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]

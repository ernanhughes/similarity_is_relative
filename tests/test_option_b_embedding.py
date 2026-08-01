from __future__ import annotations

import hashlib

import numpy as np
import pytest

from relate.experiments.option_b_embedding import (
    MAX_LENGTH,
    canonical_embed_batch,
    canonical_embed_loaded,
    embedding_implementation_sha256,
    tokenization_config,
    tokenization_config_sha256,
    verify_fixture_preflight,
)
from relate.experiments.option_b_real_code import array_hash


torch = pytest.importorskip("torch")


class FakeTokenizer:
    padding_side = "left"
    truncation_side = "left"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, codes, **kwargs):
        self.calls.append(kwargs)
        rows = []
        masks = []
        for code in codes:
            width = min(len(code) + 2, MAX_LENGTH)
            row = list(range(1, width + 1)) + [0] * (MAX_LENGTH - width)
            mask = [1] * width + [0] * (MAX_LENGTH - width)
            rows.append(row)
            masks.append(mask)
        return {
            "input_ids": torch.tensor(rows, dtype=torch.int64),
            "attention_mask": torch.tensor(masks, dtype=torch.int64),
        }


class FakeModel:
    def __call__(self, **encoded):
        values = encoded["input_ids"].to(torch.float32)
        hidden = torch.stack((values, values * 2.0, values + 3.0), dim=-1)
        return type("Output", (), {"last_hidden_state": hidden})()


def test_canonical_embedding_uses_frozen_fixed_padding() -> None:
    tokenizer = FakeTokenizer()
    matrix = canonical_embed_batch(
        ["a", "abcd"],
        tokenizer,
        FakeModel(),
        device="cpu",
        torch_module=torch,
    )

    assert matrix.shape == (2, 3)
    assert matrix.dtype == np.float32
    assert tokenizer.padding_side == "right"
    assert tokenizer.truncation_side == "right"
    assert tokenizer.calls == [
        {
            "add_special_tokens": True,
            "padding": "max_length",
            "truncation": True,
            "max_length": 256,
            "return_tensors": "pt",
        }
    ]
    assert tokenization_config()["padding"] == "max_length"
    assert len(tokenization_config_sha256()) == 64
    assert len(embedding_implementation_sha256()) == 64


def test_canonical_embedding_is_exact_across_batch_partitions() -> None:
    codes = ["a", "bb", "ccc", "dddd", "eeeee"]
    tokenizer = FakeTokenizer()
    model = FakeModel()

    one_batch = canonical_embed_loaded(
        codes,
        tokenizer,
        model,
        batch_size=len(codes),
        device="cpu",
        torch_module=torch,
    )
    two_batches = canonical_embed_loaded(
        codes,
        tokenizer,
        model,
        batch_size=2,
        device="cpu",
        torch_module=torch,
    )
    one_row = canonical_embed_loaded(
        codes,
        tokenizer,
        model,
        batch_size=1,
        device="cpu",
        torch_module=torch,
    )

    assert np.array_equal(one_batch, two_batches)
    assert np.array_equal(one_batch, one_row)


def test_fixture_preflight_verifies_current_code_and_exact_rows() -> None:
    codes = ("a", "bb", "ccc")
    tokenizer = FakeTokenizer()
    model = FakeModel()
    matrix = canonical_embed_loaded(
        codes,
        tokenizer,
        model,
        batch_size=2,
        device="cpu",
        torch_module=torch,
    )
    identity = {
        "embedding_implementation_sha256": embedding_implementation_sha256(),
        "tokenization_config_sha256": tokenization_config_sha256(),
        "fixture": {
            "count": len(codes),
            "preflight_batch_size": 2,
            "matrix_array_sha256": array_hash(matrix),
            "rows": [
                {
                    "index": index,
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                    "embedding_array_sha256": array_hash(row),
                }
                for index, (code, row) in enumerate(zip(codes, matrix, strict=True))
            ],
        },
    }

    result = verify_fixture_preflight(
        identity,
        codes,
        tokenizer,
        model,
        device="cpu",
        torch_module=torch,
    )

    assert result["status"] == "EMBEDDING_FIXTURE_PREFLIGHT_VERIFIED"
    bad = {**identity, "tokenization_config_sha256": "0" * 64}
    with pytest.raises(ValueError, match="tokenization configuration"):
        verify_fixture_preflight(
            bad,
            codes,
            tokenizer,
            model,
            device="cpu",
            torch_module=torch,
        )

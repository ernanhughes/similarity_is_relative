from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from relate.experiments import option_b_identity_v2
from relate.experiments.option_b_embedding import MAX_LENGTH


torch = pytest.importorskip("torch")


class FakeTokenizer:
    padding_side = "right"
    truncation_side = "right"

    def __call__(self, codes, **_kwargs):
        rows = []
        masks = []
        for code in codes:
            width = min(len(code) + 2, MAX_LENGTH)
            rows.append(list(range(1, width + 1)) + [0] * (MAX_LENGTH - width))
            masks.append([1] * width + [0] * (MAX_LENGTH - width))
        return {
            "input_ids": torch.tensor(rows, dtype=torch.int64),
            "attention_mask": torch.tensor(masks, dtype=torch.int64),
        }


class FakeModel:
    def __call__(self, **encoded):
        values = encoded["input_ids"].to(torch.float32)
        hidden = torch.stack((values, values * 2.0), dim=-1)
        return type("Output", (), {"last_hidden_state": hidden})()


def _predecessor(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )


def test_identity_v2_preserves_revisions_and_requires_batch_invariance(
    monkeypatch, tmp_path: Path
) -> None:
    predecessor = tmp_path / "v1.json"
    _predecessor(predecessor)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}", encoding="utf-8")

    hub = ModuleType("huggingface_hub")
    hub.snapshot_download = lambda *_args, **_kwargs: str(snapshot)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setattr(
        option_b_identity_v2,
        "load_canonical_backend",
        lambda **_kwargs: (FakeTokenizer(), FakeModel(), torch),
    )

    output = tmp_path / "identity-v2.json"
    result = option_b_identity_v2.capture(output, predecessor_path=predecessor)

    assert result["status"] == "EMBEDDING_IDENTITY_V2_COMPLETE"
    assert result["model"]["revision"] == "model-revision"
    assert result["dataset"]["revision"] == "dataset-revision"
    assert result["tokenization_config"]["padding"] == "max_length"
    assert all(
        item["exactly_equal_to_canonical"]
        for item in result["fixture"]["batch_invariance"].values()
    )
    assert output.exists()


def test_identity_v2_rejects_non_cpu_capture(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be captured on cpu"):
        option_b_identity_v2.capture(tmp_path / "identity.json", device="cuda")

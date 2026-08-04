from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import numpy as np

from relate.experiments import option_b_identity


def test_identity_capture_uses_current_embed_code_api(monkeypatch, tmp_path) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}", encoding="utf-8")

    hub = ModuleType("huggingface_hub")
    hub.model_info = lambda _repo_id: SimpleNamespace(sha="model-revision")
    hub.dataset_info = lambda _repo_id: SimpleNamespace(sha="dataset-revision")
    hub.snapshot_download = lambda *_args, **_kwargs: str(snapshot)

    class FakeTokenizer:
        def __call__(self, code, **_kwargs):
            return {"input_ids": list(range(len(code.split()) + 2))}

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(*_args, **_kwargs):
            return FakeTokenizer()

    transformers = ModuleType("transformers")
    transformers.AutoTokenizer = FakeAutoTokenizer

    torch = ModuleType("torch")
    torch.__version__ = "test-torch"

    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setitem(sys.modules, "torch", torch)

    observed = {}

    def fake_embed_code(records, *, model_id, revision, batch_size, device):
        observed.update(
            {
                "record_count": len(records),
                "model_id": model_id,
                "revision": revision,
                "batch_size": batch_size,
                "device": device,
            }
        )
        return (
            np.arange(len(records) * 4, dtype=np.float32).reshape(len(records), 4),
            {"model_id": model_id, "revision": revision},
        )

    monkeypatch.setattr(option_b_identity, "embed_code", fake_embed_code)
    output = tmp_path / "identity.json"

    result = option_b_identity.capture(output)

    assert observed == {
        "record_count": 10,
        "model_id": "microsoft/codebert-base",
        "revision": "model-revision",
        "batch_size": 5,
        "device": "cpu",
    }
    assert result["fixture"]["embedding_shape"] == [10, 4]
    assert result["status"] == "IDENTITY_CAPTURE_COMPLETE"
    assert output.exists()

from __future__ import annotations

from types import SimpleNamespace

from relate.experiments import option_b_embedding_preflight


def test_cuda_preflight_records_runtime(monkeypatch, tmp_path) -> None:
    identity_path = tmp_path / "identity.json"
    identity_path.write_text(
        '{"identity_id":"option-b-embedding-identity-v2",'
        '"status":"EMBEDDING_IDENTITY_V2_COMPLETE",'
        '"model":{"revision":"model-revision"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        option_b_embedding_preflight,
        "load_canonical_backend",
        lambda **_kwargs: (
            object(),
            object(),
            SimpleNamespace(
                __version__="test-torch",
                version=SimpleNamespace(cuda="12.8"),
                cuda=SimpleNamespace(
                    is_available=lambda: True,
                    get_device_name=lambda _index: "Test GPU",
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        option_b_embedding_preflight,
        "verify_fixture_preflight",
        lambda *_args, **_kwargs: {
            "status": "EMBEDDING_FIXTURE_PREFLIGHT_VERIFIED",
            "rows": 10,
        },
    )

    result = option_b_embedding_preflight.run_preflight(
        identity_path,
        device="cuda",
    )

    assert result["status"] == "EMBEDDING_ENVIRONMENT_PREFLIGHT_VERIFIED"
    assert result["runtime"]["gpu_name"] == "Test GPU"
    assert result["next_allowed_action"] == "INDEPENDENT_EMBEDDING_RUN_A"

from __future__ import annotations

import sys

import pytest

from relate.experiments import option_b_probe_cli as cli


def test_probe_cli_exposes_no_alpha_or_fold_controls(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["relate-option-b-fit-probes", "--folds", "3"])

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 2


def test_probe_cli_passes_only_evidence_paths(monkeypatch, capsys) -> None:
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(cli, "run_probe_fit", fake_run)
    monkeypatch.setattr(sys, "argv", ["relate-option-b-fit-probes"])

    cli.main()

    assert "alphas" not in captured
    assert "folds" not in captured
    assert set(captured) == {
        "checkpoint_path",
        "amendment_path",
        "selection_dir",
        "embedding_report_path",
        "embedding_dir",
        "output_dir",
    }
    assert '"status": "ok"' in capsys.readouterr().out

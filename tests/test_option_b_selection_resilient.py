from __future__ import annotations

from collections import Counter

from relate.experiments import option_b_selection_resilient as resilient
from relate.experiments.option_b_real_code import OptionBConfig


class _Tokenizer:
    def __call__(self, code: str, **_: object) -> dict[str, list[int]]:
        return {"input_ids": list(range(32))}


def test_recursion_error_isolated_counted_and_reported(monkeypatch, capsys) -> None:
    rows = [
        {"code": "good", "_split": "train"},
        {"code": "bad", "_split": "train"},
        {"code": "also-good", "_split": "train"},
    ]

    def fake_build_records(batch, tokenizer, config):
        del tokenizer, config
        if any(row["code"] == "bad" for row in batch):
            raise RecursionError("pathological AST")
        return [row["code"] for row in batch], Counter()

    monkeypatch.setattr(resilient, "_build_records", fake_build_records)
    monkeypatch.setattr(resilient, "CHUNK_SIZE", 2)
    records, reasons = resilient.build_records_resilient(
        rows, _Tokenizer(), OptionBConfig()
    )

    assert records == ["good", "also-good"]
    assert reasons == Counter({"ast_recursion_limit": 1})
    output = capsys.readouterr().err
    assert "train: starting AST/token scan for 3 source rows" in output
    assert "2/3 rows" in output
    assert "3/3 rows" in output
    assert "ast_recursion_limit=1" in output

from __future__ import annotations

from collections import Counter

from relate.experiments import option_b_selection_resilient as resilient
from relate.experiments.option_b_real_code import OptionBConfig


class _Tokenizer:
    def __call__(self, code: str, **_: object) -> dict[str, list[int]]:
        return {"input_ids": list(range(32))}


def test_recursion_error_isolated_and_counted(monkeypatch) -> None:
    rows = [{"code": "good"}, {"code": "bad"}, {"code": "also-good"}]

    def fake_build_records(batch, tokenizer, config):
        del tokenizer, config
        if any(row["code"] == "bad" for row in batch):
            raise RecursionError("pathological AST")
        return [row["code"] for row in batch], Counter()

    monkeypatch.setattr(resilient, "_build_records", fake_build_records)
    records, reasons = resilient.build_records_resilient(rows, _Tokenizer(), OptionBConfig())

    assert records == ["good", "also-good"]
    assert reasons == Counter({"ast_recursion_limit": 1})

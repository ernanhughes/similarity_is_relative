from __future__ import annotations

from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json


def test_historical_protocol_writer_bytes_unchanged(tmp_path: Path) -> None:
    destination = tmp_path / "protocol.json"
    contract = historical.write_protocol_contract(destination)
    assert destination.read_text(encoding="utf-8") == canonical_json(contract) + "\n"
    assert historical.verify_protocol_contract(contract) is True
    assert contract["protocol_sha256"] == (
        "a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08"
    )


def test_historical_protocol_writer_overwrite_contract_unchanged(tmp_path: Path) -> None:
    destination = tmp_path / "protocol.json"
    historical.write_protocol_contract(destination)
    with pytest.raises(FileExistsError, match="refuses overwrite"):
        historical.write_protocol_contract(destination)
    historical.write_protocol_contract(destination, overwrite=True)

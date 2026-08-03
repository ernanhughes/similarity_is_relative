"""Small JSON file helpers for supported CLIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.immutable import refuse_overwrite


def read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON record must be an object: {path}")
    return value


def write_json_object_immutable(path: Path, value: dict[str, Any]) -> None:
    refuse_overwrite(path)
    atomic_write_json(path, value)

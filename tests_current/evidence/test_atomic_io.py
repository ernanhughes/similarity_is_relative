"""Tests for relate.evidence.atomic_io."""

from __future__ import annotations

import json
from pathlib import Path

from relate.evidence.atomic_io import atomic_write_json, fsync_directory


class TestFsyncDirectory:
    def test_no_error_on_existing_dir(self, tmp_path: Path) -> None:
        # Should not raise on a real directory.
        fsync_directory(tmp_path)

    def test_no_error_on_nested_dir(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        fsync_directory(nested)


class TestAtomicWriteJson:
    def test_writes_expected_content(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        data = {"key": "value", "number": 42}
        atomic_write_json(path, data)
        content = path.read_text(encoding="utf-8")
        assert json.loads(content) == data

    def test_indented_with_trailing_newline(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        data = {"a": 1}
        atomic_write_json(path, data)
        content = path.read_bytes().decode()
        # json.dumps with indent=2 produces a non-compact layout
        assert "  " in content
        assert content.endswith("\n")

    def test_sorted_keys(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"z": 1, "a": 2})
        content = path.read_bytes().decode()
        # "a" key must appear before "z" key in the file
        assert content.index('"a"') < content.index('"z"')

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "out.json"
        atomic_write_json(path, {"x": 1})
        assert path.exists()

    def test_no_temp_file_left_on_success(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        atomic_write_json(path, {"ok": True})
        leftover = list(tmp_path.glob(".out.json.tmp-*"))
        assert leftover == []

    def test_exact_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        data = {"b": 2, "a": 1}
        atomic_write_json(path, data)
        expected = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()
        assert path.read_bytes() == expected

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "out.json"
        path.write_text("old content", encoding="utf-8")
        atomic_write_json(path, {"new": True})
        assert json.loads(path.read_bytes()) == {"new": True}

    def test_nested_value(self, tmp_path: Path) -> None:
        path = tmp_path / "nested.json"
        data = {"outer": {"inner": [1, 2, 3]}}
        atomic_write_json(path, data)
        assert json.loads(path.read_bytes()) == data

    def test_empty_dict(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        atomic_write_json(path, {})
        assert json.loads(path.read_bytes()) == {}

"""Tests for relate.evidence.immutable."""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.evidence.immutable import refuse_overwrite


class TestRefuseOverwrite:
    def test_no_error_when_path_absent(self, tmp_path: Path) -> None:
        path = tmp_path / "not_yet_written.json"
        refuse_overwrite(path)  # should not raise

    def test_raises_when_path_exists(self, tmp_path: Path) -> None:
        path = tmp_path / "existing.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(FileExistsError):
            refuse_overwrite(path)

    def test_error_includes_label(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(FileExistsError, match="canonical artifact"):
            refuse_overwrite(path, label="canonical artifact")

    def test_error_includes_path_when_no_label(self, tmp_path: Path) -> None:
        path = tmp_path / "artifact.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(FileExistsError, match="artifact.json"):
            refuse_overwrite(path)

    def test_directory_raises(self, tmp_path: Path) -> None:
        existing_dir = tmp_path / "mydir"
        existing_dir.mkdir()
        with pytest.raises(FileExistsError):
            refuse_overwrite(existing_dir)

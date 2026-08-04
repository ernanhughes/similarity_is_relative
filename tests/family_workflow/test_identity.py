"""Source identity tests for the family workflow."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from relate.family.workflow.identity import (
    EXECUTION_CRITICAL_SOURCE_FILES,
    FAMILY_WORKFLOW_SOURCE_MANIFEST_SCHEMA_ID,
    compute_family_workflow_source_identity,
)


def _copy_source_manifest(src_root: Path, dst_root: Path) -> None:
    for relative in EXECUTION_CRITICAL_SOURCE_FILES:
        target = dst_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_root / relative, target)


def test_source_identity_is_deterministic() -> None:
    repo_root = Path.cwd()
    assert compute_family_workflow_source_identity(repo_root) == (
        compute_family_workflow_source_identity(repo_root)
    )


def test_source_identity_is_absolute_path_independent(tmp_path: Path) -> None:
    _copy_source_manifest(Path.cwd(), tmp_path)
    assert compute_family_workflow_source_identity(Path.cwd()) == (
        compute_family_workflow_source_identity(tmp_path)
    )


def test_source_identity_is_content_sensitive(tmp_path: Path) -> None:
    _copy_source_manifest(Path.cwd(), tmp_path)
    before = compute_family_workflow_source_identity(tmp_path)
    target = tmp_path / EXECUTION_CRITICAL_SOURCE_FILES[0]
    target.write_text(target.read_text(encoding="utf-8") + "\n# identity test\n", encoding="utf-8")
    assert compute_family_workflow_source_identity(tmp_path) != before


def test_missing_execution_critical_source_file_rejected(tmp_path: Path) -> None:
    _copy_source_manifest(Path.cwd(), tmp_path)
    (tmp_path / EXECUTION_CRITICAL_SOURCE_FILES[0]).unlink()
    with pytest.raises(FileNotFoundError):
        compute_family_workflow_source_identity(tmp_path)


def test_manifest_schema_and_file_list_are_explicit() -> None:
    assert FAMILY_WORKFLOW_SOURCE_MANIFEST_SCHEMA_ID == (
        "relate-family-workflow-source-manifest-v1"
    )
    assert EXECUTION_CRITICAL_SOURCE_FILES == tuple(sorted(EXECUTION_CRITICAL_SOURCE_FILES))
    assert all(not Path(relative).is_absolute() for relative in EXECUTION_CRITICAL_SOURCE_FILES)
    assert all(
        "artifacts/canonical" not in relative for relative in EXECUTION_CRITICAL_SOURCE_FILES
    )

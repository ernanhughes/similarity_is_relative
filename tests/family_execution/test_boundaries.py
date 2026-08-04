from __future__ import annotations

import ast
from pathlib import Path

from relate.cli.family import build_parser
from relate.family.workflow.models import FamilyWorkflowExecutionMode


def test_execute_command_has_only_authorized_inputs() -> None:
    help_text = build_parser().format_help()
    assert "execute-authorized-canonical" in help_text
    assert "run-canonical" not in help_text
    assert "approve-and-run" not in help_text
    assert "publish-canonical" not in help_text


def test_no_canonical_mode_enum_added() -> None:
    assert tuple(item.value for item in FamilyWorkflowExecutionMode) == ("NONCANONICAL",)


def test_execution_dependency_boundary_and_no_raw_sql() -> None:
    for path in (Path("src/relate/family/execution.py"), Path("src/relate/cli/family.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "relate.experiments"
            if isinstance(node, ast.Attribute):
                assert node.attr != "publish_canonical"
        text = path.read_text(encoding="utf-8")
        assert ".execute(" not in text
        assert "FamilyWorkflowExecutionMode.CANONICAL" not in text
        assert "publish-canonical" not in text
        assert "promote-canonical" not in text

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from relate.cli.family import EXIT_BLOCKED_OR_WITHHELD, EXIT_FAILURE, EXIT_OK, build_parser
from relate.family.workflow.models import FamilyWorkflowExecutionMode


def test_parser_exposes_separate_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for command in (
        "run-noncanonical",
        "make-publication-disposition",
        "publish-review",
        "create-canonical-execution-request",
        "make-canonical-execution-authorization",
        "verify-canonical-execution-authorization",
    ):
        assert command in help_text
    assert "approve-and-run" not in help_text
    assert "publish-canonical" not in help_text


def test_help_module_invocation() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "relate.cli.family", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == EXIT_OK
    assert "run-noncanonical" in result.stdout


def test_exit_codes_are_stable() -> None:
    assert EXIT_OK == 0
    assert EXIT_FAILURE == 1
    assert EXIT_BLOCKED_OR_WITHHELD == 3


def test_no_canonical_execution_enum_member() -> None:
    assert tuple(item.value for item in FamilyWorkflowExecutionMode) == ("NONCANONICAL",)


def test_no_execution_surface_in_authorization_or_cli() -> None:
    for path in (Path("src/relate/family/authorization.py"), Path("src/relate/cli/family.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr != "execute_canonical"
                assert node.attr != "publish_canonical"
            if isinstance(node, ast.ImportFrom):
                assert node.module != "relate.experiments"
        text = path.read_text(encoding="utf-8")
        assert "FamilyWorkflowExecutionMode.CANONICAL" not in text
        assert "publish_canonical" not in text
        assert "execute_canonical" not in text

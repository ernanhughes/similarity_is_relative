"""Dependency-boundary tests for relate.workflows.

Verifies that no module under src/relate/workflows/ imports relate.experiments
or relate.family, keeping the generic workflow kernel domain-neutral.
"""

from __future__ import annotations

import ast
from pathlib import Path

WORKFLOWS_PACKAGE = Path(__file__).resolve().parents[2] / "src" / "relate" / "workflows"

FORBIDDEN_PREFIXES = ("relate.experiments", "relate.family", "relate.cli")


def _imported_module_names(source: str) -> list[str]:
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class TestNoForbiddenImports:
    def test_package_exists(self) -> None:
        assert WORKFLOWS_PACKAGE.is_dir()

    def test_no_file_imports_experiments_family_or_cli(self) -> None:
        offenders: list[str] = []
        for path in sorted(WORKFLOWS_PACKAGE.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            for module_name in _imported_module_names(source):
                if any(
                    module_name == prefix or module_name.startswith(prefix + ".")
                    for prefix in FORBIDDEN_PREFIXES
                ):
                    offenders.append(f"{path.name} imports {module_name!r}")
        assert offenders == []

    def test_relate_workflows_importable_standalone(self) -> None:
        import relate.workflows  # noqa: F401

        assert hasattr(relate.workflows, "WorkflowRunner")
        assert hasattr(relate.workflows, "WorkflowContext")
        assert hasattr(relate.workflows, "WorkflowDefinition")

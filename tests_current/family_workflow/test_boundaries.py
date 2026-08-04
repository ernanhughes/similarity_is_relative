"""Safety and dependency-boundary checks for family workflow modules."""

from __future__ import annotations

import ast
from pathlib import Path

WORKFLOW_ROOT = Path("src/relate/family/workflow")


def _modules() -> tuple[Path, ...]:
    return tuple(sorted(WORKFLOW_ROOT.glob("*.py")))


def test_workflow_modules_do_not_import_historical_experiments_or_cli() -> None:
    for path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
            else:
                continue
            assert not any(name.startswith("relate.experiments") for name in imported)
            assert not any(name.startswith("relate.cli") for name in imported)


def test_workflow_steps_use_no_raw_sql_or_publication_network_cli_calls() -> None:
    path = WORKFLOW_ROOT / "steps.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden_imports = {"subprocess", "requests", "urllib", "httpx"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not (forbidden_imports & {alias.name.split(".", 1)[0] for alias in node.names})
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".", 1)[0] not in forbidden_imports
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr != "execute"
        elif isinstance(node, ast.Attribute):
            assert node.attr != "connection"

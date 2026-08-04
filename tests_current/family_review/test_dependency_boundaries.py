from __future__ import annotations

import ast
from pathlib import Path

MODULES = (
    Path("src/relate/family/review.py"),
    Path("src/relate/family/publication.py"),
)


def test_review_publication_modules_do_not_import_experiments_or_cli() -> None:
    for path in MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(name.startswith("relate.experiments") for name in names)
            assert not any(name.startswith("relate.cli") for name in names)


def test_no_raw_sql_in_review_publication_modules() -> None:
    for path in MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "execute"
            if isinstance(node, ast.Attribute):
                assert node.attr != "connection"


def test_workflow_steps_do_not_import_publication() -> None:
    text = Path("src/relate/family/workflow/steps.py").read_text(encoding="utf-8")
    assert "relate.family.publication" not in text
    assert "relate.family.review" not in text

from __future__ import annotations

import json
from pathlib import Path

from relate.experiments.option_b_real_code import OptionBConfig
from relate.experiments.option_b_selection import prepare_selection


class _Tokenizer:
    def __call__(self, code: str, **_: object) -> dict[str, list[int]]:
        return {"input_ids": list(range(max(32, min(256, len(code.split()) + 32))))}


def _identity(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "IDENTITY_CAPTURE_COMPLETE",
                "model": {
                    "repo_id": "microsoft/codebert-base",
                    "revision": "model-revision",
                },
                "dataset": {
                    "repo_id": "code-search-net/code_search_net",
                    "revision": "dataset-revision",
                    "subset": "python",
                },
                "fixture": {"matrix_sha256": "fixture-hash"},
                "pooling_implementation_sha256": "pooling-hash",
            }
        ),
        encoding="utf-8",
    )


def _row(repo: str, name: str, code: str) -> dict[str, str]:
    return {
        "repo": repo,
        "path": f"{name}.py",
        "func_name": name,
        "code": code,
    }


def test_selection_is_deterministic_and_removes_cross_split_duplicates(tmp_path: Path) -> None:
    identity = tmp_path / "identity.json"
    _identity(identity)
    duplicate = "def duplicate(x):\n    if x:\n        return call(x)\n    return None\n"
    dataset = {
        "train": [
            _row("repo-a", "train_a", "def train_a(x):\n    return one(x)\n"),
            _row("repo-a", "duplicate", duplicate),
        ],
        "validation": [
            _row("repo-b", "validation_a", "def validation_a(x):\n    return two(x)\n")
        ],
        "test": [
            _row("repo-c", "test_a", "def test_a(x):\n    return three(x)\n"),
            _row("repo-c", "duplicate", duplicate),
        ],
    }
    config = OptionBConfig(train_limit=10, validation_limit=10, test_limit=10)

    first = prepare_selection(
        identity,
        tmp_path / "first",
        config=config,
        dataset_by_split=dataset,
        tokenizer=_Tokenizer(),
    )
    second = prepare_selection(
        identity,
        tmp_path / "second",
        config=config,
        dataset_by_split=dataset,
        tokenizer=_Tokenizer(),
    )

    assert first["cross_split_deduplication"]["cross_split_ast_count"] == 1
    assert first["selected_rows"] == {"train": 1, "validation": 1, "test": 1}
    assert first["scientific_result_observed"] is False
    for split in ("train", "validation", "test"):
        assert (
            first["artifacts"][split]["selected_manifest"]["sha256"]
            == second["artifacts"][split]["selected_manifest"]["sha256"]
        )
        assert (
            first["artifacts"][split]["primitive_table"]["sha256"]
            == second["artifacts"][split]["primitive_table"]["sha256"]
        )


def test_selection_requires_canonical_identity(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    try:
        prepare_selection(
            missing,
            tmp_path / "output",
            dataset_by_split={"train": [], "validation": [], "test": []},
            tokenizer=_Tokenizer(),
        )
    except FileNotFoundError as error:
        assert "canonical identity artifact is required" in str(error)
    else:  # pragma: no cover
        raise AssertionError("selection should require the frozen identity artifact")

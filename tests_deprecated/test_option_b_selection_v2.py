from __future__ import annotations

import json
from pathlib import Path

from relate.experiments.option_b_real_code import AST_RECURSION_LIMIT, OptionBConfig
from relate.experiments.option_b_selection_v2 import prepare_selection_v2


class _Tokenizer:
    def __call__(self, code: str, **_: object) -> dict[str, list[int]]:
        return {"input_ids": list(range(32))}


def _identity(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "status": "IDENTITY_CAPTURE_COMPLETE",
                "model": {"repo_id": "microsoft/codebert-base", "revision": "model-revision"},
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


def _dataset() -> dict[str, list[dict[str, str]]]:
    return {
        split: [
            {
                "repository_name": f"repo-{split}",
                "func_path_in_repository": f"src/{split}.py",
                "func_name": split,
                "whole_func_string": f"def {split}(x):\n    return call(x)\n",
            }
        ]
        for split in ("train", "validation", "test")
    }


def test_selection_v2_preserves_v1_and_writes_versioned_artifacts(tmp_path: Path) -> None:
    identity = tmp_path / "identity.json"
    _identity(identity)
    output = tmp_path / "selection"
    report = prepare_selection_v2(
        identity,
        output,
        config=OptionBConfig(train_limit=1, validation_limit=1, test_limit=1),
        dataset_by_split=_dataset(),
        tokenizer=_Tokenizer(),
    )

    assert report["selection_id"] == "option-b-canonical-row-selection-v2"
    assert report["ast_recursion_limit"] == AST_RECURSION_LIMIT
    assert report["embedding_extraction_allowed"] is False
    assert (output / "option-b-selected-train-v2.jsonl").exists()
    assert (output / "option-b-primitives-test-v2.jsonl").exists()
    assert (output / "option-b-canonical-row-selection-v2.json").exists()
    assert not (output / "option-b-selected-train-v1.jsonl").exists()
    assert not (output / "option-b-canonical-row-selection-v1.json").exists()

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from relate.experiments.option_c0_data_firewall import prepare_c0_allocation
from relate.experiments.option_c0_data_firewall_independent import (
    RUNNER_IMPORTED,
    verify_c0_allocation,
)


class _Tokenizer:
    def __call__(self, code: str, **_: object) -> dict[str, list[int]]:
        return {"input_ids": list(range(32))}


def _write_identity(path: Path) -> None:
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
        newline="\n",
    )


def _dataset(repository_count: int = 12) -> dict[str, list[dict[str, str]]]:
    result = {"train": [], "validation": [], "test": []}
    splits = tuple(result)
    for index in range(repository_count):
        split = splits[index % len(splits)]
        result[split].append(
            {
                "repository_name": f"repo-{index:03d}",
                "func_path_in_repository": f"src/f_{index}.py",
                "func_name": f"f_{index}",
                "whole_func_string": (
                    f"def f_{index}(x):\n"
                    f"    return call_{index}(x)\n"
                ),
            }
        )
    return result


def _write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_id": "option-c0-repository-allocation-v1",
                "domain": "fixture-c0-allocation",
                "role_names": [
                    "c0_fit",
                    "c0_iteration",
                    "c0_selection",
                    "c1_reserve",
                ],
                "role_weights": [4, 2, 1, 3],
                "minimum_repositories": [1, 1, 1, 1],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_option_b_selection(path: Path) -> None:
    path.mkdir(parents=True)
    artifacts = {}
    repositories = {
        "train": "repo-000",
        "validation": "repo-001",
        "test": "repo-002",
    }
    for split, repository in repositories.items():
        manifest_path = path / f"option-b-selected-{split}-v2.jsonl"
        payload = (
            json.dumps(
                {
                    "repository": repository,
                    "stable_key": f"{split}-key",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        manifest_path.write_text(
            payload,
            encoding="utf-8",
            newline="\n",
        )
        artifacts[split] = {
            "selected_manifest": {
                "rows": 1,
                "sha256": hashlib.sha256(payload.encode()).hexdigest(),
            }
        }
    (path / "option-b-canonical-row-selection-v2.json").write_text(
        json.dumps(
            {
                "selection_id": "option-b-canonical-row-selection-v2",
                "artifacts": artifacts,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _prepare(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, list[dict[str, str]]]]:
    identity = tmp_path / "identity.json"
    selection = tmp_path / "selection"
    config = tmp_path / "config.json"
    result = tmp_path / "result"
    dataset = _dataset()
    _write_identity(identity)
    _write_option_b_selection(selection)
    _write_config(config)
    prepare_c0_allocation(
        identity,
        selection,
        config,
        result,
        dataset_by_split=dataset,
        tokenizer=_Tokenizer(),
    )
    (result / "option-c0-candidate-registry-v1.jsonl").write_bytes(b"")
    (result / "option-c0-discovery-ledger-v1.jsonl").write_bytes(b"")
    return identity, selection, config, dataset


def test_independent_verifier_does_not_import_runner() -> None:
    source = inspect.getsource(
        __import__(
            "relate.experiments.option_c0_data_firewall_independent",
            fromlist=["verify_c0_allocation"],
        )
    )
    forbidden = "from relate.experiments.option_c0_data_firewall import"
    assert forbidden not in source
    assert RUNNER_IMPORTED is False


def test_canonical_allocation_config_is_frozen() -> None:
    path = Path(
        "artifacts/canonical/option-c0/"
        "option-c0-allocation-config-v1.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value == {
        "domain": "option-c0-canonical-repository-allocation-v1:2026-08-02",
        "minimum_repositories": [64, 32, 32, 64],
        "role_names": [
            "c0_fit",
            "c0_iteration",
            "c0_selection",
            "c1_reserve",
        ],
        "role_weights": [4, 2, 1, 3],
        "schema_id": "option-c0-repository-allocation-v1",
    }


def test_independent_verification_exactly_recomputes_allocation(
    tmp_path: Path,
) -> None:
    identity, selection, config, dataset = _prepare(tmp_path)
    result = verify_c0_allocation(
        identity,
        selection,
        config,
        tmp_path / "result",
        dataset_by_split=dataset,
        tokenizer=_Tokenizer(),
    )
    assert result["status"] == (
        "C0_CANONICAL_REPOSITORY_ALLOCATION_INDEPENDENTLY_RECOMPUTED"
    )
    assert result["checks"]["allocation_exactly_equal"] is True
    assert result["checks"]["option_b_repositories_excluded"] is True
    assert result["counts"]["candidate_registry_entries"] == 0
    assert result["counts"]["discovery_ledger_entries"] == 0
    assert result["c1_rows_selected"] is False


def test_independent_verification_rejects_nonempty_registry(
    tmp_path: Path,
) -> None:
    identity, selection, config, dataset = _prepare(tmp_path)
    result_dir = tmp_path / "result"
    (result_dir / "option-c0-candidate-registry-v1.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="candidate registry"):
        verify_c0_allocation(
            identity,
            selection,
            config,
            result_dir,
            dataset_by_split=dataset,
            tokenizer=_Tokenizer(),
        )


def test_independent_verification_rejects_manifest_tampering(
    tmp_path: Path,
) -> None:
    identity, selection, config, dataset = _prepare(tmp_path)
    result_dir = tmp_path / "result"
    manifest = result_dir / "option-c0-repository-allocation-v1.jsonl"
    manifest.write_bytes(manifest.read_bytes() + b"{}\n")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verify_c0_allocation(
            identity,
            selection,
            config,
            result_dir,
            dataset_by_split=dataset,
            tokenizer=_Tokenizer(),
        )

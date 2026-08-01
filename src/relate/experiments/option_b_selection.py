"""Prepare the canonical Option B row and primitive manifests without embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from relate.experiments.option_b_real_code import (
    MODEL_ID,
    FunctionRecord,
    OptionBConfig,
    build_records,
    deterministic_limit,
    remove_cross_split_duplicates,
)

DATASET_ID = "code-search-net/code_search_net"
REQUIRED_SPLITS = ("train", "validation", "test")
DEFAULT_IDENTITY = Path(
    "artifacts/canonical/option-b/option-b-external-identity-v1.json"
)
DEFAULT_OUTPUT = Path("runs/option-b/selection")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: Any) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return _sha256_bytes(payload.encode())


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            line = json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n"
            handle.write(line)
            digest.update(line.encode())
            count += 1
    return count, digest.hexdigest()


def load_identity(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"canonical identity artifact is required before row selection: {path}"
        )
    identity = json.loads(path.read_text(encoding="utf-8"))
    if identity.get("status") != "IDENTITY_CAPTURE_COMPLETE":
        raise ValueError("identity artifact is not complete")
    model = identity.get("model", {})
    dataset = identity.get("dataset", {})
    if model.get("repo_id") != MODEL_ID:
        raise ValueError("identity artifact model does not match frozen Option B model")
    if dataset.get("repo_id") != DATASET_ID or dataset.get("subset") != "python":
        raise ValueError("identity artifact dataset does not match frozen Option B dataset")
    if not model.get("revision") or not dataset.get("revision"):
        raise ValueError("identity artifact must contain immutable model and dataset revisions")
    return identity


def _dataset_row(row: Mapping[str, Any], split: str) -> dict[str, Any]:
    result = dict(row)
    result["_split"] = split
    return result


def _record_manifest_row(record: FunctionRecord) -> dict[str, Any]:
    return {
        "split": record.split,
        "stable_key": record.stable_key,
        "repository": record.repository,
        "path": record.path,
        "function_id": record.function_id,
        "code_sha256": record.code_sha256,
        "normalized_ast_sha256": record.normalized_ast_sha256,
        "token_count": record.token_count,
    }


def _primitive_row(record: FunctionRecord) -> dict[str, Any]:
    return {
        "split": record.split,
        "stable_key": record.stable_key,
        "cyclomatic_complexity": record.cyclomatic_complexity,
        "max_control_depth": record.max_control_depth,
        "distinct_call_sites": record.distinct_call_sites,
    }


def prepare_selection(
    identity_path: Path = DEFAULT_IDENTITY,
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    config: OptionBConfig | None = None,
    dataset_by_split: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    tokenizer: Any | None = None,
) -> dict[str, Any]:
    """Create deterministic selected-row manifests and primitive tables.

    ``dataset_by_split`` and ``tokenizer`` are injectable for tests. Canonical use
    resolves both from the immutable revisions in the identity artifact.
    """

    identity = load_identity(identity_path)
    config = config or OptionBConfig()
    model_revision = identity["model"]["revision"]
    dataset_revision = identity["dataset"]["revision"]

    if tokenizer is None or dataset_by_split is None:
        try:
            from datasets import load_dataset
            from transformers import AutoTokenizer
        except ImportError as error:  # pragma: no cover - full runtime only
            raise RuntimeError("install Option B dependencies with pip install -e '.[option-b]'") from error
        if tokenizer is None:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=model_revision)
        if dataset_by_split is None:
            loaded = load_dataset(
                DATASET_ID,
                "python",
                revision=dataset_revision,
            )
            dataset_by_split = {split: loaded[split] for split in REQUIRED_SPLITS}

    missing = [split for split in REQUIRED_SPLITS if split not in dataset_by_split]
    if missing:
        raise ValueError(f"dataset is missing frozen splits: {missing}")

    records_by_split: dict[str, list[FunctionRecord]] = {}
    exclusion_counts: dict[str, dict[str, int]] = {}
    source_counts: dict[str, int] = {}
    for split in REQUIRED_SPLITS:
        rows = [_dataset_row(row, split) for row in dataset_by_split[split]]
        source_counts[split] = len(rows)
        records, reasons = build_records(rows, tokenizer, config)
        records_by_split[split] = records
        exclusion_counts[split] = dict(sorted(Counter(reasons).items()))

    deduplicated, duplicate_report = remove_cross_split_duplicates(records_by_split)
    limits = {
        "train": config.train_limit,
        "validation": config.validation_limit,
        "test": config.test_limit,
    }
    selected = {
        split: deterministic_limit(deduplicated[split], limits[split])
        for split in REQUIRED_SPLITS
    }

    artifact_hashes: dict[str, Any] = {}
    for split in REQUIRED_SPLITS:
        manifest_path = output_dir / f"option-b-selected-{split}-v1.jsonl"
        primitive_path = output_dir / f"option-b-primitives-{split}-v1.jsonl"
        manifest_count, manifest_sha = _write_jsonl(
            manifest_path, (_record_manifest_row(record) for record in selected[split])
        )
        primitive_count, primitive_sha = _write_jsonl(
            primitive_path, (_primitive_row(record) for record in selected[split])
        )
        artifact_hashes[split] = {
            "selected_manifest": {
                "path": str(manifest_path).replace("\\", "/"),
                "rows": manifest_count,
                "sha256": manifest_sha,
            },
            "primitive_table": {
                "path": str(primitive_path).replace("\\", "/"),
                "rows": primitive_count,
                "sha256": primitive_sha,
            },
        }

    report = {
        "selection_id": "option-b-canonical-row-selection-v1",
        "status": "CANONICAL_ROW_SELECTION_COMPLETE",
        "scientific_result_observed": False,
        "identity": {
            "path": str(identity_path).replace("\\", "/"),
            "model_revision": model_revision,
            "dataset_revision": dataset_revision,
            "fixture_matrix_sha256": identity["fixture"]["matrix_sha256"],
            "pooling_implementation_sha256": identity[
                "pooling_implementation_sha256"
            ],
        },
        "config": asdict(config),
        "source_rows": source_counts,
        "eligible_before_cross_split_deduplication": {
            split: len(records_by_split[split]) for split in REQUIRED_SPLITS
        },
        "exclusions": exclusion_counts,
        "cross_split_deduplication": duplicate_report,
        "eligible_after_cross_split_deduplication": {
            split: len(deduplicated[split]) for split in REQUIRED_SPLITS
        },
        "selected_rows": {split: len(selected[split]) for split in REQUIRED_SPLITS},
        "artifacts": artifact_hashes,
        "next_allowed_action": "CANONICAL_EMBEDDING_EXTRACTION",
        "prohibited_actions": [
            "scientific metric evaluation",
            "threshold changes",
            "query changes",
            "second model or language",
        ],
    }
    report_path = output_dir / "option-b-canonical-row-selection-v1.json"
    report["report_payload_sha256"] = _write_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_selection(args.identity, args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

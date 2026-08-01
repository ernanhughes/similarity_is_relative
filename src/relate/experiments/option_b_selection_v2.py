"""Generate versioned Option B canonical row-selection v2 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from relate.experiments import option_b_selection as selection
from relate.experiments.option_b_real_code import AST_RECURSION_LIMIT, OptionBConfig
from relate.experiments.option_b_selection_resilient import build_records_resilient

SPLITS = ("train", "validation", "test")


def _write_json(path: Path, value: Any) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def prepare_selection_v2(
    identity_path: Path = selection.DEFAULT_IDENTITY,
    output_dir: Path = selection.DEFAULT_OUTPUT,
    *,
    config: OptionBConfig | None = None,
    dataset_by_split: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    tokenizer: Any | None = None,
) -> dict[str, Any]:
    """Run the repaired selector and publish immutable v2 filenames."""

    report = selection.prepare_selection(
        identity_path,
        output_dir,
        config=config,
        dataset_by_split=dataset_by_split,
        tokenizer=tokenizer,
    )

    for split in SPLITS:
        for kind in ("selected", "primitives"):
            old_path = output_dir / f"option-b-{kind}-{split}-v1.jsonl"
            new_path = output_dir / f"option-b-{kind}-{split}-v2.jsonl"
            old_path.replace(new_path)
        report["artifacts"][split]["selected_manifest"]["path"] = str(
            output_dir / f"option-b-selected-{split}-v2.jsonl"
        ).replace("\\", "/")
        report["artifacts"][split]["primitive_table"]["path"] = str(
            output_dir / f"option-b-primitives-{split}-v2.jsonl"
        ).replace("\\", "/")

    old_report = output_dir / "option-b-canonical-row-selection-v1.json"
    old_report.unlink()
    report.update(
        {
            "selection_id": "option-b-canonical-row-selection-v2",
            "status": "CANONICAL_ROW_SELECTION_V2_GENERATED",
            "ast_recursion_limit": AST_RECURSION_LIMIT,
            "embedding_extraction_allowed": False,
            "next_allowed_action": "CANONICAL_SELECTION_V2_INDEPENDENT_VERIFICATION",
        }
    )
    report.pop("report_payload_sha256", None)
    report_path = output_dir / "option-b-canonical-row-selection-v2.json"
    report["report_payload_sha256"] = _write_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, default=selection.DEFAULT_IDENTITY)
    parser.add_argument("--output-dir", type=Path, default=selection.DEFAULT_OUTPUT)
    args = parser.parse_args()
    selection.build_records = build_records_resilient
    print(
        json.dumps(
            prepare_selection_v2(args.identity, args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

SPLITS = ("train", "validation", "test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compare_identity(
    v1_rows: list[dict[str, Any]], v2_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    def identity(row: dict[str, Any]) -> tuple[str, str, str]:
        return (row["repository"], row["function_id"], row["code_sha256"])

    v1 = [identity(row) for row in v1_rows]
    v2 = [identity(row) for row in v2_rows]
    common = set(v1) & set(v2)
    return {
        "v1_rows": len(v1),
        "v2_rows": len(v2),
        "same_identity_order": v1 == v2,
        "identity_overlap": len(common),
        "v1_only": len(set(v1) - set(v2)),
        "v2_only": len(set(v2) - set(v1)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--v1", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    args = parser.parse_args()

    verification: dict[str, Any] = {
        "status": "CANONICAL_ROW_SELECTION_V2_VERIFIED",
        "scientific_result_observed": False,
        "runs": {"a": str(args.run_a), "b": str(args.run_b)},
        "splits": {},
    }
    all_v2_keys: set[str] = set()
    all_v2_asts: dict[str, str] = {}

    for split in SPLITS:
        selected_name = f"option-b-selected-{split}-v2.jsonl"
        primitive_name = f"option-b-primitives-{split}-v2.jsonl"
        a_selected = args.run_a / selected_name
        b_selected = args.run_b / selected_name
        a_primitives = args.run_a / primitive_name
        b_primitives = args.run_b / primitive_name
        if a_selected.read_bytes() != b_selected.read_bytes():
            raise SystemExit(f"selected manifest mismatch for {split}")
        if a_primitives.read_bytes() != b_primitives.read_bytes():
            raise SystemExit(f"primitive table mismatch for {split}")

        selected = load_jsonl(a_selected)
        primitives = load_jsonl(a_primitives)
        selected_keys = [row["stable_key"] for row in selected]
        primitive_keys = [row["stable_key"] for row in primitives]
        if len(selected_keys) != len(set(selected_keys)):
            raise SystemExit(f"duplicate stable keys in {split}")
        if selected_keys != primitive_keys:
            raise SystemExit(f"primitive/manifest key order mismatch for {split}")
        if all_v2_keys.intersection(selected_keys):
            raise SystemExit(f"stable key crosses split boundary: {split}")
        all_v2_keys.update(selected_keys)
        for row in selected:
            ast_hash = row["normalized_ast_sha256"]
            previous = all_v2_asts.get(ast_hash)
            if previous and previous != split:
                raise SystemExit(f"normalized AST crosses split boundary: {ast_hash}")
            all_v2_asts[ast_hash] = split

        v1_selected = load_jsonl(args.v1 / f"option-b-selected-{split}-v1.jsonl")
        verification["splits"][split] = {
            "rows": len(selected),
            "selected_sha256": sha256(a_selected),
            "primitive_sha256": sha256(a_primitives),
            "run_a_run_b_byte_identical": True,
            "stable_key_unique": True,
            "primitive_key_order_exact": True,
            "v1_comparison": compare_identity(v1_selected, selected),
        }

        args.canonical.mkdir(parents=True, exist_ok=True)
        shutil.copy2(a_selected, args.canonical / selected_name)
        shutil.copy2(a_primitives, args.canonical / primitive_name)

    run_report = json.loads(
        (args.run_a / "option-b-canonical-row-selection-v2.json").read_text(encoding="utf-8")
    )
    report = {
        **run_report,
        "status": "CANONICAL_ROW_SELECTION_V2_VERIFIED",
        "verification": verification,
        "next_allowed_action": "PREDICTED_EXECUTOR_CONTRACT_COMPLETION",
        "embedding_extraction_allowed": False,
    }
    for split in SPLITS:
        report["artifacts"][split]["selected_manifest"]["path"] = (
            f"artifacts/canonical/option-b/selection/option-b-selected-{split}-v2.jsonl"
        )
        report["artifacts"][split]["primitive_table"]["path"] = (
            f"artifacts/canonical/option-b/selection/option-b-primitives-{split}-v2.jsonl"
        )
    report.pop("report_payload_sha256", None)
    write_json(args.canonical / "option-b-canonical-row-selection-v2.json", report)

    markdown = [
        "# Option B canonical row-selection checkpoint v2",
        "",
        "Date: 2026-08-01",
        "",
        "## Status",
        "",
        "```text",
        "Option B contract: FROZEN",
        "Primitive contract conformance: COMPLETE",
        "Canonical row selection v2: REPRODUCED AND VERIFIED",
        "Primitive tables v2: PUBLISHED",
        "Selected manifests v2: REVERIFIED",
        "Canonical embeddings: NOT GENERATED",
        "Primitive probes: NOT FIT",
        "Hard-negative manifest: NOT GENERATED",
        "Scientific result: NOT OBSERVED",
        "Gate: BLOCK BEFORE EMBEDDING EXTRACTION",
        "```",
        "",
        "Two independent selections were run in fresh directories. All six v2 JSONL artifacts matched byte-for-byte. Stable keys are unique, no stable key or normalized AST crosses a split boundary, and each primitive table has exactly the selected-manifest key order.",  # NOQA E501
        "",
        "## Artifact hashes",
        "",
        "| Split | Selected rows | Selected SHA-256 | Primitive SHA-256 | v1 identity overlap |",
        "|---|---:|---|---|---:|",
    ]
    for split in SPLITS:
        item = verification["splits"][split]
        markdown.append(
            f"| {split} | {item['rows']:,} | `{item['selected_sha256']}` | `{item['primitive_sha256']}` | {item['v1_comparison']['identity_overlap']:,} |"  # NOQA E501
        )
    markdown += [
        "",
        "The v1 comparison uses `(repository, function_id, code_sha256)` rather than v1 stable keys because PR 2 repaired the previously missing CodeSearchNet path field. Exact overlap and differences are recorded in the JSON report.",  # NOQA E501
        "",
        "## Scientific boundary",
        "",
        "No embedding, probe, hard-negative, metric, or scientific decision was generated. The frozen threshold and two-outcome decision are unchanged.",  # NOQA E501
        "",
        "## Next permitted stage",
        "",
        "The next bounded stage is **PR 4 — predicted executor contract completion**. Canonical embedding extraction remains blocked until PRs 4–6 are merged.",  # NOQA E501
        "",
    ]
    checkpoint = Path("docs/research/option-b-canonical-row-selection-v2-complete-2026-08-01.md")
    checkpoint.write_text("\n".join(markdown), encoding="utf-8")

    audit = Path("docs/audits/option-b-pre-embedding-review-and-remediation-2026-08-01.md")
    text = audit.read_text(encoding="utf-8")
    text = text.replace(
        "Canonical row selection v1: REPRODUCED\nPrimitive tables v1: INVALIDATED BY CONTRACT/IMPLEMENTATION MISMATCH\nSelected manifests: REQUIRE REVERIFICATION AFTER PRIMITIVE REPAIR",  # NOQA E501
        "Canonical row selection v2: REPRODUCED AND VERIFIED\nPrimitive tables v2: PUBLISHED; v1 REMAINS INVALIDATED\nSelected manifests v2: REVERIFIED",  # NOQA E501
    )
    text = text.replace(
        "The next implementation PR after this audit is merged is:\n\n```text\nPR 2 — primitive contract conformance\n```\n\nIt must not generate embeddings, fit probes, generate hard negatives, or compute scientific metrics.",  # NOQA E501
        "Completed stages:\n\n- PR 2 — primitive contract conformance;\n- PR 3 — canonical selection and primitive checkpoint v2.\n\nThe next implementation PR is:\n\n```text\nPR 4 — predicted executor contract completion\n```\n\nCanonical embedding extraction remains blocked.",  # NOQA E501
    )
    audit.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

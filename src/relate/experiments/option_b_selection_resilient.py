"""Resilient, observable CLI wrapper for canonical Option B row selection.

A small number of real-world Python functions contain ASTs deep enough to exceed
Python's recursive ``ast.NodeVisitor`` limit. Those samples are ineligible under
the frozen parser/extractor implementation and must be counted rather than abort
canonical selection.
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from typing import Any

from relate.experiments import option_b_selection as selection
from relate.experiments.option_b_real_code import (
    FunctionRecord,
    OptionBConfig,
    build_records as _build_records,
)

CHUNK_SIZE = 5_000


def _format_reasons(reasons: Counter[str]) -> str:
    if not reasons:
        return "none"
    return ", ".join(f"{name}={count:,}" for name, count in sorted(reasons.items()))


def _build_chunk_resilient(
    rows: list[dict[str, Any]],
    tokenizer: Any,
    config: OptionBConfig,
) -> tuple[list[FunctionRecord], Counter[str]]:
    """Isolate recursion-limit rows within one deterministic chunk."""

    if not rows:
        return [], Counter()
    try:
        return _build_records(rows, tokenizer, config)
    except RecursionError:
        if len(rows) == 1:
            return [], Counter({"ast_recursion_limit": 1})
        midpoint = len(rows) // 2
        left_records, left_reasons = _build_chunk_resilient(
            rows[:midpoint], tokenizer, config
        )
        right_records, right_reasons = _build_chunk_resilient(
            rows[midpoint:], tokenizer, config
        )
        return left_records + right_records, left_reasons + right_reasons


def build_records_resilient(
    rows: list[dict[str, Any]],
    tokenizer: Any,
    config: OptionBConfig,
) -> tuple[list[FunctionRecord], Counter[str]]:
    """Build records in visible chunks while isolating pathological AST rows."""

    total = len(rows)
    split = str(rows[0].get("_split", "unknown")) if rows else "unknown"
    started = time.perf_counter()
    all_records: list[FunctionRecord] = []
    all_reasons: Counter[str] = Counter()

    print(
        f"[option-b] {split}: starting AST/token scan for {total:,} source rows",
        file=sys.stderr,
        flush=True,
    )

    for start in range(0, total, CHUNK_SIZE):
        chunk = rows[start : start + CHUNK_SIZE]
        records, reasons = _build_chunk_resilient(chunk, tokenizer, config)
        all_records.extend(records)
        all_reasons.update(reasons)

        processed = min(start + len(chunk), total)
        elapsed = max(time.perf_counter() - started, 1e-9)
        rate = processed / elapsed
        print(
            f"[option-b] {split}: {processed:,}/{total:,} rows "
            f"({processed / total:6.1%}) | eligible={len(all_records):,} | "
            f"excluded={sum(all_reasons.values()):,} | {rate:,.0f} rows/s | "
            f"elapsed={elapsed:,.1f}s",
            file=sys.stderr,
            flush=True,
        )

    elapsed = time.perf_counter() - started
    print(
        f"[option-b] {split}: complete | eligible={len(all_records):,} | "
        f"exclusions: {_format_reasons(all_reasons)} | elapsed={elapsed:,.1f}s",
        file=sys.stderr,
        flush=True,
    )
    return all_records, all_reasons


def main() -> None:
    print(
        "[option-b] loading frozen identity, tokenizer and CodeSearchNet splits; "
        "the first dataset load may be quiet for a while",
        file=sys.stderr,
        flush=True,
    )
    selection.build_records = build_records_resilient
    selection.main()


if __name__ == "__main__":
    main()

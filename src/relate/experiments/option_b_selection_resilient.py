"""Resilient CLI wrapper for canonical Option B row selection.

A small number of real-world Python functions contain ASTs deep enough to exceed
Python's recursive ``ast.NodeVisitor`` limit. Those samples are ineligible under
the frozen parser/extractor implementation and must be counted rather than abort
canonical selection.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from relate.experiments import option_b_selection as selection
from relate.experiments.option_b_real_code import (
    FunctionRecord,
    OptionBConfig,
)
from relate.experiments.option_b_real_code import (
    build_records as _build_records,
)


def build_records_resilient(
    rows: list[dict[str, Any]],
    tokenizer: Any,
    config: OptionBConfig,
) -> tuple[list[FunctionRecord], Counter[str]]:
    """Build records while isolating rows that exceed AST recursion limits.

    The normal bulk path is retained. Only a batch that raises ``RecursionError``
    is bisected deterministically until the pathological row is isolated. That
    row is excluded as ``ast_recursion_limit``.
    """

    if not rows:
        return [], Counter()
    try:
        return _build_records(rows, tokenizer, config)
    except RecursionError:
        if len(rows) == 1:
            return [], Counter({"ast_recursion_limit": 1})
        midpoint = len(rows) // 2
        left_records, left_reasons = build_records_resilient(rows[:midpoint], tokenizer, config)
        right_records, right_reasons = build_records_resilient(rows[midpoint:], tokenizer, config)
        return left_records + right_records, left_reasons + right_reasons


def main() -> None:
    selection.build_records = build_records_resilient
    selection.main()


if __name__ == "__main__":
    main()

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from relate.experiments import option_b_real_code as option_b
from relate.experiments.option_b_real_code import (
    AST_RECURSION_LIMIT,
    OptionBConfig,
    build_hard_negative_manifest,
    build_records,
    chebyshev_distance,
    extract_primitives,
    manifest_triplet_accuracy,
    robust_scale,
    robust_scale_fit,
)


class _Tokenizer:
    def __call__(self, code: str, **_: object) -> dict[str, list[int]]:
        del code
        return {"input_ids": list(range(32))}


def test_extracts_frozen_primitives_and_excludes_nested_functions() -> None:
    code = """
def outer(xs):
    total = 0
    if xs and len(xs) > 1:
        for value in xs:
            total += transform(value)
    def nested():
        if hidden():
            return secret()
    return total
"""
    _, values = extract_primitives(code)
    # Base path + If + For + BoolOp increment.
    assert values.tolist() == [4.0, 2.0, 2.0]


def test_match_and_conditional_expression_rules_are_explicit() -> None:
    code = """
def classify(x):
    value = 1 if x else 0
    match x:
        case 0:
            return zero()
        case 1:
            return one()
        case _:
            return other()
"""
    _, values = extract_primitives(code)
    # Base + IfExp + two additional match branches.
    assert values.tolist() == [4.0, 1.0, 3.0]


def test_call_targets_are_distinct_and_normalized() -> None:
    code = """
def calls(obj):
    foo()
    foo()
    obj.save()
    factory()()
"""
    _, values = extract_primitives(code)
    assert values.tolist() == [1.0, 0.0, 4.0]


@pytest.mark.parametrize(
    ("code", "expected_complexity", "expected_depth"),
    [
        ("def f(x):\n    if x:\n        return x\n", 2.0, 1.0),
        ("def f(xs):\n    for x in xs:\n        consume(x)\n", 2.0, 1.0),
        ("async def f(xs):\n    async for x in xs:\n        consume(x)\n", 2.0, 1.0),
        ("def f(x):\n    while x:\n        x -= 1\n", 2.0, 1.0),
        (
            "def f():\n    try:\n        work()\n    except ValueError:\n        recover()\n",
            2.0,
            1.0,
        ),
        ("def f(ctx):\n    with ctx:\n        work()\n", 1.0, 1.0),
        ("async def f(ctx):\n    async with ctx:\n        work()\n", 1.0, 1.0),
        (
            "def f(x):\n    match x:\n        case 0:\n            return 0\n        case _:\n            return 1\n",  # NOQA E501
            2.0,
            1.0,
        ),
        ("def f(xs):\n    return [x for x in xs]\n", 2.0, 1.0),
        ("def f(xs):\n    return {x for x in xs}\n", 2.0, 1.0),
        ("def f(xs):\n    return {x: x for x in xs}\n", 2.0, 1.0),
        ("def f(xs):\n    return tuple(x for x in xs)\n", 2.0, 1.0),
    ],
)
def test_registered_control_constructs_are_pinned(
    code: str,
    expected_complexity: float,
    expected_depth: float,
) -> None:
    _, values = extract_primitives(code)
    assert values[:2].tolist() == [expected_complexity, expected_depth]


def test_comprehension_generators_nest_and_filters_only_add_complexity() -> None:
    code = """
def pairs(xs, ys):
    return [(x, y) for x in xs if keep_x(x) for y in ys if keep_y(y)]
"""
    _, values = extract_primitives(code)
    # Base + two generators + two filters; generators nest to depth two.
    assert values.tolist() == [5.0, 2.0, 2.0]


def test_elif_is_not_an_extra_nesting_level_but_else_if_is() -> None:
    elif_code = """
def classify(x):
    if x == 0:
        return 0
    elif x == 1:
        return 1
    return 2
"""
    else_if_code = """
def classify(x):
    if x == 0:
        return 0
    else:
        if x == 1:
            return 1
    return 2
"""
    _, elif_values = extract_primitives(elif_code)
    _, else_if_values = extract_primitives(else_if_code)
    assert elif_values[:2].tolist() == [3.0, 1.0]
    assert else_if_values[:2].tolist() == [3.0, 2.0]


def test_nested_try_with_and_while_reach_depth_three() -> None:
    code = """
def nested(ctx, ready):
    try:
        with ctx:
            while ready():
                work()
    finally:
        close()
"""
    _, values = extract_primitives(code)
    assert values.tolist() == [2.0, 3.0, 3.0]


def test_codesearchnet_provenance_fields_are_preserved() -> None:
    rows = [
        {
            "_split": "train",
            "repository_name": "owner/repository",
            "func_path_in_repository": "src/package/module.py",
            "func_name": "qualified.method",
            "whole_func_string": "def method(x):\n    return transform(x)\n",
        }
    ]
    records, reasons = build_records(rows, _Tokenizer(), OptionBConfig())
    assert reasons == Counter()
    assert len(records) == 1
    assert records[0].repository == "owner/repository"
    assert records[0].path == "src/package/module.py"
    assert records[0].function_id == "qualified.method"


def test_missing_provenance_is_excluded() -> None:
    rows = [
        {
            "_split": "train",
            "repository_name": "owner/repository",
            "func_name": "method",
            "whole_func_string": "def method(x):\n    return x\n",
        }
    ]
    records, reasons = build_records(rows, _Tokenizer(), OptionBConfig())
    assert records == []
    assert reasons == Counter({"missing_provenance": 1})


def test_build_records_pins_recursion_and_counts_only_ast_recursion(monkeypatch) -> None:
    pin_calls: list[bool] = []

    def fake_pin() -> None:
        pin_calls.append(True)

    def fake_extract(code: str) -> tuple[str, np.ndarray]:
        if "deep" in code:
            raise RecursionError("pathological AST")
        return "ast-sha", np.asarray([1.0, 0.0, 0.0])

    monkeypatch.setattr(option_b, "pin_ast_recursion_limit", fake_pin)
    monkeypatch.setattr(option_b, "extract_primitives", fake_extract)
    rows = [
        {
            "_split": "train",
            "repository_name": "owner/repository",
            "func_path_in_repository": "deep.py",
            "func_name": "deep",
            "whole_func_string": "def deep():\n    pass\n",
        },
        {
            "_split": "train",
            "repository_name": "owner/repository",
            "func_path_in_repository": "ok.py",
            "func_name": "ok",
            "whole_func_string": "def ok():\n    pass\n",
        },
    ]
    records, reasons = build_records(rows, _Tokenizer(), OptionBConfig())
    assert pin_calls == [True]
    assert len(records) == 1
    assert records[0].function_id == "ok"
    assert reasons == Counter({"ast_recursion_limit": 1})
    assert AST_RECURSION_LIMIT == 1_000


def test_robust_scaling_uses_training_median_and_iqr_floor() -> None:
    train = np.asarray([[1.0, 2.0], [2.0, 2.0], [5.0, 2.0]])
    median, scale = robust_scale_fit(train)
    assert median.tolist() == [2.0, 2.0]
    assert scale.tolist() == [2.0, 1.0]
    assert robust_scale(np.asarray([[4.0, 3.0]]), median, scale).tolist() == [[1.0, 1.0]]


def test_hard_negative_manifest_is_deterministic_and_informative() -> None:
    oracle = np.asarray([[float(index) for index in range(40)]])
    config = OptionBConfig(max_pairs_per_query=8, min_rank_separation=5, max_rank_separation=6)
    lengths = np.full(40, 100)
    first = build_hard_negative_manifest(oracle, np.asarray([100]), lengths, config)
    second = build_hard_negative_manifest(oracle, np.asarray([100]), lengths, config)
    assert first == second
    assert len(first) == 8
    assert all(item["farther"] > item["closer"] for item in first)


def test_manifest_triplet_accuracy_awards_half_for_ties() -> None:
    manifest = [
        {"query": 0, "closer": 0, "farther": 1},
        {"query": 0, "closer": 1, "farther": 2},
    ]
    distances = np.asarray([[0.1, 0.1, 0.3]])
    assert manifest_triplet_accuracy(distances, manifest) == 0.75


def test_chebyshev_distance_encodes_worst_primitive_mismatch() -> None:
    query = np.asarray([[0.0, 0.0, 0.0]])
    candidates = np.asarray([[0.1, 0.2, 0.3], [0.4, 0.1, 0.2]])
    assert chebyshev_distance(query, candidates).tolist() == [[0.3, 0.4]]

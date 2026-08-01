from __future__ import annotations

import numpy as np

from relate.experiments.option_b_real_code import (
    OptionBConfig,
    build_hard_negative_manifest,
    chebyshev_distance,
    extract_primitives,
    manifest_triplet_accuracy,
    robust_scale,
    robust_scale_fit,
)


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

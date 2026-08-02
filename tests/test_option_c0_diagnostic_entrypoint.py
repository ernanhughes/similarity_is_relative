from __future__ import annotations

import numpy as np

from relate.experiments import option_c0_discovery_runner as runner
from relate.experiments.option_c0_diagnostic_entrypoint import (
    corrected_diagnostic_bundle,
    corrected_interval_coverage,
    install_diagnostic_contract_adapter,
    restore_diagnostic_contract_adapter,
)
from relate.experiments.option_c0_selective_baselines import SelectiveDecision


def test_corrected_diagnostic_bundle_uses_declared_labels_first_contract():
    decision = SelectiveDecision(
        predictions=np.asarray([True, False, True], dtype=np.bool_),
        accepted=np.asarray([True, True, False], dtype=np.bool_),
        scores=np.asarray([0.9, 0.8, 0.2], dtype=np.float64),
        reasons=(
            "accepted_supported_true",
            "accepted_supported_false",
            "refused_primitive_support_overlap",
        ),
    )
    labels = np.asarray([True, True, False], dtype=np.bool_)
    repositories = ("repo-a", "repo-b", "repo-c")
    regimes = ("supported", "shifted", "weak")

    result = corrected_diagnostic_bundle(
        decision,
        labels,
        repositories,
        regimes,
        (0.5, 1.0),
    )

    assert result["selective"]["rows"] == 3
    assert result["selective"]["accepted"] == 2
    assert result["selective"]["errors"] == 1
    assert [row["target_coverage"] for row in result["risk_coverage"]] == [0.5, 1.0]
    assert result["regimes"]["supported"]["rows"] == 1
    assert result["regimes"]["shifted"]["rows"] == 1
    assert result["regimes"]["weak"]["rows"] == 1


def test_corrected_interval_coverage_recovers_prediction_and_constant_radius():
    prediction = np.asarray(
        [
            [0.5, -0.5, 1.0],
            [1.5, 0.0, -1.0],
        ],
        dtype=np.float64,
    )
    radius = np.asarray([0.25, 0.5, 0.75], dtype=np.float64)
    truth = np.asarray(
        [
            [0.6, -0.2, 1.5],
            [1.4, 0.4, -1.6],
        ],
        dtype=np.float64,
    )

    result = corrected_interval_coverage(
        truth,
        prediction - radius,
        prediction + radius,
    )

    assert result["rows"] == 2
    assert result["per_primitive_empirical_coverage"] == [1.0, 1.0, 1.0]
    assert result["joint_empirical_coverage"] == 1.0


def test_install_and_restore_replaces_only_the_two_mismatched_interfaces():
    original_bundle = runner._diagnostic_bundle
    original_coverage = runner.primitive_interval_coverage

    originals = install_diagnostic_contract_adapter()
    try:
        assert runner._diagnostic_bundle is corrected_diagnostic_bundle
        assert runner.primitive_interval_coverage is corrected_interval_coverage
    finally:
        restore_diagnostic_contract_adapter(originals)

    assert runner._diagnostic_bundle is original_bundle
    assert runner.primitive_interval_coverage is original_coverage

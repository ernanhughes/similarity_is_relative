"""Pre-publication diagnostic-interface correction for Option C0 discovery.

The reviewed discovery runner called the diagnostics module with positional
arguments in the opposite order from the declared interfaces. This adapter
corrects only that plumbing and delegates identity handling and all mechanism
computation to the previously reviewed entrypoint and runner.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from relate.experiments import option_c0_discovery_entrypoint as identity_entrypoint
from relate.experiments import option_c0_discovery_runner as runner
from relate.experiments.option_c0_diagnostics import (
    primitive_interval_coverage as declared_primitive_interval_coverage,
)
from relate.experiments.option_c0_diagnostics import (
    ranked_risk_coverage_curve,
    selective_diagnostics,
    stratified_selective_diagnostics,
)
from relate.experiments.option_c0_selective_baselines import SelectiveDecision


def corrected_diagnostic_bundle(
    decision: SelectiveDecision,
    labels: np.ndarray,
    repositories: Sequence[str],
    regimes: Sequence[str],
    anchors: Sequence[float],
) -> dict[str, Any]:
    """Call every diagnostic using its declared labels-first interface."""

    return {
        "selective": selective_diagnostics(labels, decision, repositories),
        "risk_coverage": ranked_risk_coverage_curve(
            labels,
            decision.predictions,
            decision.scores,
            repositories,
            anchors,
        ),
        "regimes": stratified_selective_diagnostics(
            labels,
            decision,
            repositories,
            regimes,
        ),
    }


def corrected_interval_coverage(
    truth: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> dict[str, Any]:
    """Adapt the runner's lower/upper call to prediction-plus-radius semantics."""

    true_values = np.asarray(truth, dtype=np.float64)
    low = np.asarray(lower, dtype=np.float64)
    high = np.asarray(upper, dtype=np.float64)
    if true_values.ndim != 2 or low.shape != true_values.shape or high.shape != low.shape:
        raise ValueError("joint interval coverage arrays must be aligned matrices")
    if np.any(low > high):
        raise ValueError("joint interval lower bounds cannot exceed upper bounds")

    prediction = (low + high) / 2.0
    radii = (high - low) / 2.0
    radius = radii[0]
    if not np.allclose(radii, radius[None, :], atol=1e-12, rtol=0.0):
        raise ValueError("joint interval radius must be constant across evaluated rows")
    return declared_primitive_interval_coverage(true_values, prediction, radius)


def install_diagnostic_contract_adapter() -> tuple[Any, Any]:
    """Install the reviewed correction and return the original callables."""

    originals = (runner._diagnostic_bundle, runner.primitive_interval_coverage)
    runner._diagnostic_bundle = corrected_diagnostic_bundle
    runner.primitive_interval_coverage = corrected_interval_coverage
    return originals


def restore_diagnostic_contract_adapter(originals: tuple[Any, Any]) -> None:
    """Restore runner globals after command completion or failure."""

    runner._diagnostic_bundle, runner.primitive_interval_coverage = originals


def main() -> None:
    originals = install_diagnostic_contract_adapter()
    try:
        identity_entrypoint.main()
    finally:
        restore_diagnostic_contract_adapter(originals)


if __name__ == "__main__":
    main()

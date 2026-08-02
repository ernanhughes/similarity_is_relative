"""Guarded Option C0 initial-candidate fit and iteration runner.

This module is exploratory infrastructure. It may access only C0_FIT and
C0_ITERATION repositories. C0_SELECTION and the C1 reserve are unavailable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import time
import tracemalloc
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from relate.experiments.option_b_embedding import (
    canonical_embed_loaded,
    load_canonical_backend,
    verify_fixture_preflight,
)
from relate.experiments.option_b_identity import FIXTURE_CODES
from relate.experiments.option_b_real_code import (
    ALPHAS,
    PRIMITIVES,
    FunctionRecord,
    OptionBConfig,
    remove_cross_split_duplicates,
)
from relate.experiments.option_b_selection import DATASET_ID, REQUIRED_SPLITS, load_identity
from relate.experiments.option_b_selection_resilient import build_records_resilient
from relate.experiments.option_c0_data_firewall import read_candidate_registry
from relate.experiments.option_c0_diagnostics import (
    primitive_interval_coverage,
    ranked_risk_coverage_curve,
    selective_diagnostics,
    stratified_selective_diagnostics,
)
from relate.experiments.option_c0_mechanism_harness import (
    HiddenRoleAccessError,
    load_visible_repository_assignments,
)
from relate.experiments.option_c0_selective_baselines import (
    QueryForm,
    SelectiveDecision,
    direct_compound_conformal_decision,
    fit_direct_compound_conformal,
    fit_independent_primitive_calibration,
    fit_joint_max_residual_calibration,
    independent_primitive_conformal_decision,
    joint_box_support_decision,
    oracle_support_decision,
    query_truth,
    uncalibrated_confidence_decision,
)

PLAN_SCHEMA: Final = "option-c0-initial-candidate-plan-v1"
RESULT_SCHEMA: Final = "option-c0-discovery-iteration-v1"
FIT_PARTITION_DOMAIN: Final = "option-c0-fit-calibration-partition-v1"
FOLD_DOMAIN: Final = "option-c0-ridge-group-folds-v1"
VISIBLE_ROLES: Final = ("c0_fit", "c0_iteration")
QUERY_ORDER: Final = (
    "all_primitives_above_fit_median",
    "any_primitive_above_fit_median",
    "two_of_three_primitives_above_fit_median",
)
CANDIDATE_FAMILIES: Final = (
    "joint_max_residual_box",
    "empirical_residual_mass",
)


class DiscoveryRunnerError(RuntimeError):
    """Base contract error for the C0 discovery runner."""


class CandidateRegistryMismatch(DiscoveryRunnerError):
    """Raised when the committed candidate registry differs from the plan."""


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    version: str
    family: str
    query_id: str
    support_object_definition: str
    propagation_rule: str
    nonconformity_score: str
    expected_failure_mode: str
    implementation_commit_sha: str


@dataclass(frozen=True)
class DiscoveryPlan:
    status: str
    primitives: tuple[str, ...]
    query_forms: tuple[QueryForm, ...]
    candidates: tuple[CandidateSpec, ...]
    alpha_grid: tuple[float, ...]
    residual_mass_beta_grid: tuple[float, ...]
    coverage_anchors: tuple[float, ...]
    fit_calibration_fraction: float
    ridge_alphas: tuple[float, ...]
    ridge_folds: int
    embedding_batch_size: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DiscoveryPlan":
        if value.get("schema_id") != PLAN_SCHEMA:
            raise ValueError("unexpected initial candidate-plan schema")
        for field in (
            "scientific_result_observed",
            "mechanism_result_observed",
            "c0_selection_accessed",
            "c1_rows_selected",
        ):
            if value.get(field) is not False:
                raise ValueError(f"candidate plan must keep {field}=false")
        primitives = tuple(str(item) for item in value.get("primitives", ()))
        if primitives != PRIMITIVES:
            raise ValueError("candidate plan changed the frozen Option B primitives")
        query_forms = tuple(_query_from_mapping(item) for item in value.get("query_forms", ()))
        if tuple(item.query_id for item in query_forms) != QUERY_ORDER:
            raise ValueError("candidate plan changed the reviewed query order")
        candidates = tuple(
            CandidateSpec(
                candidate_id=str(item["candidate_id"]),
                version=str(item["version"]),
                family=str(item["family"]),
                query_id=str(item["query_id"]),
                support_object_definition=str(item["support_object_definition"]),
                propagation_rule=str(item["propagation_rule"]),
                nonconformity_score=str(item["nonconformity_score"]),
                expected_failure_mode=str(item["expected_failure_mode"]),
                implementation_commit_sha=str(item["implementation_commit_sha"]),
            )
            for item in value.get("candidates", ())
        )
        expected = {
            (family, query_id)
            for family in CANDIDATE_FAMILIES
            for query_id in QUERY_ORDER
        }
        observed = {(item.family, item.query_id) for item in candidates}
        if observed != expected or len(candidates) != len(expected):
            raise ValueError("candidate plan must register both families for all queries")
        if len({(item.candidate_id, item.version) for item in candidates}) != len(candidates):
            raise ValueError("candidate IDs and versions must be unique")
        for item in candidates:
            _require_hex(item.implementation_commit_sha, {40}, "implementation_commit_sha")
            for text in (
                item.support_object_definition,
                item.propagation_rule,
                item.nonconformity_score,
                item.expected_failure_mode,
            ):
                if not text.strip():
                    raise ValueError("candidate text fields must be non-empty")
        alpha_grid = _strict_probability_grid(value.get("alpha_grid"), "alpha_grid")
        beta_grid = _strict_probability_grid(
            value.get("residual_mass_beta_grid"),
            "residual_mass_beta_grid",
        )
        anchors = tuple(float(item) for item in value.get("coverage_anchors", ()))
        if tuple(sorted(set(anchors))) != anchors or any(
            not 0.0 < item <= 1.0 for item in anchors
        ):
            raise ValueError("coverage anchors must be unique and ascending")
        fraction = float(value.get("fit_calibration_fraction", 0.0))
        if not 0.0 < fraction < 0.5:
            raise ValueError("fit calibration fraction must lie in (0, 0.5)")
        ridge_alphas = tuple(float(item) for item in value.get("ridge_alphas", ()))
        if ridge_alphas != tuple(float(item) for item in ALPHAS):
            raise ValueError("ridge alpha grid differs from Option B")
        folds = int(value.get("ridge_folds", 0))
        if folds < 2:
            raise ValueError("ridge_folds must be at least two")
        batch_size = int(value.get("embedding_batch_size", 0))
        if batch_size <= 0:
            raise ValueError("embedding_batch_size must be positive")
        return cls(
            status=str(value.get("status", "")),
            primitives=primitives,
            query_forms=query_forms,
            candidates=candidates,
            alpha_grid=alpha_grid,
            residual_mass_beta_grid=beta_grid,
            coverage_anchors=anchors,
            fit_calibration_fraction=fraction,
            ridge_alphas=ridge_alphas,
            ridge_folds=folds,
            embedding_batch_size=batch_size,
        )


@dataclass(frozen=True)
class VisibleRecord:
    role: str
    record: FunctionRecord


@dataclass(frozen=True)
class PreparedData:
    fit_model: tuple[VisibleRecord, ...]
    fit_calibration: tuple[VisibleRecord, ...]
    iteration: tuple[VisibleRecord, ...]
    partition_commitment: str


@dataclass(frozen=True)
class PrimitiveModel:
    scaler: StandardScaler
    estimators: tuple[Ridge, ...]
    selected_alphas: tuple[float, ...]


@dataclass(frozen=True)
class QueryTransform:
    thresholds: np.ndarray
    scales: np.ndarray


def _query_from_mapping(value: Mapping[str, Any]) -> QueryForm:
    return QueryForm(
        query_id=str(value["query_id"]),
        operator=str(value["operator"]),
        primitive_names=tuple(str(item) for item in value["primitive_names"]),
        k=None if value.get("k") is None else int(value["k"]),
    )


def _strict_probability_grid(value: Any, name: str) -> tuple[float, ...]:
    grid = tuple(float(item) for item in value or ())
    if tuple(sorted(set(grid))) != grid or any(not 0.0 < item < 0.5 for item in grid):
        raise ValueError(f"{name} must be unique, ascending, and in (0, 0.5)")
    return grid


def _require_hex(value: str, lengths: set[int], name: str) -> None:
    valid = len(value) in lengths and all(character in "0123456789abcdef" for character in value)
    if not valid:
        raise ValueError(f"{name} must be lowercase hexadecimal with length {sorted(lengths)}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_discovery_plan(path: Path) -> DiscoveryPlan:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("initial candidate plan must be a JSON object")
    return DiscoveryPlan.from_mapping(value)


def verify_registered_candidates(
    plan: DiscoveryPlan,
    registry_path: Path,
) -> tuple[dict[str, Any], ...]:
    events = read_candidate_registry(registry_path)
    registrations = tuple(event for event in events if event.get("event_type") == "REGISTERED")
    expected = {(item.candidate_id, item.version): item for item in plan.candidates}
    observed = {
        (str(event.get("candidate_id")), str(event.get("version"))): event
        for event in registrations
    }
    if set(observed) != set(expected) or len(registrations) != len(expected):
        raise CandidateRegistryMismatch("candidate registry differs from the plan")
    if any(event.get("event_type") != "REGISTERED" for event in events):
        raise CandidateRegistryMismatch("pre-execution registry may contain only registrations")
    for identity, candidate in expected.items():
        event = observed[identity]
        if event.get("commit_sha") != candidate.implementation_commit_sha:
            raise CandidateRegistryMismatch(f"implementation commit mismatch: {identity}")
        if event.get("status") != "active":
            raise CandidateRegistryMismatch(f"candidate is not active: {identity}")
        if event.get("data_roles") != ["C0_FIT", "C0_ITERATION"]:
            raise CandidateRegistryMismatch(f"candidate roles changed: {identity}")
        query = next(item for item in plan.query_forms if item.query_id == candidate.query_id)
        if json.loads(str(event.get("query_form"))) != query.to_dict():
            raise CandidateRegistryMismatch(f"candidate query changed: {identity}")
    return registrations


def split_fit_repositories(
    repositories: Iterable[str],
    *,
    allocation_context_sha256: str,
    calibration_fraction: float,
) -> tuple[set[str], set[str], str]:
    _require_hex(allocation_context_sha256, {64}, "allocation_context_sha256")
    unique = sorted(set(str(item) for item in repositories))
    if len(unique) < 2:
        raise ValueError("C0_FIT requires at least two repositories")
    ordered = sorted(
        unique,
        key=lambda repository: hashlib.sha256(
            f"{FIT_PARTITION_DOMAIN}\0{allocation_context_sha256}\0{repository}".encode()
        ).hexdigest(),
    )
    calibration_count = max(1, math.ceil(len(ordered) * calibration_fraction))
    if calibration_count >= len(ordered):
        raise ValueError("fit/calibration partition leaves no model-fit repositories")
    calibration = set(ordered[:calibration_count])
    model_fit = set(ordered[calibration_count:])
    commitment = _sha256_json(
        {
            "domain": FIT_PARTITION_DOMAIN,
            "allocation_context_sha256": allocation_context_sha256,
            "calibration_fraction": calibration_fraction,
            "model_fit_repositories": sorted(model_fit),
            "calibration_repositories": sorted(calibration),
        }
    )
    return model_fit, calibration, commitment


def reconstruct_visible_records(
    identity_path: Path,
    canonical_firewall_dir: Path,
) -> tuple[tuple[VisibleRecord, ...], dict[str, Any]]:
    assignments = load_visible_repository_assignments(canonical_firewall_dir)
    repository_roles = {str(item["repository"]): str(item["role"]) for item in assignments}
    identity = load_identity(identity_path)
    try:
        from datasets import load_dataset
        from transformers import AutoTokenizer
    except ImportError as error:  # pragma: no cover
        message = "install Option B dependencies with pip install -e '.[option-b]'"
        raise RuntimeError(message) from error
    tokenizer = AutoTokenizer.from_pretrained(
        identity["model"]["repo_id"],
        revision=identity["model"]["revision"],
    )
    loaded = load_dataset(DATASET_ID, "python", revision=identity["dataset"]["revision"])
    config = OptionBConfig()
    records_by_split: dict[str, list[FunctionRecord]] = {}
    exclusion_counts: dict[str, dict[str, int]] = {}
    for split in REQUIRED_SPLITS:
        source_rows = [dict(row, _split=split) for row in loaded[split]]
        records, reasons = build_records_resilient(source_rows, tokenizer, config)
        records_by_split[split] = records
        exclusion_counts[split] = dict(sorted(reasons.items()))
    deduplicated, duplicate_report = remove_cross_split_duplicates(records_by_split)
    visible: list[VisibleRecord] = []
    seen_repositories: set[str] = set()
    for split in REQUIRED_SPLITS:
        for record in deduplicated[split]:
            role = repository_roles.get(record.repository)
            if role is None:
                continue
            visible.append(VisibleRecord(role, record))
            seen_repositories.add(record.repository)
    if seen_repositories != set(repository_roles):
        missing = sorted(set(repository_roles) - seen_repositories)
        raise ValueError(f"allocated repositories missing from reconstruction: {missing[:5]}")
    visible.sort(key=lambda item: (item.role, item.record.stable_key))
    expected_rows = {
        role: sum(int(item["row_count"]) for item in assignments if item["role"] == role)
        for role in VISIBLE_ROLES
    }
    observed_rows = {role: sum(item.role == role for item in visible) for role in VISIBLE_ROLES}
    if observed_rows != expected_rows:
        raise ValueError("reconstructed visible row counts differ from allocation")
    return tuple(visible), {
        "identity_sha256": _sha256_file(identity_path),
        "visible_rows": observed_rows,
        "exclusions": exclusion_counts,
        "cross_split_deduplication": duplicate_report,
    }


def prepare_visible_data(
    visible: Sequence[VisibleRecord],
    *,
    allocation_context_sha256: str,
    calibration_fraction: float,
) -> PreparedData:
    fit_repositories = {item.record.repository for item in visible if item.role == "c0_fit"}
    model_repositories, calibration_repositories, commitment = split_fit_repositories(
        fit_repositories,
        allocation_context_sha256=allocation_context_sha256,
        calibration_fraction=calibration_fraction,
    )
    model_fit = tuple(
        item
        for item in visible
        if item.role == "c0_fit" and item.record.repository in model_repositories
    )
    calibration = tuple(
        item
        for item in visible
        if item.role == "c0_fit" and item.record.repository in calibration_repositories
    )
    iteration = tuple(item for item in visible if item.role == "c0_iteration")
    if not model_fit or not calibration or not iteration:
        raise ValueError("visible data partition produced an empty phase")
    return PreparedData(model_fit, calibration, iteration, commitment)


def _record_arrays(
    records: Sequence[VisibleRecord],
) -> tuple[list[str], np.ndarray, tuple[str, ...]]:
    codes = [item.record.code for item in records]
    primitives = np.stack([item.record.primitive_vector for item in records]).astype(np.float64)
    repositories = tuple(item.record.repository for item in records)
    return codes, primitives, repositories


def embed_prepared_data(
    prepared: PreparedData,
    identity_path: Path,
    *,
    device: str,
    batch_size: int,
    cache_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    identity = load_identity(identity_path)
    tokenizer, model, torch_module = load_canonical_backend(
        model_id=identity["model"]["repo_id"],
        revision=identity["model"]["revision"],
        device=device,
        cache_dir=cache_dir,
    )
    verify_fixture_preflight(
        identity,
        FIXTURE_CODES,
        tokenizer,
        model,
        device=device,
        torch_module=torch_module,
    )
    matrices: dict[str, np.ndarray] = {}
    for name, records in (
        ("fit_model", prepared.fit_model),
        ("fit_calibration", prepared.fit_calibration),
        ("iteration", prepared.iteration),
    ):
        codes, _, _ = _record_arrays(records)
        matrices[name] = canonical_embed_loaded(
            codes,
            tokenizer,
            model,
            batch_size=batch_size,
            device=device,
            torch_module=torch_module,
        )
    return matrices, {
        "model_id": identity["model"]["repo_id"],
        "revision": identity["model"]["revision"],
        "device": device,
        "batch_size": batch_size,
        "torch": torch_module.__version__,
    }


def _group_folds(repositories: Sequence[str], folds: int) -> np.ndarray:
    unique = sorted(set(repositories))
    if len(unique) < folds:
        raise ValueError("not enough repositories for grouped ridge folds")
    ordered = sorted(
        unique,
        key=lambda repository: hashlib.sha256(
            f"{FOLD_DOMAIN}\0{repository}".encode()
        ).hexdigest(),
    )
    owner = {repository: index % folds for index, repository in enumerate(ordered)}
    return np.asarray([owner[item] for item in repositories], dtype=np.int64)


def fit_primitive_models(
    embeddings: np.ndarray,
    primitives: np.ndarray,
    repositories: Sequence[str],
    *,
    alphas: Sequence[float],
    folds: int,
) -> PrimitiveModel:
    x = np.asarray(embeddings, dtype=np.float64)
    y = np.asarray(primitives, dtype=np.float64)
    if x.ndim != 2 or y.shape != (len(x), len(PRIMITIVES)):
        raise ValueError("primitive model arrays have incompatible shapes")
    scaler = StandardScaler().fit(x)
    transformed = scaler.transform(x)
    fold_ids = _group_folds(repositories, folds)
    selected: list[float] = []
    estimators: list[Ridge] = []
    for primitive_index in range(y.shape[1]):
        scores: list[tuple[float, float]] = []
        for alpha in alphas:
            errors: list[float] = []
            for fold in range(folds):
                train = fold_ids != fold
                validation = fold_ids == fold
                estimator = Ridge(alpha=float(alpha)).fit(
                    transformed[train], y[train, primitive_index]
                )
                prediction = estimator.predict(transformed[validation])
                errors.append(float(np.mean(np.abs(y[validation, primitive_index] - prediction))))
            scores.append((float(np.mean(errors)), float(alpha)))
        _, chosen = min(scores, key=lambda item: (item[0], item[1]))
        selected.append(chosen)
        estimators.append(Ridge(alpha=chosen).fit(transformed, y[:, primitive_index]))
    return PrimitiveModel(scaler, tuple(estimators), tuple(selected))


def predict_primitives(model: PrimitiveModel, embeddings: np.ndarray) -> np.ndarray:
    transformed = model.scaler.transform(np.asarray(embeddings, dtype=np.float64))
    return np.column_stack([estimator.predict(transformed) for estimator in model.estimators])


def fit_query_transform(primitives: np.ndarray) -> QueryTransform:
    values = np.asarray(primitives, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != len(PRIMITIVES):
        raise ValueError("query transform requires the three frozen primitives")
    thresholds = np.quantile(values, 0.5, axis=0, method="linear")
    lower = np.quantile(values, 0.25, axis=0, method="linear")
    upper = np.quantile(values, 0.75, axis=0, method="linear")
    scales = np.maximum(upper - lower, 1.0)
    return QueryTransform(thresholds.astype(np.float64), scales.astype(np.float64))


def to_signed_margins(primitives: np.ndarray, transform: QueryTransform) -> np.ndarray:
    values = np.asarray(primitives, dtype=np.float64)
    return (values - transform.thresholds) / transform.scales


def empirical_residual_mass_decision(
    predicted_margins: np.ndarray,
    calibration_residuals: np.ndarray,
    query: QueryForm,
    *,
    beta: float,
    chunk_size: int = 128,
) -> SelectiveDecision:
    prediction = np.asarray(predicted_margins, dtype=np.float64)
    residuals = np.asarray(calibration_residuals, dtype=np.float64)
    if prediction.ndim != 2 or residuals.ndim != 2:
        raise ValueError("empirical residual support requires matrices")
    if prediction.shape[1] != residuals.shape[1]:
        raise ValueError("empirical residual dimensions do not match")
    if not len(residuals):
        raise ValueError("empirical residual support requires calibration residuals")
    if not 0.0 <= beta < 0.5:
        raise ValueError("beta must lie in [0, 0.5)")
    true_counts = np.zeros(len(prediction), dtype=np.int64)
    for start in range(0, len(residuals), chunk_size):
        support = prediction[:, None, :] + residuals[None, start : start + chunk_size, :]
        flattened = support.reshape(-1, support.shape[-1])
        truth = query_truth(flattened, query).reshape(len(prediction), -1)
        true_counts += np.sum(truth, axis=1)
    probability = true_counts.astype(np.float64) / len(residuals)
    predictions = (probability > 0.5).astype(np.bool_)
    accepted = ((probability <= beta) | (probability >= 1.0 - beta)).astype(np.bool_)
    confidence = np.maximum(probability, 1.0 - probability)
    reasons = tuple(
        "accepted_empirical_support_mass"
        if item
        else "refused_empirical_support_disagreement"
        for item in accepted
    )
    return SelectiveDecision(predictions, accepted, confidence, reasons)


def _regime_labels(true_margins: np.ndarray, predicted_margins: np.ndarray) -> tuple[str, ...]:
    truth = np.asarray(true_margins, dtype=np.float64)
    predicted = np.asarray(predicted_margins, dtype=np.float64)
    minimum_truth = np.min(np.abs(truth), axis=1)
    residual = np.max(np.abs(truth - predicted), axis=1)
    labels: list[str] = []
    for index, (boundary, error) in enumerate(zip(minimum_truth, residual, strict=True)):
        if boundary <= 0.10:
            labels.append("weak")
        elif error >= 1.5:
            labels.append("shifted")
        elif np.all(np.abs(truth[index]) <= 0.25):
            labels.append("absent")
        else:
            labels.append("supported")
    return tuple(labels)


def _diagnostic_bundle(
    decision: SelectiveDecision,
    labels: np.ndarray,
    repositories: Sequence[str],
    regimes: Sequence[str],
    anchors: Sequence[float],
) -> dict[str, Any]:
    return {
        "selective": selective_diagnostics(decision, labels, repositories=repositories),
        "risk_coverage": ranked_risk_coverage_curve(
            decision.predictions,
            labels,
            decision.scores,
            anchors=anchors,
            repositories=repositories,
        ),
        "regimes": stratified_selective_diagnostics(
            decision, labels, regimes, repositories=repositories
        ),
    }


def evaluate_query(
    query: QueryForm,
    *,
    fit_embeddings: np.ndarray,
    calibration_embeddings: np.ndarray,
    iteration_embeddings: np.ndarray,
    fit_true_margins: np.ndarray,
    calibration_true_margins: np.ndarray,
    iteration_true_margins: np.ndarray,
    calibration_predicted_margins: np.ndarray,
    iteration_predicted_margins: np.ndarray,
    iteration_repositories: Sequence[str],
    alpha_grid: Sequence[float],
    beta_grid: Sequence[float],
    coverage_anchors: Sequence[float],
) -> dict[str, Any]:
    fit_labels = query_truth(fit_true_margins, query)
    calibration_labels = query_truth(calibration_true_margins, query)
    iteration_labels = query_truth(iteration_true_margins, query)
    result: dict[str, Any] = {
        "query": query.to_dict(),
        "label_prevalence": {
            "fit_model": float(np.mean(fit_labels)),
            "fit_calibration": float(np.mean(calibration_labels)),
            "iteration": float(np.mean(iteration_labels)),
        },
        "methods": {},
    }
    regimes = _regime_labels(iteration_true_margins, iteration_predicted_margins)
    residuals = calibration_true_margins - calibration_predicted_margins
    for alpha in alpha_grid:
        independent = fit_independent_primitive_calibration(
            calibration_true_margins,
            calibration_predicted_margins,
            alpha=float(alpha),
        )
        independent_decision = independent_primitive_conformal_decision(
            iteration_predicted_margins, independent, query
        )
        result["methods"][f"independent_primitive_alpha_{alpha:g}"] = _diagnostic_bundle(
            independent_decision,
            iteration_labels,
            iteration_repositories,
            regimes,
            coverage_anchors,
        )
        joint = fit_joint_max_residual_calibration(
            calibration_true_margins,
            calibration_predicted_margins,
            alpha=float(alpha),
        )
        joint_decision = joint_box_support_decision(iteration_predicted_margins, joint, query)
        joint_bundle = _diagnostic_bundle(
            joint_decision,
            iteration_labels,
            iteration_repositories,
            regimes,
            coverage_anchors,
        )
        radius = joint.quantile * joint.scales
        joint_bundle["primitive_interval_coverage"] = primitive_interval_coverage(
            iteration_true_margins,
            iteration_predicted_margins - radius,
            iteration_predicted_margins + radius,
        )
        result["methods"][f"candidate_joint_box_alpha_{alpha:g}"] = joint_bundle
        direct = fit_direct_compound_conformal(
            fit_embeddings,
            fit_labels,
            calibration_embeddings,
            calibration_labels,
            alpha=float(alpha),
        )
        direct_decision = direct_compound_conformal_decision(direct, iteration_embeddings)
        result["methods"][f"direct_compound_alpha_{alpha:g}"] = _diagnostic_bundle(
            direct_decision,
            iteration_labels,
            iteration_repositories,
            regimes,
            coverage_anchors,
        )
        if alpha == alpha_grid[0]:
            probabilities = direct.estimator.predict_proba(iteration_embeddings)
            for anchor in coverage_anchors:
                confidence = uncalibrated_confidence_decision(
                    probabilities, target_coverage=float(anchor)
                )
                key = f"uncalibrated_confidence_coverage_{anchor:g}"
                result["methods"][key] = _diagnostic_bundle(
                    confidence,
                    iteration_labels,
                    iteration_repositories,
                    regimes,
                    coverage_anchors,
                )
    for beta in beta_grid:
        empirical = empirical_residual_mass_decision(
            iteration_predicted_margins, residuals, query, beta=float(beta)
        )
        result["methods"][f"candidate_empirical_mass_beta_{beta:g}"] = _diagnostic_bundle(
            empirical,
            iteration_labels,
            iteration_repositories,
            regimes,
            coverage_anchors,
        )
    oracle = oracle_support_decision(iteration_true_margins, query)
    result["methods"]["oracle_support"] = _diagnostic_bundle(
        oracle,
        iteration_labels,
        iteration_repositories,
        regimes,
        coverage_anchors,
    )
    return result


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run_discovery_iteration(
    *,
    plan_path: Path,
    registry_path: Path,
    identity_path: Path,
    canonical_firewall_dir: Path,
    output_dir: Path,
    device: str,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"discovery output already exists: {output_dir}")
    plan = load_discovery_plan(plan_path)
    registrations = verify_registered_candidates(plan, registry_path)
    publication = json.loads(
        (canonical_firewall_dir / "option-c0-data-firewall-publication-v1.json").read_text(
            encoding="utf-8"
        )
    )
    if publication.get("c1_rows_selected") is not False:
        raise HiddenRoleAccessError("C1 evidence state changed")
    allocation_context = str(publication["allocation_context_sha256"])
    started = time.perf_counter()
    tracemalloc.start()
    visible, reconstruction = reconstruct_visible_records(identity_path, canonical_firewall_dir)
    prepared = prepare_visible_data(
        visible,
        allocation_context_sha256=allocation_context,
        calibration_fraction=plan.fit_calibration_fraction,
    )
    embeddings, embedding_runtime = embed_prepared_data(
        prepared,
        identity_path,
        device=device,
        batch_size=plan.embedding_batch_size,
        cache_dir=cache_dir,
    )
    _, fit_primitives, fit_repositories = _record_arrays(prepared.fit_model)
    _, calibration_primitives, calibration_repositories = _record_arrays(
        prepared.fit_calibration
    )
    _, iteration_primitives, iteration_repositories = _record_arrays(prepared.iteration)
    primitive_model = fit_primitive_models(
        embeddings["fit_model"],
        fit_primitives,
        fit_repositories,
        alphas=plan.ridge_alphas,
        folds=plan.ridge_folds,
    )
    calibration_prediction = predict_primitives(
        primitive_model, embeddings["fit_calibration"]
    )
    iteration_prediction = predict_primitives(primitive_model, embeddings["iteration"])
    transform = fit_query_transform(fit_primitives)
    fit_true_margins = to_signed_margins(fit_primitives, transform)
    calibration_true_margins = to_signed_margins(calibration_primitives, transform)
    iteration_true_margins = to_signed_margins(iteration_primitives, transform)
    calibration_predicted_margins = to_signed_margins(calibration_prediction, transform)
    iteration_predicted_margins = to_signed_margins(iteration_prediction, transform)
    direct_embeddings = {
        name: primitive_model.scaler.transform(np.asarray(matrix, dtype=np.float64))
        for name, matrix in embeddings.items()
    }
    queries: dict[str, Any] = {}
    for query in plan.query_forms:
        queries[query.query_id] = evaluate_query(
            query,
            fit_embeddings=direct_embeddings["fit_model"],
            calibration_embeddings=direct_embeddings["fit_calibration"],
            iteration_embeddings=direct_embeddings["iteration"],
            fit_true_margins=fit_true_margins,
            calibration_true_margins=calibration_true_margins,
            iteration_true_margins=iteration_true_margins,
            calibration_predicted_margins=calibration_predicted_margins,
            iteration_predicted_margins=iteration_predicted_margins,
            iteration_repositories=iteration_repositories,
            alpha_grid=plan.alpha_grid,
            beta_grid=plan.residual_mass_beta_grid,
            coverage_anchors=plan.coverage_anchors,
        )
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {
        "result_id": RESULT_SCHEMA,
        "status": "C0_ITERATION_EXPLORATORY_RESULTS_PENDING_LEDGER_PUBLICATION",
        "scientific_result_observed": False,
        "mechanism_result_observed": True,
        "c0_selection_accessed": False,
        "c1_rows_selected": False,
        "phase": "C0_ITERATION",
        "exploratory_only": True,
        "plan_sha256": _sha256_file(plan_path),
        "registry_sha256": _sha256_file(registry_path),
        "candidate_registrations": len(registrations),
        "allocation_context_sha256": allocation_context,
        "reconstruction": reconstruction,
        "partition": {
            "commitment_sha256": prepared.partition_commitment,
            "fit_model_rows": len(prepared.fit_model),
            "fit_calibration_rows": len(prepared.fit_calibration),
            "iteration_rows": len(prepared.iteration),
            "fit_calibration_repositories": len(set(calibration_repositories)),
        },
        "primitive_model": {
            "selected_alphas": dict(zip(PRIMITIVES, primitive_model.selected_alphas, strict=True)),
            "thresholds": dict(zip(PRIMITIVES, transform.thresholds.tolist(), strict=True)),
            "scales": dict(zip(PRIMITIVES, transform.scales.tolist(), strict=True)),
        },
        "embedding_runtime": embedding_runtime,
        "runtime": {
            "seconds": time.perf_counter() - started,
            "tracemalloc_current_bytes": current,
            "tracemalloc_peak_bytes": peak,
        },
        "queries": queries,
        "next_allowed_action": "APPEND_CANDIDATE_EVALUATED_AND_DISCOVERY_EVENTS",
        "prohibited_actions": [
            "C0 selection access",
            "C1 reserve access",
            "C1 calibration or test row selection",
            "Option C scientific decision",
        ],
    }
    temporary_dir = output_dir.parent / f".{output_dir.name}.tmp-{uuid.uuid4().hex}"
    temporary_dir.mkdir(parents=True)
    try:
        _atomic_write_json(temporary_dir / "option-c0-discovery-iteration-v1.json", result)
        shutil.copyfile(registry_path, temporary_dir / registry_path.name)
        os.replace(temporary_dir, output_dir)
    finally:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
    return result


def validate_discovery_setup(
    plan_path: Path,
    registry_path: Path,
    canonical_firewall_dir: Path,
) -> dict[str, Any]:
    plan = load_discovery_plan(plan_path)
    registrations = verify_registered_candidates(plan, registry_path)
    assignments = load_visible_repository_assignments(canonical_firewall_dir)
    return {
        "status": "C0_INITIAL_CANDIDATE_PLAN_REGISTERED_PENDING_ITERATION_EXECUTION",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_accessed": False,
        "c1_rows_selected": False,
        "candidate_registry_entries": len(registrations),
        "query_forms": [item.to_dict() for item in plan.query_forms],
        "candidate_families": list(CANDIDATE_FAMILIES),
        "visible_repositories": {
            role: sum(item["role"] == role for item in assignments)
            for role in VISIBLE_ROLES
        },
        "next_allowed_action": "REVIEWED_ONE_TIME_C0_ITERATION_EXECUTION",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--canonical-firewall-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        result = validate_discovery_setup(
            args.plan, args.registry, args.canonical_firewall_dir
        )
    else:
        if args.identity is None or args.output_dir is None:
            parser.error("--identity and --output-dir are required unless --validate-only is used")
        result = run_discovery_iteration(
            plan_path=args.plan,
            registry_path=args.registry,
            identity_path=args.identity,
            canonical_firewall_dir=args.canonical_firewall_dir,
            output_dir=args.output_dir,
            device=args.device,
            cache_dir=args.cache_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

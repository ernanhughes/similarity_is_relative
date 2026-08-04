"""Phase guards, candidate plans, and setup validation for Option C0."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import numpy as np

from relate.experiments.option_c0_selective_baselines import (
    QUERY_OPERATORS,
    QueryForm,
    query_truth,
)

HARNESS_SCHEMA: Final = "option-c0-development-harness-contract-v1"
VISIBLE_ALLOCATION_ROLES: Final = ("c0_fit", "c0_iteration")
BLOCKED_ALLOCATION_ROLES: Final = ("c0_selection", "c1_reserve")
VISIBLE_PHASE_LABELS: Final = ("C0_FIT", "C0_ITERATION")
BLOCKED_PHASE_LABELS: Final = ("C0_SELECTION", "C1_CALIBRATION", "C1_TEST")
REQUIRED_BASELINES: Final = (
    "independent_primitive_split_conformal",
    "direct_compound_split_conformal",
    "uncalibrated_confidence",
    "oracle_support_diagnostic",
)
PUBLICATION_NAME: Final = "option-c0-data-firewall-publication-v1.json"
ALLOCATION_NAME: Final = "option-c0-repository-allocation-v1.jsonl"
_HEX = re.compile(r"^[0-9a-f]+$")


class C0HarnessError(RuntimeError):
    pass


class HiddenRoleAccessError(C0HarnessError):
    pass


class CandidatePlanError(C0HarnessError):
    pass


@dataclass(frozen=True)
class HarnessContract:
    schema_id: str
    status: str
    visible_roles: tuple[str, ...]
    blocked_roles: tuple[str, ...]
    query_operators: tuple[str, ...]
    max_query_forms: int
    required_baselines: tuple[str, ...]
    development_alpha_grid: tuple[float, ...]
    coverage_anchors: tuple[float, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> HarnessContract:
        if value.get("schema_id") != HARNESS_SCHEMA:
            raise ValueError("unexpected Option C0 harness schema")
        for name in (
            "scientific_result_observed",
            "mechanism_result_observed",
            "c1_rows_selected",
        ):
            if value.get(name) is not False:
                raise ValueError(f"harness contract must keep {name}=false")
        visible = tuple(str(item) for item in value.get("visible_roles", ()))
        blocked = tuple(str(item) for item in value.get("blocked_roles", ()))
        operators = tuple(str(item) for item in value.get("query_operators", ()))
        baselines = tuple(str(item) for item in value.get("required_baselines", ()))
        alpha_grid = tuple(float(item) for item in value.get("development_alpha_grid", ()))
        anchors = tuple(float(item) for item in value.get("coverage_anchors", ()))
        if visible != VISIBLE_ALLOCATION_ROLES or blocked != BLOCKED_ALLOCATION_ROLES:
            raise ValueError("visible or blocked roles differ from the reviewed contract")
        if operators != QUERY_OPERATORS or baselines != REQUIRED_BASELINES:
            raise ValueError("query operators or required baselines changed")
        if int(value.get("max_query_forms", 0)) != 3:
            raise ValueError("C0 may examine at most three query forms")
        if tuple(sorted(set(alpha_grid))) != alpha_grid or any(
            not 0.0 < item < 1.0 for item in alpha_grid
        ):
            raise ValueError("development alpha grid must be unique, ascending, and in (0, 1)")
        if tuple(sorted(set(anchors))) != anchors or any(
            not 0.0 < item <= 1.0 for item in anchors
        ):
            raise ValueError("coverage anchors must be unique, ascending, and in (0, 1]")
        if value.get("candidate_registration_required_before_iteration") is not True:
            raise ValueError("candidate registration must precede iteration evaluation")
        if value.get("c0_selection_access") is not False or value.get("c1_access") is not False:
            raise ValueError("this harness must not expose C0 selection or C1 evidence")
        return cls(
            HARNESS_SCHEMA,
            str(value.get("status", "")),
            visible,
            blocked,
            operators,
            3,
            baselines,
            alpha_grid,
            anchors,
        )


def load_harness_contract(path: Path) -> HarnessContract:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("harness contract must be a JSON object")
    return HarnessContract.from_mapping(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_visible_repository_assignments(
    canonical_dir: Path,
    *,
    requested_roles: Sequence[str] = VISIBLE_ALLOCATION_ROLES,
) -> tuple[dict[str, Any], ...]:
    roles = tuple(str(item) for item in requested_roles)
    invalid = sorted(set(roles) - set(VISIBLE_ALLOCATION_ROLES))
    if not roles or invalid:
        raise HiddenRoleAccessError(f"hidden or empty role request: {invalid}")
    publication = json.loads((canonical_dir / PUBLICATION_NAME).read_text(encoding="utf-8"))
    if publication.get("status") not in {
        "C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED_PENDING_REVIEW",
        "C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED",
    }:
        raise ValueError("canonical C0 allocation is not verified")
    for name in (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c1_rows_selected",
    ):
        if publication.get(name) is not False:
            raise ValueError(f"canonical allocation changed forbidden state: {name}")
    artifact = publication["artifacts"][ALLOCATION_NAME]
    allocation_path = canonical_dir / Path(str(artifact["path"])).name
    if _sha256(allocation_path) != artifact["file_sha256"]:
        raise ValueError("canonical repository allocation hash mismatch")
    assignments: list[dict[str, Any]] = []
    repositories: set[str] = set()
    with allocation_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            role = str(row.get("role", ""))
            repository = str(row.get("repository", ""))
            if role not in (*VISIBLE_ALLOCATION_ROLES, *BLOCKED_ALLOCATION_ROLES):
                raise ValueError(f"unknown allocation role: {role}")
            if not repository or repository in repositories:
                raise ValueError("allocation contains a duplicate repository")
            repositories.add(repository)
            if role in roles:
                assignments.append(dict(row))
    if len(repositories) != int(publication["counts"]["allocated_repositories"]):
        raise ValueError("allocation repository count mismatch")
    expected = sum(int(publication["role_counts"][role]["repositories"]) for role in roles)
    if len(assignments) != expected:
        raise ValueError("visible role count differs from publication")
    return tuple(sorted(assignments, key=lambda row: (row["role"], row["repository"])))


def require_c0_selection_unavailable() -> None:
    raise HiddenRoleAccessError("C0 selection remains hidden until registry closure")


def require_c1_evidence_unavailable() -> None:
    raise HiddenRoleAccessError("C1 evidence does not exist before the C1 contract merges")


@dataclass(frozen=True)
class DevelopmentBatch:
    phase: str
    query: QueryForm
    true_margins: np.ndarray
    predicted_margins: np.ndarray
    direct_features: np.ndarray
    repositories: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.phase not in VISIBLE_PHASE_LABELS:
            if self.phase in BLOCKED_PHASE_LABELS:
                raise HiddenRoleAccessError(f"hidden development phase: {self.phase}")
            raise ValueError(f"unknown development phase: {self.phase}")
        truth = np.asarray(self.true_margins, dtype=np.float64)
        predicted = np.asarray(self.predicted_margins, dtype=np.float64)
        features = np.asarray(self.direct_features, dtype=np.float64)
        if truth.ndim != 2 or truth.shape[1] != len(self.query.primitive_names):
            raise ValueError("true margins do not match query primitives")
        if predicted.shape != truth.shape:
            raise ValueError("predicted margins must match true margins")
        if features.ndim != 2 or features.shape[0] != len(truth):
            raise ValueError("direct features must have one row per example")
        if len(self.repositories) != len(truth) or any(not item for item in self.repositories):
            raise ValueError("repository identities must align with rows")
        if not np.all(np.isfinite(truth)) or not np.all(np.isfinite(predicted)):
            raise ValueError("primitive margins must be finite")
        if not np.all(np.isfinite(features)):
            raise ValueError("direct features must be finite")

    @property
    def labels(self) -> np.ndarray:
        return query_truth(self.true_margins, self.query)


def _require_hex(value: str, *, lengths: set[int], name: str) -> None:
    if len(value) not in lengths or _HEX.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase hexadecimal with length {sorted(lengths)}")


@dataclass(frozen=True)
class CandidatePlan:
    candidate_id: str
    version: str
    commit_sha: str
    support_object_definition: str
    propagation_rule: str
    query: QueryForm
    nonconformity_score: str
    fit_data_role: str = "C0_FIT"
    calibration_data_role: str = "C0_FIT"
    evaluation_data_role: str = "C0_ITERATION"
    hyperparameters: Mapping[str, Any] = field(default_factory=dict)
    expected_failure_mode: str = ""
    predecessor_version: str | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.version.strip():
            raise CandidatePlanError("candidate ID and version must be non-empty")
        _require_hex(self.commit_sha, lengths={40, 64}, name="commit_sha")
        for name, value in (
            ("support_object_definition", self.support_object_definition),
            ("propagation_rule", self.propagation_rule),
            ("nonconformity_score", self.nonconformity_score),
            ("expected_failure_mode", self.expected_failure_mode),
        ):
            if not value.strip():
                raise CandidatePlanError(f"{name} must be non-empty")
        roles = (self.fit_data_role, self.calibration_data_role, self.evaluation_data_role)
        if any(role not in VISIBLE_PHASE_LABELS for role in roles):
            raise HiddenRoleAccessError("candidate plans may use only fit and iteration")
        if self.fit_data_role != "C0_FIT" or self.calibration_data_role != "C0_FIT":
            raise CandidatePlanError("fit and development calibration must use C0_FIT")
        if self.evaluation_data_role != "C0_ITERATION":
            raise CandidatePlanError("candidate iteration evaluation must use C0_ITERATION")

    def to_registry_payload(
        self,
        *,
        timestamp: str,
        artifact_hashes: Mapping[str, str],
    ) -> dict[str, Any]:
        checked: dict[str, str] = {}
        for name, digest in sorted(artifact_hashes.items()):
            _require_hex(str(digest), lengths={64}, name=f"artifact hash {name}")
            checked[str(name)] = str(digest)
        hyperparameters = dict(self.hyperparameters)
        hyperparameters.update(
            {
                "fit_data_role": self.fit_data_role,
                "calibration_data_role": self.calibration_data_role,
                "evaluation_data_role": self.evaluation_data_role,
            }
        )
        return {
            "candidate_id": self.candidate_id,
            "version": self.version,
            "commit_sha": self.commit_sha,
            "support_object_definition": self.support_object_definition,
            "propagation_rule": self.propagation_rule,
            "query_form": json.dumps(self.query.to_dict(), sort_keys=True),
            "confidence_score": self.nonconformity_score,
            "data_roles": ["C0_FIT", "C0_ITERATION"],
            "hyperparameters": hyperparameters,
            "expected_failure_mode": self.expected_failure_mode,
            "status": "active",
            "timestamp": timestamp,
            "predecessor_version": self.predecessor_version,
            "artifact_hashes": checked,
        }


def validate_candidate_collection(candidates: Sequence[CandidatePlan]) -> None:
    if not candidates:
        raise CandidatePlanError("at least one candidate plan is required")
    identities = [(item.candidate_id, item.version) for item in candidates]
    if len(identities) != len(set(identities)):
        raise CandidatePlanError("candidate identities must be unique")
    definitions: dict[str, str] = {}
    for candidate in candidates:
        definition = json.dumps(candidate.query.to_dict(), sort_keys=True)
        previous = definitions.setdefault(candidate.query.query_id, definition)
        if previous != definition:
            raise CandidatePlanError("one query ID cannot have multiple definitions")
    if len(definitions) > 3:
        raise CandidatePlanError("candidate collection exceeds three query forms")


def require_candidate_registered(
    registry_path: Path,
    *,
    candidate_id: str,
    version: str,
) -> dict[str, Any]:
    from relate.experiments.option_c0_data_firewall import read_candidate_registry

    for event in read_candidate_registry(registry_path):
        if (
            event.get("event_type") == "REGISTERED"
            and event.get("candidate_id") == candidate_id
            and event.get("version") == version
        ):
            return dict(event)
    raise CandidatePlanError(f"candidate is not registered: {candidate_id}@{version}")


def validate_harness_setup(
    contract_path: Path,
    canonical_firewall_dir: Path,
) -> dict[str, Any]:
    contract = load_harness_contract(contract_path)
    assignments = load_visible_repository_assignments(canonical_firewall_dir)
    repository_counts = {role: 0 for role in VISIBLE_ALLOCATION_ROLES}
    row_counts = {role: 0 for role in VISIBLE_ALLOCATION_ROLES}
    for assignment in assignments:
        role = str(assignment["role"])
        repository_counts[role] += 1
        row_counts[role] += int(assignment["row_count"])
    return {
        "status": "C0_MECHANISM_HARNESS_VALIDATED_PENDING_CANDIDATE_REGISTRATION",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_accessed": False,
        "c1_rows_selected": False,
        "contract_schema": contract.schema_id,
        "visible_repository_counts": repository_counts,
        "visible_row_counts": row_counts,
        "required_baselines": list(contract.required_baselines),
        "next_allowed_action": "C0_CANDIDATE_PLAN_REVIEW",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--canonical-firewall-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            validate_harness_setup(args.contract, args.canonical_firewall_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

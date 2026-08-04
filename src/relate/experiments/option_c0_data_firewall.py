"""Option C0 repository firewall and append-only evidence infrastructure.

This module implements only the infrastructure authorised by the frozen C0
protocol. It does not implement a propagation mechanism, conformal method,
risk-coverage metric, C1 row selection, or scientific decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.hashing import sha256_bytes as _sha256_bytes

ROLE_NAMES: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
C0_PHASE_LABELS: Final = ("C0_FIT", "C0_ITERATION", "C0_SELECTION")
DISCOVERY_CLASSIFICATIONS: Final = (
    "PLANNED_MECHANISM_DIAGNOSTIC",
    "EXPLORATORY_OBSERVATION",
    "UNEXPECTED_FINDING",
    "NEW_HYPOTHESIS_REQUIRING_FRESH_DATA",
    "IMPLEMENTATION_OR_DATA_INTEGRITY_FINDING",
)
CANDIDATE_STATUSES: Final = (
    "active",
    "superseded",
    "rejected",
    "selected_for_c0_selection",
)
CANDIDATE_EVENT_TYPES: Final = ("REGISTERED", "EVALUATED", "STATUS_CHANGED")
DATASET_SPLITS: Final = ("train", "validation", "test")
ALLOCATION_SCHEMA: Final = "option-c0-repository-allocation-v1"
CANDIDATE_REGISTRY_SCHEMA: Final = "option-c0-candidate-registry-v1"
DISCOVERY_LEDGER_SCHEMA: Final = "option-c0-discovery-ledger-v1"
EMPTY_HASH: Final = "0" * 64
_HEX = re.compile(r"^[0-9a-f]+$")


class C0InfrastructureError(RuntimeError):
    """Base error for C0 infrastructure contract violations."""


class InsufficientRepositoriesError(C0InfrastructureError):
    """Raised when the frozen roles cannot be populated without borrowing."""


class AppendOnlyViolation(C0InfrastructureError):
    """Raised when a caller attempts mutation, deletion, or duplicate insertion."""


class C1SelectionForbidden(C0InfrastructureError):
    """Raised whenever C1 calibration or test row selection is attempted."""


@dataclass(frozen=True)
class AllocationConfig:
    """Reviewed configuration consumed by a later one-time allocation run."""

    schema_id: str = ALLOCATION_SCHEMA
    domain: str = "option-c0-repository-allocation-v1"
    role_weights: tuple[int, int, int, int] = (5, 2, 1, 2)
    minimum_repositories: tuple[int, int, int, int] = (1, 1, 1, 1)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> AllocationConfig:
        schema_id = str(value.get("schema_id", ""))
        domain = str(value.get("domain", ""))
        weights = tuple(int(item) for item in value.get("role_weights", ()))
        minimums = tuple(int(item) for item in value.get("minimum_repositories", ()))
        if schema_id != ALLOCATION_SCHEMA:
            raise ValueError(f"unexpected allocation schema: {schema_id}")
        if not domain:
            raise ValueError("allocation domain must be non-empty")
        if len(weights) != len(ROLE_NAMES) or any(item <= 0 for item in weights):
            raise ValueError("role_weights must contain four positive integers")
        if len(minimums) != len(ROLE_NAMES) or any(item < 1 for item in minimums):
            raise ValueError("minimum_repositories must contain four positive integers")
        return cls(
            schema_id=schema_id,
            domain=domain,
            role_weights=weights,  # type: ignore[arg-type]
            minimum_repositories=minimums,  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "domain": self.domain,
            "role_names": list(ROLE_NAMES),
            "role_weights": list(self.role_weights),
            "minimum_repositories": list(self.minimum_repositories),
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode())


def _require_hex(value: str, *, lengths: set[int], field: str) -> None:
    if len(value) not in lengths or _HEX.fullmatch(value) is None:
        raise ValueError(f"{field} must be lowercase hexadecimal with length {sorted(lengths)}")


def _validate_artifact_hashes(value: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, digest in sorted(value.items()):
        key = str(name)
        sha = str(digest)
        if not key:
            raise ValueError("artifact hash names must be non-empty")
        _require_hex(sha, lengths={64}, field=f"artifact hash {key}")
        result[key] = sha
    return result


def verify_artifact_hashes(root: Path, artifacts: Mapping[str, str]) -> None:
    """Require every relative artifact path to match its declared SHA-256."""

    for relative_path, expected in sorted(artifacts.items()):
        _require_hex(expected, lengths={64}, field=f"artifact hash {relative_path}")
        path = root / relative_path
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256_bytes(path.read_bytes())
        if actual != expected:
            raise ValueError(f"artifact hash mismatch: {relative_path}")


def load_allocation_config(path: Path) -> AllocationConfig:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("allocation config must be a JSON object")
    return AllocationConfig.from_mapping(value)


def _normalise_eligible_row(row: Mapping[str, Any]) -> dict[str, Any]:
    repository = str(row.get("repository", "")).strip()
    stable_key = str(row.get("stable_key", "")).strip()
    source_split = str(row.get("source_split", row.get("split", ""))).strip()
    if not repository or not stable_key or source_split not in DATASET_SPLITS:
        raise ValueError("eligible rows require repository, stable_key, and a frozen source split")
    result = {
        "repository": repository,
        "stable_key": stable_key,
        "source_split": source_split,
        "path": str(row.get("path", "")),
        "function_id": str(row.get("function_id", "")),
        "code_sha256": str(row.get("code_sha256", "")),
        "normalized_ast_sha256": str(row.get("normalized_ast_sha256", "")),
        "token_count": int(row.get("token_count", 0)),
    }
    for field in ("code_sha256", "normalized_ast_sha256"):
        if result[field]:
            _require_hex(result[field], lengths={64}, field=field)
    return result


def compute_source_commitment(rows: Iterable[Mapping[str, Any]]) -> str:
    normalised = sorted(
        (_normalise_eligible_row(row) for row in rows),
        key=lambda row: row["stable_key"],
    )
    stable_keys = [row["stable_key"] for row in normalised]
    if len(stable_keys) != len(set(stable_keys)):
        raise ValueError("eligible source stable keys must be unique")
    payload = b"".join((_canonical_json(row) + "\n").encode() for row in normalised)
    return _sha256_bytes(payload)


def _commit_string_set(values: Iterable[str]) -> str:
    return _sha256_bytes(("\n".join(sorted(set(values))) + "\n").encode())


def _role_quotas(repository_count: int, config: AllocationConfig) -> dict[str, int]:
    minimum_total = sum(config.minimum_repositories)
    if repository_count < minimum_total:
        raise InsufficientRepositoriesError(
            f"{repository_count} repositories cannot satisfy minimum total {minimum_total}"
        )
    remaining = repository_count - minimum_total
    weight_total = sum(config.role_weights)
    raw = [remaining * weight / weight_total for weight in config.role_weights]
    extras = [int(value) for value in raw]
    unassigned = remaining - sum(extras)
    fractional_order = sorted(
        range(len(ROLE_NAMES)),
        key=lambda index: (-(raw[index] - extras[index]), index),
    )
    for index in fractional_order[:unassigned]:
        extras[index] += 1
    return {
        role: config.minimum_repositories[index] + extras[index]
        for index, role in enumerate(ROLE_NAMES)
    }


def allocate_repositories(
    eligible_rows: Iterable[Mapping[str, Any]],
    option_b_repositories: Iterable[str],
    config: AllocationConfig,
    *,
    source_identity_commitment: str,
) -> dict[str, Any]:
    """Deterministically allocate whole repositories into C0 roles and one C1 reserve."""

    _require_hex(
        source_identity_commitment,
        lengths={64},
        field="source_identity_commitment",
    )
    normalised = [_normalise_eligible_row(row) for row in eligible_rows]
    source_commitment = compute_source_commitment(normalised)
    excluded = {str(repository) for repository in option_b_repositories}
    if "" in excluded:
        raise ValueError("Option B repository exclusions must be non-empty")
    exclusion_commitment = _commit_string_set(excluded)

    by_repository: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded_rows = 0
    for row in normalised:
        if row["repository"] in excluded:
            excluded_rows += 1
        else:
            by_repository[row["repository"]].append(row)
    if not by_repository:
        raise InsufficientRepositoriesError("no repositories remain after Option B exclusion")

    config_commitment = _sha256_json(config.to_dict())
    allocation_context = _sha256_json(
        {
            "schema": ALLOCATION_SCHEMA,
            "source_identity_commitment": source_identity_commitment,
            "source_commitment": source_commitment,
            "option_b_exclusion_commitment": exclusion_commitment,
            "config_commitment": config_commitment,
        }
    )
    ordered_repositories = sorted(
        by_repository,
        key=lambda repository: hashlib.sha256(
            f"{config.domain}\0{allocation_context}\0{repository}".encode()
        ).hexdigest(),
    )
    quotas = _role_quotas(len(ordered_repositories), config)

    assignments: list[dict[str, Any]] = []
    role_repositories: dict[str, list[str]] = {role: [] for role in ROLE_NAMES}
    cursor = 0
    for role in ROLE_NAMES:
        selected = ordered_repositories[cursor : cursor + quotas[role]]
        cursor += quotas[role]
        role_repositories[role].extend(selected)
        for repository in selected:
            rows = sorted(by_repository[repository], key=lambda row: row["stable_key"])
            assignments.append(
                {
                    "role": role,
                    "repository": repository,
                    "repository_order_key": hashlib.sha256(
                        f"{config.domain}\0{allocation_context}\0{repository}".encode()
                    ).hexdigest(),
                    "row_count": len(rows),
                    "source_splits": sorted({row["source_split"] for row in rows}),
                    "repository_rows_sha256": _sha256_bytes(
                        b"".join((_canonical_json(row) + "\n").encode() for row in rows)
                    ),
                }
            )
    if cursor != len(ordered_repositories):
        raise AssertionError("allocation quotas did not consume all repositories")
    verify_role_disjointness(assignments)

    role_counts: dict[str, Any] = {}
    for role in ROLE_NAMES:
        repositories = role_repositories[role]
        role_rows = sum(len(by_repository[repository]) for repository in repositories)
        role_counts[role] = {
            "repositories": len(repositories),
            "rows": role_rows,
            "repository_commitment": _commit_string_set(repositories),
        }

    return {
        "allocation_id": ALLOCATION_SCHEMA,
        "status": "C0_REPOSITORY_ALLOCATION_PREPARED_PENDING_PUBLICATION",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "source": {
            "source_identity_commitment": source_identity_commitment,
            "eligible_pool_commitment": source_commitment,
            "eligible_rows": len(normalised),
            "eligible_repositories": len({row["repository"] for row in normalised}),
        },
        "option_b_exclusion": {
            "repository_count": len(excluded),
            "repository_commitment": exclusion_commitment,
            "excluded_eligible_rows": excluded_rows,
            "repositories": sorted(excluded),
        },
        "allocation_context_sha256": allocation_context,
        "config": config.to_dict(),
        "config_sha256": config_commitment,
        "role_counts": role_counts,
        "assignments": sorted(assignments, key=lambda item: (item["role"], item["repository"])),
        "checks": {
            "whole_repository_allocation": True,
            "pairwise_role_disjointness": True,
            "option_b_repositories_excluded": not any(
                item["repository"] in excluded for item in assignments
            ),
            "c1_reserve_undivided": True,
        },
        "next_allowed_action": "CANONICAL_C0_ALLOCATION_PUBLICATION_AND_INDEPENDENT_VERIFICATION",
        "prohibited_actions": [
            "propagation mechanism evaluation",
            "conformal calibration",
            "risk-coverage evaluation",
            "C1 calibration row selection",
            "C1 test row selection",
            "Option C scientific decision",
        ],
    }


def verify_role_disjointness(assignments: Sequence[Mapping[str, Any]]) -> None:
    owners: dict[str, str] = {}
    for item in assignments:
        role = str(item.get("role", ""))
        repository = str(item.get("repository", ""))
        if role not in ROLE_NAMES or not repository:
            raise ValueError("allocation entries require a frozen role and repository")
        if repository in owners:
            raise ValueError(f"repository appears more than once: {repository}")
        owners[repository] = role


def select_c1_rows(*_: Any, **__: Any) -> None:
    """C1 row identities are deliberately unavailable before the C1 contract merges."""

    raise C1SelectionForbidden(
        "final C1 calibration/test rows cannot be selected by the C0 infrastructure"
    )


def _write_durable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join((_canonical_json(dict(row)) + "\n").encode() for row in rows)


def publish_allocation_bundle(output_dir: Path, allocation: Mapping[str, Any]) -> dict[str, Any]:
    """Publish one allocation bundle atomically and refuse every overwrite."""

    if output_dir.exists():
        raise FileExistsError(f"allocation output already exists: {output_dir}")
    assignments = [dict(item) for item in allocation.get("assignments", [])]
    verify_role_disjointness(assignments)
    if allocation.get("c1_rows_selected") is not False:
        raise ValueError("C0 allocation bundles must not contain selected C1 rows")

    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = parent / f".{output_dir.name}.tmp-{uuid.uuid4().hex}"
    temporary_dir.mkdir()
    try:
        manifest_name = "option-c0-repository-allocation-v1.jsonl"
        manifest_path = temporary_dir / manifest_name
        manifest_payload = _jsonl_bytes(assignments)
        _write_durable(manifest_path, manifest_payload)

        report = json.loads(
            json.dumps({key: value for key, value in allocation.items() if key != "assignments"})
        )
        excluded_repositories = list(report["option_b_exclusion"].pop("repositories", []))
        exclusion_metadata = report["option_b_exclusion"]
        if len(excluded_repositories) != exclusion_metadata["repository_count"]:
            raise ValueError("Option B exclusion count does not match the repository list")
        if _commit_string_set(excluded_repositories) != exclusion_metadata["repository_commitment"]:
            raise ValueError("Option B exclusion commitment does not match the repository list")
        exclusion_name = "option-c0-option-b-excluded-repositories-v1.jsonl"
        exclusion_path = temporary_dir / exclusion_name
        exclusion_rows = [{"repository": repository} for repository in excluded_repositories]
        exclusion_payload = _jsonl_bytes(exclusion_rows)
        _write_durable(exclusion_path, exclusion_payload)
        report["status"] = "C0_REPOSITORY_ALLOCATION_GENERATED_PENDING_INDEPENDENT_VERIFICATION"
        report["artifacts"] = {
            "repository_allocation": {
                "path": manifest_name,
                "rows": len(assignments),
                "file_sha256": _sha256_bytes(manifest_payload),
            },
            "option_b_excluded_repositories": {
                "path": exclusion_name,
                "rows": len(exclusion_rows),
                "file_sha256": _sha256_bytes(exclusion_payload),
            },
        }
        report_path = temporary_dir / "option-c0-data-firewall-v1.json"
        _write_durable(
            report_path,
            (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
        )
        os.replace(temporary_dir, output_dir)
    finally:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
    return verify_allocation_bundle(output_dir)


def verify_allocation_bundle(output_dir: Path) -> dict[str, Any]:
    report_path = output_dir / "option-c0-data-firewall-v1.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_status = "C0_REPOSITORY_ALLOCATION_GENERATED_PENDING_INDEPENDENT_VERIFICATION"
    if report.get("status") != expected_status:
        raise ValueError("unexpected C0 allocation status")
    for field in ("scientific_result_observed", "mechanism_result_observed", "c1_rows_selected"):
        if report.get(field) is not False:
            raise ValueError(f"C0 allocation field must remain false: {field}")
    artifact = report["artifacts"]["repository_allocation"]
    manifest_path = output_dir / artifact["path"]
    payload = manifest_path.read_bytes()
    if _sha256_bytes(payload) != artifact["file_sha256"]:
        raise ValueError("repository allocation hash mismatch")
    assignments = [json.loads(line) for line in payload.decode().splitlines() if line.strip()]
    if len(assignments) != artifact["rows"]:
        raise ValueError("repository allocation row-count mismatch")
    verify_role_disjointness(assignments)
    exclusion_artifact = report["artifacts"]["option_b_excluded_repositories"]
    exclusion_path = output_dir / exclusion_artifact["path"]
    exclusion_payload = exclusion_path.read_bytes()
    if _sha256_bytes(exclusion_payload) != exclusion_artifact["file_sha256"]:
        raise ValueError("Option B exclusion manifest hash mismatch")
    exclusion_rows = [
        json.loads(line) for line in exclusion_payload.decode().splitlines() if line.strip()
    ]
    if len(exclusion_rows) != exclusion_artifact["rows"]:
        raise ValueError("Option B exclusion manifest row-count mismatch")
    excluded = {row["repository"] for row in exclusion_rows}
    exclusion_metadata = report["option_b_exclusion"]
    if len(excluded) != exclusion_metadata["repository_count"]:
        raise ValueError("Option B exclusion repository count mismatch")
    if _commit_string_set(excluded) != exclusion_metadata["repository_commitment"]:
        raise ValueError("Option B exclusion repository commitment mismatch")
    if any(item["repository"] in excluded for item in assignments):
        raise ValueError("Option B repository appears in a C0 role")
    observed_role_counts: dict[str, dict[str, Any]] = {}
    for role in ROLE_NAMES:
        selected = [item for item in assignments if item["role"] == role]
        repositories = [item["repository"] for item in selected]
        observed_role_counts[role] = {
            "repositories": len(repositories),
            "rows": sum(int(item["row_count"]) for item in selected),
            "repository_commitment": _commit_string_set(repositories),
        }
    if observed_role_counts != report["role_counts"]:
        raise ValueError("published role counts or commitments do not match the manifest")
    return {
        "status": "C0_DATA_FIREWALL_BUNDLE_VERIFIED",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "checks": {
            "artifact_hash_verified": True,
            "pairwise_role_disjointness": True,
            "c1_rows_unselected": True,
        },
    }


def _verified_text_bytes(path: Path, expected_sha256: str) -> bytes:
    raw = path.read_bytes()
    if _sha256_bytes(raw) == expected_sha256:
        return raw
    normalised = raw.replace(b"\r\n", b"\n")
    if _sha256_bytes(normalised) == expected_sha256:
        return normalised
    raise ValueError(f"frozen text hash mismatch: {path}")


def load_option_b_repository_exclusions(selection_dir: Path) -> tuple[set[str], dict[str, Any]]:
    """Load and verify every repository present in Option B selected manifests."""

    report_path = selection_dir / "option-b-canonical-row-selection-v2.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("selection_id") != "option-b-canonical-row-selection-v2":
        raise ValueError("unexpected Option B selection identity")
    repositories: set[str] = set()
    artifacts: dict[str, Any] = {}
    for split in DATASET_SPLITS:
        path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
        expected = str(report["artifacts"][split]["selected_manifest"]["sha256"])
        payload = _verified_text_bytes(path, expected)
        rows = 0
        for line in payload.decode().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            repository = str(row.get("repository", "")).strip()
            if not repository:
                raise ValueError("Option B selected rows require repository identity")
            repositories.add(repository)
            rows += 1
        expected_rows = int(report["artifacts"][split]["selected_manifest"]["rows"])
        if rows != expected_rows:
            raise ValueError(f"Option B selected-manifest row-count mismatch: {split}")
        artifacts[split] = {"rows": rows, "file_sha256": expected}
    return repositories, {
        "selection_id": report["selection_id"],
        "repository_count": len(repositories),
        "repository_commitment": _commit_string_set(repositories),
        "artifacts": artifacts,
    }


def reconstruct_eligible_pool(
    identity_path: Path,
    *,
    dataset_by_split: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    tokenizer: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconstruct the Option C eligible pool using the frozen Option B eligibility rules."""

    from relate.experiments.option_b_real_code import OptionBConfig, remove_cross_split_duplicates
    from relate.experiments.option_b_selection import DATASET_ID, REQUIRED_SPLITS, load_identity
    from relate.experiments.option_b_selection_resilient import build_records_resilient

    identity = load_identity(identity_path)
    if tokenizer is None or dataset_by_split is None:
        try:
            from datasets import load_dataset
            from transformers import AutoTokenizer
        except ImportError as error:  # pragma: no cover - canonical runtime only
            message = "install Option B dependencies with pip install -e '.[option-b]'"
            raise RuntimeError(message) from error
        if tokenizer is None:
            tokenizer = AutoTokenizer.from_pretrained(
                identity["model"]["repo_id"],
                revision=identity["model"]["revision"],
            )
        if dataset_by_split is None:
            loaded = load_dataset(
                DATASET_ID,
                "python",
                revision=identity["dataset"]["revision"],
            )
            dataset_by_split = {split: loaded[split] for split in REQUIRED_SPLITS}
    missing = [split for split in REQUIRED_SPLITS if split not in dataset_by_split]
    if missing:
        raise ValueError(f"dataset is missing frozen splits: {missing}")

    config = OptionBConfig()
    records_by_split: dict[str, list[Any]] = {}
    exclusion_counts: dict[str, dict[str, int]] = {}
    source_counts: dict[str, int] = {}
    for split in REQUIRED_SPLITS:
        source_rows = [dict(row, _split=split) for row in dataset_by_split[split]]
        source_counts[split] = len(source_rows)
        records, reasons = build_records_resilient(source_rows, tokenizer, config)
        records_by_split[split] = records
        exclusion_counts[split] = dict(sorted(Counter(reasons).items()))
    deduplicated, duplicate_report = remove_cross_split_duplicates(records_by_split)

    rows: list[dict[str, Any]] = []
    for split in REQUIRED_SPLITS:
        for record in deduplicated[split]:
            rows.append(
                {
                    "repository": record.repository,
                    "stable_key": record.stable_key,
                    "source_split": split,
                    "path": record.path,
                    "function_id": record.function_id,
                    "code_sha256": record.code_sha256,
                    "normalized_ast_sha256": record.normalized_ast_sha256,
                    "token_count": record.token_count,
                }
            )
    rows.sort(key=lambda row: row["stable_key"])
    report = {
        "reconstruction_id": "option-c0-eligible-pool-reconstruction-v1",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "identity_sha256": _sha256_bytes(identity_path.read_bytes()),
        "source_rows": source_counts,
        "exclusions": exclusion_counts,
        "cross_split_deduplication": duplicate_report,
        "eligible_rows": len(rows),
        "eligible_repositories": len({row["repository"] for row in rows}),
        "eligible_pool_commitment": compute_source_commitment(rows),
    }
    return rows, report


def prepare_c0_allocation(
    identity_path: Path,
    option_b_selection_dir: Path,
    allocation_config_path: Path,
    output_dir: Path,
    *,
    dataset_by_split: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    tokenizer: Any | None = None,
) -> dict[str, Any]:
    """Reconstruct, allocate, and publish a C0 firewall bundle without C1 row selection."""

    config = load_allocation_config(allocation_config_path)
    rows, reconstruction = reconstruct_eligible_pool(
        identity_path,
        dataset_by_split=dataset_by_split,
        tokenizer=tokenizer,
    )
    option_b_repositories, exclusion = load_option_b_repository_exclusions(option_b_selection_dir)
    allocation = allocate_repositories(
        rows,
        option_b_repositories,
        config,
        source_identity_commitment=reconstruction["identity_sha256"],
    )
    allocation["reconstruction"] = reconstruction
    allocation["option_b_selection"] = exclusion
    verification = publish_allocation_bundle(output_dir, allocation)
    return {
        "status": "C0_REPOSITORY_ALLOCATION_GENERATED_PENDING_INDEPENDENT_VERIFICATION",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "output_dir": str(output_dir).replace("\\", "/"),
        "allocation_context_sha256": allocation["allocation_context_sha256"],
        "role_counts": allocation["role_counts"],
        "verification": verification,
    }


def _read_chain(path: Path, schema_id: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    previous = EMPTY_HASH
    with path.open("r", encoding="utf-8") as handle:
        for expected_sequence, line in enumerate(handle):
            if not line.strip():
                continue
            envelope = json.loads(line)
            if envelope.get("schema_id") != schema_id:
                raise AppendOnlyViolation("append-only schema mismatch")
            if envelope.get("sequence") != expected_sequence:
                raise AppendOnlyViolation("append-only sequence mismatch")
            if envelope.get("previous_entry_sha256") != previous:
                raise AppendOnlyViolation("append-only previous hash mismatch")
            core = {
                "schema_id": schema_id,
                "sequence": expected_sequence,
                "previous_entry_sha256": previous,
                "payload": envelope.get("payload"),
            }
            actual = _sha256_json(core)
            if envelope.get("entry_sha256") != actual:
                raise AppendOnlyViolation("append-only entry hash mismatch")
            entries.append(envelope)
            previous = actual
    return entries


def _append_chain(path: Path, schema_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    entries = _read_chain(path, schema_id)
    previous = entries[-1]["entry_sha256"] if entries else EMPTY_HASH
    core = {
        "schema_id": schema_id,
        "sequence": len(entries),
        "previous_entry_sha256": previous,
        "payload": dict(payload),
    }
    envelope = {**core, "entry_sha256": _sha256_json(core)}
    all_entries = [*entries, envelope]
    _write_durable(path, _jsonl_bytes(all_entries))
    return envelope


def _candidate_events(path: Path) -> list[dict[str, Any]]:
    events = [entry["payload"] for entry in _read_chain(path, CANDIDATE_REGISTRY_SCHEMA)]
    if any(event.get("event_type") not in CANDIDATE_EVENT_TYPES for event in events):
        raise AppendOnlyViolation("candidate registry contains an unknown event type")
    return events


def register_candidate(path: Path, candidate: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "candidate_id",
        "version",
        "commit_sha",
        "support_object_definition",
        "propagation_rule",
        "query_form",
        "confidence_score",
        "data_roles",
        "hyperparameters",
        "expected_failure_mode",
        "status",
        "timestamp",
        "predecessor_version",
        "artifact_hashes",
    }
    missing = sorted(required - set(candidate))
    if missing:
        raise ValueError(f"candidate registration is missing fields: {missing}")
    candidate_id = str(candidate["candidate_id"]).strip()
    version = str(candidate["version"]).strip()
    if not candidate_id or not version:
        raise ValueError("candidate_id and version must be non-empty")
    commit_sha = str(candidate["commit_sha"])
    _require_hex(commit_sha, lengths={40, 64}, field="commit_sha")
    roles = tuple(str(role) for role in candidate["data_roles"])
    if not roles or any(role not in C0_PHASE_LABELS for role in roles):
        raise ValueError("candidate data_roles must contain only C0 phase labels")
    status = str(candidate["status"])
    if status not in CANDIDATE_STATUSES:
        raise ValueError(f"unexpected candidate status: {status}")
    artifacts = _validate_artifact_hashes(candidate["artifact_hashes"])
    events = _candidate_events(path)
    if any(
        event["candidate_id"] == candidate_id and event["version"] == version
        for event in events
        if event["event_type"] == "REGISTERED"
    ):
        raise AppendOnlyViolation(f"candidate version already exists: {candidate_id}@{version}")
    if status != "active":
        raise ValueError("new candidate versions must be registered with active status")
    predecessor = candidate["predecessor_version"]
    if predecessor is not None:
        predecessor_text = str(predecessor).strip()
        if not predecessor_text:
            raise ValueError("predecessor_version must be non-empty when supplied")
        if not any(
            event["event_type"] == "REGISTERED"
            and event["candidate_id"] == candidate_id
            and event["version"] == predecessor_text
            for event in events
        ):
            raise ValueError("predecessor_version must reference a registered candidate version")
    payload = {
        "event_type": "REGISTERED",
        **{key: candidate[key] for key in sorted(required - {"artifact_hashes"})},
        "candidate_id": candidate_id,
        "version": version,
        "commit_sha": commit_sha,
        "data_roles": list(roles),
        "status": status,
        "artifact_hashes": artifacts,
    }
    return _append_chain(path, CANDIDATE_REGISTRY_SCHEMA, payload)


def _require_registered_candidate(
    events: Sequence[Mapping[str, Any]], candidate_id: str, version: str
) -> Mapping[str, Any]:
    for event in events:
        if (
            event["event_type"] == "REGISTERED"
            and event["candidate_id"] == candidate_id
            and event["version"] == version
        ):
            return event
    raise KeyError(f"candidate version is not registered: {candidate_id}@{version}")


def record_candidate_evaluation(
    path: Path,
    *,
    candidate_id: str,
    version: str,
    commit_sha: str,
    timestamp: str,
    artifact_hashes: Mapping[str, str],
) -> dict[str, Any]:
    events = _candidate_events(path)
    _require_registered_candidate(events, candidate_id, version)
    if any(
        event["event_type"] == "EVALUATED"
        and event["candidate_id"] == candidate_id
        and event["version"] == version
        for event in events
    ):
        raise AppendOnlyViolation(f"candidate is already evaluated: {candidate_id}@{version}")
    _require_hex(commit_sha, lengths={40, 64}, field="commit_sha")
    payload = {
        "event_type": "EVALUATED",
        "candidate_id": candidate_id,
        "version": version,
        "commit_sha": commit_sha,
        "timestamp": timestamp,
        "artifact_hashes": _validate_artifact_hashes(artifact_hashes),
    }
    return _append_chain(path, CANDIDATE_REGISTRY_SCHEMA, payload)


def change_candidate_status(
    path: Path,
    *,
    candidate_id: str,
    version: str,
    status: str,
    commit_sha: str,
    timestamp: str,
) -> dict[str, Any]:
    if status not in CANDIDATE_STATUSES:
        raise ValueError(f"unexpected candidate status: {status}")
    events = _candidate_events(path)
    _require_registered_candidate(events, candidate_id, version)
    if status == "selected_for_c0_selection" and not any(
        event["event_type"] == "EVALUATED"
        and event["candidate_id"] == candidate_id
        and event["version"] == version
        for event in events
    ):
        raise AppendOnlyViolation("a candidate must be evaluated before C0 selection")
    _require_hex(commit_sha, lengths={40, 64}, field="commit_sha")
    return _append_chain(
        path,
        CANDIDATE_REGISTRY_SCHEMA,
        {
            "event_type": "STATUS_CHANGED",
            "candidate_id": candidate_id,
            "version": version,
            "status": status,
            "commit_sha": commit_sha,
            "timestamp": timestamp,
        },
    )


def delete_candidate(*_: Any, **__: Any) -> None:
    raise AppendOnlyViolation("candidate registry entries cannot be deleted")


def mutate_candidate(*_: Any, **__: Any) -> None:
    raise AppendOnlyViolation("candidate definitions are immutable; register a new version")


def read_candidate_registry(path: Path) -> list[dict[str, Any]]:
    return _candidate_events(path)


def append_discovery(path: Path, discovery: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "discovery_id",
        "classification",
        "first_observed_timestamp",
        "first_observed_commit",
        "first_observed_data_role",
        "anticipated",
        "observation",
        "affected_candidates_or_assumptions",
        "possible_explanations",
        "action_taken",
        "c1_contract_relevance",
        "fresh_evidence_requirement",
        "artifact_hashes",
    }
    missing = sorted(required - set(discovery))
    if missing:
        raise ValueError(f"discovery row is missing fields: {missing}")
    discovery_id = str(discovery["discovery_id"]).strip()
    if not discovery_id:
        raise ValueError("discovery_id must be non-empty")
    classification = str(discovery["classification"])
    if classification not in DISCOVERY_CLASSIFICATIONS:
        raise ValueError(f"unexpected discovery classification: {classification}")
    phase = str(discovery["first_observed_data_role"])
    if phase not in C0_PHASE_LABELS:
        raise ValueError(f"unexpected C0 phase label: {phase}")
    commit_sha = str(discovery["first_observed_commit"])
    _require_hex(commit_sha, lengths={40, 64}, field="first_observed_commit")
    if not isinstance(discovery["anticipated"], bool):
        raise ValueError("anticipated must be boolean")
    if not isinstance(discovery["c1_contract_relevance"], bool):
        raise ValueError("c1_contract_relevance must be boolean")
    if not str(discovery["fresh_evidence_requirement"]).strip():
        raise ValueError("fresh_evidence_requirement must be non-empty")
    existing = [entry["payload"] for entry in _read_chain(path, DISCOVERY_LEDGER_SCHEMA)]
    if any(entry["discovery_id"] == discovery_id for entry in existing):
        raise AppendOnlyViolation(f"discovery ID already exists: {discovery_id}")
    payload = {
        **{key: discovery[key] for key in sorted(required - {"artifact_hashes"})},
        "discovery_id": discovery_id,
        "classification": classification,
        "first_observed_data_role": phase,
        "first_observed_commit": commit_sha,
        "artifact_hashes": _validate_artifact_hashes(discovery["artifact_hashes"]),
    }
    return _append_chain(path, DISCOVERY_LEDGER_SCHEMA, payload)


def read_discovery_ledger(path: Path) -> list[dict[str, Any]]:
    return [entry["payload"] for entry in _read_chain(path, DISCOVERY_LEDGER_SCHEMA)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--option-b-selection-dir", type=Path, required=True)
    parser.add_argument("--allocation-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = prepare_c0_allocation(
        args.identity,
        args.option_b_selection_dir,
        args.allocation_config,
        args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

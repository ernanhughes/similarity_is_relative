"""Independent recomputation for the canonical Option C0 repository allocation.

This module deliberately does not import the Option C0 allocation runner. It
reconstructs the eligible pool, Option B exclusions, role quotas, repository
ordering, commitments, and published manifests independently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final

ROLE_NAMES: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
DATASET_SPLITS: Final = ("train", "validation", "test")
ALLOCATION_SCHEMA: Final = "option-c0-repository-allocation-v1"
VERIFICATION_ID: Final = "option-c0-data-firewall-independent-v1"
VERIFICATION_NAME: Final = "option-c0-data-firewall-independent-v1.json"
REPORT_NAME: Final = "option-c0-data-firewall-v1.json"
ALLOCATION_NAME: Final = "option-c0-repository-allocation-v1.jsonl"
EXCLUSION_NAME: Final = "option-c0-option-b-excluded-repositories-v1.jsonl"
CANDIDATE_REGISTRY_NAME: Final = "option-c0-candidate-registry-v1.jsonl"
DISCOVERY_LEDGER_NAME: Final = "option-c0-discovery-ledger-v1.jsonl"
RUNNER_IMPORTED: Final = False
_HEX = re.compile(r"^[0-9a-f]+$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value).encode())


def _require_hex(value: str, *, lengths: set[int], field: str) -> None:
    if len(value) not in lengths or _HEX.fullmatch(value) is None:
        raise ValueError(
            f"{field} must be lowercase hexadecimal with length {sorted(lengths)}"
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


def _verified_text_bytes(path: Path, expected_sha256: str) -> bytes:
    raw = path.read_bytes()
    if _sha256_bytes(raw) == expected_sha256:
        return raw
    normalised = raw.replace(b"\r\n", b"\n")
    if _sha256_bytes(normalised) == expected_sha256:
        return normalised
    raise ValueError(f"frozen text hash mismatch: {path}")


def _normalise_row(row: Mapping[str, Any]) -> dict[str, Any]:
    repository = str(row.get("repository", "")).strip()
    stable_key = str(row.get("stable_key", "")).strip()
    source_split = str(row.get("source_split", row.get("split", ""))).strip()
    if not repository or not stable_key or source_split not in DATASET_SPLITS:
        raise ValueError(
            "eligible rows require repository, stable_key, and a frozen source split"
        )
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


def _source_commitment(rows: Iterable[Mapping[str, Any]]) -> str:
    normalised = sorted(
        (_normalise_row(row) for row in rows),
        key=lambda row: row["stable_key"],
    )
    stable_keys = [row["stable_key"] for row in normalised]
    if len(stable_keys) != len(set(stable_keys)):
        raise ValueError("eligible source stable keys must be unique")
    payload = b"".join((_canonical_json(row) + "\n").encode() for row in normalised)
    return _sha256_bytes(payload)


def _commit_string_set(values: Iterable[str]) -> str:
    return _sha256_bytes(("\n".join(sorted(set(values))) + "\n").encode())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_config(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("allocation config must be a JSON object")
    expected_keys = {
        "schema_id",
        "domain",
        "role_names",
        "role_weights",
        "minimum_repositories",
    }
    if set(value) != expected_keys:
        raise ValueError("allocation config fields do not match the frozen schema")
    if value["schema_id"] != ALLOCATION_SCHEMA:
        raise ValueError("unexpected allocation schema")
    if value["role_names"] != list(ROLE_NAMES):
        raise ValueError("allocation role order changed")
    weights = tuple(int(item) for item in value["role_weights"])
    minimums = tuple(int(item) for item in value["minimum_repositories"])
    if len(weights) != len(ROLE_NAMES) or any(item <= 0 for item in weights):
        raise ValueError("role_weights must contain four positive integers")
    if len(minimums) != len(ROLE_NAMES) or any(item < 1 for item in minimums):
        raise ValueError("minimum_repositories must contain four positive integers")
    if not str(value["domain"]):
        raise ValueError("allocation domain must be non-empty")
    return {
        "schema_id": ALLOCATION_SCHEMA,
        "domain": str(value["domain"]),
        "role_names": list(ROLE_NAMES),
        "role_weights": list(weights),
        "minimum_repositories": list(minimums),
    }


def _role_quotas(repository_count: int, config: Mapping[str, Any]) -> dict[str, int]:
    minimums = tuple(int(item) for item in config["minimum_repositories"])
    weights = tuple(int(item) for item in config["role_weights"])
    minimum_total = sum(minimums)
    if repository_count < minimum_total:
        raise ValueError(
            f"{repository_count} repositories cannot satisfy minimum total "
            f"{minimum_total}"
        )
    remaining = repository_count - minimum_total
    weight_total = sum(weights)
    raw = [remaining * weight / weight_total for weight in weights]
    extras = [int(value) for value in raw]
    unassigned = remaining - sum(extras)
    fractional_order = sorted(
        range(len(ROLE_NAMES)),
        key=lambda index: (-(raw[index] - extras[index]), index),
    )
    for index in fractional_order[:unassigned]:
        extras[index] += 1
    return {
        role: minimums[index] + extras[index]
        for index, role in enumerate(ROLE_NAMES)
    }


def _reconstruct_eligible_pool(
    identity_path: Path,
    *,
    dataset_by_split: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    tokenizer: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from relate.experiments.option_b_real_code import (
        OptionBConfig,
        remove_cross_split_duplicates,
    )
    from relate.experiments.option_b_selection import (
        DATASET_ID,
        REQUIRED_SPLITS,
        load_identity,
    )
    from relate.experiments.option_b_selection_resilient import (
        build_records_resilient,
    )

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
    return rows, {
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
        "eligible_pool_commitment": _source_commitment(rows),
    }


def _load_option_b_exclusions(
    selection_dir: Path,
) -> tuple[set[str], dict[str, Any]]:
    report_path = selection_dir / "option-b-canonical-row-selection-v2.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("selection_id") != "option-b-canonical-row-selection-v2":
        raise ValueError("unexpected Option B selection identity")

    repositories: set[str] = set()
    artifacts: dict[str, Any] = {}
    for split in DATASET_SPLITS:
        path = selection_dir / f"option-b-selected-{split}-v2.jsonl"
        metadata = report["artifacts"][split]["selected_manifest"]
        expected = str(metadata["sha256"])
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
        if rows != int(metadata["rows"]):
            raise ValueError(
                f"Option B selected-manifest row-count mismatch: {split}"
            )
        artifacts[split] = {"rows": rows, "file_sha256": expected}
    return repositories, {
        "selection_id": report["selection_id"],
        "repository_count": len(repositories),
        "repository_commitment": _commit_string_set(repositories),
        "artifacts": artifacts,
    }


def _recompute_allocation(
    eligible_rows: Sequence[Mapping[str, Any]],
    excluded_repositories: set[str],
    config: Mapping[str, Any],
    *,
    source_identity_commitment: str,
) -> dict[str, Any]:
    _require_hex(
        source_identity_commitment,
        lengths={64},
        field="source_identity_commitment",
    )
    rows = [_normalise_row(row) for row in eligible_rows]
    source_commitment = _source_commitment(rows)
    exclusion_commitment = _commit_string_set(excluded_repositories)

    by_repository: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded_rows = 0
    for row in rows:
        if row["repository"] in excluded_repositories:
            excluded_rows += 1
        else:
            by_repository[row["repository"]].append(row)
    if not by_repository:
        raise ValueError("no repositories remain after Option B exclusion")

    config_commitment = _sha256_json(config)
    allocation_context = _sha256_json(
        {
            "schema": ALLOCATION_SCHEMA,
            "source_identity_commitment": source_identity_commitment,
            "source_commitment": source_commitment,
            "option_b_exclusion_commitment": exclusion_commitment,
            "config_commitment": config_commitment,
        }
    )
    domain = str(config["domain"])
    ordered_repositories = sorted(
        by_repository,
        key=lambda repository: hashlib.sha256(
            f"{domain}\0{allocation_context}\0{repository}".encode()
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
            repository_rows = sorted(
                by_repository[repository],
                key=lambda row: row["stable_key"],
            )
            assignments.append(
                {
                    "role": role,
                    "repository": repository,
                    "repository_order_key": hashlib.sha256(
                        f"{domain}\0{allocation_context}\0{repository}".encode()
                    ).hexdigest(),
                    "row_count": len(repository_rows),
                    "source_splits": sorted(
                        {row["source_split"] for row in repository_rows}
                    ),
                    "repository_rows_sha256": _sha256_bytes(
                        b"".join(
                            (_canonical_json(row) + "\n").encode()
                            for row in repository_rows
                        )
                    ),
                }
            )
    if cursor != len(ordered_repositories):
        raise AssertionError("allocation quotas did not consume all repositories")

    seen: set[str] = set()
    for item in assignments:
        repository = item["repository"]
        if repository in seen:
            raise ValueError(f"repository appears more than once: {repository}")
        seen.add(repository)
        if repository in excluded_repositories:
            raise ValueError("Option B repository appears in the allocation")

    role_counts: dict[str, Any] = {}
    for role in ROLE_NAMES:
        repositories = role_repositories[role]
        role_counts[role] = {
            "repositories": len(repositories),
            "rows": sum(len(by_repository[item]) for item in repositories),
            "repository_commitment": _commit_string_set(repositories),
        }
    return {
        "source": {
            "source_identity_commitment": source_identity_commitment,
            "eligible_pool_commitment": source_commitment,
            "eligible_rows": len(rows),
            "eligible_repositories": len({row["repository"] for row in rows}),
        },
        "option_b_exclusion": {
            "repository_count": len(excluded_repositories),
            "repository_commitment": exclusion_commitment,
            "excluded_eligible_rows": excluded_rows,
        },
        "allocation_context_sha256": allocation_context,
        "config": dict(config),
        "config_sha256": config_commitment,
        "role_counts": role_counts,
        "assignments": sorted(
            assignments,
            key=lambda item: (item["role"], item["repository"]),
        ),
    }


def _require_empty_file(path: Path, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = path.read_bytes()
    if payload:
        raise ValueError(f"{label} must have zero entries before mechanism discovery")
    return _sha256_bytes(payload)


def verify_c0_allocation(
    identity_path: Path,
    option_b_selection_dir: Path,
    allocation_config_path: Path,
    result_dir: Path,
    *,
    dataset_by_split: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    tokenizer: Any | None = None,
) -> dict[str, Any]:
    """Independently reconstruct and exactly verify the canonical C0 allocation."""

    output_path = result_dir / VERIFICATION_NAME
    if output_path.exists():
        raise FileExistsError(f"independent verification already exists: {output_path}")

    config = _load_config(allocation_config_path)
    rows, reconstruction = _reconstruct_eligible_pool(
        identity_path,
        dataset_by_split=dataset_by_split,
        tokenizer=tokenizer,
    )
    excluded, option_b_selection = _load_option_b_exclusions(
        option_b_selection_dir
    )
    recomputed = _recompute_allocation(
        rows,
        excluded,
        config,
        source_identity_commitment=reconstruction["identity_sha256"],
    )

    report_path = result_dir / REPORT_NAME
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != (
        "C0_REPOSITORY_ALLOCATION_GENERATED_PENDING_INDEPENDENT_VERIFICATION"
    ):
        raise ValueError("unexpected C0 allocation status")
    for field in (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c1_rows_selected",
    ):
        if report.get(field) is not False:
            raise ValueError(f"C0 allocation field must remain false: {field}")

    allocation_artifact = report["artifacts"]["repository_allocation"]
    allocation_path = result_dir / str(allocation_artifact["path"])
    allocation_payload = allocation_path.read_bytes()
    if _sha256_bytes(allocation_payload) != allocation_artifact["file_sha256"]:
        raise ValueError("repository-allocation artifact hash mismatch")
    assignments = _read_jsonl(allocation_path)
    if len(assignments) != int(allocation_artifact["rows"]):
        raise ValueError("repository-allocation artifact row-count mismatch")

    exclusion_artifact = report["artifacts"]["option_b_excluded_repositories"]
    exclusion_path = result_dir / str(exclusion_artifact["path"])
    exclusion_payload = exclusion_path.read_bytes()
    if _sha256_bytes(exclusion_payload) != exclusion_artifact["file_sha256"]:
        raise ValueError("Option B exclusion artifact hash mismatch")
    exclusion_rows = _read_jsonl(exclusion_path)
    if len(exclusion_rows) != int(exclusion_artifact["rows"]):
        raise ValueError("Option B exclusion artifact row-count mismatch")
    published_exclusions = {str(row["repository"]) for row in exclusion_rows}

    if published_exclusions != excluded:
        raise ValueError("published Option B exclusions differ from recomputation")
    if assignments != recomputed["assignments"]:
        raise ValueError("published repository allocation differs from recomputation")
    for field in (
        "source",
        "option_b_exclusion",
        "allocation_context_sha256",
        "config",
        "config_sha256",
        "role_counts",
    ):
        if report.get(field) != recomputed[field]:
            raise ValueError(f"published allocation field differs: {field}")
    if report.get("reconstruction") != reconstruction:
        raise ValueError("published eligible-pool reconstruction differs")
    if report.get("option_b_selection") != option_b_selection:
        raise ValueError("published Option B selection verification differs")

    candidate_hash = _require_empty_file(
        result_dir / CANDIDATE_REGISTRY_NAME,
        "candidate registry",
    )
    discovery_hash = _require_empty_file(
        result_dir / DISCOVERY_LEDGER_NAME,
        "discovery ledger",
    )
    observed_roles = sorted({str(item["role"]) for item in assignments})
    if observed_roles != sorted(ROLE_NAMES):
        raise ValueError("allocation does not contain exactly the four frozen roles")

    result = {
        "verification_id": VERIFICATION_ID,
        "status": "C0_CANONICAL_REPOSITORY_ALLOCATION_INDEPENDENTLY_RECOMPUTED",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c1_rows_selected": False,
        "runner_imported": RUNNER_IMPORTED,
        "checks": {
            "eligible_pool_recomputed": True,
            "option_b_exclusion_recomputed": True,
            "allocation_exactly_equal": True,
            "role_counts_exactly_equal": True,
            "pairwise_role_disjointness": True,
            "option_b_repositories_excluded": True,
            "c1_reserve_undivided": True,
            "candidate_registry_empty": True,
            "discovery_ledger_empty": True,
        },
        "counts": {
            "eligible_rows": reconstruction["eligible_rows"],
            "eligible_repositories": reconstruction["eligible_repositories"],
            "option_b_excluded_repositories": len(excluded),
            "allocated_repositories": len(assignments),
            "candidate_registry_entries": 0,
            "discovery_ledger_entries": 0,
        },
        "role_counts": recomputed["role_counts"],
        "commitments": {
            "identity_file_sha256": reconstruction["identity_sha256"],
            "eligible_pool_sha256": reconstruction["eligible_pool_commitment"],
            "option_b_repository_set_sha256": option_b_selection[
                "repository_commitment"
            ],
            "allocation_context_sha256": recomputed[
                "allocation_context_sha256"
            ],
            "config_sha256": recomputed["config_sha256"],
        },
        "artifacts": {
            "source_report": {
                "path": REPORT_NAME,
                "file_sha256": _sha256_bytes(report_path.read_bytes()),
            },
            "repository_allocation": {
                "path": ALLOCATION_NAME,
                "rows": len(assignments),
                "file_sha256": _sha256_bytes(allocation_payload),
            },
            "option_b_excluded_repositories": {
                "path": EXCLUSION_NAME,
                "rows": len(exclusion_rows),
                "file_sha256": _sha256_bytes(exclusion_payload),
            },
            "allocation_config": {
                "path": str(allocation_config_path).replace("\\", "/"),
                "file_sha256": _sha256_bytes(
                    allocation_config_path.read_bytes()
                ),
            },
            "candidate_registry": {
                "path": CANDIDATE_REGISTRY_NAME,
                "entries": 0,
                "file_sha256": candidate_hash,
            },
            "discovery_ledger": {
                "path": DISCOVERY_LEDGER_NAME,
                "entries": 0,
                "file_sha256": discovery_hash,
            },
        },
        "next_allowed_action": "CANONICAL_C0_ALLOCATION_PUBLICATION_REVIEW",
        "prohibited_actions": [
            "propagation mechanism evaluation before allocation review",
            "candidate registration before allocation review",
            "C0 iteration or selection metrics",
            "C1 calibration row selection",
            "C1 test row selection",
            "Option C scientific decision",
        ],
    }
    _write_durable(
        output_path,
        (json.dumps(result, indent=2, sort_keys=True) + "\n").encode(),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--option-b-selection-dir", type=Path, required=True)
    parser.add_argument("--allocation-config", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path, required=True)
    args = parser.parse_args()
    result = verify_c0_allocation(
        args.identity,
        args.option_b_selection_dir,
        args.allocation_config,
        args.result_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

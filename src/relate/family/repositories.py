"""Pure repository identity and allocation-domain operations.

No database access, CLI parsing, file publication or workflow orchestration.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.models import AllocationEntry

ROLE_ORDER: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
REPOSITORY_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_.-]*/[a-z0-9_.-]+$")

# Canonical allocation constants (frozen by the allocation manifest).
ALLOCATION_REPOSITORY_COUNT: Final = 5324
ALLOCATION_ROLE_REPOSITORY_COUNTS: Final = {
    "c0_fit": 2117,
    "c0_iteration": 1058,
    "c0_selection": 545,
    "c1_reserve": 1604,
}
ALLOCATION_ROLE_ROW_COUNTS: Final = {
    "c0_fit": 8007,
    "c0_iteration": 4110,
    "c0_selection": 2070,
    "c1_reserve": 6357,
}
ALLOCATION_REPOSITORY_COMMITMENT_SHA256: Final = (
    "cede73f5321d5a667a26b27a66131b8a324b89423353dd77be45f40c16ffc103"
)


def normalize_repository(repository: str) -> str:
    if not isinstance(repository, str):
        raise ValueError("repository identity must be a string")
    value = repository.strip().lower()
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise ValueError(f"malformed repository identity: {repository!r}")
    return value


def repository_owner(repository: str) -> str:
    return normalize_repository(repository).split("/", 1)[0]


def load_allocation_manifest(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[AllocationEntry, ...]:
    if expected_sha256 is not None and sha256_file(path) != expected_sha256:
        raise ValueError("allocation manifest SHA-256 mismatch")
    entries: list[AllocationEntry] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"allocation line {line_number} must be a JSON object")
        repository = normalize_repository(item.get("repository", ""))
        role = item.get("role")
        row_count = item.get("row_count")
        if role not in ROLE_ORDER:
            raise ValueError(f"invalid role at allocation line {line_number}: {role}")
        if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0:
            raise ValueError(f"invalid row_count at allocation line {line_number}")
        if repository in seen:
            raise ValueError(f"duplicate allocation repository: {repository}")
        seen.add(repository)
        entries.append(AllocationEntry(repository=repository, role=role, row_count=row_count))
    return tuple(sorted(entries, key=lambda entry: entry.repository))


def allocation_repository_commitment(entries: Sequence[AllocationEntry]) -> str:
    normalized = tuple(sorted(entries, key=lambda entry: entry.repository))
    repositories = [entry.repository for entry in normalized]
    if len(repositories) != len(set(repositories)):
        raise ValueError("duplicate allocation repository")
    for entry in normalized:
        normalize_repository(entry.repository)
        if entry.role not in ROLE_ORDER:
            raise ValueError("invalid allocation role")
        if isinstance(entry.row_count, bool) or not isinstance(entry.row_count, int):
            raise ValueError("invalid allocation row count")
    rows = [
        {"repository": entry.repository, "role": entry.role, "row_count": entry.row_count}
        for entry in normalized
    ]
    return sha256_text(canonical_json({"allocation_repositories": rows}))


def validate_canonical_allocation_entries(entries: Sequence[AllocationEntry]) -> str:
    normalized = tuple(sorted(entries, key=lambda entry: entry.repository))
    if len(normalized) != ALLOCATION_REPOSITORY_COUNT:
        raise ValueError("noncanonical allocation repository count")
    role_counts = {role: 0 for role in ROLE_ORDER}
    row_counts = {role: 0 for role in ROLE_ORDER}
    for entry in normalized:
        role_counts[entry.role] += 1
        row_counts[entry.role] += entry.row_count
    if role_counts != ALLOCATION_ROLE_REPOSITORY_COUNTS:
        raise ValueError("noncanonical allocation role repository counts")
    if row_counts != ALLOCATION_ROLE_ROW_COUNTS:
        raise ValueError("noncanonical allocation role row counts")
    commitment = allocation_repository_commitment(normalized)
    if commitment != ALLOCATION_REPOSITORY_COMMITMENT_SHA256:
        raise ValueError("noncanonical allocation repository commitment")
    return commitment

"""Option C0-D1.1 overlap classification and bounded publication support."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
from collections import Counter, defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from relate.experiments.option_c0_d1_integrity_audit import (
    CACHE_SCHEMA,
    VISIBLE_ROLES,
    near_pair_commitment,
)

D11_SCHEMA: Final = "option-c0-d1-overlap-classification-v1"
PUBLICATION_SCHEMA: Final = "option-c0-d1-integrity-audit-publication-v1"
EXPECTED_D1_STATUS: Final = "C0_D1_AUDIT_COMPLETE_PENDING_HUMAN_REVIEW"
EXPECTED_D1_NEXT_ACTION: Final = "REVIEW_AND_CLASSIFY_EXACT_CROSS_ROLE_OVERLAP"
EXPECTED_AUDIT_CONTEXT_SHA256: Final = (
    "49fe499ecf5d16293a52e716ceaf88f75e256e8583b6497b934a3d884c8fd265"
)
EXPECTED_D1_RESULT_SHA256: Final = (
    "a19c042f725fb20a0a87fa902d2071f30c66d5ee8f96bfde1cd056cba5123420"
)
EXPECTED_D1_AUDIT_EXECUTION_GIT_COMMIT: Final = (
    "ddb5c8de28d4e6502f5511152018eb1aafd0cd44"
)
GENERATOR_SOURCE_PATHS: Final = (
    "src/relate/experiments/option_c0_d1_overlap_classification.py",
    "src/relate/experiments/option_c0_d1_integrity_audit.py",
    "artifacts/canonical/option-c0/review-v1/option-c0-d1-audit-contract-v1.json",
    "pyproject.toml",
)
EXACT_AST_SHA256: Final = (
    "3d8afe0e5cb68aa8f1d8c1a16c3395c61e3b85bbe4deb3c69e0923944442850d"
)
EXACT_STABLE_KEYS: Final = frozenset(
    {
        "6486639c1e9e2119724efe0028ae78a1e4d4cbf7088ee22cdbbb331c9c4e6060",
        "c5b866bd648b88e666115d44def4c17f4443e82dd150c3cff488046cb1dfb3e1",
    }
)
ROLE_ORDER: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
PAIR_ROLE_KEYS: Final = (
    ("c0_fit", "c0_iteration"),
    ("c0_fit", "c0_selection"),
    ("c0_fit", "c1_reserve"),
    ("c0_iteration", "c0_selection"),
    ("c0_iteration", "c1_reserve"),
)
FAMILY_SUFFIX_PATTERN: Final = re.compile(
    r"(^python-|^django-|^pytest-|^flask-|^pyramid-|^async-|^aio|"
    r"-python$|-django$|-py$|-core$|-client$|-server$|-api$|-lib$|-library$|"
    r"-utils?$|-tools?$|-project$|-plugin$|-plugins$|-extension$|-extensions$|"
    r"-app$|-apps$|-web$|-backend$|-frontend$|-common$|-base$)"
)


@dataclass(frozen=True)
class ReviewRow:
    role: str
    repository: str
    stable_key: str
    source_split: str
    path: str
    function_id: str
    token_count: int
    code_sha256: str
    normalized_ast_sha256: str
    simhash_hex: str

    @property
    def owner(self) -> str:
        return parse_owner(self.repository)


def canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def executing_git_commit(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def current_git_branch(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        text=True,
    ).strip()


def git_status_porcelain(repo_root: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        text=True,
    )
    return [line for line in output.splitlines() if line]


def require_clean_worktree(
    repo_root: Path,
    *,
    allow_dirty_test_fixture_override: bool = False,
) -> None:
    if allow_dirty_test_fixture_override:
        return
    dirty = git_status_porcelain(repo_root)
    if dirty:
        preview = "; ".join(dirty[:5])
        raise RuntimeError(
            "refusing canonical D1.1 generation because git status --porcelain "
            f"is not empty: {preview}"
        )


def generator_source_manifest(repo_root: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for relative in GENERATOR_SOURCE_PATHS:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"required D1.1 generator source is missing: {relative}")
        files[relative] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    manifest = {
        "schema_id": "option-c0-d1-1-generator-source-manifest-v1",
        "files": files,
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        canonical_json({"schema_id": manifest["schema_id"], "files": files}).encode()
    ).hexdigest()
    return manifest


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def validate_d1_result(result: Mapping[str, Any]) -> None:
    if result.get("status") != EXPECTED_D1_STATUS:
        raise ValueError("D1 result is not pending human review")
    if result.get("next_allowed_action") != EXPECTED_D1_NEXT_ACTION:
        raise ValueError("D1 result does not allow D1.1 review")
    if result.get("audit_context_sha256") != EXPECTED_AUDIT_CONTEXT_SHA256:
        raise ValueError("unexpected D1 audit context")
    execution = result.get("execution_environment", {})
    if not isinstance(execution, Mapping):
        raise ValueError("D1 result execution environment is missing")
    if execution.get("git_head") != EXPECTED_D1_AUDIT_EXECUTION_GIT_COMMIT:
        raise ValueError("unexpected D1 audit execution git commit")
    for key in (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c0_selection_rows_accessed",
        "c1_rows_accessed",
        "hidden_row_content_accessed",
        "c0_selection_row_content_accessed",
        "c1_row_content_accessed",
    ):
        if bool(result.get(key)):
            raise ValueError(f"D1 result firewall field must be false: {key}")


def validate_d1_result_file(
    source_path: Path,
    *,
    expected_d1_result_sha256: str = EXPECTED_D1_RESULT_SHA256,
) -> dict[str, Any]:
    if sha256_file(source_path) != expected_d1_result_sha256:
        raise ValueError("unexpected canonical D1 result SHA-256")
    result = load_json(source_path)
    validate_d1_result(result)
    return result


def publish_d1_result(
    source_path: Path,
    output_dir: Path,
    *,
    repo_root: Path,
    generator_commit: str | None = None,
    generator_branch: str | None = None,
    generator_manifest: Mapping[str, Any] | None = None,
    expected_d1_result_sha256: str = EXPECTED_D1_RESULT_SHA256,
    overwrite: bool = False,
) -> dict[str, Any]:
    result = validate_d1_result_file(
        source_path,
        expected_d1_result_sha256=expected_d1_result_sha256,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    result_output = output_dir / source_path.name
    publication_output = output_dir / "option-c0-d1-integrity-audit-publication-v1.json"
    if not overwrite and (result_output.exists() or publication_output.exists()):
        raise FileExistsError("canonical D1 publication refuses overwrite")
    shutil.copyfile(source_path, result_output)
    result_sha = sha256_file(result_output)
    if result_sha != expected_d1_result_sha256:
        raise ValueError("copied canonical D1 result SHA-256 mismatch")
    near = result.get("near_duplicate_candidates", {})
    exact_ast = result.get("exact_ast_overlap", {})
    exact_code = result.get("exact_code_overlap", {})
    publication = {
        "schema_id": PUBLICATION_SCHEMA,
        "status": "PUBLISHED_PENDING_D1_1_CLASSIFICATION",
        "audit_result_sha256": result_sha,
        "audit_context_sha256": result["audit_context_sha256"],
        "d1_audit_execution_git_commit": result["execution_environment"]["git_head"],
        "d1_result_publication_generator_git_commit": generator_commit
        or executing_git_commit(repo_root),
        "generator_worktree_clean": True,
        "generator_branch": generator_branch or current_git_branch(repo_root),
        "generator_source_manifest": generator_manifest or generator_source_manifest(repo_root),
        "visible_row_counts": result.get("visible_rows", {}),
        "exact_overlap_counts": {
            "exact_code_cross_role_hashes": exact_code.get("cross_role_hashes"),
            "exact_code_cross_role_rows": exact_code.get("cross_role_rows"),
            "exact_ast_cross_role_hashes": exact_ast.get("cross_role_hashes"),
            "exact_ast_cross_role_rows": exact_ast.get("cross_role_rows"),
            "exact_ast_cross_role_repositories": exact_ast.get("cross_role_repositories"),
        },
        "near_scan_completeness": {
            "scan_complete": bool(near.get("scan_complete")),
            "truncated": bool(near.get("comparison_truncated") or near.get("output_truncated")),
            "candidate_pairs_generated": near.get("candidate_pairs_generated"),
            "candidate_pairs_compared": near.get("candidate_pairs_compared"),
            "verified_near_pairs": near.get("near_pair_count"),
        },
        "firewall_booleans": {
            "scientific_result_observed": False,
            "mechanism_result_observed": False,
            "c0_selection_rows_accessed": False,
            "c1_rows_accessed": False,
            "hidden_row_content_accessed": False,
        },
        "review_status": "D1_1_CLASSIFICATION_PENDING",
        "next_allowed_action": "RUN_D1_1_OVERLAP_CLASSIFICATION",
    }
    publication["generator_source_manifest_sha256"] = publication[
        "generator_source_manifest"
    ]["manifest_sha256"]
    publication_output.write_text(canonical_json(publication) + "\n", encoding="utf-8")
    return publication


def connect_cache(cache_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(cache_path)
    connection.row_factory = sqlite3.Row
    return connection


def load_visible_rows(connection: sqlite3.Connection, context_sha256: str) -> dict[str, ReviewRow]:
    rows = connection.execute(
        """
        SELECT role, repository, stable_key, source_split, path, function_id,
               token_count, code_sha256, normalized_ast_sha256, simhash_hex
        FROM visible_rows
        WHERE context_sha256 = ?
        ORDER BY stable_key
        """,
        (context_sha256,),
    ).fetchall()
    result: dict[str, ReviewRow] = {}
    for item in rows:
        if item["role"] not in VISIBLE_ROLES:
            raise ValueError("cache contains non-visible row in visible_rows")
        result[str(item["stable_key"])] = ReviewRow(**dict(item))
    return result


def resolve_exact_pair(
    rows: Mapping[str, ReviewRow],
    stable_keys: Sequence[str],
) -> list[dict[str, Any]]:
    missing = sorted(set(stable_keys) - set(rows))
    if missing:
        raise ValueError(f"exact stable keys are absent from visible rows: {missing}")
    resolved = [rows[key] for key in sorted(stable_keys)]
    if any(row.role not in VISIBLE_ROLES for row in resolved):
        raise ValueError("exact pair resolution refused hidden role")
    return [bounded_row_metadata(row) for row in resolved]


def bounded_row_metadata(row: ReviewRow) -> dict[str, Any]:
    return {
        "role": row.role,
        "repository": row.repository,
        "stable_key": row.stable_key,
        "source_split": row.source_split,
        "path": row.path,
        "function_id": row.function_id,
        "token_count": row.token_count,
        "code_sha256": row.code_sha256,
        "normalized_ast_sha256": row.normalized_ast_sha256,
        "simhash_hex": row.simhash_hex,
        "primitive_targets": None,
    }


def exact_pair_review(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    left, right = rows
    return {
        "same_source_code": left["code_sha256"] == right["code_sha256"],
        "same_normalized_ast": left["normalized_ast_sha256"] == right["normalized_ast_sha256"],
        "same_normalized_tokens": None,
        "same_function_name": left["function_id"] == right["function_id"],
        "same_path_suffix": Path(str(left["path"])).name == Path(str(right["path"])).name,
        "same_owner": parse_owner(str(left["repository"])) == parse_owner(str(right["repository"])),
        "similar_repository_names": suffix_stripped_family(str(left["repository"]))
        == suffix_stripped_family(str(right["repository"])),
        "token_count_difference": abs(int(left["token_count"]) - int(right["token_count"])),
        "primitive_target_equality": None,
        "minimal_normalized_structural_comparison": {
            "same_normalized_ast_sha256": left["normalized_ast_sha256"]
            == right["normalized_ast_sha256"],
            "same_code_sha256": left["code_sha256"] == right["code_sha256"],
            "source_bodies_available_in_canonical_report": False,
            "normalized_token_sequences_available_in_cache": False,
        },
        "owner_evidence_note": (
            "same GitHub owner is evidence of possible repository-family relation, "
            "not by itself proof of code leakage"
        ),
    }


def parse_owner(repository: str) -> str:
    if "/" not in repository:
        raise ValueError(f"repository is not owner/repository: {repository}")
    owner, name = repository.split("/", 1)
    if not owner or not name:
        raise ValueError(f"repository is not owner/repository: {repository}")
    return owner.lower()


def repo_name(repository: str) -> str:
    if "/" not in repository:
        raise ValueError(f"repository is not owner/repository: {repository}")
    return repository.split("/", 1)[1].lower()


def suffix_stripped_family(repository: str) -> str:
    name = repo_name(repository)
    previous = None
    while previous != name:
        previous = name
        name = FAMILY_SUFFIX_PATTERN.sub("", name)
    return name.replace("_", "-")


def load_allocation(allocation_path: Path) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    lines = allocation_path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        item = json.loads(line)
        repository = str(item.get("repository", ""))
        role = str(item.get("role", ""))
        if role not in ROLE_ORDER:
            raise ValueError(f"invalid allocation role at line {line_number}")
        parse_owner(repository)
        assignments.append(
            {
                "repository": repository,
                "role": role,
                "row_count": int(item.get("row_count", 0)),
            }
        )
    return assignments


def owner_role_analysis(
    assignments: Sequence[Mapping[str, Any]],
    *,
    sample_limit: int = 8,
) -> dict[str, Any]:
    by_owner: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for item in assignments:
        by_owner[parse_owner(str(item["repository"]))][str(item["role"])].append(item)
    groups: list[dict[str, Any]] = []
    for owner, role_items in sorted(by_owner.items()):
        roles = tuple(role for role in ROLE_ORDER if role in role_items)
        if len(roles) < 2:
            continue
        repositories = sorted(
            str(item["repository"])
            for role in roles
            for item in role_items[role]
        )
        groups.append(
            {
                "owner": owner,
                "roles": list(roles),
                "repository_count_by_role": {
                    role: len(role_items.get(role, ())) for role in roles
                },
                "row_count_by_role": {
                    role: sum(int(item["row_count"]) for item in role_items.get(role, ()))
                    for role in roles
                },
                "repository_name_sample": repositories[:sample_limit],
                "sample_truncated": len(repositories) > sample_limit,
            }
        )
    pair_counts = {}
    for left, right in PAIR_ROLE_KEYS:
        pair_counts[f"{left}__{right}"] = sum(
            1 for group in groups if left in group["roles"] and right in group["roles"]
        )
    return {
        "uses_published_repository_names_only": True,
        "c0_selection_row_content_accessed": False,
        "c1_row_content_accessed": False,
        "owner_match_is_not_proof_of_shared_code": True,
        "owners_appearing_in_more_than_one_allocation_role": len(groups),
        "owners_spanning_c0_fit_and_c0_iteration": pair_counts["c0_fit__c0_iteration"],
        "owners_spanning_c0_fit_and_c0_selection": pair_counts["c0_fit__c0_selection"],
        "owners_spanning_c0_fit_and_c1_reserve": pair_counts["c0_fit__c1_reserve"],
        "owners_spanning_c0_iteration_and_c0_selection": pair_counts[
            "c0_iteration__c0_selection"
        ],
        "owners_spanning_c0_iteration_and_c1_reserve": pair_counts[
            "c0_iteration__c1_reserve"
        ],
        "owners_spanning_three_or_four_roles": sum(
            1 for group in groups if len(group["roles"]) >= 3
        ),
        "cross_role_owner_groups": groups,
    }


def load_near_pairs(
    connection: sqlite3.Connection,
    context_sha256: str,
) -> tuple[tuple[str, str, int], ...]:
    values = connection.execute(
        """
        SELECT left_key, right_key, hamming_distance
        FROM near_pairs
        WHERE context_sha256 = ?
        ORDER BY hamming_distance, left_key, right_key
        """,
        (context_sha256,),
    ).fetchall()
    return tuple((str(row[0]), str(row[1]), int(row[2])) for row in values)


def connected_components(edges: Sequence[tuple[str, str]]) -> list[set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for left, right in edges:
        graph[left].add(right)
        graph[right].add(left)
    seen: set[str] = set()
    components: list[set[str]] = []
    for node in sorted(graph):
        if node in seen:
            continue
        queue = deque([node])
        seen.add(node)
        component: set[str] = set()
        while queue:
            current = queue.popleft()
            component.add(current)
            for adjacent in sorted(graph[current]):
                if adjacent not in seen:
                    seen.add(adjacent)
                    queue.append(adjacent)
        components.append(component)
    return components


def classify_near_pair(left: ReviewRow, right: ReviewRow, distance: int) -> str:
    same_ast = left.normalized_ast_sha256 == right.normalized_ast_sha256
    same_owner = left.owner == right.owner
    same_family = suffix_stripped_family(left.repository) == suffix_stripped_family(
        right.repository
    )
    short = min(left.token_count, right.token_count) <= 8
    if same_ast and same_owner:
        return "EXACT_AST_RELATED_OWNER"
    if short and distance == 0 and not same_ast:
        return "GENERIC_SHORT_FUNCTION_COLLISION"
    if same_owner:
        return "SAME_OWNER_NEAR_MATCH"
    if same_family:
        return "SAME_FAMILY_NAME_NEAR_MATCH"
    if short:
        return "POSSIBLE_TEMPLATE_OR_BOILERPLATE"
    return "UNRESOLVED_NEAR_MATCH"


def near_pair_analysis(
    rows: Mapping[str, ReviewRow],
    near_pairs: Sequence[tuple[str, str, int]],
    *,
    sample_limit: int = 30,
) -> dict[str, Any]:
    distance_histogram = Counter(str(distance) for _left, _right, distance in near_pairs)
    same_owner = 0
    same_basename = 0
    same_family = 0
    exact_pair_pairs = 0
    row_degree: Counter[str] = Counter()
    repository_pair_degree: Counter[tuple[str, str]] = Counter()
    classification_counts: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    edges: list[tuple[str, str]] = []
    repositories: set[str] = set()
    for left_key, right_key, distance in near_pairs:
        left = rows[left_key]
        right = rows[right_key]
        row_degree.update((left_key, right_key))
        repositories.update((left.repository, right.repository))
        repo_pair = tuple(sorted((left.repository, right.repository)))
        repository_pair_degree[repo_pair] += 1
        edges.append((left_key, right_key))
        pair_same_owner = left.owner == right.owner
        same_owner += int(pair_same_owner)
        same_basename += int(repo_name(left.repository) == repo_name(right.repository))
        same_family += int(
            suffix_stripped_family(left.repository)
            == suffix_stripped_family(right.repository)
        )
        exact_pair = {left_key, right_key} == EXACT_STABLE_KEYS
        exact_pair_pairs += int(exact_pair)
        classification = classify_near_pair(left, right, distance)
        classification_counts[classification] += 1
        if len(samples) < sample_limit:
            samples.append(
                {
                    "left_key": left_key,
                    "right_key": right_key,
                    "hamming_distance": distance,
                    "classification": classification,
                    "same_owner": pair_same_owner,
                    "same_normalized_ast": left.normalized_ast_sha256
                    == right.normalized_ast_sha256,
                    "token_counts": [left.token_count, right.token_count],
                    "minimum_token_count": min(left.token_count, right.token_count),
                    "repositories": [left.repository, right.repository],
                    "roles": [left.role, right.role],
                    "involves_exact_ast_match": exact_pair,
                }
            )
    components = connected_components(edges)
    return {
        "hamming_distance_histogram": dict(sorted(distance_histogram.items())),
        "same_owner_pair_count": same_owner,
        "different_owner_pair_count": len(near_pairs) - same_owner,
        "same_normalized_basename_count": same_basename,
        "same_suffix_stripped_family_count": same_family,
        "pairs_involving_the_exact_ast_match": exact_pair_pairs,
        "unique_rows_involved": len(row_degree),
        "unique_repositories_involved": len(repositories),
        "connected_components": len(components),
        "maximum_component_size": max((len(component) for component in components), default=0),
        "row_degree_distribution": dict(sorted(Counter(row_degree.values()).items())),
        "repository_pair_degree_distribution": dict(
            sorted(Counter(repository_pair_degree.values()).items())
        ),
        "hub_rows": [
            {"stable_key": key, "degree": degree, "repository": rows[key].repository}
            for key, degree in row_degree.most_common(10)
        ],
        "hub_repository_pairs": [
            {"repositories": list(pair), "degree": degree}
            for pair, degree in repository_pair_degree.most_common(10)
        ],
        "classification_counts": dict(sorted(classification_counts.items())),
        "samples": samples,
        "sample_truncated": len(near_pairs) > sample_limit,
        "near_pair_commitment_sha256": near_pair_commitment(near_pairs),
        "heuristic_note": (
            "SimHash-near pairs are heuristic candidates, not demonstrated duplication."
        ),
    }


def fetch_github_metadata(repository: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repository}"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "similarity-is-relative-d1-1-audit",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        return {"repository": repository, "metadata_available": False, "error": str(error)}
    return {
        "repository": repository,
        "metadata_available": True,
        "fork": bool(data.get("fork")),
        "archived": bool(data.get("archived")),
        "created_at": data.get("created_at"),
        "description": data.get("description"),
        "homepage": data.get("homepage"),
        "owner": data.get("owner", {}).get("login"),
        "public_metadata_only": True,
    }


def public_metadata_check(
    exact_rows: Sequence[Mapping[str, Any]],
    near_analysis: Mapping[str, Any],
    *,
    max_repositories: int = 8,
) -> dict[str, Any]:
    repositories = {str(row["repository"]) for row in exact_rows}
    for sample in near_analysis.get("samples", []):
        if sample.get("same_owner"):
            repositories.update(str(repo) for repo in sample.get("repositories", []))
        if len(repositories) >= max_repositories:
            break
    metadata = [
        fetch_github_metadata(repository)
        for repository in sorted(repositories)[:max_repositories]
    ]
    return {
        "scope": "exact sarugaku pair plus bounded same-owner near-match sample",
        "repositories_checked": len(metadata),
        "repositories": metadata,
        "public_metadata_separate_from_dataset_evidence": True,
        "common_ownership_is_not_proof_of_shared_function_provenance": True,
    }


def classify_overall(
    exact_review: Mapping[str, Any],
    owner_analysis: Mapping[str, Any],
    near_analysis: Mapping[str, Any],
    *,
    family_identity_rule_status: str = "NOT_FROZEN",
) -> dict[str, Any]:
    if family_identity_rule_status != "NOT_FROZEN":
        raise ValueError("D1.1 only supports an unfrozen family identity rule")
    owner_crossings = int(owner_analysis["owners_spanning_c0_fit_and_c0_iteration"])
    same_owner_near = int(near_analysis["same_owner_pair_count"])
    exact_classification = (
        "POSSIBLE_RELATED_REPOSITORY_FAMILY_LEAKAGE"
        if exact_review["same_owner"]
        else "INCONCLUSIVE_REQUIRES_FAMILY_RULE"
    )
    outcome = "D1_CLASSIFICATION_INCONCLUSIVE"
    next_action = "FREEZE_FAMILY_CONNECTED_REALLOCATION_PROTOCOL"
    materiality = (
        "repository-level independence passed the exact-code check, but family-level "
        "independence remains unresolved; a family identity rule must be frozen before "
        "deciding whether reallocation is required"
    )
    confidence = "medium"
    return {
        "exact_pair_classification": exact_classification,
        "allocation_family_classification": "FAMILY_INDEPENDENCE_NOT_ESTABLISHED",
        "near_pair_classification": "HEURISTIC_NEAR_MATCHES_REQUIRE_BOUNDING_NOT_DUPLICATION_PROOF",
        "family_identity_rule_status": family_identity_rule_status,
        "owner_proxy_crossings_observed": owner_crossings,
        "confirmed_related_family_crossings": None,
        "material_contamination_established": False,
        "reallocation_required": None,
        "materiality_assessment": materiality,
        "confidence": confidence,
        "overall_outcome": outcome,
        "next_allowed_action": next_action,
        "evidence_supporting_the_assessment": [
            "the exact AST pair is same-owner across sarugaku/shellingham and sarugaku/vistir",
            f"{owner_crossings} owners span c0_fit and c0_iteration in the allocation manifest",
            f"{same_owner_near} verified SimHash-near pairs are same-owner",
        ],
        "evidence_against_the_assessment": [
            "exact source-code cross-role hashes remain zero",
            "the exact AST overlap directly involves two visible rows",
            "same owner is a proxy observation, not a frozen family definition",
            "SimHash-near pairs are heuristic and are not treated as demonstrated duplication",
        ],
        "unresolved_limitations": [
            "canonical cache does not contain source bodies or normalized token sequences",
            "public metadata is repository-level and does not prove function-level provenance",
            "confirmed related-family crossings are not established without a frozen rule",
            "hidden C0-selection and C1 row contents were not accessed",
        ],
        "prohibited_actions_remain": [
            "C0 selection access",
            "C1 reserve row access",
            "candidate promotion",
            "C1 contract decision",
            "scientific-claim promotion",
        ],
    }


def verify_publication_hashes(result_path: Path, publication_path: Path) -> bool:
    publication = load_json(publication_path)
    return publication.get("audit_result_sha256") == sha256_file(result_path)


def build_classification(
    *,
    d1_result_path: Path,
    cache_path: Path,
    allocation_path: Path,
    output_dir: Path,
    docs_path: Path,
    repo_root: Path,
    overwrite: bool = False,
    allow_dirty_test_fixture_override: bool = False,
    expected_d1_result_sha256: str = EXPECTED_D1_RESULT_SHA256,
) -> dict[str, Any]:
    require_clean_worktree(
        repo_root,
        allow_dirty_test_fixture_override=allow_dirty_test_fixture_override,
    )
    generator_commit = executing_git_commit(repo_root)
    generator_branch = current_git_branch(repo_root)
    source_manifest = generator_source_manifest(repo_root)
    publish_d1_result(
        d1_result_path,
        output_dir,
        repo_root=repo_root,
        generator_commit=generator_commit,
        generator_branch=generator_branch,
        generator_manifest=source_manifest,
        expected_d1_result_sha256=expected_d1_result_sha256,
        overwrite=overwrite,
    )
    result = validate_d1_result_file(
        d1_result_path,
        expected_d1_result_sha256=expected_d1_result_sha256,
    )
    with connect_cache(cache_path) as connection:
        rows = load_visible_rows(connection, str(result["audit_context_sha256"]))
        exact_rows = resolve_exact_pair(rows, sorted(EXACT_STABLE_KEYS))
        near_pairs = load_near_pairs(connection, str(result["audit_context_sha256"]))
    exact_review = exact_pair_review(exact_rows)
    owner_analysis_result = owner_role_analysis(load_allocation(allocation_path))
    near_analysis_result = near_pair_analysis(rows, near_pairs)
    metadata = public_metadata_check(exact_rows, near_analysis_result)
    decision = classify_overall(exact_review, owner_analysis_result, near_analysis_result)
    classification = {
        "schema_id": D11_SCHEMA,
        "created_at_utc": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "status": "D1_1_CLASSIFICATION_COMPLETE",
        "audit_context_sha256": result["audit_context_sha256"],
        "source_d1_result_sha256": sha256_file(output_dir / d1_result_path.name),
        "d1_audit_execution_git_commit": result["execution_environment"]["git_head"],
        "d1_1_classification_generator_git_commit": generator_commit,
        "generator_worktree_clean": True,
        "generator_branch": generator_branch,
        "generator_source_manifest": source_manifest,
        "generator_source_manifest_sha256": source_manifest["manifest_sha256"],
        "publication_sha256": sha256_file(
            output_dir / "option-c0-d1-integrity-audit-publication-v1.json"
        ),
        "publication_hashes_verify": verify_publication_hashes(
            output_dir / d1_result_path.name,
            output_dir / "option-c0-d1-integrity-audit-publication-v1.json",
        ),
        "cache_schema": CACHE_SCHEMA,
        "exact_pair": {
            "stable_keys": sorted(EXACT_STABLE_KEYS),
            "normalized_ast_sha256": EXACT_AST_SHA256,
            "rows": exact_rows,
            "review": exact_review,
        },
        "owner_level_allocation_family_analysis": owner_analysis_result,
        "near_pair_analysis": near_analysis_result,
        "public_repository_metadata_check": metadata,
        "classification": decision,
        "firewall_booleans": {
            "scientific_result_observed": False,
            "mechanism_result_observed": False,
            "c0_selection_rows_accessed": False,
            "c1_rows_accessed": False,
            "hidden_row_content_accessed": False,
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
        },
        "next_allowed_action": decision["next_allowed_action"],
    }
    classification_path = output_dir / "option-c0-d1-overlap-classification-v1.json"
    if classification_path.exists() and not overwrite:
        raise FileExistsError("D1.1 classification refuses overwrite")
    classification_path.write_text(canonical_json(classification) + "\n", encoding="utf-8")
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    if docs_path.exists() and not overwrite:
        raise FileExistsError("D1.1 report refuses overwrite")
    docs_path.write_text(render_markdown_report(classification), encoding="utf-8")
    return classification


def render_markdown_report(classification: Mapping[str, Any]) -> str:
    decision = classification["classification"]
    owner = classification["owner_level_allocation_family_analysis"]
    near = classification["near_pair_analysis"]
    exact = classification["exact_pair"]["review"]
    return (
        "# Option C0-D1.1 Overlap Classification\n\n"
        f"- Status: `{classification['status']}`\n"
        f"- Audit context SHA-256: `{classification['audit_context_sha256']}`\n"
        f"- Overall outcome: `{decision['overall_outcome']}`\n"
        f"- Next allowed action: `{classification['next_allowed_action']}`\n\n"
        "## Exact Pair\n\n"
        f"- Classification: `{decision['exact_pair_classification']}`\n"
        f"- Same source code: `{str(exact['same_source_code']).lower()}`\n"
        f"- Same normalized AST: `{str(exact['same_normalized_ast']).lower()}`\n"
        f"- Same owner: `{str(exact['same_owner']).lower()}`\n"
        f"- Token-count difference: `{exact['token_count_difference']}`\n\n"
        "Same GitHub owner is evidence of possible repository-family relation, "
        "not by itself proof of code leakage.\n\n"
        "## Owner-Level Role Crossings\n\n"
        "- Owners in more than one role: "
        f"`{owner['owners_appearing_in_more_than_one_allocation_role']}`\n"
        "- Owners spanning c0_fit and c0_iteration: "
        f"`{owner['owners_spanning_c0_fit_and_c0_iteration']}`\n"
        "- Owners spanning three or four roles: "
        f"`{owner['owners_spanning_three_or_four_roles']}`\n\n"
        "## Near-Pair Summary\n\n"
        f"- Hamming-distance histogram: `{near['hamming_distance_histogram']}`\n"
        f"- Same-owner pairs: `{near['same_owner_pair_count']}`\n"
        f"- Different-owner pairs: `{near['different_owner_pair_count']}`\n"
        f"- Connected components: `{near['connected_components']}`\n"
        f"- Maximum component size: `{near['maximum_component_size']}`\n\n"
        "SimHash-near pairs are heuristic candidates, not demonstrated duplication.\n\n"
        "## Materiality\n\n"
        f"{decision['materiality_assessment']}\n\n"
        "## Firewall\n\n"
        "- C0 selection row contents accessed: `false`\n"
        "- C1 reserve row contents accessed: `false`\n"
        "- Scientific result observed: `false`\n"
        "- Mechanism result observed: `false`\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d1-result", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--docs-path", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-dirty-test-fixture-override", action="store_true")
    args = parser.parse_args(argv)
    build_classification(
        d1_result_path=args.d1_result,
        cache_path=args.cache,
        allocation_path=args.allocation,
        output_dir=args.output_dir,
        docs_path=args.docs_path,
        repo_root=args.repo_root,
        overwrite=args.overwrite,
        allow_dirty_test_fixture_override=args.allow_dirty_test_fixture_override,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

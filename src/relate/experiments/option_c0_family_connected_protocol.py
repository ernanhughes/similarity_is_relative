"""Frozen Option C0 family-connected allocation protocol primitives."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.commitments import (
    component_commitment as _clean_component_commitment,
)
from relate.family.commitments import (
    edge_commitment as _clean_edge_commitment,
)
from relate.family.edges import (
    PROTOCOL_VERSION,
    REVIEW_DISPOSITIONS,
    derive_edge_id,
    evidence_candidate_from_record,
    evidence_edge_from_record,
    make_evidence_candidate,
    make_manual_review_disposition,
    manual_review_disposition_from_record,
    resolve_evidence_candidate,
    validate_evidence_candidate,
    validate_evidence_edge,
    validate_manual_review_disposition,
    validate_resolved_edge,
    validate_rule_payload,
    validate_rule_semantics,
    validate_source_payload_binding,
)
from relate.family.graph import UnionFind, build_components, component_id

# --- Compatibility re-exports from relate.family ---
# These names are imported explicitly so that callers using the historical
# module path continue to resolve the same objects.  All imports in this
# section are intentional re-exports; F401 is suppressed for this file in
# pyproject.toml.
from relate.family.models import (
    EDGE_SCHEMA_ID,
    AllocationEntry,
    EdgeRule,
    EvidenceCandidate,
    EvidenceEdge,
    ManualReviewDisposition,
    SourceEvidenceRecord,
)
from relate.family.outcome import family_graph_outcome, graph_completeness
from relate.family.repositories import (
    ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
    ALLOCATION_REPOSITORY_COUNT,
    ALLOCATION_ROLE_REPOSITORY_COUNTS,
    ALLOCATION_ROLE_ROW_COUNTS,
    REPOSITORY_PATTERN,
    ROLE_ORDER,
    allocation_repository_commitment,
    load_allocation_manifest,
    normalize_repository,
    repository_owner,
    validate_canonical_allocation_entries,
)
from relate.family.rules import (
    ALL_EDGE_TYPES,
    CONDITIONAL_CONNECTING_EDGE_TYPES,
    CONNECTING_EDGE_TYPES,
    EDGE_RULES,
    HARD_CONNECTING_EDGE_TYPES,
    NONCONNECTING_EDGE_TYPES,
    edge_rules_contract,
)
from relate.family.sources import (
    ALLOWED_EVIDENCE_SOURCES,
    FORBIDDEN_PAYLOAD_PATTERNS,
    HASH_PATTERN,
    LOCATOR_PATTERN,
    MAX_EVIDENCE_STRING_LENGTH,
    METADATA_STATUSES,
    PUBLIC_METADATA_FIELDS,
    make_source_record,
    parse_timestamp,
    payload_hash,
    public_metadata_snapshot,
    source_bundle_commitment,
    source_record_from_record,
    validate_evidence_source_bundle,
    validate_payload_firewall,
    validate_source_identity,
    validate_source_record,
    validate_source_registry,
)
from relate.family.store import (
    CACHE_SCHEMA_ID,
    FamilyGraphCache,
    FamilyGraphCacheIdentity,
    make_cache_identity,
)
from relate.family.verification import (
    FamilyProtocolExpectedIdentity,
    FamilyProtocolInputPaths,
    validate_firewall_booleans,
    verify_family_protocol_inputs,
)

# --- Historical-only schema constants ---
# CACHE_SCHEMA_ID now originates in relate.family.store; re-exported above.

SCHEMA_ID: Final = "option-c0-family-connected-allocation-contract-v1"
D1_RESULT_SHA256: Final = "a19c042f725fb20a0a87fa902d2071f30c66d5ee8f96bfde1cd056cba5123420"
D1_1_CLASSIFICATION_SHA256: Final = (
    "64787803c775193335c98dfef7ccdd23989c54d0a110efb0284f7960640c5be4"
)
ALLOCATION_MANIFEST_SHA256: Final = (
    "41e48447171ac2f0553b795f2b3e50dfc5ac389b68fb30607b7d1c496bdb5bfc"
)
ALLOCATION_CONTEXT_SHA256: Final = (
    "a3ae0b5dcbef0ae8e5056900ba44eeb53b4fd53a20f7cea8d842f67197ab02ed"
)


# --- make_evidence_edge compatibility wrapper ---
# The clean relate.family.edges version accepts protocol_sha256 explicitly.
# This wrapper calls protocol_contract() to supply the canonical value so that
# callers of the historical module path see the same behaviour as before.


def make_evidence_edge(
    left_repository: str,
    right_repository: str,
    edge_type: str,
    *,
    evidence_sources: Mapping[str, str] | None = None,
    evidence_source: str | None = None,
    evidence_source_identity: str | None = None,
    retrieval_timestamp: str | None = None,
    evidence_payload: Mapping[str, Any],
    reason: str | None = None,
    rule_version: str = PROTOCOL_VERSION,
) -> EvidenceEdge:
    from relate.family.edges import make_evidence_edge as _clean_make_evidence_edge

    return _clean_make_evidence_edge(
        left_repository,
        right_repository,
        edge_type,
        protocol_sha256=protocol_contract()["protocol_sha256"],
        evidence_sources=evidence_sources,
        evidence_source=evidence_source,
        evidence_source_identity=evidence_source_identity,
        retrieval_timestamp=retrieval_timestamp,
        evidence_payload=evidence_payload,
        reason=reason,
        rule_version=rule_version,
    )


# --- FamilyGraphCacheIdentity / FamilyGraphCache ---
# Moved to relate.family.store in Stage 2B (family persistence extraction) and
# re-exported above. default_cache_identity remains here because it binds
# family_runner_source_identity to sha256_file(__file__) of *this* module.
# Moving that default to relate.family.store would change the identity, since
# __file__ would then refer to a different source file. The clean constructor
# make_cache_identity takes family_runner_source_identity explicitly instead.


def default_cache_identity(family_protocol_sha256: str) -> FamilyGraphCacheIdentity:
    return make_cache_identity(
        family_protocol_sha256=family_protocol_sha256,
        allocation_manifest_sha256=ALLOCATION_MANIFEST_SHA256,
        allocation_context_sha256=ALLOCATION_CONTEXT_SHA256,
        d1_audit_result_sha256=D1_RESULT_SHA256,
        d1_1_classification_sha256=D1_1_CLASSIFICATION_SHA256,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity=sha256_file(Path(__file__)),
    )


# --- validate_frozen_protocol_inputs / validate_firewall_booleans ---
# Moved to relate.family.verification in Stage 2E (family input verification
# and explicit workflow composition). validate_firewall_booleans is
# re-exported directly above: it never referenced anything historical-only.
# validate_frozen_protocol_inputs remains here as a thin wrapper supplying
# the historical canonical relative paths and frozen constants, since the
# clean verify_family_protocol_inputs requires explicit paths/identity
# rather than hard-coding them.


def validate_frozen_protocol_inputs(repo_root: Path) -> dict[str, Any]:
    paths = FamilyProtocolInputPaths(
        allocation_manifest=repo_root
        / "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-repository-allocation-v1.jsonl",
        firewall_publication=repo_root
        / "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-data-firewall-publication-v1.json",
        d1_result=repo_root
        / "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-integrity-audit-v1.json",
        d1_1_classification=repo_root
        / "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-overlap-classification-v1.json",
    )
    expected_identity = FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=ALLOCATION_MANIFEST_SHA256,
        allocation_context_sha256=ALLOCATION_CONTEXT_SHA256,
        allocation_repository_commitment_sha256=ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
        d1_result_sha256=D1_RESULT_SHA256,
        d1_1_classification_sha256=D1_1_CLASSIFICATION_SHA256,
    )
    verified = verify_family_protocol_inputs(paths, expected_identity)
    return {
        "allocation_manifest_sha256": verified.allocation_manifest_sha256,
        "allocation_context_sha256": verified.allocation_context_sha256,
        "allocation_repository_commitment_sha256": (
            verified.allocation_repository_commitment_sha256
        ),
        "d1_audit_result_sha256": verified.d1_result_sha256,
        "d1_1_classification_sha256": verified.d1_1_classification_sha256,
    }


# --- UnionFind / build_components / component_id ---
# Moved to relate.family.graph in Stage 2D (family graph and outcome
# capability extraction) and re-exported above. Nothing kept here: every
# caller in this module used only the required protocol_sha256 keyword
# argument, so no compatibility wrapper is needed.

# --- family_graph_outcome / graph_completeness ---
# Moved to relate.family.outcome in Stage 2D and re-exported above. Neither
# function ever read protocol_contract() internally, so no wrapper is
# needed.

# --- component_commitment / edge_commitment compatibility wrappers ---
# The clean relate.family.commitments versions require protocol_sha256
# explicitly (see that module's docstring for why). The historical
# versions read it from protocol_contract() when the caller omits it;
# these wrappers preserve that exact historical calling behaviour.


def component_commitment(components: Sequence[Mapping[str, Any]]) -> str:
    return _clean_component_commitment(
        components,
        protocol_sha256=protocol_contract()["protocol_sha256"],
    )


def edge_commitment(
    edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str | None = None,
    candidates: Mapping[str, EvidenceCandidate] | None = None,
    dispositions: Mapping[str, ManualReviewDisposition] | None = None,
    source_records: Mapping[tuple[str, str], SourceEvidenceRecord] | None = None,
) -> str:
    return _clean_edge_commitment(
        edges,
        protocol_sha256=protocol_sha256 or protocol_contract()["protocol_sha256"],
        candidates=candidates,
        dispositions=dispositions,
        source_records=source_records,
    )


def protocol_contract() -> dict[str, Any]:
    contract = {
        "schema_id": SCHEMA_ID,
        "schema_version": "v1",
        "source_allocation_identity": {
            "allocation_manifest_sha256": ALLOCATION_MANIFEST_SHA256,
            "allocation_context_sha256": ALLOCATION_CONTEXT_SHA256,
            "allocation_repository_commitment_sha256": ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
            "repository_count": ALLOCATION_REPOSITORY_COUNT,
            "role_repository_counts": ALLOCATION_ROLE_REPOSITORY_COUNTS,
            "role_row_counts": ALLOCATION_ROLE_ROW_COUNTS,
        },
        "d1_audit_result_sha256": D1_RESULT_SHA256,
        "d1_1_classification_sha256": D1_1_CLASSIFICATION_SHA256,
        "repository_normalization_rule": {
            "case": "lowercase",
            "trim_python_unicode_whitespace": True,
            "required_shape": "owner/repository",
            "allowed_pattern": REPOSITORY_PATTERN.pattern,
        },
        "edge_rules": edge_rules_contract(),
        "edge_taxonomy": {
            "hard_connecting": list(HARD_CONNECTING_EDGE_TYPES),
            "conditional_connecting": list(CONDITIONAL_CONNECTING_EDGE_TYPES),
            "nonconnecting_review_evidence": list(NONCONNECTING_EDGE_TYPES),
        },
        "component_algorithm": {
            "sort_connecting_edges": "by immutable edge_id",
            "duplicate_edge_ids": "rejected before counts, commitments, publication, and union",
            "union_find_uses_connecting_edges_only": True,
            "reviewed_edges_require_validated_candidate_and_disposition_before_union": True,
            "component_id": "sha256(canonical_json(sorted members + protocol sha256))",
            "transitivity": "applies only through connecting edges",
        },
        "resolved_edge_validation": {
            "approved_required_edges_validate_against_candidate_and_disposition": True,
            "recompute_fields": [
                "canonical endpoint order",
                "edge_id",
                "candidate_id",
                "payload hash",
                "source-bundle hash",
                "evidence commitment",
                "review disposition identity",
                "connecting status",
                "review status",
                "confidence category",
                "human-review requirement",
                "rule version",
                "frozen reason",
            ],
        },
        "evidence_source_binding": {
            "source_requirements_are_conjunctive": True,
            "payload_evidence_identities_must_match_source_bundle_identities": True,
        },
        "public_metadata_policy": {
            "snapshot_and_hash_public_metadata": True,
            "allowed_statuses": list(METADATA_STATUSES),
            "live_api_responses_not_silent_dependencies": True,
        },
        "cache_schema": {
            "schema_id": CACHE_SCHEMA_ID,
            "path": ".writer/option-c0/cache/option-c0-family-graph-v1.sqlite3",
            "identity_fields": list(FamilyGraphCacheIdentity.__annotations__),
            "tables": [
                "cache_identity",
                "allocation_repositories",
                "repository_metadata_snapshots",
                "source_records",
                "evidence_candidates",
                "typed_evidence_edges",
                "manual_review_dispositions",
                "component_memberships",
                "phase_commitments",
            ],
            "sqlite_pragmas": {"journal_mode": "WAL", "synchronous": "FULL", "foreign_keys": "ON"},
            "resolved_edge_foreign_keys": {
                "candidate_id": "evidence_candidates(candidate_id)",
                "disposition_id": "manual_review_dispositions(disposition_id)",
            },
            "final_disposition_uniqueness": "one final disposition per candidate",
        },
        "progress_contract": {
            "fields": [
                "phase",
                "completed",
                "total",
                "percentage",
                "cache_hits",
                "cache_misses",
                "request_rate",
                "elapsed_time",
                "ETA",
            ],
            "checkpoint_cadence": "after every durable phase transition and bounded request batch",
            "phase_status_enum": ["PENDING", "IN_PROGRESS", "COMPLETE", "INCOMPLETE", "FAILED"],
            "resume_cursor_requirements": [
                "cursor value",
                "cursor input identity",
                "phase commitment before cursor",
            ],
            "phase_commitment_requirements": [
                "phase name",
                "status",
                "input identities",
                "ordered output commitment",
                "cache identity",
            ],
        },
        "decision_rules": {
            "allowed_outcomes": [
                "FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS",
                "FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED",
                "FAMILY_GRAPH_INCOMPLETE_METADATA",
                "FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED",
            ],
            "family_crossing_observed": "true when a connecting component spans roles",
            "allocation_family_disjointness_violated": (
                "true when any connecting component spans roles"
            ),
            "material_contamination_established": "false in automatic run pending human review",
            "reallocation_required": "null in automatic run pending human review",
            "automatic_reallocation_from_crossing": False,
            "materiality_inputs": [
                "number of connecting family components crossing roles",
                "repositories affected by role pair",
                "rows affected by role pair",
                "largest component",
                "fraction of c0_fit rows affected",
                "fraction of c0_iteration rows affected",
                "hard-edge crossing count",
                "conditional-edge crossing count",
                "whether a valid family-disjoint allocation remains feasible",
            ],
            "materiality_threshold": "no automatic materiality threshold in v1",
            "explicit_human_review_required": True,
        },
        "permitted_inputs": [
            "published repository names",
            "published role assignments",
            "published aggregate row counts",
            "D1 visible-row hashes and bounded metadata",
            "public repository metadata",
        ],
        "prohibited_actions": [
            "canonical family graph execution in this PR",
            "allocation changes",
            "model refits",
            "C0 replay",
            "C0 selection row-content access",
            "C1 reserve row-content access",
            "D2 execution",
        ],
        "firewall_booleans": {
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
            "hidden_row_content_accessed": False,
        },
    }
    contract["protocol_sha256"] = sha256_text(canonical_json(contract))
    return contract


def verify_protocol_contract(contract: Mapping[str, Any]) -> bool:
    expected = dict(contract)
    observed = expected.pop("protocol_sha256", None)
    return observed == sha256_text(canonical_json(expected))


def write_protocol_contract(path: Path, *, overwrite: bool = False) -> dict[str, Any]:
    if path.exists() and not overwrite:
        raise FileExistsError("protocol contract refuses overwrite")
    contract = protocol_contract()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(canonical_json(contract) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)
    return contract


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the frozen Option C0 family-connected protocol contract."
    )
    parser.add_argument("--write-contract", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if args.write_contract:
        write_protocol_contract(args.write_contract, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

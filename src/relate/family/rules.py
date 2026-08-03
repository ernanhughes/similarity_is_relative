"""Frozen edge-rule taxonomy and rule-derived constants.

No database access, CLI parsing, file publication or workflow orchestration.
"""

from __future__ import annotations

from typing import Any, Final

from relate.family.models import EdgeRule

# Confidence category vocabulary used in EDGE_RULES.
CONFIDENCE_CATEGORIES: Final = ("high", "medium", "low", "review_only")

EDGE_RULES: Final[dict[str, EdgeRule]] = {
    "DECLARED_GITHUB_FORK": EdgeRule(
        edge_type="DECLARED_GITHUB_FORK",
        category="hard_connecting",
        connecting_policy=(
            "connect when GitHub fork metadata proves one endpoint is the other "
            "endpoint's parent/source"
        ),
        required_fields={
            "left_repository_id": "str",
            "right_repository_id": "str",
            "child_full_name": "repository",
            "parent_or_source_full_name": "repository",
            "fork": "true",
            "metadata_snapshot_identity": "sha256",
            "snapshot_status": "str",
        },
        allowed_values={"snapshot_status": ("COMPLETE",)},
        forbidden_fields=(),
        evidence_source_requirements=("github_rest", "public_metadata_snapshot"),
        review_requirement="AUTO",
        confidence_category="high",
        reason_template="declared GitHub fork relationship connects repositories",
        negative_conditions=("same owner alone is not fork evidence",),
    ),
    "VERIFIED_REPOSITORY_SUCCESSION": EdgeRule(
        edge_type="VERIFIED_REPOSITORY_SUCCESSION",
        category="hard_connecting",
        connecting_policy="connect only after approved public succession or rename/archive review",
        required_fields={
            "predecessor_repository": "repository",
            "successor_repository": "repository",
            "direction": "str",
            "public_succession_record": "str",
            "record_snapshot_hash": "sha256",
        },
        allowed_values={
            "direction": ("predecessor_to_successor",),
        },
        forbidden_fields=(),
        evidence_source_requirements=("public_metadata_snapshot",),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="high",
        reason_template="approved repository succession connects repositories",
        negative_conditions=("similar names or creation dates alone are insufficient",),
    ),
    "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY": EdgeRule(
        edge_type="EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
        category="hard_connecting",
        connecting_policy=(
            "connect only complete repository tree or approved complete "
            "non-generated module scope identity"
        ),
        required_fields={
            "identity_scope": "str",
            "d1_visible_evidence_identity": "sha256",
            "matching_content_sha256": "sha256",
            "left_scope_identity": "sha256",
            "right_scope_identity": "sha256",
            "source_identity_provenance": "str",
            "generated_vendor_boilerplate_exclusion": "true",
            "complete_evidence_status": "str",
        },
        allowed_values={
            "identity_scope": ("complete_repository_source_tree", "approved_non_generated_module"),
            "complete_evidence_status": ("COMPLETE",),
        },
        forbidden_fields=("function_stable_key", "function_code_sha256"),
        evidence_source_requirements=("d1_visible_cache", "public_metadata_snapshot"),
        review_requirement="AUTO",
        confidence_category="high",
        reason_template="complete source scope identity connects repositories",
        negative_conditions=("a single identical function is not a hard repository connection",),
    ),
    "VERIFIED_SHARED_PACKAGE_LINEAGE": EdgeRule(
        edge_type="VERIFIED_SHARED_PACKAGE_LINEAGE",
        category="hard_connecting",
        connecting_policy=(
            "connect approved movement, split, rename, or continuation of the "
            "same package/project lineage"
        ),
        required_fields={
            "lineage_record_type": "str",
            "approved_lineage_record": "str",
            "evidence_snapshot_hash": "sha256",
        },
        allowed_values={
            "lineage_record_type": ("movement", "split", "rename", "continuation"),
        },
        forbidden_fields=("common_dependency_only", "same_owner_only"),
        evidence_source_requirements=("public_metadata_snapshot",),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="high",
        reason_template="approved shared package lineage connects repositories",
        negative_conditions=(
            "common dependency is insufficient",
            "same framework is insufficient",
            "shared package name token is insufficient",
            "same owner is insufficient",
        ),
    ),
    "EXACT_AST_WITH_CORROBORATING_PROVENANCE": EdgeRule(
        edge_type="EXACT_AST_WITH_CORROBORATING_PROVENANCE",
        category="conditional_connecting",
        connecting_policy=(
            "connect only when all corroborating provenance fields are exactly "
            "true and review is approved"
        ),
        required_fields={
            "left_stable_key": "str",
            "right_stable_key": "str",
            "normalized_ast_sha256": "sha256",
            "d1_visible_evidence_identity": "sha256",
            "visible_role_left": "visible_role",
            "visible_role_right": "visible_role",
            "left_function_identity": "str",
            "right_function_identity": "str",
            "left_path_suffix": "str",
            "right_path_suffix": "str",
            "same_normalized_ast": "true",
            "same_function_identity": "true",
            "same_path_suffix": "true",
            "compatible_repository_dates": "true",
            "public_shared_package_history": "true",
        },
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("d1_visible_cache", "public_metadata_snapshot"),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="medium",
        reason_template="approved exact AST plus corroborating provenance connects repositories",
        negative_conditions=("exact AST alone is insufficient",),
    ),
    "SAME_MODULE_LINEAGE_WITH_CORROBORATION": EdgeRule(
        edge_type="SAME_MODULE_LINEAGE_WITH_CORROBORATION",
        category="conditional_connecting",
        connecting_policy="connect only approved same-module lineage with public corroboration",
        required_fields={
            "same_module_lineage": "true",
            "public_shared_package_history": "true",
            "compatible_repository_dates": "true",
        },
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("public_metadata_snapshot",),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="medium",
        reason_template="approved same-module lineage connects repositories",
        negative_conditions=("same module name alone is insufficient",),
    ),
    "EXPLICIT_COPY_OR_EXTRACTION_HISTORY": EdgeRule(
        edge_type="EXPLICIT_COPY_OR_EXTRACTION_HISTORY",
        category="conditional_connecting",
        connecting_policy="connect only approved public copy or extraction history",
        required_fields={
            "public_copy_or_extraction_record": "str",
            "compatible_repository_dates": "true",
        },
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("public_metadata_snapshot",),
        review_requirement="APPROVED_REQUIRED",
        confidence_category="medium",
        reason_template="approved copy or extraction history connects repositories",
        negative_conditions=("unreviewed copy suspicion is insufficient",),
    ),
    "EXACT_FUNCTION_SOURCE_MATCH": EdgeRule(
        edge_type="EXACT_FUNCTION_SOURCE_MATCH",
        category="nonconnecting_review_evidence",
        connecting_policy="never connects repositories by itself",
        required_fields={
            "left_stable_key": "str",
            "right_stable_key": "str",
            "code_sha256": "sha256",
            "d1_visible_evidence_identity": "sha256",
            "visible_role_left": "visible_role",
            "visible_role_right": "visible_role",
        },
        allowed_values={},
        forbidden_fields=("source_body", "raw_source"),
        evidence_source_requirements=("d1_visible_cache",),
        review_requirement="REVIEW_ONLY",
        confidence_category="review_only",
        reason_template="single exact function source match is review evidence only",
        negative_conditions=("function-level exact source does not hard-connect repositories",),
    ),
    "SAME_OWNER_PROXY": EdgeRule(
        edge_type="SAME_OWNER_PROXY",
        category="nonconnecting_review_evidence",
        connecting_policy="never connects repositories",
        required_fields={"same_owner": "true", "owner": "str"},
        allowed_values={},
        forbidden_fields=(),
        evidence_source_requirements=("allocation_manifest",),
        review_requirement="REVIEW_ONLY",
        confidence_category="review_only",
        reason_template="same owner is proxy review evidence only",
        negative_conditions=("same owner is not a family rule",),
    ),
    "SIMILAR_REPOSITORY_NAME": EdgeRule(
        "SIMILAR_REPOSITORY_NAME",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"similarity_method": "str", "score": "number"},
        {},
        (),
        ("allocation_manifest",),
        "REVIEW_ONLY",
        "review_only",
        "similar names are review evidence only",
        ("similar names alone are insufficient",),
    ),
    "SUFFIX_STRIPPED_NAME_MATCH": EdgeRule(
        "SUFFIX_STRIPPED_NAME_MATCH",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"normalized_family_token": "str"},
        {},
        (),
        ("allocation_manifest",),
        "REVIEW_ONLY",
        "review_only",
        "suffix-stripped name match is review evidence only",
        ("shared name tokens alone are insufficient",),
    ),
    "SIMHASH_NEAR_FUNCTION": EdgeRule(
        "SIMHASH_NEAR_FUNCTION",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {
            "left_stable_key": "str",
            "right_stable_key": "str",
            "hamming_distance": "int",
            "d1_visible_evidence_identity": "sha256",
        },
        {},
        ("source_body", "raw_source"),
        ("d1_visible_cache",),
        "REVIEW_ONLY",
        "review_only",
        "SimHash-near function pair is heuristic review evidence only",
        ("SimHash-near alone is insufficient",),
    ),
    "COMMON_FRAMEWORK_OR_BOILERPLATE": EdgeRule(
        "COMMON_FRAMEWORK_OR_BOILERPLATE",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"framework_or_boilerplate_name": "str"},
        {},
        (),
        ("public_metadata_snapshot",),
        "REVIEW_ONLY",
        "review_only",
        "common framework or boilerplate is review evidence only",
        ("common framework is insufficient",),
    ),
    "SHARED_LANGUAGE_OR_TOPIC": EdgeRule(
        "SHARED_LANGUAGE_OR_TOPIC",
        "nonconnecting_review_evidence",
        "never connects repositories",
        {"topic_or_language": "str"},
        {},
        (),
        ("public_metadata_snapshot",),
        "REVIEW_ONLY",
        "review_only",
        "shared language or topic is review evidence only",
        ("shared language or topic is insufficient",),
    ),
}
HARD_CONNECTING_EDGE_TYPES: Final = tuple(
    key for key, rule in EDGE_RULES.items() if rule.category == "hard_connecting"
)
CONDITIONAL_CONNECTING_EDGE_TYPES: Final = tuple(
    key for key, rule in EDGE_RULES.items() if rule.category == "conditional_connecting"
)
NONCONNECTING_EDGE_TYPES: Final = tuple(
    key for key, rule in EDGE_RULES.items() if rule.category == "nonconnecting_review_evidence"
)
CONNECTING_EDGE_TYPES: Final = HARD_CONNECTING_EDGE_TYPES + CONDITIONAL_CONNECTING_EDGE_TYPES
ALL_EDGE_TYPES: Final = tuple(EDGE_RULES)


def edge_rules_contract() -> dict[str, Any]:
    return {
        name: {
            "edge_type": rule.edge_type,
            "category": rule.category,
            "connecting_policy": rule.connecting_policy,
            "required_fields": dict(rule.required_fields),
            "field_types": dict(rule.required_fields),
            "allowed_values": {key: list(value) for key, value in rule.allowed_values.items()},
            "forbidden_fields": list(rule.forbidden_fields),
            "evidence_source_requirements": list(rule.evidence_source_requirements),
            "review_requirement": rule.review_requirement,
            "automatic_or_human_reviewed_disposition": rule.review_requirement,
            "confidence_policy": rule.confidence_category,
            "reason_template": rule.reason_template,
            "negative_exclusion_conditions": list(rule.negative_conditions),
        }
        for name, rule in sorted(EDGE_RULES.items())
    }

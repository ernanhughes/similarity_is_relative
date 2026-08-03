"""Tests for relate.family.rules."""

from __future__ import annotations

from relate.family.rules import (
    ALL_EDGE_TYPES,
    CONDITIONAL_CONNECTING_EDGE_TYPES,
    CONNECTING_EDGE_TYPES,
    EDGE_RULES,
    HARD_CONNECTING_EDGE_TYPES,
    NONCONNECTING_EDGE_TYPES,
    edge_rules_contract,
)


class TestEdgeTypeTaxonomy:
    def test_hard_connecting_types_ordered(self) -> None:
        assert HARD_CONNECTING_EDGE_TYPES == (
            "DECLARED_GITHUB_FORK",
            "VERIFIED_REPOSITORY_SUCCESSION",
            "EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY",
            "VERIFIED_SHARED_PACKAGE_LINEAGE",
        )

    def test_conditional_connecting_types_ordered(self) -> None:
        assert CONDITIONAL_CONNECTING_EDGE_TYPES == (
            "EXACT_AST_WITH_CORROBORATING_PROVENANCE",
            "SAME_MODULE_LINEAGE_WITH_CORROBORATION",
            "EXPLICIT_COPY_OR_EXTRACTION_HISTORY",
        )

    def test_nonconnecting_types_ordered(self) -> None:
        assert NONCONNECTING_EDGE_TYPES == (
            "EXACT_FUNCTION_SOURCE_MATCH",
            "SAME_OWNER_PROXY",
            "SIMILAR_REPOSITORY_NAME",
            "SUFFIX_STRIPPED_NAME_MATCH",
            "SIMHASH_NEAR_FUNCTION",
            "COMMON_FRAMEWORK_OR_BOILERPLATE",
            "SHARED_LANGUAGE_OR_TOPIC",
        )

    def test_connecting_is_hard_plus_conditional(self) -> None:
        assert CONNECTING_EDGE_TYPES == (
            HARD_CONNECTING_EDGE_TYPES + CONDITIONAL_CONNECTING_EDGE_TYPES
        )

    def test_all_edge_types_covers_all(self) -> None:
        assert set(ALL_EDGE_TYPES) == set(EDGE_RULES)

    def test_all_edge_types_ordered_by_insertion(self) -> None:
        assert ALL_EDGE_TYPES == tuple(EDGE_RULES)

    def test_no_overlap_between_categories(self) -> None:
        hard = set(HARD_CONNECTING_EDGE_TYPES)
        conditional = set(CONDITIONAL_CONNECTING_EDGE_TYPES)
        nonconnecting = set(NONCONNECTING_EDGE_TYPES)
        assert not (hard & conditional)
        assert not (hard & nonconnecting)
        assert not (conditional & nonconnecting)

    def test_partition_covers_all(self) -> None:
        all_types = set(EDGE_RULES)
        partitioned = (
            set(HARD_CONNECTING_EDGE_TYPES)
            | set(CONDITIONAL_CONNECTING_EDGE_TYPES)
            | set(NONCONNECTING_EDGE_TYPES)
        )
        assert partitioned == all_types

    def test_total_count(self) -> None:
        assert len(ALL_EDGE_TYPES) == 14


class TestEdgeRules:
    def test_all_rules_have_required_fields(self) -> None:
        for name, rule in EDGE_RULES.items():
            assert rule.edge_type == name
            assert rule.category in {
                "hard_connecting",
                "conditional_connecting",
                "nonconnecting_review_evidence",
            }
            assert rule.review_requirement in {"AUTO", "APPROVED_REQUIRED", "REVIEW_ONLY"}
            assert rule.confidence_category in ("high", "medium", "low", "review_only")

    def test_hard_connecting_rules_are_high_confidence(self) -> None:
        for name in HARD_CONNECTING_EDGE_TYPES:
            assert EDGE_RULES[name].confidence_category == "high", name

    def test_conditional_connecting_rules_are_medium_confidence(self) -> None:
        for name in CONDITIONAL_CONNECTING_EDGE_TYPES:
            assert EDGE_RULES[name].confidence_category == "medium", name

    def test_nonconnecting_rules_are_review_only_confidence(self) -> None:
        for name in NONCONNECTING_EDGE_TYPES:
            assert EDGE_RULES[name].confidence_category == "review_only", name

    def test_auto_rules_are_hard_connecting(self) -> None:
        for name, rule in EDGE_RULES.items():
            if rule.review_requirement == "AUTO":
                assert rule.category == "hard_connecting", name

    def test_review_only_rules_never_connect(self) -> None:
        for name, rule in EDGE_RULES.items():
            if rule.review_requirement == "REVIEW_ONLY":
                assert not rule.is_connecting_candidate, name
                assert not rule.human_review_required, name

    def test_approved_required_rules_need_human_review(self) -> None:
        for name, rule in EDGE_RULES.items():
            if rule.review_requirement == "APPROVED_REQUIRED":
                assert rule.human_review_required, name

    def test_review_requirements_retained(self) -> None:
        assert EDGE_RULES["DECLARED_GITHUB_FORK"].review_requirement == "AUTO"
        succession = EDGE_RULES["VERIFIED_REPOSITORY_SUCCESSION"]
        assert succession.review_requirement == "APPROVED_REQUIRED"
        assert EDGE_RULES["EXACT_FUNCTION_SOURCE_MATCH"].review_requirement == "REVIEW_ONLY"

    def test_declared_github_fork_required_fields(self) -> None:
        rule = EDGE_RULES["DECLARED_GITHUB_FORK"]
        assert "left_repository_id" in rule.required_fields
        assert "child_full_name" in rule.required_fields
        assert "fork" in rule.required_fields

    def test_exact_function_source_match_forbidden_fields(self) -> None:
        rule = EDGE_RULES["EXACT_FUNCTION_SOURCE_MATCH"]
        assert "source_body" in rule.forbidden_fields
        assert "raw_source" in rule.forbidden_fields

    def test_simhash_forbidden_fields(self) -> None:
        rule = EDGE_RULES["SIMHASH_NEAR_FUNCTION"]
        assert "source_body" in rule.forbidden_fields


class TestEdgeRulesContract:
    def test_returns_dict(self) -> None:
        contract = edge_rules_contract()
        assert isinstance(contract, dict)

    def test_sorted_by_name(self) -> None:
        contract = edge_rules_contract()
        assert list(contract) == sorted(contract)

    def test_all_edge_types_present(self) -> None:
        contract = edge_rules_contract()
        assert set(contract) == set(EDGE_RULES)

    def test_required_contract_fields(self) -> None:
        contract = edge_rules_contract()
        for name, entry in contract.items():
            for field in (
                "edge_type",
                "category",
                "connecting_policy",
                "required_fields",
                "field_types",
                "allowed_values",
                "forbidden_fields",
                "evidence_source_requirements",
                "review_requirement",
                "automatic_or_human_reviewed_disposition",
                "confidence_policy",
                "reason_template",
                "negative_exclusion_conditions",
            ):
                assert field in entry, f"missing {field!r} in contract for {name}"

    def test_field_types_equals_required_fields(self) -> None:
        contract = edge_rules_contract()
        for name, entry in contract.items():
            assert entry["field_types"] == entry["required_fields"], name

    def test_review_requirement_equals_automatic_disposition(self) -> None:
        contract = edge_rules_contract()
        for name, entry in contract.items():
            assert (
                entry["review_requirement"] == entry["automatic_or_human_reviewed_disposition"]
            ), name

    def test_deterministic(self) -> None:
        assert edge_rules_contract() == edge_rules_contract()

"""Tests for relate.family.verification.

Covers exact valid bundles, every hash-mismatch and firewall-violation
failure mode, and object-identity compatibility with the historical facade.
A verification failure always raises (fail-closed); it is never a blocked
result.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.evidence.hashing import sha256_file
from relate.family.verification import (
    FamilyProtocolExpectedIdentity,
    FamilyProtocolInputPaths,
    validate_firewall_booleans,
    verify_family_protocol_inputs,
)

COMMON_FIREWALL = {
    "scientific_result_observed": False,
    "mechanism_result_observed": False,
    "c0_selection_rows_accessed": False,
    "c1_rows_accessed": False,
    "hidden_row_content_accessed": False,
}


def _build_fixture(
    tmp_path: Path,
    *,
    d1_data: dict | None = None,
    d11_data: dict | None = None,
    firewall_data: dict | None = None,
    allocation_text: str | None = None,
) -> tuple[FamilyProtocolInputPaths, FamilyProtocolExpectedIdentity]:
    allocation = tmp_path / "allocation.jsonl"
    allocation.write_text(
        allocation_text or '{"repository":"owner/a","role":"c0_fit","row_count":1}\n',
        encoding="utf-8",
    )

    d1 = tmp_path / "d1.json"
    d1.write_text(
        json.dumps(
            d1_data if d1_data is not None else {"firewall_booleans": dict(COMMON_FIREWALL)}
        ),
        encoding="utf-8",
    )

    d11 = tmp_path / "d11.json"
    default_d11 = {
        "classification": {
            "overall_outcome": "D1_CLASSIFICATION_INCONCLUSIVE",
            "family_identity_rule_status": "NOT_FROZEN",
        },
        "firewall_booleans": {
            **COMMON_FIREWALL,
            "c0_selection_row_content_accessed": False,
            "c1_row_content_accessed": False,
        },
    }
    d11.write_text(json.dumps(d11_data if d11_data is not None else default_d11), encoding="utf-8")

    firewall = tmp_path / "firewall.json"
    firewall.write_text(
        json.dumps(
            firewall_data if firewall_data is not None else {"allocation_context_sha256": "c" * 64}
        ),
        encoding="utf-8",
    )

    paths = FamilyProtocolInputPaths(
        allocation_manifest=allocation,
        firewall_publication=firewall,
        d1_result=d1,
        d1_1_classification=d11,
    )
    expected = FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=sha256_file(allocation),
        allocation_context_sha256=json.loads(firewall.read_text(encoding="utf-8"))[
            "allocation_context_sha256"
        ],
        allocation_repository_commitment_sha256="d" * 64,
        d1_result_sha256=sha256_file(d1),
        d1_1_classification_sha256=sha256_file(d11),
    )
    return paths, expected


class TestExactValidBundle:
    def test_valid_bundle_verifies(self, tmp_path: Path) -> None:
        paths, expected = _build_fixture(tmp_path)
        verified = verify_family_protocol_inputs(paths, expected)
        assert verified.allocation_manifest_sha256 == expected.allocation_manifest_sha256
        assert verified.allocation_context_sha256 == expected.allocation_context_sha256
        assert (
            verified.allocation_repository_commitment_sha256
            == expected.allocation_repository_commitment_sha256
        )
        assert verified.d1_result_sha256 == expected.d1_result_sha256
        assert verified.d1_1_classification_sha256 == expected.d1_1_classification_sha256
        assert verified.d1_1_overall_outcome == "D1_CLASSIFICATION_INCONCLUSIVE"
        assert verified.d1_1_family_identity_rule_status == "NOT_FROZEN"


class TestHashMismatches:
    def test_allocation_manifest_hash_mismatch(self, tmp_path: Path) -> None:
        paths, expected = _build_fixture(tmp_path)
        tampered = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256="0" * 64,
            allocation_context_sha256=expected.allocation_context_sha256,
            allocation_repository_commitment_sha256=expected.allocation_repository_commitment_sha256,
            d1_result_sha256=expected.d1_result_sha256,
            d1_1_classification_sha256=expected.d1_1_classification_sha256,
        )
        with pytest.raises(ValueError, match="allocation manifest hash mismatch"):
            verify_family_protocol_inputs(paths, tampered)

    def test_d1_hash_mismatch(self, tmp_path: Path) -> None:
        paths, expected = _build_fixture(tmp_path)
        tampered = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=expected.allocation_manifest_sha256,
            allocation_context_sha256=expected.allocation_context_sha256,
            allocation_repository_commitment_sha256=expected.allocation_repository_commitment_sha256,
            d1_result_sha256="0" * 64,
            d1_1_classification_sha256=expected.d1_1_classification_sha256,
        )
        with pytest.raises(ValueError, match="D1 result hash mismatch"):
            verify_family_protocol_inputs(paths, tampered)

    def test_d11_hash_mismatch(self, tmp_path: Path) -> None:
        paths, expected = _build_fixture(tmp_path)
        tampered = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=expected.allocation_manifest_sha256,
            allocation_context_sha256=expected.allocation_context_sha256,
            allocation_repository_commitment_sha256=expected.allocation_repository_commitment_sha256,
            d1_result_sha256=expected.d1_result_sha256,
            d1_1_classification_sha256="0" * 64,
        )
        with pytest.raises(ValueError, match="D1.1 classification hash mismatch"):
            verify_family_protocol_inputs(paths, tampered)

    def test_allocation_context_mismatch(self, tmp_path: Path) -> None:
        paths, expected = _build_fixture(tmp_path)
        tampered = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=expected.allocation_manifest_sha256,
            allocation_context_sha256="0" * 64,
            allocation_repository_commitment_sha256=expected.allocation_repository_commitment_sha256,
            d1_result_sha256=expected.d1_result_sha256,
            d1_1_classification_sha256=expected.d1_1_classification_sha256,
        )
        with pytest.raises(ValueError, match="allocation context SHA-256 mismatch"):
            verify_family_protocol_inputs(paths, tampered)


class TestClassificationChecks:
    def test_d11_wrong_outcome_rejected(self, tmp_path: Path) -> None:
        d11_data = {
            "classification": {
                "overall_outcome": "D1_CLASSIFICATION_SOMETHING_ELSE",
                "family_identity_rule_status": "NOT_FROZEN",
            },
            "firewall_booleans": {
                **COMMON_FIREWALL,
                "c0_selection_row_content_accessed": False,
                "c1_row_content_accessed": False,
            },
        }
        paths, expected = _build_fixture(tmp_path, d11_data=d11_data)
        with pytest.raises(ValueError, match="D1.1 outcome is not inconclusive"):
            verify_family_protocol_inputs(paths, expected)

    def test_family_rule_status_not_not_frozen_rejected(self, tmp_path: Path) -> None:
        d11_data = {
            "classification": {
                "overall_outcome": "D1_CLASSIFICATION_INCONCLUSIVE",
                "family_identity_rule_status": "FROZEN",
            },
            "firewall_booleans": {
                **COMMON_FIREWALL,
                "c0_selection_row_content_accessed": False,
                "c1_row_content_accessed": False,
            },
        }
        paths, expected = _build_fixture(tmp_path, d11_data=d11_data)
        with pytest.raises(ValueError, match="family identity rule status"):
            verify_family_protocol_inputs(paths, expected)


class TestFirewallBooleans:
    def test_missing_d1_firewall_key_rejected(self, tmp_path: Path) -> None:
        incomplete = dict(COMMON_FIREWALL)
        incomplete.pop("scientific_result_observed")
        paths, expected = _build_fixture(tmp_path, d1_data={"firewall_booleans": incomplete})
        with pytest.raises(ValueError, match="scientific_result_observed"):
            verify_family_protocol_inputs(paths, expected)

    def test_missing_d11_firewall_key_rejected(self, tmp_path: Path) -> None:
        d11_firewall = {**COMMON_FIREWALL, "c0_selection_row_content_accessed": False}
        # c1_row_content_accessed deliberately omitted.
        d11_data = {
            "classification": {
                "overall_outcome": "D1_CLASSIFICATION_INCONCLUSIVE",
                "family_identity_rule_status": "NOT_FROZEN",
            },
            "firewall_booleans": d11_firewall,
        }
        paths, expected = _build_fixture(tmp_path, d11_data=d11_data)
        with pytest.raises(ValueError, match="c1_row_content_accessed"):
            verify_family_protocol_inputs(paths, expected)

    def test_firewall_value_true_rejected(self, tmp_path: Path) -> None:
        tampered_firewall = {**COMMON_FIREWALL, "hidden_row_content_accessed": True}
        paths, expected = _build_fixture(tmp_path, d1_data={"firewall_booleans": tampered_firewall})
        with pytest.raises(ValueError, match="hidden_row_content_accessed"):
            verify_family_protocol_inputs(paths, expected)

    def test_validate_firewall_booleans_directly(self) -> None:
        d1 = dict(COMMON_FIREWALL)
        d11 = {
            "firewall_booleans": {
                **COMMON_FIREWALL,
                "c0_selection_row_content_accessed": False,
                "c1_row_content_accessed": False,
            }
        }
        validate_firewall_booleans(d1, d11)  # must not raise

    def test_validate_firewall_booleans_rejects_true_value(self) -> None:
        d1 = {**COMMON_FIREWALL, "c1_rows_accessed": True}
        d11 = {
            "firewall_booleans": {
                **COMMON_FIREWALL,
                "c0_selection_row_content_accessed": False,
                "c1_row_content_accessed": False,
            }
        }
        with pytest.raises(ValueError, match="c1_rows_accessed"):
            validate_firewall_booleans(d1, d11)


class TestNonObjectJson:
    def test_non_object_json_rejected(self, tmp_path: Path) -> None:
        allocation = tmp_path / "allocation.jsonl"
        allocation.write_text(
            '{"repository":"owner/a","role":"c0_fit","row_count":1}\n',
            encoding="utf-8",
        )
        d1 = tmp_path / "d1.json"
        d1.write_text("[]", encoding="utf-8")
        d11 = tmp_path / "d11.json"
        d11.write_text(json.dumps({"classification": {}}), encoding="utf-8")
        firewall = tmp_path / "firewall.json"
        firewall.write_text(json.dumps({"allocation_context_sha256": "c" * 64}), encoding="utf-8")

        paths = FamilyProtocolInputPaths(
            allocation_manifest=allocation,
            firewall_publication=firewall,
            d1_result=d1,
            d1_1_classification=d11,
        )
        expected = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=sha256_file(allocation),
            allocation_context_sha256="c" * 64,
            allocation_repository_commitment_sha256="d" * 64,
            d1_result_sha256=sha256_file(d1),
            d1_1_classification_sha256=sha256_file(d11),
        )
        with pytest.raises(ValueError, match="must be a JSON object"):
            verify_family_protocol_inputs(paths, expected)


class TestHistoricalCompatibility:
    def test_validate_firewall_booleans_same_object(self) -> None:
        assert historical.validate_firewall_booleans is validate_firewall_booleans

    def test_historical_wrapper_matches_clean_result(self) -> None:
        real_paths = FamilyProtocolInputPaths(
            allocation_manifest=Path(
                "artifacts/canonical/option-c0/data-firewall-v1/"
                "option-c0-repository-allocation-v1.jsonl"
            ),
            firewall_publication=Path(
                "artifacts/canonical/option-c0/data-firewall-v1/"
                "option-c0-data-firewall-publication-v1.json"
            ),
            d1_result=Path(
                "artifacts/canonical/option-c0/review-v1/d1-integrity/"
                "option-c0-d1-integrity-audit-v1.json"
            ),
            d1_1_classification=Path(
                "artifacts/canonical/option-c0/review-v1/d1-integrity/"
                "option-c0-d1-overlap-classification-v1.json"
            ),
        )
        if not real_paths.allocation_manifest.exists():
            pytest.skip("canonical protocol inputs not accessible from test working directory")
        expected = FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256=historical.ALLOCATION_MANIFEST_SHA256,
            allocation_context_sha256=historical.ALLOCATION_CONTEXT_SHA256,
            allocation_repository_commitment_sha256=(
                historical.ALLOCATION_REPOSITORY_COMMITMENT_SHA256
            ),
            d1_result_sha256=historical.D1_RESULT_SHA256,
            d1_1_classification_sha256=historical.D1_1_CLASSIFICATION_SHA256,
        )
        clean_result = verify_family_protocol_inputs(real_paths, expected)
        historical_result = historical.validate_frozen_protocol_inputs(Path("."))
        assert (
            historical_result["allocation_manifest_sha256"]
            == clean_result.allocation_manifest_sha256
        )
        assert (
            historical_result["allocation_context_sha256"] == clean_result.allocation_context_sha256
        )
        assert (
            historical_result["allocation_repository_commitment_sha256"]
            == clean_result.allocation_repository_commitment_sha256
        )
        assert historical_result["d1_audit_result_sha256"] == clean_result.d1_result_sha256
        assert (
            historical_result["d1_1_classification_sha256"]
            == clean_result.d1_1_classification_sha256
        )

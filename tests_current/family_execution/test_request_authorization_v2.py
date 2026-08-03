from __future__ import annotations

from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.family.authorization import (
    AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
    WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
    canonical_execution_authorization_v2_from_record,
    canonical_execution_request_v2_from_record,
    compute_canonical_executor_source_identity,
    make_canonical_execution_authorization,
    make_canonical_execution_authorization_v2,
    make_canonical_execution_request,
    make_canonical_execution_request_v2,
    validate_executable_canonical_authorization_v2,
)
from relate.family.execution import execute_authorized_canonical_family
from relate.family.review import FamilyReviewPacket
from relate.family.verification import FamilyProtocolExpectedIdentity, FamilyProtocolInputPaths
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import FamilyEvidenceBundle, evidence_bundle_commitment


def _paths() -> FamilyProtocolInputPaths:
    return FamilyProtocolInputPaths(
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


def _expected() -> FamilyProtocolExpectedIdentity:
    return FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=historical.ALLOCATION_MANIFEST_SHA256,
        allocation_context_sha256=historical.ALLOCATION_CONTEXT_SHA256,
        allocation_repository_commitment_sha256=historical.ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
        d1_result_sha256=historical.D1_RESULT_SHA256,
        d1_1_classification_sha256=historical.D1_1_CLASSIFICATION_SHA256,
    )


def _packet(bundle: FamilyEvidenceBundle) -> FamilyReviewPacket:
    source = compute_family_workflow_source_identity(Path.cwd())
    return FamilyReviewPacket(
        {
            "schema_id": "relate-family-review-packet-v1",
            "family_protocol_sha256": historical.protocol_contract()["protocol_sha256"],
            "workflow": {
                "name": FAMILY_GRAPH_WORKFLOW_NAME,
                "version": FAMILY_GRAPH_WORKFLOW_VERSION,
                "run_id": "review-run",
                "run_identity_commitment": "0" * 64,
                "source_identity": source,
                "allowed_roles": ["c0_fit", "c0_iteration", "c0_selection", "c1_reserve"],
            },
            "identities": {
                "allocation_manifest_sha256": historical.ALLOCATION_MANIFEST_SHA256,
                "allocation_context_sha256": historical.ALLOCATION_CONTEXT_SHA256,
                "allocation_repository_commitment_sha256": (
                    historical.ALLOCATION_REPOSITORY_COMMITMENT_SHA256
                ),
                "evidence_bundle_commitment": evidence_bundle_commitment(bundle),
            },
            "firewall_declarations": {
                "c0_selection_row_content_accessed": False,
                "c1_row_content_accessed": False,
                "hidden_row_content_accessed": False,
            },
            "publication_scope": "BOUNDED_FAMILY_RESULT_ONLY",
            "packet_contains": "BOUNDED_FAMILY_GRAPH_FACTS_ONLY",
            "not_concluded": [
                "MATERIAL_CONTAMINATION",
                "MATERIALITY_THRESHOLD",
                "REALLOCATION_REQUIRED",
                "D2_AUTHORIZED",
            ],
        }
    )


def _v2_request(tmp_path: Path):
    bundle = FamilyEvidenceBundle((), (), ())
    packet = _packet(bundle)
    request = make_canonical_execution_request_v2(
        repo_root=Path.cwd(),
        review_packet=packet,
        evidence_bundle=bundle,
        requested_run_id="canonical-run-v2",
        allowed_roles=frozenset({"c0_fit", "c0_iteration", "c0_selection", "c1_reserve"}),
        canonical_input_paths=_paths(),
        expected_identity=_expected(),
        intended_work_dir=Path(".writer") / "stage-2h-tests" / tmp_path.name / "work",
        intended_store_path=Path(".writer")
        / "stage-2h-tests"
        / tmp_path.name
        / "work"
        / "family-graph.sqlite3",
    )
    return request, packet, bundle


def test_v2_request_binds_firewall_file_and_executor_identity(tmp_path: Path) -> None:
    request, _packet_value, _bundle = _v2_request(tmp_path)
    record = request.as_record()
    assert record["schema_id"] == "relate-family-canonical-execution-request-v2"
    assert "firewall_publication_sha256" in record["canonical_inputs"]
    executor_identity = compute_canonical_executor_source_identity(Path.cwd())
    assert record["canonical_executor_source_identity"] == executor_identity
    assert "PROTECTED_ROW_ACCESS" in record["prohibitions"]
    canonical_execution_request_v2_from_record(record)


def test_v2_authorization_binds_executor_identity_and_validates(tmp_path: Path) -> None:
    request, packet, bundle = _v2_request(tmp_path)
    auth = make_canonical_execution_authorization_v2(
        request=request,
        disposition=AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2h",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact canonical input execution to staging",
    )
    assert auth.as_record()["schema_id"] == "relate-family-canonical-execution-authorization-v2"
    assert auth.as_record()["canonical_executor_source_identity"] == request.as_record()[
        "canonical_executor_source_identity"
    ]
    assert (
        validate_executable_canonical_authorization_v2(
            request=request,
            authorization=auth,
            repo_root=Path.cwd(),
            review_packet=packet,
            evidence_bundle=bundle,
        ).status
        == "AUTHORIZED"
    )
    canonical_execution_authorization_v2_from_record(auth.as_record())


def test_withheld_v2_execution_does_not_claim(tmp_path: Path) -> None:
    request, packet, bundle = _v2_request(tmp_path)
    auth = make_canonical_execution_authorization_v2(
        request=request,
        disposition=WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2h",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="withhold execution",
    )
    result = execute_authorized_canonical_family(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        review_packet=packet,
        evidence_bundle=bundle,
    )
    assert result.status.value == "WITHHELD"
    work_dir = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["work_dir"]
    assert not work_dir.exists()


def test_v1_records_are_not_executable(tmp_path: Path) -> None:
    bundle = FamilyEvidenceBundle((), (), ())
    packet = _packet(bundle)
    v1 = make_canonical_execution_request(
        repo_root=Path.cwd(),
        review_packet=packet,
        evidence_bundle=bundle,
        requested_run_id="canonical-run-v1",
        allowed_roles=frozenset({"c0_fit", "c0_iteration", "c0_selection", "c1_reserve"}),
        canonical_input_paths=_paths(),
        expected_identity=_expected(),
        intended_work_dir=Path(".writer") / "stage-2h-tests" / tmp_path.name / "v1-work",
        intended_store_path=Path(".writer") / "stage-2h-tests" / tmp_path.name / "v1.sqlite3",
    )
    with pytest.raises(ValueError, match="validation-only and is not executable"):
        canonical_execution_request_v2_from_record(v1.as_record())
    v1_auth = make_canonical_execution_authorization(
        request=v1,
        disposition=AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2h",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="v1 is historical only",
    )
    with pytest.raises(ValueError, match="validation-only and is not executable"):
        canonical_execution_authorization_v2_from_record(v1_auth.as_record())

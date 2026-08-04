from __future__ import annotations

from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.family.authorization import (
    AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
    WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
    canonical_execution_authorization_from_record,
    canonical_execution_request_commitment,
    make_canonical_execution_authorization,
    make_canonical_execution_request,
    validate_canonical_execution_authorization,
)
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


def _request(tmp_path: Path):
    bundle = FamilyEvidenceBundle((), (), ())
    packet = _packet(bundle)
    stem = tmp_path.name.replace("\\", "-").replace("/", "-")
    work_dir = Path(".writer") / "stage-2g-tests" / stem / "work"
    store_path = Path(".writer") / "stage-2g-tests" / stem / "store.sqlite3"
    (Path.cwd() / store_path).unlink(missing_ok=True)
    request = make_canonical_execution_request(
        repo_root=Path.cwd(),
        review_packet=packet,
        evidence_bundle=bundle,
        requested_run_id="canonical-run-1",
        allowed_roles=frozenset({"c0_fit", "c0_iteration", "c0_selection", "c1_reserve"}),
        canonical_input_paths=_paths(),
        expected_identity=_expected(),
        intended_work_dir=work_dir,
        intended_store_path=store_path,
    )
    return request, packet, bundle


def test_request_is_deterministic_and_binds_prohibitions(tmp_path: Path) -> None:
    first, _packet_value, _bundle = _request(tmp_path)
    second, _packet_value, _bundle = _request(tmp_path)
    assert canonical_execution_request_commitment(first) == (
        canonical_execution_request_commitment(second)
    )
    record = first.as_record()
    assert "CANONICAL_RESULT_PUBLICATION" in record["prohibitions"]
    assert "publication_destination" not in record


def test_request_rejects_noncanonical_input_path(tmp_path: Path) -> None:
    bundle = FamilyEvidenceBundle((), (), ())
    packet = _packet(bundle)
    bad_paths = _paths()
    bad_paths = FamilyProtocolInputPaths(
        allocation_manifest=tmp_path / "allocation.jsonl",
        firewall_publication=bad_paths.firewall_publication,
        d1_result=bad_paths.d1_result,
        d1_1_classification=bad_paths.d1_1_classification,
    )
    with pytest.raises(ValueError, match="artifacts/canonical"):
        make_canonical_execution_request(
            repo_root=Path.cwd(),
            review_packet=packet,
            evidence_bundle=bundle,
            requested_run_id="run",
            allowed_roles=frozenset({"c0_fit", "c0_iteration", "c0_selection", "c1_reserve"}),
            canonical_input_paths=bad_paths,
            expected_identity=_expected(),
            intended_work_dir=tmp_path / "work",
            intended_store_path=tmp_path / "store.sqlite3",
        )


def test_authorization_validation_authorized_and_withheld(tmp_path: Path) -> None:
    request, packet, bundle = _request(tmp_path)
    auth = make_canonical_execution_authorization(
        request=request,
        disposition=AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2g",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact future execution",
    )
    result = validate_canonical_execution_authorization(
        request=request,
        authorization=auth,
        repo_root=Path.cwd(),
        review_packet=packet,
        evidence_bundle=bundle,
    )
    assert result.status == "AUTHORIZED"
    withheld = make_canonical_execution_authorization(
        request=request,
        disposition=WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2g",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="withhold exact future execution",
    )
    assert (
        validate_canonical_execution_authorization(
            request=request,
            authorization=withheld,
            repo_root=Path.cwd(),
            review_packet=packet,
            evidence_bundle=bundle,
        ).status
        == "WITHHELD"
    )


def test_publication_disposition_string_rejected(tmp_path: Path) -> None:
    request, _packet_value, _bundle = _request(tmp_path)
    with pytest.raises(ValueError, match="invalid canonical"):
        make_canonical_execution_authorization(
            request=request,
            disposition="AUTHORIZE_BOUNDED_REVIEW_PUBLICATION",
            reviewer_identity="reviewer:2g",
            review_timestamp="2026-08-03T12:00:00+00:00",
            bounded_reason="wrong authorization class",
        )


def test_tampered_authorization_id_rejected(tmp_path: Path) -> None:
    request, _packet_value, _bundle = _request(tmp_path)
    auth = make_canonical_execution_authorization(
        request=request,
        disposition=AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2g",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact future execution",
    ).as_record()
    auth["authorization_id"] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        canonical_execution_authorization_from_record(auth)


def test_populated_staging_store_invalidates_authorization(tmp_path: Path) -> None:
    request, packet, bundle = _request(tmp_path)
    auth = make_canonical_execution_authorization(
        request=request,
        disposition=AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2g",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact future execution",
    )
    store = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["fresh_store_path"]
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text("not fresh", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="no longer fresh"):
            validate_canonical_execution_authorization(
                request=request,
                authorization=auth,
                repo_root=Path.cwd(),
                review_packet=packet,
                evidence_bundle=bundle,
            )
    finally:
        store.unlink(missing_ok=True)

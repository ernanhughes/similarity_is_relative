from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.hashing import sha256_file
from relate.family.authorization import (
    AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
    make_canonical_execution_authorization_v2,
    make_canonical_execution_request_v2,
)
from relate.family.execution_review import (
    ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
    WITHHOLD_EXECUTION_EVIDENCE,
    bounded_scientific_payload_commitment,
    canonical_execution_review_report_from_record,
    inspect_authorized_canonical_execution,
    make_canonical_execution_review_disposition,
    write_canonical_execution_review_bundle,
)
from relate.family.review import FamilyReviewPacket, family_review_packet_commitment
from relate.family.store import CACHE_SCHEMA_ID, FamilyGraphCache, make_cache_identity
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
    return FamilyReviewPacket(
        {
            "schema_id": "relate-family-review-packet-v1",
            "family_protocol_sha256": historical.protocol_contract()["protocol_sha256"],
            "workflow": {
                "name": FAMILY_GRAPH_WORKFLOW_NAME,
                "version": FAMILY_GRAPH_WORKFLOW_VERSION,
                "run_id": "review-run",
                "run_identity_commitment": "0" * 64,
                "source_identity": compute_family_workflow_source_identity(Path.cwd()),
                "allowed_roles": ["c0_fit", "c0_iteration", "c0_selection", "c1_reserve"],
            },
            "identities": {
                "allocation_manifest_sha256": historical.ALLOCATION_MANIFEST_SHA256,
                "allocation_context_sha256": historical.ALLOCATION_CONTEXT_SHA256,
                "allocation_repository_commitment_sha256": (
                    historical.ALLOCATION_REPOSITORY_COMMITMENT_SHA256
                ),
                "evidence_bundle_commitment": evidence_bundle_commitment(bundle),
                "resolved_edge_commitment": "4" * 64,
                "component_commitment": "5" * 64,
                "graph_readiness_commitment": "6" * 64,
                "role_crossing_analysis_commitment": "7" * 64,
                "bounded_outcome_commitment": "8" * 64,
            },
            "bounded_family_outcome": {"family_graph_outcome": "TEST_OUTCOME"},
            "bounded_role_crossing_analysis": {"cross_role_connecting_components": 0},
            "materiality_inputs": {
                "family_disjoint_allocation_feasibility": {"status": "NOT_ASSESSED"}
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
            "downstream_decisions": {
                "material_contamination": "NOT_DETERMINED",
                "materiality_threshold": "NOT_APPLIED",
                "reallocation_required": "NOT_AUTHORIZED",
                "d2_authorization": "NOT_AUTHORIZED",
            },
        }
    )


def _v2_request(tmp_path: Path):
    bundle = FamilyEvidenceBundle((), (), ())
    packet = _packet(bundle)
    staging_root = Path(".writer") / "stage-2i-tests" / f"{tmp_path.name}-{uuid4().hex}"
    request = make_canonical_execution_request_v2(
        repo_root=Path.cwd(),
        review_packet=packet,
        evidence_bundle=bundle,
        requested_run_id="canonical-run-v2",
        allowed_roles=frozenset({"c0_fit", "c0_iteration", "c0_selection", "c1_reserve"}),
        canonical_input_paths=_paths(),
        expected_identity=_expected(),
        intended_work_dir=staging_root,
        intended_store_path=staging_root / "family-graph.sqlite3",
    )
    return request, packet, bundle


def _auth(request):
    return make_canonical_execution_authorization_v2(
        request=request,
        disposition=AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
        reviewer_identity="reviewer:2i",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact execution",
    )


def _packet_like(
    packet: FamilyReviewPacket, *, run_id: str = "canonical-run"
) -> FamilyReviewPacket:
    record = packet.as_record()
    workflow = dict(record["workflow"])
    workflow["run_id"] = run_id
    workflow["run_identity_commitment"] = "3" * 64
    return FamilyReviewPacket({**record, "workflow": workflow})


def _claim(request, auth) -> dict:
    record = request.as_record()
    from relate.family.execution import _claim_record

    return _claim_record(
        request_record=record,
        request_commitment=record["request_commitment"],
        authorization_id=auth.as_record()["authorization_id"],
        store_path=record["intended_noncanonical_staging"]["fresh_store_path"],
    )


def _receipt(request, auth, claim, *, status: str, packet_commitment: str | None = None) -> dict:
    record = request.as_record()
    staging = record["intended_noncanonical_staging"]
    steps = []
    names = (
        (
            "verify_family_inputs",
            "register_allocation",
            "register_prepared_evidence",
            "resolve_candidates",
            "assess_graph_readiness",
            "build_family_components",
            "analyse_role_crossings",
            "determine_family_outcome",
        )
        if status == "COMPLETED"
        else (
            "verify_family_inputs",
            "register_allocation",
            "register_prepared_evidence",
            "resolve_candidates",
            "assess_graph_readiness",
        )
    )
    for index, name in enumerate(names):
        step_status = "BLOCKED" if status == "BLOCKED" and index == len(names) - 1 else "COMPLETED"
        steps.append(
            {
                "step_name": name,
                "step_version": "1",
                "status": step_status,
                "input_commitment": f"{index + 1:064x}",
                "output_commitment": f"{index + 11:064x}",
                **({"blocked_reason": "FAKE_BLOCKED"} if step_status == "BLOCKED" else {}),
            }
        )
    from relate.family.execution import _commit

    payload = {
        "schema_id": "relate-family-authorized-canonical-execution-receipt-v1",
        "execution_status": status,
        "family_protocol_sha256": record["family_protocol_sha256"],
        "workflow_name": record["workflow_name"],
        "workflow_version": record["workflow_version"],
        "requested_run_id": record["requested_run_id"],
        "workflow_source_identity": record["workflow_source_identity"],
        "canonical_executor_source_identity": record["canonical_executor_source_identity"],
        "authorised_runner_source_identity": "1" * 64,
        "canonical_execution_request_commitment": record["request_commitment"],
        "canonical_execution_authorization_id": auth.as_record()["authorization_id"],
        "claim_commitment": claim["claim_commitment"],
        "canonical_inputs": dict(record["canonical_inputs"]),
        "staging_work_directory": staging["work_dir"],
        "staging_store_path": staging["fresh_store_path"],
        "store_identity_mapping": {
            "family_protocol_sha256": record["family_protocol_sha256"],
            "allocation_manifest_sha256": record["canonical_inputs"]["allocation_manifest_sha256"],
            "allocation_context_sha256": record["canonical_inputs"]["allocation_context_sha256"],
            "d1_audit_result_sha256": record["canonical_inputs"]["d1_result_sha256"],
            "d1_1_classification_sha256": record["canonical_inputs"]["d1_1_classification_sha256"],
            "cache_schema_version": CACHE_SCHEMA_ID,
            "family_runner_source_identity": "1" * 64,
        },
        "workflow_run_identity_commitment": "3" * 64,
        "ordered_steps": steps,
        "continuing_prohibitions": list(record["prohibitions"]),
        **(
            {"canonical_run_review_packet_commitment": packet_commitment}
            if packet_commitment is not None
            else {}
        ),
    }
    return _commit(payload, "receipt_commitment")


def _trace(receipt: dict | None = None) -> dict:
    events = []
    if receipt is not None:
        for step in receipt["ordered_steps"]:
            events.append(
                {
                    "event_type": "STEP_STARTED",
                    "step_name": step["step_name"],
                    "step_version": "1",
                    "timestamp": "2026-08-03T12:00:00+00:00",
                    "input_commitment": step["input_commitment"],
                    "output_commitment": None,
                    "latency_seconds": None,
                    "blocked_reason": None,
                    "failure_message": None,
                }
            )
            events.append(
                {
                    "event_type": "STEP_BLOCKED"
                    if step["status"] == "BLOCKED"
                    else "STEP_COMPLETED",
                    "step_name": step["step_name"],
                    "step_version": "1",
                    "timestamp": "2026-08-03T12:00:01+00:00",
                    "input_commitment": step["input_commitment"],
                    "output_commitment": step["output_commitment"],
                    "latency_seconds": 0.1,
                    "blocked_reason": step.get("blocked_reason"),
                    "failure_message": None,
                }
            )
    return {"schema_id": "relate-family-canonical-execution-trace-v1", "events": events}


def _write_completed(tmp_path: Path):
    request, rehearsal_packet, bundle = _v2_request(tmp_path)
    auth = _auth(request)
    work_dir = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["work_dir"]
    work_dir.mkdir(parents=True)
    store = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["fresh_store_path"]
    packet = _packet_like(rehearsal_packet)
    claim = _claim(request, auth)
    receipt = _receipt(
        request,
        auth,
        claim,
        status="COMPLETED",
        packet_commitment=family_review_packet_commitment(packet),
    )
    atomic_write_json(work_dir / "canonical-execution-claim.json", claim)
    atomic_write_json(work_dir / "canonical-execution-review-packet.json", packet.as_record())
    atomic_write_json(work_dir / "canonical-execution-receipt.json", receipt)
    atomic_write_json(work_dir / "canonical-execution-trace.json", _trace(receipt))
    identity = make_cache_identity(**receipt["store_identity_mapping"])
    with FamilyGraphCache(store, identity=identity) as cache:
        identities = packet.as_record()["identities"]
        cache.put_phase_commitment(
            "initial_allocation",
            status="COMPLETE",
            commitment_sha256=identities["allocation_repository_commitment_sha256"],
            metadata={},
        )
        cache.put_phase_commitment(
            "resolved_edges",
            status="COMPLETE",
            commitment_sha256=identities["resolved_edge_commitment"],
            metadata={},
        )
        cache.put_phase_commitment(
            "family_components",
            status="COMPLETE",
            commitment_sha256=identities["component_commitment"],
            metadata={},
        )
        cache.put_phase_commitment(
            "graph_readiness",
            status="COMPLETE",
            commitment_sha256=identities["graph_readiness_commitment"],
            metadata={},
        )
        cache.put_phase_commitment(
            "role_crossing_analysis",
            status="COMPLETE",
            commitment_sha256=identities["role_crossing_analysis_commitment"],
            metadata={},
        )
        cache.put_phase_commitment(
            "family_outcome",
            status="COMPLETE",
            commitment_sha256=identities["bounded_outcome_commitment"],
            metadata={},
        )
    return request, auth, rehearsal_packet, bundle, work_dir


def test_completed_execution_review_report_is_eligible(tmp_path: Path) -> None:
    request, auth, packet, bundle, work_dir = _write_completed(tmp_path)
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    record = report.as_record()
    assert record["terminal_execution_status"] == "VALID_COMPLETED"
    assert record["eligible_for_publication_authorization_review"] is True
    assert record["scientific_payload_equivalence"]["matches"] is True


def test_completed_review_rejects_placeholder_store(tmp_path: Path) -> None:
    request, auth, packet, bundle, work_dir = _write_completed(tmp_path)
    store = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["fresh_store_path"]
    store.unlink()
    store.write_text("placeholder", encoding="utf-8")
    with pytest.raises(Exception, match="file is not a database|malformed|schema"):
        inspect_authorized_canonical_execution(
            repo_root=Path.cwd(),
            request=request,
            authorization=auth,
            authorization_review_packet=packet,
            evidence_bundle=bundle,
            work_dir=work_dir,
        )


def test_completed_review_rejects_empty_trace(tmp_path: Path) -> None:
    request, auth, packet, bundle, work_dir = _write_completed(tmp_path)
    atomic_write_json(work_dir / "canonical-execution-trace.json", _trace(None))
    with pytest.raises(ValueError, match="nonempty|count"):
        inspect_authorized_canonical_execution(
            repo_root=Path.cwd(),
            request=request,
            authorization=auth,
            authorization_review_packet=packet,
            evidence_bundle=bundle,
            work_dir=work_dir,
        )


def test_blocked_execution_review_is_not_eligible(tmp_path: Path) -> None:
    request, rehearsal_packet, bundle = _v2_request(tmp_path)
    auth = _auth(request)
    work_dir = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["work_dir"]
    work_dir.mkdir(parents=True)
    claim = _claim(request, auth)
    receipt = _receipt(request, auth, claim, status="BLOCKED")
    atomic_write_json(work_dir / "canonical-execution-claim.json", claim)
    atomic_write_json(work_dir / "canonical-execution-receipt.json", receipt)
    atomic_write_json(work_dir / "canonical-execution-trace.json", _trace(receipt))
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=rehearsal_packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    assert report.as_record()["terminal_execution_status"] == "VALID_BLOCKED"
    assert report.as_record()["eligible_for_publication_authorization_review"] is False


def test_failure_before_claim_persisted_is_valid_terminal_state(tmp_path: Path) -> None:
    request, rehearsal_packet, bundle = _v2_request(tmp_path)
    auth = _auth(request)
    work_dir = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["work_dir"]
    work_dir.mkdir(parents=True)
    atomic_write_json(
        work_dir / "canonical-execution-failure.json",
        {
            "schema_id": "relate-family-canonical-execution-failure-v1",
            "canonical_execution_request_commitment": request.as_record()["request_commitment"],
            "canonical_execution_authorization_id": auth.as_record()["authorization_id"],
            "failed_step": None,
            "bounded_exception_type": "RuntimeError",
            "bounded_message": "claim construction failed",
        },
    )
    atomic_write_json(work_dir / "canonical-execution-trace.json", _trace(None))
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=rehearsal_packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    assert report.as_record()["terminal_execution_status"] == "FAILED_BEFORE_CLAIM_PERSISTED"


def test_conflicting_receipt_and_failure_rejected(tmp_path: Path) -> None:
    request, auth, packet, bundle, work_dir = _write_completed(tmp_path)
    atomic_write_json(
        work_dir / "canonical-execution-failure.json",
        {
            "schema_id": "relate-family-canonical-execution-failure-v1",
            "canonical_execution_request_commitment": request.as_record()["request_commitment"],
            "canonical_execution_authorization_id": auth.as_record()["authorization_id"],
            "failed_step": None,
            "bounded_exception_type": "RuntimeError",
            "bounded_message": "conflict",
        },
    )
    with pytest.raises(ValueError, match="conflict"):
        inspect_authorized_canonical_execution(
            repo_root=Path.cwd(),
            request=request,
            authorization=auth,
            authorization_review_packet=packet,
            evidence_bundle=bundle,
            work_dir=work_dir,
        )


def test_scientific_payload_ignores_run_identity_but_not_science(tmp_path: Path) -> None:
    _request, packet, _bundle = _v2_request(tmp_path)
    first = _packet_like(packet, run_id="a")
    second = _packet_like(packet, run_id="b")
    assert bounded_scientific_payload_commitment(first) == bounded_scientific_payload_commitment(
        second
    )
    changed = second.as_record()
    changed["firewall_declarations"] = {
        **changed["firewall_declarations"],
        "hidden_row_content_accessed": True,
    }
    assert bounded_scientific_payload_commitment(first) != bounded_scientific_payload_commitment(
        FamilyReviewPacket(changed)
    )


def test_disposition_and_bundle_are_noncanonical_and_immutable(tmp_path: Path) -> None:
    request, auth, packet, bundle, work_dir = _write_completed(tmp_path)
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    disposition = make_canonical_execution_review_disposition(
        report=report,
        disposition=ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
        reviewer_identity="reviewer:2i",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="accept for later publication authorization review",
    )
    output = tmp_path / "review-bundle.json"
    receipt = write_canonical_execution_review_bundle(
        report=report,
        disposition=disposition,
        destination=output,
        repo_root=Path.cwd(),
    )
    assert receipt.bundle_file_sha256 == sha256_file(output)
    with pytest.raises(FileExistsError):
        write_canonical_execution_review_bundle(
            report=report,
            disposition=disposition,
            destination=output,
            repo_root=Path.cwd(),
        )


def test_forged_failed_report_with_eligibility_is_rejected(tmp_path: Path) -> None:
    request, auth, packet, bundle, work_dir = _write_completed(tmp_path)
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    forged = report.as_record()
    forged["terminal_execution_status"] = "VALID_FAILED"
    from relate.evidence.canonical_json import canonical_json_compact_unicode
    from relate.evidence.hashing import sha256_text

    payload = dict(forged)
    payload.pop("report_commitment")
    forged["report_commitment"] = sha256_text(canonical_json_compact_unicode(payload))
    with pytest.raises(ValueError, match="eligibility"):
        canonical_execution_review_report_from_record(forged)


def test_bundle_rejects_forged_acceptance_for_blocked_report(tmp_path: Path) -> None:
    request, rehearsal_packet, bundle = _v2_request(tmp_path)
    auth = _auth(request)
    work_dir = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["work_dir"]
    work_dir.mkdir(parents=True)
    claim = _claim(request, auth)
    receipt = _receipt(request, auth, claim, status="BLOCKED")
    atomic_write_json(work_dir / "canonical-execution-claim.json", claim)
    atomic_write_json(work_dir / "canonical-execution-receipt.json", receipt)
    atomic_write_json(work_dir / "canonical-execution-trace.json", _trace(receipt))
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=rehearsal_packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    disposition = make_canonical_execution_review_disposition(
        report=report,
        disposition=WITHHOLD_EXECUTION_EVIDENCE,
        reviewer_identity="reviewer:2i",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="blocked evidence",
    ).as_record()
    disposition["disposition"] = ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW
    from relate.evidence.canonical_json import canonical_json_compact_unicode
    from relate.evidence.hashing import sha256_text
    from relate.family.execution_review import CanonicalExecutionReviewDisposition

    payload = dict(disposition)
    payload.pop("disposition_id")
    disposition["disposition_id"] = sha256_text(canonical_json_compact_unicode(payload))
    with pytest.raises(ValueError, match="not eligible"):
        write_canonical_execution_review_bundle(
            report=report,
            disposition=CanonicalExecutionReviewDisposition(record=disposition),
            destination=tmp_path / "forged.json",
            repo_root=Path.cwd(),
        )


def test_acceptance_rejected_for_blocked_report(tmp_path: Path) -> None:
    request, rehearsal_packet, bundle = _v2_request(tmp_path)
    auth = _auth(request)
    work_dir = Path.cwd() / request.as_record()["intended_noncanonical_staging"]["work_dir"]
    work_dir.mkdir(parents=True)
    claim = _claim(request, auth)
    receipt = _receipt(request, auth, claim, status="BLOCKED")
    atomic_write_json(work_dir / "canonical-execution-claim.json", claim)
    atomic_write_json(work_dir / "canonical-execution-receipt.json", receipt)
    atomic_write_json(work_dir / "canonical-execution-trace.json", _trace(receipt))
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=rehearsal_packet,
        evidence_bundle=bundle,
        work_dir=work_dir,
    )
    with pytest.raises(ValueError, match="not eligible"):
        make_canonical_execution_review_disposition(
            report=report,
            disposition=ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
            reviewer_identity="reviewer:2i",
            review_timestamp="2026-08-03T12:00:00+00:00",
            bounded_reason="cannot accept",
        )
    withheld = make_canonical_execution_review_disposition(
        report=report,
        disposition=WITHHOLD_EXECUTION_EVIDENCE,
        reviewer_identity="reviewer:2i",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="blocked evidence",
    )
    assert withheld.as_record()["disposition"] == WITHHOLD_EXECUTION_EVIDENCE


def test_execution_review_module_does_not_execute_or_import_experiments() -> None:
    path = Path("src/relate/family/execution_review.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "relate.experiments"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "execute_authorized_canonical_family"

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from relate.cli.family import EXIT_OK, main
from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.canonical_json import canonical_json_compact_unicode
from relate.evidence.hashing import sha256_file, sha256_text
from relate.family.canonical_publication import execute_authorized_canonical_publication
from relate.family.canonical_publication_authorization import (
    AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    make_canonical_family_publication_authorization,
    make_canonical_family_publication_request,
)
from relate.family.canonical_publication_review import (
    CLOSE_COMPLETED_CANONICAL_PUBLICATION,
    WITHHOLD_CANONICAL_PUBLICATION_CLOSURE,
    canonical_publication_closure_bundle_from_record,
    canonical_publication_closure_disposition_from_record,
    canonical_publication_evidence_review_report_from_record,
    canonical_publication_trace_from_record,
    inspect_canonical_publication_evidence,
    make_canonical_publication_closure_disposition,
    write_canonical_publication_closure_bundle,
)
from tests_current.family_canonical_publication.test_canonical_publication import _chain


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _execute(chain: dict) -> None:
    execute_authorized_canonical_publication(
        repo_root=chain["repo"],
        stage_2j_request=chain["stage2j_request"],
        stage_2j_authorization=chain["stage2j_auth"],
        executable_request=chain["exec_request"],
        executable_authorization=chain["exec_auth"],
        candidate_file=chain["candidate_path"],
        execution_review_bundle_file=chain["bundle_path"],
        stage_2j_request_file_sha256=sha256_file(chain["stage2j_request_path"]),
        stage_2j_authorization_file_sha256=sha256_file(chain["stage2j_auth_path"]),
    )


def _commit_record(record: dict, field: str) -> dict:
    payload = dict(record)
    payload.pop(field, None)
    return {**payload, field: sha256_text(canonical_json_compact_unicode(payload))}


def _inspect(chain: dict):
    return inspect_canonical_publication_evidence(
        repo_root=chain["repo"],
        stage_2j_request=chain["stage2j_request"],
        stage_2j_request_file_sha256=sha256_file(chain["stage2j_request_path"]),
        stage_2j_authorization=chain["stage2j_auth"],
        stage_2j_authorization_file_sha256=sha256_file(chain["stage2j_auth_path"]),
        executable_request=chain["exec_request"],
        executable_request_file_sha256=sha256_file(chain["exec_request_path"]),
        executable_authorization=chain["exec_auth"],
        executable_authorization_file_sha256=sha256_file(chain["exec_auth_path"]),
        candidate_file=chain["candidate_path"],
        execution_review_bundle_file=chain["bundle_path"],
    )


def test_completed_publication_review_and_closure_bundle(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    report = _inspect(chain)
    record = report.as_record()
    audit = chain["repo"] / ".writer/stage-2k/audit"
    assert record["terminal_status"] == "VALID_COMPLETED"
    assert record["publication_completed"] is True
    assert record["canonical_artifact_exact_bytes_verified"] is True
    assert record["closure_eligibility"]["completed_publication_closure"] is True
    assert record["file_sha256"]["trace"] == sha256_file(
        audit / "canonical-publication-trace.json"
    )
    receipt = _read(audit / "canonical-publication-receipt.json")
    assert receipt["trace_file_sha256"] == record["file_sha256"]["trace"]
    parsed = canonical_publication_evidence_review_report_from_record(record)
    disposition = make_canonical_publication_closure_disposition(
        report=parsed,
        disposition=CLOSE_COMPLETED_CANONICAL_PUBLICATION,
        reviewer_identity="reviewer:2l",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="close completed canonical publication evidence",
    )
    out = tmp_path / "closure-bundle.json"
    bundle = write_canonical_publication_closure_bundle(
        report=parsed,
        disposition=disposition,
        destination=out,
        repo_root=chain["repo"],
    )
    assert canonical_publication_closure_bundle_from_record(
        _read(out)
    ).as_record() == bundle.as_record()


def test_receipt_trace_sha_mismatch_rejected(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    audit = chain["repo"] / ".writer/stage-2k/audit"
    trace = _read(audit / "canonical-publication-trace.json")
    trace["events"][0]["timestamp"] = "2026-08-03T12:00:01+00:00"
    atomic_write_json(audit / "canonical-publication-trace.json", trace)
    with pytest.raises(ValueError, match="trace SHA"):
        _inspect(chain)


def test_receipt_and_failure_conflict_rejected(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    audit = chain["repo"] / ".writer/stage-2k/audit"
    failure = {
        "schema_id": "relate-family-canonical-publication-failure-v1",
        "executable_request_commitment": chain["exec_request"].as_record()[
            "request_commitment"
        ],
        "executable_authorization_id": chain["exec_auth"].as_record()["authorization_id"],
        "stage_2j_publication_request_commitment": chain["stage2j_request"].as_record()[
            "request_commitment"
        ],
        "stage_2j_publication_authorization_id": chain["stage2j_auth"].as_record()[
            "authorization_id"
        ],
        "canonical_destination": "artifacts/canonical/option-c0/result.json",
        "canonical_publication_candidate_commitment": chain["candidate"].as_record()[
            "candidate_commitment"
        ],
        "canonical_publication_candidate_file_sha256": sha256_file(
            chain["candidate_path"]
        ),
        "failed_phase": "PUBLICATION_EXECUTION",
        "bounded_exception_type": "RuntimeError",
        "bounded_message": "conflict",
        "claim_persisted": True,
        "canonical_parent_created": [],
        "canonical_file_created": True,
        "canonical_file_sha256": sha256_file(
            chain["repo"] / "artifacts/canonical/option-c0/result.json"
        ),
        "receipt_persisted": False,
        "failure_timestamp": "2026-08-03T12:00:00+00:00",
    }
    from relate.evidence.canonical_json import canonical_json_compact_unicode
    from relate.evidence.hashing import sha256_text

    failure["failure_commitment"] = sha256_text(canonical_json_compact_unicode(failure))
    atomic_write_json(audit / "canonical-publication-failure.json", failure)
    with pytest.raises(ValueError, match="conflict"):
        _inspect(chain)


def test_trace_rejects_receipt_persisted_event(tmp_path: Path) -> None:
    trace = {
        "schema_id": "relate-family-canonical-publication-trace-v1",
        "events": [
            {
                "event_type": "RECEIPT_PERSISTED",
                "timestamp": "2026-08-03T12:00:00+00:00",
            }
        ],
    }
    with pytest.raises(ValueError, match="unsupported|receipt"):
        canonical_publication_trace_from_record(trace)


def test_disposition_rules_reject_completed_closure_for_incomplete_report(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    (chain["repo"] / ".writer/stage-2k/audit").mkdir(parents=True)
    claim = {
        **chain["exec_request"].as_record(),
    }
    # Claim-only evidence is incomplete; withholding remains available.
    report = _inspect_incomplete_claim_only(chain)
    with pytest.raises(ValueError, match="not eligible"):
        make_canonical_publication_closure_disposition(
            report=report,
            disposition=CLOSE_COMPLETED_CANONICAL_PUBLICATION,
            reviewer_identity="reviewer:2l",
            review_timestamp="2026-08-03T12:00:00+00:00",
            bounded_reason="cannot close incomplete evidence",
        )
    withheld = make_canonical_publication_closure_disposition(
        report=report,
        disposition=WITHHOLD_CANONICAL_PUBLICATION_CLOSURE,
        reviewer_identity="reviewer:2l",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="withhold incomplete evidence",
    )
    assert canonical_publication_closure_disposition_from_record(
        withheld.as_record(), report=report
    ).as_record() == withheld.as_record()
    assert claim


def _inspect_incomplete_claim_only(chain: dict):
    from relate.family.canonical_publication import _claim

    audit = chain["repo"] / ".writer/stage-2k/audit"
    claim = _claim(chain["exec_request"].as_record(), chain["exec_auth"].as_record())
    atomic_write_json(audit / "canonical-publication-claim.json", claim)
    return _inspect(chain)


def test_report_parser_rejects_completed_without_receipt_and_exact_artifact(
    tmp_path: Path,
) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    report = _inspect(chain).as_record()
    forged = {
        **report,
        "canonical_artifact_exists": False,
        "canonical_artifact_exact_bytes_verified": False,
        "audit_finalization_completed": False,
        "receipt_commitment": None,
        "canonical_destination_file_sha256": None,
    }
    forged["canonical_byte_validation_summary"] = {
        **forged["canonical_byte_validation_summary"],
        "destination_exists": False,
        "exact_bytes_verified": False,
        "destination_sha256": None,
    }
    forged = _commit_record(forged, "report_commitment")
    with pytest.raises(ValueError, match="terminal status|completed report"):
        canonical_publication_evidence_review_report_from_record(forged)


def test_disposition_parser_rejects_ineligible_disposition(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    report = _inspect_incomplete_claim_only(chain)
    record = {
        "schema_id": "relate-family-canonical-publication-closure-disposition-v1",
        "review_report_commitment": report.as_record()["report_commitment"],
        "terminal_status": report.as_record()["terminal_status"],
        "family_protocol_sha256": report.as_record()["family_protocol_sha256"],
        "executable_request_commitment": report.as_record()["executable_request_commitment"],
        "executable_authorization_id": report.as_record()["executable_authorization_id"],
        "candidate_commitment": report.as_record()["candidate_commitment"],
        "canonical_destination": report.as_record()["canonical_destination"],
        "canonical_destination_file_sha256": report.as_record()[
            "canonical_destination_file_sha256"
        ],
        "review_scope": "CANONICAL_PUBLICATION_EVIDENCE_INTEGRITY_AND_CLOSURE_ONLY",
        "disposition": CLOSE_COMPLETED_CANONICAL_PUBLICATION,
        "reviewer_identity": "reviewer:2l",
        "review_timestamp": "2026-08-03T12:00:00+00:00",
        "bounded_reason": "forged completed closure",
        "continuing_prohibitions": list(report.as_record()["continuing_prohibitions"]),
    }
    record = _commit_record(record, "disposition_id")
    with pytest.raises(ValueError, match="not eligible"):
        canonical_publication_closure_disposition_from_record(record, report=report)


def test_disposition_parser_rejects_mirrored_field_mismatch(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    report = _inspect(chain)
    disposition = make_canonical_publication_closure_disposition(
        report=report,
        disposition=CLOSE_COMPLETED_CANONICAL_PUBLICATION,
        reviewer_identity="reviewer:2l",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="close completed publication evidence",
    ).as_record()
    forged = _commit_record(
        {**disposition, "canonical_destination": "artifacts/canonical/other.json"},
        "disposition_id",
    )
    with pytest.raises(ValueError, match="canonical_destination mismatch"):
        canonical_publication_closure_disposition_from_record(forged, report=report)


def test_bundle_parser_rejects_top_level_report_mismatch(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    report = _inspect(chain)
    disposition = make_canonical_publication_closure_disposition(
        report=report,
        disposition=CLOSE_COMPLETED_CANONICAL_PUBLICATION,
        reviewer_identity="reviewer:2l",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="close completed publication evidence",
    )
    bundle = canonical_publication_closure_bundle_from_record(
        {
            **write_canonical_publication_closure_bundle(
                report=report,
                disposition=disposition,
                destination=tmp_path / "bundle.json",
                repo_root=chain["repo"],
            ).as_record()
        }
    ).as_record()
    forged = _commit_record(
        {**bundle, "canonical_destination": "artifacts/canonical/other.json"},
        "bundle_commitment",
    )
    with pytest.raises(ValueError, match="canonical_destination mismatch"):
        canonical_publication_closure_bundle_from_record(forged)


def test_historical_chain_rejects_authorization_for_another_stage2j_request(
    tmp_path: Path,
) -> None:
    chain = _chain(tmp_path)
    other_request = make_canonical_family_publication_request(
        repo_root=chain["repo"],
        candidate=chain["candidate"],
        candidate_file_sha256=sha256_file(chain["candidate_path"]),
        execution_review_bundle=chain["bundle"],
        execution_review_bundle_file_sha256=sha256_file(chain["bundle_path"]),
        intended_canonical_destination=Path("artifacts/canonical/option-c0/other.json"),
    )
    other_auth = make_canonical_family_publication_authorization(
        repo_root=chain["repo"],
        request=other_request,
        candidate=chain["candidate"],
        execution_review_bundle=chain["bundle"],
        disposition=AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2k",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize a different Stage 2J request",
    )
    chain = {**chain, "stage2j_auth": other_auth}
    with pytest.raises(ValueError, match="Stage 2J|canonical publication authorization"):
        _inspect(chain)


def test_completed_review_rejects_claim_destination_mismatch(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    audit = chain["repo"] / ".writer/stage-2k/audit"
    claim = _read(audit / "canonical-publication-claim.json")
    claim = _commit_record(
        {**claim, "intended_canonical_destination": "artifacts/canonical/other.json"},
        "claim_commitment",
    )
    atomic_write_json(audit / "canonical-publication-claim.json", claim)
    with pytest.raises(ValueError, match="claim intended_canonical_destination mismatch"):
        _inspect(chain)


def test_completed_review_rejects_receipt_protocol_or_bundle_mismatch(
    tmp_path: Path,
) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    audit = chain["repo"] / ".writer/stage-2k/audit"
    receipt = _read(audit / "canonical-publication-receipt.json")
    receipt = _commit_record(
        {**receipt, "accepted_execution_review_bundle_commitment": "0" * 64},
        "receipt_commitment",
    )
    atomic_write_json(audit / "canonical-publication-receipt.json", receipt)
    with pytest.raises(ValueError, match="receipt accepted_execution_review_bundle_commitment"):
        _inspect(chain)


def test_failed_before_canonical_requires_trace(tmp_path: Path) -> None:
    from relate.family.canonical_publication import _claim

    chain = _chain(tmp_path)
    audit = chain["repo"] / ".writer/stage-2k/audit"
    audit.mkdir(parents=True)
    claim = _claim(chain["exec_request"].as_record(), chain["exec_auth"].as_record())
    atomic_write_json(audit / "canonical-publication-claim.json", claim)
    failure = {
        "schema_id": "relate-family-canonical-publication-failure-v1",
        "executable_request_commitment": chain["exec_request"].as_record()[
            "request_commitment"
        ],
        "executable_authorization_id": chain["exec_auth"].as_record()["authorization_id"],
        "stage_2j_publication_request_commitment": chain["stage2j_request"].as_record()[
            "request_commitment"
        ],
        "stage_2j_publication_authorization_id": chain["stage2j_auth"].as_record()[
            "authorization_id"
        ],
        "canonical_destination": "artifacts/canonical/option-c0/result.json",
        "canonical_publication_candidate_commitment": chain["candidate"].as_record()[
            "candidate_commitment"
        ],
        "canonical_publication_candidate_file_sha256": sha256_file(chain["candidate_path"]),
        "failed_phase": "PUBLICATION_EXECUTION",
        "bounded_exception_type": "RuntimeError",
        "bounded_message": "failed before canonical creation",
        "claim_persisted": True,
        "canonical_parent_created": [],
        "canonical_file_created": False,
        "canonical_file_sha256": None,
        "receipt_persisted": False,
        "failure_timestamp": "2026-08-03T12:00:00+00:00",
    }
    atomic_write_json(
        audit / "canonical-publication-failure.json",
        _commit_record(failure, "failure_commitment"),
    )
    report = _inspect(chain).as_record()
    assert report["terminal_status"] == "INCOMPLETE_TERMINAL_EVIDENCE"
    assert report["failure_validation_summary"]["validated"] is True
    assert report["trace_validation_summary"]["events_validated"] is False


def test_cli_review_disposition_bundle_and_verify(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chain = _chain(tmp_path)
    _execute(chain)
    report_path = tmp_path / "publication-review.json"
    assert main(
        [
            "review-canonical-publication-evidence",
            "--repo-root",
            str(chain["repo"]),
            "--stage-2j-request",
            str(chain["stage2j_request_path"]),
            "--stage-2j-authorization",
            str(chain["stage2j_auth_path"]),
            "--executable-request",
            str(chain["exec_request_path"]),
            "--executable-authorization",
            str(chain["exec_auth_path"]),
            "--candidate",
            str(chain["candidate_path"]),
            "--execution-review-bundle",
            str(chain["bundle_path"]),
            "--output",
            str(report_path),
        ]
    ) == EXIT_OK
    disposition_path = tmp_path / "closure-disposition.json"
    assert main(
        [
            "make-canonical-publication-closure-disposition",
            "--report",
            str(report_path),
            "--disposition",
            CLOSE_COMPLETED_CANONICAL_PUBLICATION,
            "--reviewer",
            "reviewer:2l",
            "--timestamp",
            "2026-08-03T12:00:00+00:00",
            "--reason",
            "close completed publication evidence",
            "--output",
            str(disposition_path),
        ]
    ) == EXIT_OK
    bundle_path = tmp_path / "closure-bundle.json"
    assert main(
        [
            "write-canonical-publication-closure-bundle",
            "--repo-root",
            str(chain["repo"]),
            "--report",
            str(report_path),
            "--disposition",
            str(disposition_path),
            "--output",
            str(bundle_path),
        ]
    ) == EXIT_OK
    assert (
        main(["verify-canonical-publication-closure-bundle", "--bundle", str(bundle_path)])
        == EXIT_OK
    )
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "VERIFIED"


def test_stage_2l_static_boundaries() -> None:
    path = Path("src/relate/family/canonical_publication_review.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "relate.experiments" not in imports
    forbidden = {
        "execute_authorized_canonical_publication",
        "atomic_create_bytes_no_replace",
        "execute_authorized_canonical_family",
        "WorkflowRunner",
        "publish_family_review_bundle",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint(forbidden)
    assert "os.replace" not in source
    assert "unlink(" not in source

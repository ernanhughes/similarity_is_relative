from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from relate.cli.family import EXIT_OK, main
from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.hashing import sha256_file
from relate.family.canonical_publication import execute_authorized_canonical_publication
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

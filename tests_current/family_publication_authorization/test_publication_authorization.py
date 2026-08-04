from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from relate.cli.family import EXIT_BLOCKED_OR_WITHHELD, EXIT_FAILURE, EXIT_OK, main
from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.hashing import sha256_file
from relate.family.canonical_publication_authorization import (
    AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    canonical_family_publication_candidate_commitment,
    canonical_family_publication_candidate_from_record,
    canonical_family_publication_request_commitment,
    compute_canonical_publication_contract_source_identity,
    make_canonical_family_publication_authorization,
    make_canonical_family_publication_candidate,
    make_canonical_family_publication_request,
    validate_canonical_family_publication_authorization,
    validate_intended_canonical_destination,
)
from relate.family.execution_review import (
    ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
    WITHHOLD_EXECUTION_EVIDENCE,
    canonical_execution_review_bundle_from_record,
    inspect_authorized_canonical_execution,
    make_canonical_execution_review_disposition,
    write_canonical_execution_review_bundle,
)
from tests_current.family_execution_review.test_execution_review import (
    _packet_like,
    _v2_request,
    _write_completed,
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _stage2i_inputs(tmp_path: Path):
    request, auth, packet, evidence_bundle, work_dir = _write_completed(tmp_path)
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=packet,
        evidence_bundle=evidence_bundle,
        work_dir=work_dir,
    )
    disposition = make_canonical_execution_review_disposition(
        report=report,
        disposition=ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
        reviewer_identity="reviewer:2j",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="accept for canonical publication authorization review",
    )
    bundle_path = tmp_path / "execution-review-bundle.json"
    write_canonical_execution_review_bundle(
        report=report,
        disposition=disposition,
        destination=bundle_path,
        repo_root=Path.cwd(),
    )
    packet_path = work_dir / "canonical-execution-review-packet.json"
    return (
        canonical_execution_review_bundle_from_record(_read(bundle_path)),
        bundle_path,
        packet_path,
    )


def _candidate_and_request(tmp_path: Path):
    bundle, bundle_path, packet_path = _stage2i_inputs(tmp_path)
    candidate = make_canonical_family_publication_candidate(
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(bundle_path),
        canonical_execution_review_packet=_packet_like(_v2_request(tmp_path)[1]),
        canonical_execution_review_packet_file_sha256=sha256_file(packet_path),
    )
    candidate_path = tmp_path / "candidate.json"
    atomic_write_json(candidate_path, candidate.as_record())
    destination = Path("artifacts/canonical/stage-2j-temp/family-result-v1.json")
    request = make_canonical_family_publication_request(
        repo_root=Path.cwd(),
        candidate=candidate,
        candidate_file_sha256=sha256_file(candidate_path),
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(bundle_path),
        intended_canonical_destination=destination,
    )
    return bundle, bundle_path, candidate, candidate_path, request, destination


def test_execution_review_bundle_parser_rejects_stale_commitment(tmp_path: Path) -> None:
    bundle, _bundle_path, _packet_path = _stage2i_inputs(tmp_path)
    record = bundle.as_record()
    assert canonical_execution_review_bundle_from_record(record).as_record() == record
    record["execution_review_report_commitment"] = "0" * 64
    with pytest.raises(ValueError, match="report commitment"):
        canonical_execution_review_bundle_from_record(record)


def test_withheld_bundle_parses_but_candidate_creation_rejects(tmp_path: Path) -> None:
    request, auth, packet, evidence_bundle, work_dir = _write_completed(tmp_path)
    report = inspect_authorized_canonical_execution(
        repo_root=Path.cwd(),
        request=request,
        authorization=auth,
        authorization_review_packet=packet,
        evidence_bundle=evidence_bundle,
        work_dir=work_dir,
    )
    disposition = make_canonical_execution_review_disposition(
        report=report,
        disposition=WITHHOLD_EXECUTION_EVIDENCE,
        reviewer_identity="reviewer:2j",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="withhold publication authorization review",
    )
    bundle_path = tmp_path / "withheld-bundle.json"
    write_canonical_execution_review_bundle(
        report=report,
        disposition=disposition,
        destination=bundle_path,
        repo_root=Path.cwd(),
    )
    bundle = canonical_execution_review_bundle_from_record(_read(bundle_path))
    with pytest.raises(ValueError, match="not accepted"):
        make_canonical_family_publication_candidate(
            execution_review_bundle=bundle,
            execution_review_bundle_file_sha256=sha256_file(bundle_path),
            canonical_execution_review_packet=_packet_like(packet),
            canonical_execution_review_packet_file_sha256=sha256_file(
                work_dir / "canonical-execution-review-packet.json"
            ),
        )


def test_candidate_request_authorization_and_validation(tmp_path: Path) -> None:
    bundle, bundle_path, candidate, candidate_path, request, destination = _candidate_and_request(
        tmp_path
    )
    assert candidate.as_record()["publication_scope"] == "CANONICAL_BOUNDED_FAMILY_RESULT_ONLY"
    assert request.as_record()["intended_canonical_destination"] == destination.as_posix()
    assert request.as_record()["executable_publication_authority"] is False
    authorization = make_canonical_family_publication_authorization(
        repo_root=Path.cwd(),
        request=request,
        candidate=canonical_family_publication_candidate_from_record(_read(candidate_path)),
        execution_review_bundle=bundle,
        disposition=AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2j",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact absent canonical destination",
    )
    result = validate_canonical_family_publication_authorization(
        repo_root=Path.cwd(),
        request=request,
        authorization=authorization,
        candidate=candidate,
        execution_review_bundle=bundle,
    )
    assert result.as_record() == {
        "schema_id": "relate-family-canonical-publication-authorization-validation-v1",
        "status": "AUTHORIZED",
        "request_commitment": canonical_family_publication_request_commitment(request),
        "authorization_id": authorization.as_record()["authorization_id"],
        "candidate_commitment": canonical_family_publication_candidate_commitment(candidate),
        "intended_canonical_destination": destination.as_posix(),
        "executable_publication_authority": False,
    }
    assert compute_canonical_publication_contract_source_identity(
        Path.cwd()
    ) == request.as_record()["canonical_publication_contract_source_identity"]


def test_withheld_authorization_validates_as_withheld(tmp_path: Path) -> None:
    bundle, _bundle_path, candidate, _candidate_path, request, _destination = (
        _candidate_and_request(tmp_path)
    )
    authorization = make_canonical_family_publication_authorization(
        repo_root=Path.cwd(),
        request=request,
        candidate=candidate,
        execution_review_bundle=bundle,
        disposition=WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2j",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="withhold exact publication",
    )
    result = validate_canonical_family_publication_authorization(
        repo_root=Path.cwd(),
        request=request,
        authorization=authorization,
        candidate=candidate,
        execution_review_bundle=bundle,
    )
    assert result.status == "WITHHELD"


def test_destination_validation_uses_absent_file_under_canonical_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    canonical = repo / "artifacts" / "canonical"
    canonical.mkdir(parents=True)
    destination = repo / "artifacts" / "canonical" / "next" / "result.json"
    assert (
        validate_intended_canonical_destination(repo, destination)
        == "artifacts/canonical/next/result.json"
    )
    assert not destination.exists()
    assert not destination.parent.exists()
    with pytest.raises(ValueError, match="beneath"):
        validate_intended_canonical_destination(
            repo, repo / "artifacts" / "canonical-copy" / "x.json"
        )
    with pytest.raises(ValueError, match="root"):
        validate_intended_canonical_destination(repo, canonical)
    existing = canonical / "exists.json"
    existing.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        validate_intended_canonical_destination(repo, existing)


def test_validator_rejects_destination_created_after_request(tmp_path: Path) -> None:
    bundle, _bundle_path, candidate, _candidate_path, request, _destination = (
        _candidate_and_request(tmp_path)
    )
    authorization = make_canonical_family_publication_authorization(
        repo_root=Path.cwd(),
        request=request,
        candidate=candidate,
        execution_review_bundle=bundle,
        disposition=AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2j",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact absent canonical destination",
    )
    created = Path.cwd() / request.as_record()["intended_canonical_destination"]
    created.parent.mkdir(parents=True, exist_ok=True)
    created.write_text("{}", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="already exists"):
            validate_canonical_family_publication_authorization(
                repo_root=Path.cwd(),
                request=request,
                authorization=authorization,
                candidate=candidate,
                execution_review_bundle=bundle,
            )
    finally:
        created.unlink()
        created.parent.rmdir()


def test_cli_flow_and_withheld_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle, bundle_path, packet_path = _stage2i_inputs(tmp_path)
    candidate_path = tmp_path / "candidate.json"
    assert main(
        [
            "create-canonical-publication-candidate",
            "--execution-review-bundle",
            str(bundle_path),
            "--canonical-execution-review-packet",
            str(packet_path),
            "--output",
            str(candidate_path),
        ]
    ) == EXIT_OK
    request_path = tmp_path / "request.json"
    destination = "artifacts/canonical/stage-2j-cli-temp/family-result-cli-v1.json"
    assert main(
        [
            "create-canonical-publication-request",
            "--repo-root",
            str(Path.cwd()),
            "--candidate",
            str(candidate_path),
            "--execution-review-bundle",
            str(bundle_path),
            "--intended-canonical-destination",
            destination,
            "--output",
            str(request_path),
        ]
    ) == EXIT_OK
    auth_path = tmp_path / "auth.json"
    assert main(
        [
            "make-canonical-publication-authorization",
            "--repo-root",
            str(Path.cwd()),
            "--request",
            str(request_path),
            "--candidate",
            str(candidate_path),
            "--execution-review-bundle",
            str(bundle_path),
            "--disposition",
            WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
            "--reviewer",
            "reviewer:2j",
            "--timestamp",
            "2026-08-03T12:00:00+00:00",
            "--reason",
            "withhold exact publication",
            "--output",
            str(auth_path),
        ]
    ) == EXIT_OK
    assert main(
        [
            "verify-canonical-publication-authorization",
            "--repo-root",
            str(Path.cwd()),
            "--request",
            str(request_path),
            "--authorization",
            str(auth_path),
            "--candidate",
            str(candidate_path),
            "--execution-review-bundle",
            str(bundle_path),
        ]
    ) == EXIT_BLOCKED_OR_WITHHELD
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "WITHHELD"
    assert not (Path.cwd() / destination).exists()
    assert main(
        [
            "create-canonical-publication-candidate",
            "--execution-review-bundle",
            str(bundle_path),
            "--canonical-execution-review-packet",
            str(packet_path),
            "--output",
            str(candidate_path),
        ]
    ) == EXIT_FAILURE


def test_stage_2j_module_static_boundaries() -> None:
    path = Path("src/relate/family/canonical_publication_authorization.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "relate.experiments" not in imports
    forbidden_names = {
        "execute_authorized_canonical_family",
        "publish_family_review_bundle",
        "atomic_write_json",
        "WorkflowRunner",
    }
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint(forbidden_names)
    assert "sqlite3" not in source
    assert "hidden_row" not in source

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from relate.cli.family import EXIT_FAILURE, EXIT_OK, main
from relate.evidence.atomic_io import atomic_create_bytes_no_replace, atomic_write_json
from relate.evidence.hashing import sha256_file
from relate.family.canonical_publication import (
    AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    execute_authorized_canonical_publication,
    make_executable_canonical_family_publication_authorization_v2,
    make_executable_canonical_family_publication_request_v2,
    validate_executable_canonical_publication_authorization,
)
from relate.family.canonical_publication_authorization import (
    AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    make_canonical_family_publication_authorization,
    make_canonical_family_publication_candidate,
    make_canonical_family_publication_request,
)
from relate.family.review import family_review_packet_from_record
from tests_current.family_publication_authorization.test_publication_authorization import (
    _stage2i_inputs,
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_source_tree(repo: Path) -> None:
    shutil.copytree(Path.cwd() / "src", repo / "src")
    (repo / "artifacts" / "canonical").mkdir(parents=True)


def _chain(tmp_path: Path):
    repo = tmp_path / "repo"
    _copy_source_tree(repo)
    bundle, bundle_path, packet_path = _stage2i_inputs(tmp_path)
    candidate = make_canonical_family_publication_candidate(
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(bundle_path),
        canonical_execution_review_packet=family_review_packet_from_record(
            _read(packet_path)
        ),
        canonical_execution_review_packet_file_sha256=sha256_file(packet_path),
    )
    candidate_path = tmp_path / "candidate.json"
    atomic_write_json(candidate_path, candidate.as_record())
    stage2j_request = make_canonical_family_publication_request(
        repo_root=repo,
        candidate=candidate,
        candidate_file_sha256=sha256_file(candidate_path),
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(bundle_path),
        intended_canonical_destination=Path("artifacts/canonical/option-c0/result.json"),
    )
    stage2j_request_path = tmp_path / "stage2j-request.json"
    atomic_write_json(stage2j_request_path, stage2j_request.as_record())
    stage2j_auth = make_canonical_family_publication_authorization(
        repo_root=repo,
        request=stage2j_request,
        candidate=candidate,
        execution_review_bundle=bundle,
        disposition=AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2k",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize Stage 2J chain",
    )
    stage2j_auth_path = tmp_path / "stage2j-auth.json"
    atomic_write_json(stage2j_auth_path, stage2j_auth.as_record())
    executable_request = make_executable_canonical_family_publication_request_v2(
        repo_root=repo,
        stage_2j_request=stage2j_request,
        stage_2j_request_file_sha256=sha256_file(stage2j_request_path),
        stage_2j_authorization=stage2j_auth,
        stage_2j_authorization_file_sha256=sha256_file(stage2j_auth_path),
        candidate=candidate,
        candidate_file_sha256=sha256_file(candidate_path),
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(bundle_path),
        intended_noncanonical_audit_work_dir=Path(".writer/stage-2k/audit"),
    )
    executable_request_path = tmp_path / "exec-request.json"
    atomic_write_json(executable_request_path, executable_request.as_record())
    executable_auth = make_executable_canonical_family_publication_authorization_v2(
        request=executable_request,
        disposition=AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2k",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="authorize exact one-shot canonical publication",
    )
    executable_auth_path = tmp_path / "exec-auth.json"
    atomic_write_json(executable_auth_path, executable_auth.as_record())
    return {
        "repo": repo,
        "bundle": bundle,
        "bundle_path": bundle_path,
        "candidate": candidate,
        "candidate_path": candidate_path,
        "stage2j_request": stage2j_request,
        "stage2j_request_path": stage2j_request_path,
        "stage2j_auth": stage2j_auth,
        "stage2j_auth_path": stage2j_auth_path,
        "exec_request": executable_request,
        "exec_request_path": executable_request_path,
        "exec_auth": executable_auth,
        "exec_auth_path": executable_auth_path,
    }


def test_atomic_create_bytes_no_replace_preserves_existing(tmp_path: Path) -> None:
    destination = tmp_path / "out.json"
    atomic_create_bytes_no_replace(destination, b'{"ok": true}\n')
    assert destination.read_bytes() == b'{"ok": true}\n'
    with pytest.raises(FileExistsError):
        atomic_create_bytes_no_replace(destination, b"changed")
    assert destination.read_bytes() == b'{"ok": true}\n'
    assert not list(tmp_path.glob(".out.json.tmp-*"))


def test_v2_validation_and_successful_one_shot_execution(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    validation = validate_executable_canonical_publication_authorization(
        repo_root=chain["repo"],
        stage_2j_request=chain["stage2j_request"],
        stage_2j_request_file_sha256=sha256_file(chain["stage2j_request_path"]),
        stage_2j_authorization=chain["stage2j_auth"],
        stage_2j_authorization_file_sha256=sha256_file(chain["stage2j_auth_path"]),
        request=chain["exec_request"],
        authorization=chain["exec_auth"],
        candidate=chain["candidate"],
        candidate_file_sha256=sha256_file(chain["candidate_path"]),
        execution_review_bundle=chain["bundle"],
        execution_review_bundle_file_sha256=sha256_file(chain["bundle_path"]),
    )
    assert validation.executable_publication_authority is True
    result = execute_authorized_canonical_publication(
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
    destination = chain["repo"] / "artifacts/canonical/option-c0/result.json"
    audit = chain["repo"] / ".writer/stage-2k/audit"
    assert result.status.value == "COMPLETED"
    assert destination.read_bytes() == chain["candidate_path"].read_bytes()
    assert sha256_file(destination) == sha256_file(chain["candidate_path"])
    assert (audit / "canonical-publication-claim.json").exists()
    assert (audit / "canonical-publication-trace.json").exists()
    assert (audit / "canonical-publication-receipt.json").exists()
    assert not (audit / "canonical-publication-failure.json").exists()
    with pytest.raises(ValueError, match="already exists"):
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


def test_withheld_v2_execution_has_no_side_effects(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    withheld = make_executable_canonical_family_publication_authorization_v2(
        request=chain["exec_request"],
        disposition=WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        reviewer_identity="reviewer:2k",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="withhold one-shot publication",
    )
    result = execute_authorized_canonical_publication(
        repo_root=chain["repo"],
        stage_2j_request=chain["stage2j_request"],
        stage_2j_authorization=chain["stage2j_auth"],
        executable_request=chain["exec_request"],
        executable_authorization=withheld,
        candidate_file=chain["candidate_path"],
        execution_review_bundle_file=chain["bundle_path"],
        stage_2j_request_file_sha256=sha256_file(chain["stage2j_request_path"]),
        stage_2j_authorization_file_sha256=sha256_file(chain["stage2j_auth_path"]),
    )
    assert result.status.value == "WITHHELD"
    assert not (chain["repo"] / ".writer").exists()
    assert not (chain["repo"] / "artifacts/canonical/option-c0").exists()


def test_post_claim_destination_race_writes_failure_without_replace(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    destination = chain["repo"] / "artifacts/canonical/option-c0/result.json"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"other")
    with pytest.raises(ValueError, match="already exists"):
        validate_executable_canonical_publication_authorization(
            repo_root=chain["repo"],
            stage_2j_request=chain["stage2j_request"],
            stage_2j_request_file_sha256=sha256_file(chain["stage2j_request_path"]),
            stage_2j_authorization=chain["stage2j_auth"],
            stage_2j_authorization_file_sha256=sha256_file(chain["stage2j_auth_path"]),
            request=chain["exec_request"],
            authorization=chain["exec_auth"],
            candidate=chain["candidate"],
            candidate_file_sha256=sha256_file(chain["candidate_path"]),
            execution_review_bundle=chain["bundle"],
            execution_review_bundle_file_sha256=sha256_file(chain["bundle_path"]),
        )
    assert destination.read_bytes() == b"other"


def test_cli_v1_rejection_and_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    chain = _chain(tmp_path)
    assert main(
        [
            "execute-authorized-canonical-publication",
            "--repo-root",
            str(chain["repo"]),
            "--stage-2j-request",
            str(chain["stage2j_request_path"]),
            "--stage-2j-authorization",
            str(chain["stage2j_auth_path"]),
            "--request",
            str(chain["stage2j_request_path"]),
            "--authorization",
            str(chain["stage2j_auth_path"]),
            "--candidate",
            str(chain["candidate_path"]),
            "--execution-review-bundle",
            str(chain["bundle_path"]),
        ]
    ) == EXIT_FAILURE
    assert main(
        [
            "verify-executable-canonical-publication-authorization",
            "--repo-root",
            str(chain["repo"]),
            "--stage-2j-request",
            str(chain["stage2j_request_path"]),
            "--stage-2j-authorization",
            str(chain["stage2j_auth_path"]),
            "--request",
            str(chain["exec_request_path"]),
            "--authorization",
            str(chain["exec_auth_path"]),
            "--candidate",
            str(chain["candidate_path"]),
            "--execution-review-bundle",
            str(chain["bundle_path"]),
        ]
    ) == EXIT_OK
    assert main(
        [
            "execute-authorized-canonical-publication",
            "--repo-root",
            str(chain["repo"]),
            "--stage-2j-request",
            str(chain["stage2j_request_path"]),
            "--stage-2j-authorization",
            str(chain["stage2j_auth_path"]),
            "--request",
            str(chain["exec_request_path"]),
            "--authorization",
            str(chain["exec_auth_path"]),
            "--candidate",
            str(chain["candidate_path"]),
            "--execution-review-bundle",
            str(chain["bundle_path"]),
        ]
    ) == EXIT_OK
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == "COMPLETED"


def test_stage_2k_static_boundaries() -> None:
    path = Path("src/relate/family/canonical_publication.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "relate.experiments" not in imports
    forbidden = {
        "execute_authorized_canonical_family",
        "WorkflowRunner",
        "build_family_graph_workflow",
        "publish_family_review_bundle",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint(forbidden)
    assert "os.replace" not in source
    assert "sqlite3" not in source

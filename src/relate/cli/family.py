"""Supported family workflow and authorization CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from relate.cli.json_io import read_json_object, write_json_object_immutable
from relate.evidence.hashing import sha256_file
from relate.family.authorization import (
    AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
    CANONICAL_EXECUTION_AUTHORIZATION_SCHEMA_ID,
    CANONICAL_EXECUTION_AUTHORIZATION_V2_SCHEMA_ID,
    CANONICAL_EXECUTION_REQUEST_SCHEMA_ID,
    CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID,
    WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
    canonical_execution_authorization_from_record,
    canonical_execution_authorization_v2_from_record,
    canonical_execution_request_commitment,
    canonical_execution_request_from_record,
    canonical_execution_request_v2_from_record,
    make_canonical_execution_authorization,
    make_canonical_execution_authorization_v2,
    make_canonical_execution_request_v2,
    validate_canonical_execution_authorization,
    validate_executable_canonical_authorization_v2,
)
from relate.family.canonical_publication import (
    AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    EXECUTABLE_PUBLICATION_AUTHORIZATION_SCHEMA_ID,
    EXECUTABLE_PUBLICATION_REQUEST_SCHEMA_ID,
    WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    executable_canonical_publication_authorization_v2_from_record,
    executable_canonical_publication_request_commitment,
    executable_canonical_publication_request_v2_from_record,
    execute_authorized_canonical_publication,
    make_executable_canonical_family_publication_authorization_v2,
    make_executable_canonical_family_publication_request_v2,
    validate_executable_canonical_publication_authorization,
)
from relate.family.canonical_publication_authorization import (
    AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
    canonical_family_publication_authorization_from_record,
    canonical_family_publication_candidate_commitment,
    canonical_family_publication_candidate_from_record,
    canonical_family_publication_request_commitment,
    canonical_family_publication_request_from_record,
    make_canonical_family_publication_authorization,
    make_canonical_family_publication_candidate,
    make_canonical_family_publication_request,
    validate_canonical_family_publication_authorization,
)
from relate.family.canonical_publication_review import (
    ACKNOWLEDGE_CANONICAL_ARTIFACT_WITH_INCOMPLETE_AUDIT_FINALIZATION,
    CLOSE_COMPLETED_CANONICAL_PUBLICATION,
    CLOSE_FAILED_PUBLICATION_WITHOUT_CANONICAL_ARTIFACT,
    WITHHOLD_CANONICAL_PUBLICATION_CLOSURE,
    canonical_publication_closure_bundle_commitment,
    canonical_publication_closure_bundle_from_record,
    canonical_publication_closure_disposition_from_record,
    canonical_publication_evidence_review_report_from_record,
    inspect_canonical_publication_evidence,
    make_canonical_publication_closure_disposition,
    write_canonical_publication_closure_bundle,
)
from relate.family.execution import execute_authorized_canonical_family
from relate.family.execution_review import (
    ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
    WITHHOLD_EXECUTION_EVIDENCE,
    canonical_execution_review_bundle_from_record,
    canonical_execution_review_disposition_from_record,
    canonical_execution_review_report_from_record,
    inspect_authorized_canonical_execution,
    make_canonical_execution_review_disposition,
    write_canonical_execution_review_bundle,
)
from relate.family.publication import (
    AUTHORIZE_BOUNDED_REVIEW_PUBLICATION,
    WITHHOLD_BOUNDED_REVIEW_PUBLICATION,
    family_publication_disposition_from_record,
    make_family_publication_disposition,
    publish_family_review_bundle,
)
from relate.family.review import (
    build_family_review_packet,
    family_review_packet_commitment,
    family_review_packet_from_record,
    reject_canonical_path,
)
from relate.family.verification import FamilyProtocolExpectedIdentity, FamilyProtocolInputPaths
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    build_family_graph_workflow,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import (
    FamilyEvidenceBundle,
    FamilyWorkflowConfig,
    family_evidence_bundle_from_record,
)
from relate.workflows import WorkflowExecutionError, WorkflowRunner, WorkflowRunStatus

RUN_CONFIG_SCHEMA_ID = "relate-family-noncanonical-run-config-v1"
EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_BLOCKED_OR_WITHHELD = 3


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True))


def _paths(record: dict[str, Any], key: str = "input_paths") -> FamilyProtocolInputPaths:
    paths = record[key]
    return FamilyProtocolInputPaths(
        allocation_manifest=Path(paths["allocation_manifest"]),
        firewall_publication=Path(paths["firewall_publication"]),
        d1_result=Path(paths["d1_result"]),
        d1_1_classification=Path(paths["d1_1_classification"]),
    )


def _expected(record: dict[str, Any]) -> FamilyProtocolExpectedIdentity:
    item = record["expected_identity"]
    return FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=item["allocation_manifest_sha256"],
        allocation_context_sha256=item["allocation_context_sha256"],
        allocation_repository_commitment_sha256=item["allocation_repository_commitment_sha256"],
        d1_result_sha256=item["d1_result_sha256"],
        d1_1_classification_sha256=item["d1_1_classification_sha256"],
    )


def _load_bundle(path: Path) -> FamilyEvidenceBundle:
    return family_evidence_bundle_from_record(read_json_object(path))


def _load_packet(path: Path):
    return family_review_packet_from_record(read_json_object(path))


def _load_publication_disposition(path: Path):
    return family_publication_disposition_from_record(read_json_object(path))


def _load_execution_review_report(path: Path):
    return canonical_execution_review_report_from_record(read_json_object(path))


def _load_execution_review_disposition(path: Path):
    return canonical_execution_review_disposition_from_record(read_json_object(path))


def _load_execution_review_bundle(path: Path):
    return canonical_execution_review_bundle_from_record(read_json_object(path))


def _reject_canonical_output(path: Path, repo_root: Path, label: str) -> None:
    reject_canonical_path(path, repo_root=repo_root, label=label)
    reject_canonical_path(path.parent, repo_root=repo_root, label=f"{label} parent")


def _cmd_run_noncanonical(args: argparse.Namespace) -> int:
    record = read_json_object(args.config)
    if record.get("schema_id") != RUN_CONFIG_SCHEMA_ID:
        raise ValueError("unsupported noncanonical run config schema")
    repo_root = Path(record["repo_root"]).resolve(strict=False)
    evidence_bundle_path = Path(record["evidence_bundle_path"])
    evidence_bundle = _load_bundle(evidence_bundle_path)
    config = FamilyWorkflowConfig(
        run_id=record["run_id"],
        workflow_name=FAMILY_GRAPH_WORKFLOW_NAME,
        workflow_version=FAMILY_GRAPH_WORKFLOW_VERSION,
        repo_root=repo_root,
        work_dir=Path(record["work_dir"]),
        store_path=Path(record["store_path"]),
        allowed_roles=frozenset(record["allowed_roles"]),
        family_protocol_sha256=record["family_protocol_sha256"],
        expected_identity=_expected(record),
        input_paths=_paths(record),
        allocation_manifest_path=Path(record["allocation_manifest_path"]),
        workflow_source_identity=compute_family_workflow_source_identity(repo_root),
        evidence_bundle=evidence_bundle,
    )
    plan = build_family_graph_workflow(config)
    try:
        result = WorkflowRunner(plan.definition).run(plan.context)
    except WorkflowExecutionError as exc:
        _emit({"status": "FAILED", "failed_step": exc.failed_step_name, "error": str(exc)})
        return EXIT_FAILURE
    if result.status is WorkflowRunStatus.BLOCKED:
        _emit({"status": "BLOCKED", "blocked_step": result.blocked_step})
        return EXIT_BLOCKED_OR_WITHHELD
    packet = build_family_review_packet(plan=plan, result=result)
    destination = Path(record["review_packet_output_path"])
    write_json_object_immutable(destination, packet.as_record())
    _emit(
        {
            "status": "COMPLETED",
            "run_id": result.run_id,
            "review_packet_commitment": family_review_packet_commitment(packet),
            "review_packet_file_sha256": sha256_file(destination),
        }
    )
    return EXIT_OK


def _cmd_make_publication_disposition(args: argparse.Namespace) -> int:
    packet = _load_packet(args.packet)
    reason = (
        args.reason
        if args.reason is not None
        else args.reason_file.read_text(encoding="utf-8")
    )
    disposition = make_family_publication_disposition(
        packet=packet,
        disposition=args.disposition,
        reviewer_identity=args.reviewer,
        review_timestamp=args.timestamp,
        bounded_reason=reason,
    )
    write_json_object_immutable(args.output, disposition.as_record())
    _emit({"status": "CREATED", "disposition_id": disposition.disposition_id})
    return EXIT_OK


def _cmd_publish_review(args: argparse.Namespace) -> int:
    packet = _load_packet(args.packet)
    disposition = _load_publication_disposition(args.disposition)
    receipt = publish_family_review_bundle(
        packet=packet,
        disposition=disposition,
        destination=args.output,
        repo_root=args.repo_root.resolve(strict=False),
    )
    _emit({"status": "PUBLISHED", **receipt.as_record()})
    return EXIT_OK


def _cmd_create_canonical_request(args: argparse.Namespace) -> int:
    config = read_json_object(args.config)
    repo_root = Path(config["repo_root"]).resolve(strict=False)
    packet = _load_packet(Path(config["review_packet_path"]))
    evidence_bundle = _load_bundle(Path(config["evidence_bundle_path"]))
    request = make_canonical_execution_request_v2(
        repo_root=repo_root,
        review_packet=packet,
        evidence_bundle=evidence_bundle,
        requested_run_id=config["requested_run_id"],
        allowed_roles=frozenset(config["allowed_roles"]),
        canonical_input_paths=_paths(config, "canonical_input_paths"),
        expected_identity=_expected(config),
        intended_work_dir=Path(config["intended_work_dir"]),
        intended_store_path=Path(config["intended_store_path"]),
        rehearsal_work_dir=Path(config["rehearsal_work_dir"])
        if config.get("rehearsal_work_dir")
        else None,
        rehearsal_store_path=Path(config["rehearsal_store_path"])
        if config.get("rehearsal_store_path")
        else None,
    )
    write_json_object_immutable(args.output, request.as_record())
    _emit(
        {
            "status": "CREATED",
            "request_commitment": canonical_execution_request_commitment(request),
        }
    )
    return EXIT_OK


def _cmd_make_canonical_authorization(args: argparse.Namespace) -> int:
    raw = read_json_object(args.request)
    request = (
        canonical_execution_request_v2_from_record(raw)
        if raw.get("schema_id") == CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID
        else canonical_execution_request_from_record(raw)
    )
    reason = (
        args.reason
        if args.reason is not None
        else args.reason_file.read_text(encoding="utf-8")
    )
    if request.as_record().get("schema_id") == CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID:
        authorization = make_canonical_execution_authorization_v2(
            request=request,
            disposition=args.disposition,
            reviewer_identity=args.reviewer,
            review_timestamp=args.timestamp,
            bounded_reason=reason,
        )
    else:
        authorization = make_canonical_execution_authorization(
            request=request,
            disposition=args.disposition,
            reviewer_identity=args.reviewer,
            review_timestamp=args.timestamp,
            bounded_reason=reason,
        )
    write_json_object_immutable(args.output, authorization.as_record())
    _emit({"status": "CREATED", "authorization_id": authorization.as_record()["authorization_id"]})
    return EXIT_OK


def _cmd_verify_canonical_authorization(args: argparse.Namespace) -> int:
    raw_request = read_json_object(args.request)
    raw_auth = read_json_object(args.authorization)
    if raw_request.get("schema_id") == CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID:
        request = canonical_execution_request_v2_from_record(raw_request)
        authorization = canonical_execution_authorization_v2_from_record(raw_auth)
        result = validate_executable_canonical_authorization_v2(
            request=request,
            authorization=authorization,
            repo_root=args.repo_root.resolve(strict=False),
            review_packet=_load_packet(args.packet),
            evidence_bundle=_load_bundle(args.evidence_bundle),
        )
    else:
        request = canonical_execution_request_from_record(raw_request)
        authorization = canonical_execution_authorization_from_record(raw_auth)
        result = validate_canonical_execution_authorization(
            request=request,
            authorization=authorization,
            repo_root=args.repo_root.resolve(strict=False),
            review_packet=_load_packet(args.packet),
            evidence_bundle=_load_bundle(args.evidence_bundle),
        )
    _emit(result.as_record())
    return EXIT_OK if result.status == "AUTHORIZED" else EXIT_BLOCKED_OR_WITHHELD


def _cmd_execute_authorized_canonical(args: argparse.Namespace) -> int:
    raw_request = read_json_object(args.request)
    raw_auth = read_json_object(args.authorization)
    if raw_request.get("schema_id") == CANONICAL_EXECUTION_REQUEST_SCHEMA_ID:
        raise ValueError(
            "v1 canonical execution authorization is validation-only and is not executable"
        )
    if raw_auth.get("schema_id") == CANONICAL_EXECUTION_AUTHORIZATION_SCHEMA_ID:
        raise ValueError(
            "v1 canonical execution authorization is validation-only and is not executable"
        )
    if raw_request.get("schema_id") != CANONICAL_EXECUTION_REQUEST_V2_SCHEMA_ID:
        raise ValueError("unsupported executable canonical execution request schema")
    if raw_auth.get("schema_id") != CANONICAL_EXECUTION_AUTHORIZATION_V2_SCHEMA_ID:
        raise ValueError("unsupported executable canonical execution authorization schema")
    result = execute_authorized_canonical_family(
        repo_root=args.repo_root.resolve(strict=False),
        request=canonical_execution_request_v2_from_record(raw_request),
        authorization=canonical_execution_authorization_v2_from_record(raw_auth),
        review_packet=_load_packet(args.review_packet),
        evidence_bundle=_load_bundle(args.evidence_bundle),
    )
    _emit(result.as_summary())
    if result.status.value == "COMPLETED":
        return EXIT_OK
    if result.status.value in {"WITHHELD", "BLOCKED"}:
        return EXIT_BLOCKED_OR_WITHHELD
    return EXIT_FAILURE


def _cmd_review_authorized_canonical_execution(args: argparse.Namespace) -> int:
    request_path = args.request
    authorization_path = args.authorization
    packet_path = args.review_packet
    bundle_path = args.evidence_bundle
    request = canonical_execution_request_v2_from_record(read_json_object(request_path))
    authorization = canonical_execution_authorization_v2_from_record(
        read_json_object(authorization_path)
    )
    report = inspect_authorized_canonical_execution(
        repo_root=args.repo_root.resolve(strict=False),
        request=request,
        authorization=authorization,
        authorization_review_packet=_load_packet(packet_path),
        evidence_bundle=_load_bundle(bundle_path),
        work_dir=args.work_dir,
        file_identities={
            "request": sha256_file(request_path),
            "authorization": sha256_file(authorization_path),
            "authorization_review_packet": sha256_file(packet_path),
            "prepared_evidence_bundle": sha256_file(bundle_path),
        },
    )
    write_json_object_immutable(args.output, report.as_record())
    _emit(
        {
            "status": report.as_record()["terminal_execution_status"],
            "report_commitment": report.report_commitment,
            "eligible_for_publication_authorization_review": report.as_record()[
                "eligible_for_publication_authorization_review"
            ],
        }
    )
    return (
        EXIT_OK
        if report.as_record()["terminal_execution_status"] == "VALID_COMPLETED"
        else EXIT_BLOCKED_OR_WITHHELD
    )


def _cmd_make_execution_review_disposition(args: argparse.Namespace) -> int:
    reason = (
        args.reason
        if args.reason is not None
        else args.reason_file.read_text(encoding="utf-8")
    )
    disposition = make_canonical_execution_review_disposition(
        report=_load_execution_review_report(args.report),
        disposition=args.disposition,
        reviewer_identity=args.reviewer,
        review_timestamp=args.timestamp,
        bounded_reason=reason,
    )
    write_json_object_immutable(args.output, disposition.as_record())
    _emit({"status": "CREATED", "disposition_id": disposition.as_record()["disposition_id"]})
    return EXIT_OK


def _cmd_write_execution_review_bundle(args: argparse.Namespace) -> int:
    receipt = write_canonical_execution_review_bundle(
        report=_load_execution_review_report(args.report),
        disposition=_load_execution_review_disposition(args.disposition),
        destination=args.output,
        repo_root=args.repo_root.resolve(strict=False),
    )
    _emit({"status": "WRITTEN", **receipt.as_record()})
    return EXIT_OK


def _cmd_create_canonical_publication_candidate(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    _reject_canonical_output(args.output, repo_root, "canonical publication candidate")
    bundle = _load_execution_review_bundle(args.execution_review_bundle)
    packet = _load_packet(args.canonical_execution_review_packet)
    candidate = make_canonical_family_publication_candidate(
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(args.execution_review_bundle),
        canonical_execution_review_packet=packet,
        canonical_execution_review_packet_file_sha256=sha256_file(
            args.canonical_execution_review_packet
        ),
    )
    write_json_object_immutable(args.output, candidate.as_record())
    _emit(
        {
            "status": "CREATED",
            "candidate_commitment": canonical_family_publication_candidate_commitment(
                candidate
            ),
            "candidate_file_sha256": sha256_file(args.output),
        }
    )
    return EXIT_OK


def _cmd_create_canonical_publication_request(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve(strict=False)
    _reject_canonical_output(args.output, repo_root, "canonical publication request")
    candidate = canonical_family_publication_candidate_from_record(
        read_json_object(args.candidate)
    )
    bundle = _load_execution_review_bundle(args.execution_review_bundle)
    request = make_canonical_family_publication_request(
        repo_root=repo_root,
        candidate=candidate,
        candidate_file_sha256=sha256_file(args.candidate),
        execution_review_bundle=bundle,
        execution_review_bundle_file_sha256=sha256_file(args.execution_review_bundle),
        intended_canonical_destination=args.intended_canonical_destination,
    )
    write_json_object_immutable(args.output, request.as_record())
    _emit(
        {
            "status": "CREATED",
            "request_commitment": canonical_family_publication_request_commitment(request),
            "request_file_sha256": sha256_file(args.output),
        }
    )
    return EXIT_OK


def _cmd_make_canonical_publication_authorization(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve(strict=False)
    _reject_canonical_output(args.output, repo_root, "canonical publication authorization")
    reason = (
        args.reason
        if args.reason is not None
        else args.reason_file.read_text(encoding="utf-8")
    )
    request_record = read_json_object(args.request)
    if request_record["canonical_publication_candidate_file_sha256"] != sha256_file(
        args.candidate
    ):
        raise ValueError("canonical publication candidate file SHA mismatch")
    if request_record["accepted_execution_review_bundle_file_sha256"] != sha256_file(
        args.execution_review_bundle
    ):
        raise ValueError("execution review bundle file SHA mismatch")
    authorization = make_canonical_family_publication_authorization(
        repo_root=repo_root,
        request=canonical_family_publication_request_from_record(request_record),
        candidate=canonical_family_publication_candidate_from_record(
            read_json_object(args.candidate)
        ),
        execution_review_bundle=_load_execution_review_bundle(args.execution_review_bundle),
        disposition=args.disposition,
        reviewer_identity=args.reviewer,
        review_timestamp=args.timestamp,
        bounded_reason=reason,
    )
    write_json_object_immutable(args.output, authorization.as_record())
    _emit({"status": "CREATED", "authorization_id": authorization.as_record()["authorization_id"]})
    return EXIT_OK


def _cmd_verify_canonical_publication_authorization(args: argparse.Namespace) -> int:
    request_record = read_json_object(args.request)
    if request_record["canonical_publication_candidate_file_sha256"] != sha256_file(
        args.candidate
    ):
        raise ValueError("canonical publication candidate file SHA mismatch")
    if request_record["accepted_execution_review_bundle_file_sha256"] != sha256_file(
        args.execution_review_bundle
    ):
        raise ValueError("execution review bundle file SHA mismatch")
    result = validate_canonical_family_publication_authorization(
        repo_root=args.repo_root.resolve(strict=False),
        request=canonical_family_publication_request_from_record(request_record),
        authorization=canonical_family_publication_authorization_from_record(
            read_json_object(args.authorization)
        ),
        candidate=canonical_family_publication_candidate_from_record(
            read_json_object(args.candidate)
        ),
        execution_review_bundle=_load_execution_review_bundle(args.execution_review_bundle),
    )
    _emit(result.as_record())
    return EXIT_OK if result.status == "AUTHORIZED" else EXIT_BLOCKED_OR_WITHHELD


def _load_stage_2j_publication_request(path: Path):
    return canonical_family_publication_request_from_record(read_json_object(path))


def _load_stage_2j_publication_authorization(path: Path):
    return canonical_family_publication_authorization_from_record(read_json_object(path))


def _load_publication_candidate(path: Path):
    return canonical_family_publication_candidate_from_record(read_json_object(path))


def _cmd_create_executable_canonical_publication_request(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve(strict=False)
    _reject_canonical_output(args.output, repo_root, "executable canonical publication request")
    request = make_executable_canonical_family_publication_request_v2(
        repo_root=repo_root,
        stage_2j_request=_load_stage_2j_publication_request(args.stage_2j_request),
        stage_2j_request_file_sha256=sha256_file(args.stage_2j_request),
        stage_2j_authorization=_load_stage_2j_publication_authorization(
            args.stage_2j_authorization
        ),
        stage_2j_authorization_file_sha256=sha256_file(args.stage_2j_authorization),
        candidate=_load_publication_candidate(args.candidate),
        candidate_file_sha256=sha256_file(args.candidate),
        execution_review_bundle=_load_execution_review_bundle(args.execution_review_bundle),
        execution_review_bundle_file_sha256=sha256_file(args.execution_review_bundle),
        intended_noncanonical_audit_work_dir=args.audit_work_dir,
    )
    write_json_object_immutable(args.output, request.as_record())
    _emit(
        {
            "status": "CREATED",
            "request_commitment": executable_canonical_publication_request_commitment(
                request
            ),
        }
    )
    return EXIT_OK


def _cmd_make_executable_canonical_publication_authorization(
    args: argparse.Namespace,
) -> int:
    request = executable_canonical_publication_request_v2_from_record(
        read_json_object(args.request)
    )
    reason = (
        args.reason
        if args.reason is not None
        else args.reason_file.read_text(encoding="utf-8")
    )
    authorization = make_executable_canonical_family_publication_authorization_v2(
        request=request,
        disposition=args.disposition,
        reviewer_identity=args.reviewer,
        review_timestamp=args.timestamp,
        bounded_reason=reason,
    )
    write_json_object_immutable(args.output, authorization.as_record())
    _emit({"status": "CREATED", "authorization_id": authorization.as_record()["authorization_id"]})
    return EXIT_OK


def _cmd_verify_executable_canonical_publication_authorization(
    args: argparse.Namespace,
) -> int:
    result = validate_executable_canonical_publication_authorization(
        repo_root=args.repo_root.resolve(strict=False),
        stage_2j_request=_load_stage_2j_publication_request(args.stage_2j_request),
        stage_2j_request_file_sha256=sha256_file(args.stage_2j_request),
        stage_2j_authorization=_load_stage_2j_publication_authorization(
            args.stage_2j_authorization
        ),
        stage_2j_authorization_file_sha256=sha256_file(args.stage_2j_authorization),
        request=executable_canonical_publication_request_v2_from_record(
            read_json_object(args.request)
        ),
        authorization=executable_canonical_publication_authorization_v2_from_record(
            read_json_object(args.authorization)
        ),
        candidate=_load_publication_candidate(args.candidate),
        candidate_file_sha256=sha256_file(args.candidate),
        execution_review_bundle=_load_execution_review_bundle(args.execution_review_bundle),
        execution_review_bundle_file_sha256=sha256_file(args.execution_review_bundle),
    )
    _emit(result.as_record())
    return EXIT_OK if result.status == "AUTHORIZED" else EXIT_BLOCKED_OR_WITHHELD


def _cmd_execute_authorized_canonical_publication(args: argparse.Namespace) -> int:
    raw_request = read_json_object(args.request)
    raw_auth = read_json_object(args.authorization)
    if raw_request.get("schema_id") != EXECUTABLE_PUBLICATION_REQUEST_SCHEMA_ID:
        raise ValueError(
            "Stage 2J canonical publication records are validation-only and are not executable"
        )
    if raw_auth.get("schema_id") != EXECUTABLE_PUBLICATION_AUTHORIZATION_SCHEMA_ID:
        raise ValueError(
            "Stage 2J canonical publication records are validation-only and are not executable"
        )
    result = execute_authorized_canonical_publication(
        repo_root=args.repo_root.resolve(strict=False),
        stage_2j_request=_load_stage_2j_publication_request(args.stage_2j_request),
        stage_2j_authorization=_load_stage_2j_publication_authorization(
            args.stage_2j_authorization
        ),
        executable_request=executable_canonical_publication_request_v2_from_record(
            raw_request
        ),
        executable_authorization=executable_canonical_publication_authorization_v2_from_record(
            raw_auth
        ),
        candidate_file=args.candidate,
        execution_review_bundle_file=args.execution_review_bundle,
        stage_2j_request_file_sha256=sha256_file(args.stage_2j_request),
        stage_2j_authorization_file_sha256=sha256_file(args.stage_2j_authorization),
    )
    _emit(result.as_summary())
    return EXIT_OK if result.status.value == "COMPLETED" else EXIT_BLOCKED_OR_WITHHELD


def _cmd_review_canonical_publication_evidence(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve(strict=False)
    _reject_canonical_output(args.output, repo_root, "canonical publication review report")
    report = inspect_canonical_publication_evidence(
        repo_root=repo_root,
        stage_2j_request=_load_stage_2j_publication_request(args.stage_2j_request),
        stage_2j_request_file_sha256=sha256_file(args.stage_2j_request),
        stage_2j_authorization=_load_stage_2j_publication_authorization(
            args.stage_2j_authorization
        ),
        stage_2j_authorization_file_sha256=sha256_file(args.stage_2j_authorization),
        executable_request=executable_canonical_publication_request_v2_from_record(
            read_json_object(args.executable_request)
        ),
        executable_request_file_sha256=sha256_file(args.executable_request),
        executable_authorization=executable_canonical_publication_authorization_v2_from_record(
            read_json_object(args.executable_authorization)
        ),
        executable_authorization_file_sha256=sha256_file(args.executable_authorization),
        candidate_file=args.candidate,
        execution_review_bundle_file=args.execution_review_bundle,
    )
    write_json_object_immutable(args.output, report.as_record())
    record = report.as_record()
    _emit(
        {
            "status": record["terminal_status"],
            "report_commitment": record["report_commitment"],
            "canonical_destination": record["canonical_destination"],
            "canonical_destination_file_sha256": record[
                "canonical_destination_file_sha256"
            ],
        }
    )
    return (
        EXIT_BLOCKED_OR_WITHHELD
        if record["terminal_status"] == "INCOMPLETE_TERMINAL_EVIDENCE"
        else EXIT_OK
    )


def _cmd_make_canonical_publication_closure_disposition(args: argparse.Namespace) -> int:
    reason = (
        args.reason
        if args.reason is not None
        else args.reason_file.read_text(encoding="utf-8")
    )
    disposition = make_canonical_publication_closure_disposition(
        report=canonical_publication_evidence_review_report_from_record(
            read_json_object(args.report)
        ),
        disposition=args.disposition,
        reviewer_identity=args.reviewer,
        review_timestamp=args.timestamp,
        bounded_reason=reason,
    )
    write_json_object_immutable(args.output, disposition.as_record())
    _emit({"status": "CREATED", "disposition_id": disposition.as_record()["disposition_id"]})
    return EXIT_OK


def _cmd_write_canonical_publication_closure_bundle(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve(strict=False)
    bundle = write_canonical_publication_closure_bundle(
        report=canonical_publication_evidence_review_report_from_record(
            read_json_object(args.report)
        ),
        disposition=canonical_publication_closure_disposition_from_record(
            read_json_object(args.disposition)
        ),
        destination=args.output,
        repo_root=repo_root,
    )
    _emit(
        {
            "status": "WRITTEN",
            "bundle_commitment": canonical_publication_closure_bundle_commitment(bundle),
            "terminal_status": bundle.as_record()["terminal_status"],
        }
    )
    return EXIT_OK


def _cmd_verify_canonical_publication_closure_bundle(args: argparse.Namespace) -> int:
    bundle = canonical_publication_closure_bundle_from_record(read_json_object(args.bundle))
    record = bundle.as_record()
    _emit(
        {
            "status": "VERIFIED",
            "bundle_commitment": record["bundle_commitment"],
            "terminal_status": record["terminal_status"],
            "canonical_destination": record["canonical_destination"],
            "canonical_destination_file_sha256": record[
                "canonical_destination_file_sha256"
            ],
        }
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="relate-family")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-noncanonical")
    run.add_argument("--config", type=Path, required=True)
    run.set_defaults(func=_cmd_run_noncanonical)

    disp = sub.add_parser("make-publication-disposition")
    disp.add_argument("--packet", type=Path, required=True)
    disp.add_argument(
        "--disposition",
        choices=(
            AUTHORIZE_BOUNDED_REVIEW_PUBLICATION,
            WITHHOLD_BOUNDED_REVIEW_PUBLICATION,
        ),
        required=True,
    )
    disp.add_argument("--reviewer", required=True)
    disp.add_argument("--timestamp", required=True)
    reason = disp.add_mutually_exclusive_group(required=True)
    reason.add_argument("--reason")
    reason.add_argument("--reason-file", type=Path)
    disp.add_argument("--output", type=Path, required=True)
    disp.set_defaults(func=_cmd_make_publication_disposition)

    pub = sub.add_parser("publish-review")
    pub.add_argument("--repo-root", type=Path, required=True)
    pub.add_argument("--packet", type=Path, required=True)
    pub.add_argument("--disposition", type=Path, required=True)
    pub.add_argument("--output", type=Path, required=True)
    pub.set_defaults(func=_cmd_publish_review)

    req = sub.add_parser("create-canonical-execution-request")
    req.add_argument("--config", type=Path, required=True)
    req.add_argument("--output", type=Path, required=True)
    req.set_defaults(func=_cmd_create_canonical_request)

    auth = sub.add_parser("make-canonical-execution-authorization")
    auth.add_argument("--request", type=Path, required=True)
    auth.add_argument(
        "--disposition",
        choices=(
            AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION,
            WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION,
        ),
        required=True,
    )
    auth.add_argument("--reviewer", required=True)
    auth.add_argument("--timestamp", required=True)
    auth_reason = auth.add_mutually_exclusive_group(required=True)
    auth_reason.add_argument("--reason")
    auth_reason.add_argument("--reason-file", type=Path)
    auth.add_argument("--output", type=Path, required=True)
    auth.set_defaults(func=_cmd_make_canonical_authorization)

    verify = sub.add_parser("verify-canonical-execution-authorization")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--request", type=Path, required=True)
    verify.add_argument("--authorization", type=Path, required=True)
    verify.add_argument("--packet", type=Path, required=True)
    verify.add_argument("--evidence-bundle", type=Path, required=True)
    verify.set_defaults(func=_cmd_verify_canonical_authorization)

    execute = sub.add_parser("execute-authorized-canonical")
    execute.add_argument("--repo-root", type=Path, required=True)
    execute.add_argument("--request", type=Path, required=True)
    execute.add_argument("--authorization", type=Path, required=True)
    execute.add_argument("--review-packet", type=Path, required=True)
    execute.add_argument("--evidence-bundle", type=Path, required=True)
    execute.set_defaults(func=_cmd_execute_authorized_canonical)

    review_execution = sub.add_parser("review-authorized-canonical-execution")
    review_execution.add_argument("--repo-root", type=Path, required=True)
    review_execution.add_argument("--request", type=Path, required=True)
    review_execution.add_argument("--authorization", type=Path, required=True)
    review_execution.add_argument("--review-packet", type=Path, required=True)
    review_execution.add_argument("--evidence-bundle", type=Path, required=True)
    review_execution.add_argument("--work-dir", type=Path, required=True)
    review_execution.add_argument("--output", type=Path, required=True)
    review_execution.set_defaults(func=_cmd_review_authorized_canonical_execution)

    review_disp = sub.add_parser("make-canonical-execution-review-disposition")
    review_disp.add_argument("--report", type=Path, required=True)
    review_disp.add_argument(
        "--disposition",
        choices=(
            ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW,
            WITHHOLD_EXECUTION_EVIDENCE,
        ),
        required=True,
    )
    review_disp.add_argument("--reviewer", required=True)
    review_disp.add_argument("--timestamp", required=True)
    review_disp_reason = review_disp.add_mutually_exclusive_group(required=True)
    review_disp_reason.add_argument("--reason")
    review_disp_reason.add_argument("--reason-file", type=Path)
    review_disp.add_argument("--output", type=Path, required=True)
    review_disp.set_defaults(func=_cmd_make_execution_review_disposition)

    review_bundle = sub.add_parser("write-canonical-execution-review-bundle")
    review_bundle.add_argument("--repo-root", type=Path, required=True)
    review_bundle.add_argument("--report", type=Path, required=True)
    review_bundle.add_argument("--disposition", type=Path, required=True)
    review_bundle.add_argument("--output", type=Path, required=True)
    review_bundle.set_defaults(func=_cmd_write_execution_review_bundle)

    pub_candidate = sub.add_parser("create-canonical-publication-candidate")
    pub_candidate.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_candidate.add_argument("--canonical-execution-review-packet", type=Path, required=True)
    pub_candidate.add_argument("--output", type=Path, required=True)
    pub_candidate.set_defaults(func=_cmd_create_canonical_publication_candidate)

    pub_request = sub.add_parser("create-canonical-publication-request")
    pub_request.add_argument("--repo-root", type=Path, required=True)
    pub_request.add_argument("--candidate", type=Path, required=True)
    pub_request.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_request.add_argument("--intended-canonical-destination", type=Path, required=True)
    pub_request.add_argument("--output", type=Path, required=True)
    pub_request.set_defaults(func=_cmd_create_canonical_publication_request)

    pub_auth = sub.add_parser("make-canonical-publication-authorization")
    pub_auth.add_argument("--repo-root", type=Path, required=True)
    pub_auth.add_argument("--request", type=Path, required=True)
    pub_auth.add_argument("--candidate", type=Path, required=True)
    pub_auth.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_auth.add_argument(
        "--disposition",
        choices=(
            AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
            WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        ),
        required=True,
    )
    pub_auth.add_argument("--reviewer", required=True)
    pub_auth.add_argument("--timestamp", required=True)
    pub_auth_reason = pub_auth.add_mutually_exclusive_group(required=True)
    pub_auth_reason.add_argument("--reason")
    pub_auth_reason.add_argument("--reason-file", type=Path)
    pub_auth.add_argument("--output", type=Path, required=True)
    pub_auth.set_defaults(func=_cmd_make_canonical_publication_authorization)

    pub_verify = sub.add_parser("verify-canonical-publication-authorization")
    pub_verify.add_argument("--repo-root", type=Path, required=True)
    pub_verify.add_argument("--request", type=Path, required=True)
    pub_verify.add_argument("--authorization", type=Path, required=True)
    pub_verify.add_argument("--candidate", type=Path, required=True)
    pub_verify.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_verify.set_defaults(func=_cmd_verify_canonical_publication_authorization)

    pub_exec_req = sub.add_parser("create-executable-canonical-publication-request")
    pub_exec_req.add_argument("--repo-root", type=Path, required=True)
    pub_exec_req.add_argument("--stage-2j-request", type=Path, required=True)
    pub_exec_req.add_argument("--stage-2j-authorization", type=Path, required=True)
    pub_exec_req.add_argument("--candidate", type=Path, required=True)
    pub_exec_req.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_exec_req.add_argument("--audit-work-dir", type=Path, required=True)
    pub_exec_req.add_argument("--output", type=Path, required=True)
    pub_exec_req.set_defaults(func=_cmd_create_executable_canonical_publication_request)

    pub_exec_auth = sub.add_parser("make-executable-canonical-publication-authorization")
    pub_exec_auth.add_argument("--request", type=Path, required=True)
    pub_exec_auth.add_argument(
        "--disposition",
        choices=(
            AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
            WITHHOLD_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION,
        ),
        required=True,
    )
    pub_exec_auth.add_argument("--reviewer", required=True)
    pub_exec_auth.add_argument("--timestamp", required=True)
    pub_exec_auth_reason = pub_exec_auth.add_mutually_exclusive_group(required=True)
    pub_exec_auth_reason.add_argument("--reason")
    pub_exec_auth_reason.add_argument("--reason-file", type=Path)
    pub_exec_auth.add_argument("--output", type=Path, required=True)
    pub_exec_auth.set_defaults(func=_cmd_make_executable_canonical_publication_authorization)

    pub_exec_verify = sub.add_parser("verify-executable-canonical-publication-authorization")
    pub_exec_verify.add_argument("--repo-root", type=Path, required=True)
    pub_exec_verify.add_argument("--stage-2j-request", type=Path, required=True)
    pub_exec_verify.add_argument("--stage-2j-authorization", type=Path, required=True)
    pub_exec_verify.add_argument("--request", type=Path, required=True)
    pub_exec_verify.add_argument("--authorization", type=Path, required=True)
    pub_exec_verify.add_argument("--candidate", type=Path, required=True)
    pub_exec_verify.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_exec_verify.set_defaults(
        func=_cmd_verify_executable_canonical_publication_authorization
    )

    pub_execute = sub.add_parser("execute-authorized-canonical-publication")
    pub_execute.add_argument("--repo-root", type=Path, required=True)
    pub_execute.add_argument("--stage-2j-request", type=Path, required=True)
    pub_execute.add_argument("--stage-2j-authorization", type=Path, required=True)
    pub_execute.add_argument("--request", type=Path, required=True)
    pub_execute.add_argument("--authorization", type=Path, required=True)
    pub_execute.add_argument("--candidate", type=Path, required=True)
    pub_execute.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_execute.set_defaults(func=_cmd_execute_authorized_canonical_publication)

    pub_review = sub.add_parser("review-canonical-publication-evidence")
    pub_review.add_argument("--repo-root", type=Path, required=True)
    pub_review.add_argument("--stage-2j-request", type=Path, required=True)
    pub_review.add_argument("--stage-2j-authorization", type=Path, required=True)
    pub_review.add_argument("--executable-request", type=Path, required=True)
    pub_review.add_argument("--executable-authorization", type=Path, required=True)
    pub_review.add_argument("--candidate", type=Path, required=True)
    pub_review.add_argument("--execution-review-bundle", type=Path, required=True)
    pub_review.add_argument("--output", type=Path, required=True)
    pub_review.set_defaults(func=_cmd_review_canonical_publication_evidence)

    closure = sub.add_parser("make-canonical-publication-closure-disposition")
    closure.add_argument("--report", type=Path, required=True)
    closure.add_argument(
        "--disposition",
        choices=(
            CLOSE_COMPLETED_CANONICAL_PUBLICATION,
            CLOSE_FAILED_PUBLICATION_WITHOUT_CANONICAL_ARTIFACT,
            ACKNOWLEDGE_CANONICAL_ARTIFACT_WITH_INCOMPLETE_AUDIT_FINALIZATION,
            WITHHOLD_CANONICAL_PUBLICATION_CLOSURE,
        ),
        required=True,
    )
    closure.add_argument("--reviewer", required=True)
    closure.add_argument("--timestamp", required=True)
    closure_reason = closure.add_mutually_exclusive_group(required=True)
    closure_reason.add_argument("--reason")
    closure_reason.add_argument("--reason-file", type=Path)
    closure.add_argument("--output", type=Path, required=True)
    closure.set_defaults(func=_cmd_make_canonical_publication_closure_disposition)

    closure_bundle = sub.add_parser("write-canonical-publication-closure-bundle")
    closure_bundle.add_argument("--repo-root", type=Path, required=True)
    closure_bundle.add_argument("--report", type=Path, required=True)
    closure_bundle.add_argument("--disposition", type=Path, required=True)
    closure_bundle.add_argument("--output", type=Path, required=True)
    closure_bundle.set_defaults(func=_cmd_write_canonical_publication_closure_bundle)

    closure_verify = sub.add_parser("verify-canonical-publication-closure-bundle")
    closure_verify.add_argument("--bundle", type=Path, required=True)
    closure_verify.set_defaults(func=_cmd_verify_canonical_publication_closure_bundle)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI maps bounded failures to status JSON.
        _emit({"status": "FAILED", "error": str(exc)})
        return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

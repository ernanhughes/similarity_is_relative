"""Composition of the noncanonical family graph workflow.

Binds the explicit steps in ``relate.family.workflow.steps`` into a
``relate.workflows.WorkflowDefinition`` and ``WorkflowContext`` pair,
following the process the frozen family-connected allocation protocol
describes:

    verify frozen identities and firewall
    bind an exact run/cache identity
    register allocation repositories
    register prepared bounded evidence
    resolve evidence candidates
    stop honestly if metadata or review is incomplete
    build family components
    analyse components spanning allocation roles
    calculate the frozen bounded outcome
    retain auditable commitments
    stop before publication or downstream scientific action

This module builds the plan only. It does not execute it, does not
implement a family workflow for the canonical graph, and does not publish
anything.

This module must not import from relate.experiments or relate.cli.
"""

from __future__ import annotations

from pathlib import Path

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.store import CACHE_SCHEMA_ID, make_cache_identity
from relate.family.verification import FamilyProtocolExpectedIdentity, FamilyProtocolInputPaths
from relate.family.workflow.identity import compute_family_workflow_source_identity
from relate.family.workflow.models import (
    FamilyEvidenceBundle,
    FamilyStoreSpec,
    FamilyWorkflowConfig,
    FamilyWorkflowPlan,
    evidence_bundle_commitment,
    validate_sha256_identity,
)
from relate.family.workflow.steps import (
    AnalyseRoleCrossingsStep,
    AssessGraphReadinessStep,
    BuildFamilyComponentsStep,
    DetermineFamilyOutcomeStep,
    RegisterAllocationStep,
    RegisterPreparedEvidenceStep,
    ResolveCandidatesStep,
    VerifyFamilyInputsStep,
)
from relate.workflows import WorkflowContext, WorkflowDefinition

FAMILY_GRAPH_WORKFLOW_NAME = "family-connected-graph-workflow"
FAMILY_GRAPH_WORKFLOW_VERSION = "1"


def build_family_graph_workflow(config: FamilyWorkflowConfig) -> FamilyWorkflowPlan:
    """Build an explicit, ready-to-run (but not yet executed) family graph
    workflow plan from *config*.

    Every execution-critical identity — protocol SHA, allocation SHA,
    allocation-context SHA, D1 SHA, D1.1 SHA, workflow source identity,
    prepared evidence-bundle commitment, and cache schema identity — is
    placed into the returned ``WorkflowContext``, so the Stage 2C run
    identity commitment binds all of it.
    """
    source_identity = compute_family_workflow_source_identity(config.repo_root)
    validate_sha256_identity(source_identity, label="computed workflow source identity")
    if config.workflow_source_identity != source_identity:
        raise ValueError("caller-supplied workflow source identity does not match source files")

    return _build_family_workflow_plan_from_validated_inputs(
        run_id=config.run_id,
        workflow_name=config.workflow_name,
        workflow_version=config.workflow_version,
        repo_root=config.repo_root,
        work_dir=config.work_dir,
        store_path=config.store_path,
        allowed_roles=config.allowed_roles,
        family_protocol_sha256=config.family_protocol_sha256,
        expected_identity=config.expected_identity,
        input_paths=config.input_paths,
        allocation_manifest_path=config.allocation_manifest_path,
        workflow_source_identity=config.workflow_source_identity,
        evidence_bundle=config.evidence_bundle,
        extra_identity={},
        extra_inputs={"execution_mode": config.execution_mode.value},
        family_runner_source_identity=None,
    )


def _build_family_workflow_plan_from_validated_inputs(
    *,
    run_id: str,
    workflow_name: str,
    workflow_version: str,
    repo_root: Path,
    work_dir: Path,
    store_path: Path,
    allowed_roles: frozenset[str],
    family_protocol_sha256: str,
    expected_identity: FamilyProtocolExpectedIdentity,
    input_paths: FamilyProtocolInputPaths,
    allocation_manifest_path: Path,
    workflow_source_identity: str,
    evidence_bundle: FamilyEvidenceBundle,
    extra_identity: dict[str, str],
    extra_inputs: dict[str, str],
    family_runner_source_identity: str | None,
) -> FamilyWorkflowPlan:
    bundle_commitment = evidence_bundle_commitment(evidence_bundle)
    source_identity = compute_family_workflow_source_identity(repo_root)
    validate_sha256_identity(source_identity, label="computed workflow source identity")
    if workflow_source_identity != source_identity:
        raise ValueError("caller-supplied workflow source identity does not match source files")
    run_identity = sha256_text(
        canonical_json(
            {
                "schema_id": "relate-family-workflow-run-v1",
                "family_protocol_sha256": family_protocol_sha256,
                "workflow_source_identity": source_identity,
                "evidence_bundle_commitment": bundle_commitment,
                "run_id": run_id,
                **extra_identity,
            }
        )
    )

    cache_identity = make_cache_identity(
        family_protocol_sha256=family_protocol_sha256,
        allocation_manifest_sha256=expected_identity.allocation_manifest_sha256,
        allocation_context_sha256=expected_identity.allocation_context_sha256,
        d1_audit_result_sha256=expected_identity.d1_result_sha256,
        d1_1_classification_sha256=expected_identity.d1_1_classification_sha256,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity=family_runner_source_identity or source_identity,
    )

    steps = (
        VerifyFamilyInputsStep(
            input_paths=input_paths,
            expected_identity=expected_identity,
        ),
        RegisterAllocationStep(
            store_path=store_path,
            cache_identity=cache_identity,
            allocation_manifest_path=allocation_manifest_path,
            expected_allocation_repository_commitment=(
                expected_identity.allocation_repository_commitment_sha256
            ),
        ),
        RegisterPreparedEvidenceStep(
            store_path=store_path,
            cache_identity=cache_identity,
            evidence_bundle=evidence_bundle,
            expected_bundle_commitment=bundle_commitment,
        ),
        ResolveCandidatesStep(
            store_path=store_path,
            cache_identity=cache_identity,
            protocol_sha256=family_protocol_sha256,
        ),
        AssessGraphReadinessStep(
            store_path=store_path,
            cache_identity=cache_identity,
            protocol_sha256=family_protocol_sha256,
            incomplete_metadata_records=evidence_bundle.incomplete_metadata_records,
        ),
        BuildFamilyComponentsStep(
            store_path=store_path,
            cache_identity=cache_identity,
            protocol_sha256=family_protocol_sha256,
        ),
        AnalyseRoleCrossingsStep(
            store_path=store_path,
            cache_identity=cache_identity,
            protocol_sha256=family_protocol_sha256,
        ),
        DetermineFamilyOutcomeStep(
            store_path=store_path,
            cache_identity=cache_identity,
            protocol_sha256=family_protocol_sha256,
        ),
    )
    definition = WorkflowDefinition(
        name=workflow_name,
        version=workflow_version,
        steps=steps,
    )

    identity_fields = {
        "family_protocol_sha256": family_protocol_sha256,
        "allocation_manifest_sha256": expected_identity.allocation_manifest_sha256,
        "allocation_context_sha256": expected_identity.allocation_context_sha256,
        "allocation_repository_commitment_sha256": (
            expected_identity.allocation_repository_commitment_sha256
        ),
        "d1_audit_result_sha256": expected_identity.d1_result_sha256,
        "d1_1_classification_sha256": expected_identity.d1_1_classification_sha256,
        "workflow_source_identity": source_identity,
        "family_workflow_run_identity": run_identity,
        "cache_schema_version": CACHE_SCHEMA_ID,
        **extra_identity,
    }
    inputs = {
        "evidence_bundle_commitment": bundle_commitment,
        **extra_inputs,
    }
    context = WorkflowContext(
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        run_id=run_id,
        repo_root=repo_root,
        work_dir=work_dir,
        allowed_roles=allowed_roles,
        identity=identity_fields,
        inputs=inputs,
    )

    store_spec = FamilyStoreSpec(path=store_path, identity=cache_identity)
    return FamilyWorkflowPlan(definition=definition, context=context, store_spec=store_spec)


__all__ = [
    "FAMILY_GRAPH_WORKFLOW_NAME",
    "FAMILY_GRAPH_WORKFLOW_VERSION",
    "build_family_graph_workflow",
    "compute_family_workflow_source_identity",
]

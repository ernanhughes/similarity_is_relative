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

from relate.family.store import CACHE_SCHEMA_ID, make_cache_identity
from relate.family.workflow.identity import compute_family_workflow_source_identity
from relate.family.workflow.models import (
    FamilyStoreSpec,
    FamilyWorkflowConfig,
    FamilyWorkflowPlan,
    evidence_bundle_commitment,
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
    cache_identity = make_cache_identity(
        family_protocol_sha256=config.family_protocol_sha256,
        allocation_manifest_sha256=config.expected_identity.allocation_manifest_sha256,
        allocation_context_sha256=config.expected_identity.allocation_context_sha256,
        d1_audit_result_sha256=config.expected_identity.d1_result_sha256,
        d1_1_classification_sha256=config.expected_identity.d1_1_classification_sha256,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity=config.workflow_source_identity,
    )

    steps = (
        VerifyFamilyInputsStep(
            input_paths=config.input_paths,
            expected_identity=config.expected_identity,
        ),
        RegisterAllocationStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
            allocation_manifest_path=config.allocation_manifest_path,
        ),
        RegisterPreparedEvidenceStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
            evidence_bundle=config.evidence_bundle,
        ),
        ResolveCandidatesStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
            protocol_sha256=config.family_protocol_sha256,
        ),
        AssessGraphReadinessStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
            protocol_sha256=config.family_protocol_sha256,
            incomplete_metadata_records=config.evidence_bundle.incomplete_metadata_records,
        ),
        BuildFamilyComponentsStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
            protocol_sha256=config.family_protocol_sha256,
        ),
        AnalyseRoleCrossingsStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
        ),
        DetermineFamilyOutcomeStep(
            store_path=config.store_path,
            cache_identity=cache_identity,
        ),
    )
    definition = WorkflowDefinition(
        name=config.workflow_name,
        version=config.workflow_version,
        steps=steps,
    )

    identity_fields = {
        "family_protocol_sha256": config.family_protocol_sha256,
        "allocation_manifest_sha256": config.expected_identity.allocation_manifest_sha256,
        "allocation_context_sha256": config.expected_identity.allocation_context_sha256,
        "allocation_repository_commitment_sha256": (
            config.expected_identity.allocation_repository_commitment_sha256
        ),
        "d1_audit_result_sha256": config.expected_identity.d1_result_sha256,
        "d1_1_classification_sha256": config.expected_identity.d1_1_classification_sha256,
        "workflow_source_identity": config.workflow_source_identity,
        "cache_schema_version": CACHE_SCHEMA_ID,
    }
    inputs = {
        "evidence_bundle_commitment": evidence_bundle_commitment(config.evidence_bundle),
        "execution_mode": config.execution_mode.value,
    }
    context = WorkflowContext(
        workflow_name=config.workflow_name,
        workflow_version=config.workflow_version,
        run_id=config.run_id,
        repo_root=config.repo_root,
        work_dir=config.work_dir,
        allowed_roles=config.allowed_roles,
        identity=identity_fields,
        inputs=inputs,
    )

    store_spec = FamilyStoreSpec(path=config.store_path, identity=cache_identity)
    return FamilyWorkflowPlan(definition=definition, context=context, store_spec=store_spec)


__all__ = [
    "FAMILY_GRAPH_WORKFLOW_NAME",
    "FAMILY_GRAPH_WORKFLOW_VERSION",
    "build_family_graph_workflow",
    "compute_family_workflow_source_identity",
]

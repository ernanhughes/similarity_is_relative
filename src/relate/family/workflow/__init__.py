"""The noncanonical family graph workflow (Stage 2E).

Composes the clean family capabilities (verification, store, graph,
commitments, outcome, analysis) into an explicit sequence of
``relate.workflows.WorkflowStep`` objects, following the process the frozen
family-connected allocation protocol describes. This package builds and
proves the workflow; it never executes it against canonical inputs and
never publishes a result.

Required dependency direction (achieved):

    relate.family.workflow
        -> relate.workflows
        -> relate.evidence

    relate.family.workflow
        -> relate.family (verification, store, graph, commitments, outcome, analysis)

``relate.workflows`` remains domain-neutral: it imports neither
``relate.family`` nor ``relate.experiments``. This package must not import
``relate.experiments`` or ``relate.cli``.

Only ``FamilyWorkflowExecutionMode.NONCANONICAL`` exists. There is no
canonical mode, and canonical/output paths are rejected structurally at
configuration time (see ``relate.family.workflow.models``).
"""

from __future__ import annotations

from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    build_family_graph_workflow,
)
from relate.family.workflow.identity import (
    EXECUTION_CRITICAL_SOURCE_FILES,
    FAMILY_WORKFLOW_SOURCE_MANIFEST_SCHEMA_ID,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import (
    FAMILY_EVIDENCE_BUNDLE_SCHEMA_ID,
    FamilyEvidenceBundle,
    FamilyStoreSpec,
    FamilyWorkflowConfig,
    FamilyWorkflowExecutionMode,
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

__all__ = [
    "FAMILY_EVIDENCE_BUNDLE_SCHEMA_ID",
    "FAMILY_GRAPH_WORKFLOW_NAME",
    "FAMILY_GRAPH_WORKFLOW_VERSION",
    "FAMILY_WORKFLOW_SOURCE_MANIFEST_SCHEMA_ID",
    "EXECUTION_CRITICAL_SOURCE_FILES",
    "AnalyseRoleCrossingsStep",
    "AssessGraphReadinessStep",
    "BuildFamilyComponentsStep",
    "DetermineFamilyOutcomeStep",
    "FamilyEvidenceBundle",
    "FamilyStoreSpec",
    "FamilyWorkflowConfig",
    "FamilyWorkflowExecutionMode",
    "FamilyWorkflowPlan",
    "RegisterAllocationStep",
    "RegisterPreparedEvidenceStep",
    "ResolveCandidatesStep",
    "VerifyFamilyInputsStep",
    "build_family_graph_workflow",
    "compute_family_workflow_source_identity",
    "evidence_bundle_commitment",
]

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import relate.experiments.option_c0_family_connected_protocol as historical
from relate.family.verification import FamilyProtocolExpectedIdentity, FamilyProtocolInputPaths
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    build_family_graph_workflow,
    compute_family_workflow_source_identity,
)
from relate.family.workflow.models import FamilyEvidenceBundle, FamilyWorkflowConfig
from relate.workflows import WorkflowRunner


def _copy(path: str, dst: Path) -> Path:
    target = dst / Path(path).name
    shutil.copy2(Path(path), target)
    return target


@pytest.fixture()
def completed_family_workflow(tmp_path: Path):
    source = tmp_path / "inputs"
    source.mkdir()
    allocation = _copy(
        "artifacts/canonical/option-c0/data-firewall-v1/option-c0-repository-allocation-v1.jsonl",
        source,
    )
    firewall = _copy(
        "artifacts/canonical/option-c0/data-firewall-v1/"
        "option-c0-data-firewall-publication-v1.json",
        source,
    )
    d1 = _copy(
        "artifacts/canonical/option-c0/review-v1/d1-integrity/option-c0-d1-integrity-audit-v1.json",
        source,
    )
    d11 = _copy(
        "artifacts/canonical/option-c0/review-v1/d1-integrity/"
        "option-c0-d1-overlap-classification-v1.json",
        source,
    )
    paths = FamilyProtocolInputPaths(
        allocation_manifest=allocation,
        firewall_publication=firewall,
        d1_result=d1,
        d1_1_classification=d11,
    )
    expected = FamilyProtocolExpectedIdentity(
        allocation_manifest_sha256=historical.ALLOCATION_MANIFEST_SHA256,
        allocation_context_sha256=historical.ALLOCATION_CONTEXT_SHA256,
        allocation_repository_commitment_sha256=historical.ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
        d1_result_sha256=historical.D1_RESULT_SHA256,
        d1_1_classification_sha256=historical.D1_1_CLASSIFICATION_SHA256,
    )
    config = FamilyWorkflowConfig(
        run_id="stage-2f-test-run",
        workflow_name=FAMILY_GRAPH_WORKFLOW_NAME,
        workflow_version=FAMILY_GRAPH_WORKFLOW_VERSION,
        repo_root=Path.cwd(),
        work_dir=tmp_path / "work",
        store_path=tmp_path / "store" / "family.sqlite3",
        allowed_roles=frozenset({"c0_fit", "c0_iteration", "c0_selection", "c1_reserve"}),
        family_protocol_sha256=historical.protocol_contract()["protocol_sha256"],
        expected_identity=expected,
        input_paths=paths,
        allocation_manifest_path=allocation,
        workflow_source_identity=compute_family_workflow_source_identity(Path.cwd()),
        evidence_bundle=FamilyEvidenceBundle((), (), ()),
    )
    plan = build_family_graph_workflow(config)
    result = WorkflowRunner(plan.definition).run(plan.context)
    return plan, result

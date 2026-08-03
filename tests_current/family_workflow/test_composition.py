"""Composition boundary tests for the noncanonical family workflow."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from relate.family.verification import (
    FamilyProtocolExpectedIdentity,
    FamilyProtocolInputPaths,
)
from relate.family.workflow.composition import (
    FAMILY_GRAPH_WORKFLOW_NAME,
    FAMILY_GRAPH_WORKFLOW_VERSION,
    build_family_graph_workflow,
)
from relate.family.workflow.identity import compute_family_workflow_source_identity
from relate.family.workflow.models import FamilyEvidenceBundle, FamilyWorkflowConfig


def _config(tmp_path: Path, repo_root: Path) -> FamilyWorkflowConfig:
    source_identity = compute_family_workflow_source_identity(repo_root)
    paths = FamilyProtocolInputPaths(
        allocation_manifest=tmp_path / "allocation.jsonl",
        firewall_publication=tmp_path / "firewall.json",
        d1_result=tmp_path / "d1.json",
        d1_1_classification=tmp_path / "d11.json",
    )
    return FamilyWorkflowConfig(
        run_id="run-1",
        workflow_name=FAMILY_GRAPH_WORKFLOW_NAME,
        workflow_version=FAMILY_GRAPH_WORKFLOW_VERSION,
        repo_root=repo_root,
        work_dir=tmp_path / "work",
        store_path=tmp_path / "family.sqlite",
        allowed_roles=frozenset({"c0_fit", "c0_iteration"}),
        family_protocol_sha256="a" * 64,
        expected_identity=FamilyProtocolExpectedIdentity(
            allocation_manifest_sha256="b" * 64,
            allocation_context_sha256="c" * 64,
            allocation_repository_commitment_sha256="d" * 64,
            d1_result_sha256="e" * 64,
            d1_1_classification_sha256="f" * 64,
        ),
        input_paths=paths,
        allocation_manifest_path=paths.allocation_manifest,
        workflow_source_identity=source_identity,
        evidence_bundle=FamilyEvidenceBundle((), (), ()),
    )


def test_composition_recomputes_and_binds_source_identity(tmp_path: Path) -> None:
    repo_root = Path.cwd()
    config = _config(tmp_path, repo_root)
    plan = build_family_graph_workflow(config)
    source_identity = compute_family_workflow_source_identity(repo_root)
    assert plan.context.identity["workflow_source_identity"] == source_identity
    assert plan.store_spec.identity.family_runner_source_identity == source_identity


def test_caller_supplied_source_identity_mismatch_rejected(tmp_path: Path) -> None:
    config = replace(_config(tmp_path, Path.cwd()), workflow_source_identity="0" * 64)
    with pytest.raises(ValueError, match="workflow source identity"):
        build_family_graph_workflow(config)


def test_canonical_path_containment_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path
    config = _config(tmp_path / "run", Path.cwd())
    canonical = repo_root / "artifacts" / "canonical" / "family.sqlite"
    with pytest.raises(ValueError, match="canonical path"):
        FamilyWorkflowConfig(
            **{
                **config.__dict__,
                "repo_root": repo_root,
                "store_path": canonical,
                "workflow_source_identity": compute_family_workflow_source_identity(Path.cwd()),
            }
        )


def test_similarly_named_noncanonical_path_is_accepted(tmp_path: Path) -> None:
    config = replace(
        _config(tmp_path, Path.cwd()),
        store_path=tmp_path / "artifacts" / "canonical-copy" / "family.sqlite",
    )
    assert config.store_path.name == "family.sqlite"


def test_unknown_allowed_role_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown allowed role"):
        replace(_config(tmp_path, Path.cwd()), allowed_roles=frozenset({"not_a_role"}))

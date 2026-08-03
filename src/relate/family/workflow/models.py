"""Immutable configuration, plan, and prepared-evidence models for the
noncanonical family graph workflow.

This module contains no scientific algorithm — it binds already-clean
family capabilities (verification, store, graph, commitments, outcome,
analysis) into an explicit, validated configuration a composition function
can turn into a ``relate.workflows.WorkflowDefinition`` +
``WorkflowContext`` pair.

Only ``FamilyWorkflowExecutionMode.NONCANONICAL`` exists in this stage.
Canonical execution, publication, and downstream D2 actions are rejected
structurally: any work directory, store path, or allocation-manifest path
under ``artifacts/canonical/`` raises at construction time.

This module must not import from relate.experiments or relate.cli.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.edges import validate_evidence_candidate, validate_manual_review_disposition
from relate.family.models import EvidenceCandidate, ManualReviewDisposition, SourceEvidenceRecord
from relate.family.sources import validate_source_record
from relate.family.store import FamilyGraphCacheIdentity
from relate.family.verification import FamilyProtocolExpectedIdentity, FamilyProtocolInputPaths
from relate.workflows import WorkflowContext, WorkflowDefinition

FAMILY_EVIDENCE_BUNDLE_SCHEMA_ID: Final = "relate-family-evidence-bundle-v1"


def _reject_canonical_path(path: Path, *, label: str) -> None:
    normalized = str(path).replace("\\", "/")
    if "artifacts/canonical" in normalized:
        raise ValueError(
            f"noncanonical family workflow rejects a canonical path for {label}: {path}"
        )


@dataclass(frozen=True)
class FamilyEvidenceBundle:
    """An immutable, validated snapshot of prepared family evidence.

    The workflow never fetches public metadata or manufactures candidates:
    every record here must already be constructed and validated by the
    clean domain constructors (``make_source_record``,
    ``make_evidence_candidate``, ``make_manual_review_disposition``) before
    it is placed in a bundle. A bundle may legitimately contain
    review-required candidates with no disposition yet — that is a valid
    incomplete scientific state, not a software error.
    """

    source_records: tuple[SourceEvidenceRecord, ...]
    candidates: tuple[EvidenceCandidate, ...]
    dispositions: tuple[ManualReviewDisposition, ...]
    incomplete_metadata_records: int = 0

    def __post_init__(self) -> None:
        if self.incomplete_metadata_records < 0:
            raise ValueError("incomplete_metadata_records must be nonnegative")

        source_keys: set[tuple[str, str]] = set()
        for record in self.source_records:
            validate_source_record(record)
            key = (record.source_type, record.source_identity)
            if key in source_keys:
                raise ValueError(f"duplicate source record identity in bundle: {key}")
            source_keys.add(key)

        candidate_ids: set[str] = set()
        for candidate in self.candidates:
            validate_evidence_candidate(candidate)
            if candidate.candidate_id in candidate_ids:
                raise ValueError(
                    f"duplicate evidence candidate identity in bundle: {candidate.candidate_id}"
                )
            candidate_ids.add(candidate.candidate_id)

        candidates_by_id = {candidate.candidate_id: candidate for candidate in self.candidates}
        disposition_ids: set[str] = set()
        for disposition in self.dispositions:
            if disposition.disposition_id in disposition_ids:
                raise ValueError(
                    f"duplicate manual review disposition in bundle: {disposition.disposition_id}"
                )
            disposition_ids.add(disposition.disposition_id)
            candidate = candidates_by_id.get(disposition.edge_candidate_id)
            if candidate is None:
                raise ValueError(
                    "disposition references a candidate not present in this bundle: "
                    f"{disposition.edge_candidate_id}"
                )
            validate_manual_review_disposition(
                disposition,
                candidate,
                protocol_sha256=disposition.protocol_sha256,
            )

        object.__setattr__(
            self,
            "source_records",
            tuple(sorted(self.source_records, key=lambda r: (r.source_type, r.source_identity))),
        )
        object.__setattr__(
            self, "candidates", tuple(sorted(self.candidates, key=lambda c: c.candidate_id))
        )
        object.__setattr__(
            self,
            "dispositions",
            tuple(sorted(self.dispositions, key=lambda d: d.disposition_id)),
        )

    def as_commitment_record(self) -> dict[str, Any]:
        """A fully JSON-compatible, deterministically ordered record."""
        return {
            "schema_id": FAMILY_EVIDENCE_BUNDLE_SCHEMA_ID,
            "source_records": [record.as_record() for record in self.source_records],
            "candidates": [candidate.as_record() for candidate in self.candidates],
            "dispositions": [disposition.as_record() for disposition in self.dispositions],
            "incomplete_metadata_records": self.incomplete_metadata_records,
        }


def evidence_bundle_commitment(bundle: FamilyEvidenceBundle) -> str:
    """Deterministic SHA-256 commitment over a prepared evidence bundle."""
    return sha256_text(canonical_json(bundle.as_commitment_record()))


class FamilyWorkflowExecutionMode(StrEnum):
    """Only NONCANONICAL exists in this stage. There is no canonical mode."""

    NONCANONICAL = "NONCANONICAL"


@dataclass(frozen=True)
class FamilyStoreSpec:
    """The cache path and identity every durable step opens independently.

    Steps never share a live SQLite connection through workflow context;
    each step opens its own ``FamilyGraphCache(path, identity=identity)``
    using this spec.
    """

    path: Path
    identity: FamilyGraphCacheIdentity

    def __post_init__(self) -> None:
        _reject_canonical_path(self.path, label="store path")


@dataclass(frozen=True)
class FamilyWorkflowConfig:
    """Everything ``build_family_graph_workflow`` needs to construct a plan.

    Binds run identity, workflow identity, frozen protocol identity, the
    workflow's own explicit source identity, and a prepared evidence bundle
    into one immutable, validated configuration.
    """

    run_id: str
    workflow_name: str
    workflow_version: str
    repo_root: Path
    work_dir: Path
    store_path: Path
    allowed_roles: frozenset[str]
    family_protocol_sha256: str
    expected_identity: FamilyProtocolExpectedIdentity
    input_paths: FamilyProtocolInputPaths
    allocation_manifest_path: Path
    workflow_source_identity: str
    evidence_bundle: FamilyEvidenceBundle
    execution_mode: FamilyWorkflowExecutionMode = FamilyWorkflowExecutionMode.NONCANONICAL

    def __post_init__(self) -> None:
        if self.execution_mode is not FamilyWorkflowExecutionMode.NONCANONICAL:
            raise ValueError(
                "only FamilyWorkflowExecutionMode.NONCANONICAL is supported in this stage"
            )
        _reject_canonical_path(self.work_dir, label="work directory")
        _reject_canonical_path(self.store_path, label="store path")
        _reject_canonical_path(
            self.allocation_manifest_path, label="allocation manifest path"
        )
        object.__setattr__(self, "allowed_roles", frozenset(self.allowed_roles))


@dataclass(frozen=True)
class FamilyWorkflowPlan:
    """The output of ``build_family_graph_workflow``: an explicit,
    ready-to-run workflow definition, context, and store spec."""

    definition: WorkflowDefinition
    context: WorkflowContext
    store_spec: FamilyStoreSpec

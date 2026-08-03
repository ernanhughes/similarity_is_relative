"""Explicit, deterministic source identity for the clean family workflow.

The historical module's ``default_cache_identity`` binds
``family_runner_source_identity`` to ``sha256_file(Path(__file__))`` of
*that* module. This module deliberately does not inherit that value: it
would misattribute the historical experiment module as the source that
produced a run executed by the clean composed workflow.

Instead, a fresh run binds its own explicit source identity: a deterministic
commitment over the SHA-256 of every execution-critical source file, keyed
by its repository-relative POSIX path. This uses the existing
``relate.evidence.canonical_json`` and ``relate.evidence.hashing`` helpers;
it does not duplicate a generic hashing or manifest helper. No such neutral
execution-manifest helper exists yet in ``relate.evidence`` (see
docs/architecture/current-system-map.md's target package map, where
``evidence/manifests.py`` and ``evidence/provenance.py`` are still listed as
future, unimplemented modules) — if one is added later, this function
should be revisited to delegate to it instead of assembling the manifest
inline.

Excluded by design: absolute local paths (only repo-relative POSIX paths are
used as keys), modification timestamps, filesystem enumeration order (the
file list is explicit and sorted), temporary files, and anything under
``artifacts/canonical/``.

This module must not import from relate.experiments or relate.cli.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text

FAMILY_WORKFLOW_SOURCE_MANIFEST_SCHEMA_ID: Final = "relate-family-workflow-source-manifest-v1"

# Every module whose behaviour this workflow's commitments and persistence
# depend on. Listed explicitly and sorted (not filesystem-enumerated) so
# adding an unrelated file elsewhere in the repository never silently
# changes this identity.
EXECUTION_CRITICAL_SOURCE_FILES: Final[tuple[str, ...]] = tuple(
    sorted(
        (
            "src/relate/family/workflow/composition.py",
            "src/relate/family/workflow/steps.py",
            "src/relate/family/workflow/models.py",
            "src/relate/family/workflow/identity.py",
            "src/relate/family/verification.py",
            "src/relate/family/analysis.py",
            "src/relate/family/rules.py",
            "src/relate/family/sources.py",
            "src/relate/family/edges.py",
            "src/relate/family/graph.py",
            "src/relate/family/commitments.py",
            "src/relate/family/outcome.py",
            "src/relate/family/store.py",
            "src/relate/family/repositories.py",
            "src/relate/family/models.py",
            "src/relate/workflows/runner.py",
            "src/relate/workflows/commitments.py",
            "src/relate/workflows/models.py",
            "src/relate/workflows/step.py",
            "src/relate/workflows/trace.py",
            "src/relate/workflows/errors.py",
        )
    )
)


def compute_family_workflow_source_identity(repo_root: Path) -> str:
    """Return a deterministic SHA-256 commitment over the execution-critical
    family workflow source files, rooted at *repo_root*.

    The manifest maps each repo-relative POSIX path in
    ``EXECUTION_CRITICAL_SOURCE_FILES`` to its own SHA-256
    (``relate.evidence.hashing.sha256_file``), then commits the whole sorted
    mapping with ``relate.evidence.canonical_json.canonical_json_compact_unicode``
    and ``sha256_text``.
    """
    manifest = {
        relative_path: sha256_file(repo_root / relative_path)
        for relative_path in EXECUTION_CRITICAL_SOURCE_FILES
    }
    payload = {
        "schema_id": FAMILY_WORKFLOW_SOURCE_MANIFEST_SCHEMA_ID,
        "files": manifest,
    }
    return sha256_text(canonical_json(payload))

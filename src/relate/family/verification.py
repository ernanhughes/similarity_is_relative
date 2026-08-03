"""Frozen-input and protocol-level firewall verification.

Extracted from ``relate.experiments.option_c0_family_connected_protocol``
(Stage 2E). This module separates *what identity is expected* and *where the
inputs live* from the verification logic itself, so the verifier is reusable
for synthetic or copied fixture inputs, not hard-coded to the historical
canonical repository-relative paths.

A hash mismatch or firewall violation is an invariant/security failure: it
raises. It is not a scientifically-incomplete-but-valid ``BLOCKED`` state —
those are reserved for things like a missing required manual review or
incomplete bounded metadata (see ``relate.family.outcome``).

No database access, CLI parsing, file publication, or workflow
orchestration. This module must not import from relate.experiments,
relate.workflows, or relate.cli.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from relate.evidence.hashing import sha256_file

_COMMON_FIREWALL_KEYS: tuple[str, ...] = (
    "scientific_result_observed",
    "mechanism_result_observed",
    "c0_selection_rows_accessed",
    "c1_rows_accessed",
    "hidden_row_content_accessed",
)
_D11_ONLY_FIREWALL_KEYS: tuple[str, ...] = (
    "c0_selection_row_content_accessed",
    "c1_row_content_accessed",
)


@dataclass(frozen=True)
class FamilyProtocolInputPaths:
    """Filesystem locations of the four frozen protocol input artifacts.

    Deliberately separate from ``FamilyProtocolExpectedIdentity``: the same
    expected identity can be verified against a canonical path, a copied
    fixture path, or a temporary test path without changing what is
    expected.
    """

    allocation_manifest: Path
    firewall_publication: Path
    d1_result: Path
    d1_1_classification: Path


@dataclass(frozen=True)
class FamilyProtocolExpectedIdentity:
    """The frozen SHA-256 identities a set of protocol inputs must match."""

    allocation_manifest_sha256: str
    allocation_context_sha256: str
    allocation_repository_commitment_sha256: str
    d1_result_sha256: str
    d1_1_classification_sha256: str


@dataclass(frozen=True)
class VerifiedFamilyProtocolInputs:
    """Bounded, validated facts about a verified set of protocol inputs.

    Exposes only echoed identities and frozen classification labels that the
    verification already confirmed — never raw JSON payloads or row
    contents from the underlying artifacts.
    """

    allocation_manifest_sha256: str
    allocation_context_sha256: str
    allocation_repository_commitment_sha256: str
    d1_result_sha256: str
    d1_1_classification_sha256: str
    d1_1_overall_outcome: str
    d1_1_family_identity_rule_status: str


def validate_firewall_booleans(d1_data: Mapping[str, Any], d11_data: Mapping[str, Any]) -> None:
    """Verify every D1 and D1.1 hidden-row firewall boolean is exactly ``False``.

    ``d1_data`` may be the D1 result object itself or a mapping already
    scoped to its ``firewall_booleans`` block (either shape is accepted, as
    in the historical implementation).
    """
    d11_firewall_keys = (*_COMMON_FIREWALL_KEYS, *_D11_ONLY_FIREWALL_KEYS)
    d11_firewall_booleans = d11_data.get("firewall_booleans", {})
    for key in d11_firewall_keys:
        if key not in d11_firewall_booleans or d11_firewall_booleans[key] is not False:
            raise ValueError(f"hidden-row firewall field is true: {key}")
    d1_firewall = d1_data.get("firewall_booleans", d1_data)
    for key in _COMMON_FIREWALL_KEYS:
        if key not in d1_firewall or d1_firewall[key] is not False:
            raise ValueError(f"D1 hidden-row firewall field is not exactly false: {key}")


def verify_family_protocol_inputs(
    paths: FamilyProtocolInputPaths,
    expected_identity: FamilyProtocolExpectedIdentity,
) -> VerifiedFamilyProtocolInputs:
    """Verify frozen protocol inputs and the protocol-level firewall.

    Raises ``ValueError`` (an invariant/security failure — not a blocked
    state) if any hash, D1.1 classification field, or firewall boolean does
    not exactly match what is expected.
    """
    if sha256_file(paths.allocation_manifest) != expected_identity.allocation_manifest_sha256:
        raise ValueError("canonical allocation manifest hash mismatch")
    if sha256_file(paths.d1_result) != expected_identity.d1_result_sha256:
        raise ValueError("canonical D1 result hash mismatch")
    if sha256_file(paths.d1_1_classification) != expected_identity.d1_1_classification_sha256:
        raise ValueError("canonical D1.1 classification hash mismatch")

    firewall_data = json.loads(paths.firewall_publication.read_text(encoding="utf-8"))
    d1_data = json.loads(paths.d1_result.read_text(encoding="utf-8"))
    d11_data = json.loads(paths.d1_1_classification.read_text(encoding="utf-8"))
    for artifact in (firewall_data, d1_data, d11_data):
        if not isinstance(artifact, dict):
            raise ValueError("canonical protocol input must be a JSON object")

    observed_context_sha256 = firewall_data.get("allocation_context_sha256")
    if observed_context_sha256 != expected_identity.allocation_context_sha256:
        raise ValueError("allocation context SHA-256 mismatch")

    classification = d11_data.get("classification", {})
    overall_outcome = classification.get("overall_outcome")
    if overall_outcome != "D1_CLASSIFICATION_INCONCLUSIVE":
        raise ValueError("D1.1 outcome is not inconclusive")
    family_identity_rule_status = classification.get("family_identity_rule_status")
    if family_identity_rule_status != "NOT_FROZEN":
        raise ValueError("D1.1 family identity rule status is not frozen as NOT_FROZEN")

    validate_firewall_booleans(d1_data, d11_data)

    return VerifiedFamilyProtocolInputs(
        allocation_manifest_sha256=expected_identity.allocation_manifest_sha256,
        allocation_context_sha256=expected_identity.allocation_context_sha256,
        allocation_repository_commitment_sha256=(
            expected_identity.allocation_repository_commitment_sha256
        ),
        d1_result_sha256=expected_identity.d1_result_sha256,
        d1_1_classification_sha256=expected_identity.d1_1_classification_sha256,
        d1_1_overall_outcome=overall_outcome,
        d1_1_family_identity_rule_status=family_identity_rule_status,
    )

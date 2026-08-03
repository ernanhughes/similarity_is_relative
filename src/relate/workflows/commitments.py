"""Deterministic commitment chain for the workflow kernel.

Serializer choice
------------------
This module uses ``relate.evidence.canonical_json.canonical_json_compact_unicode``
(sort_keys=True, separators=(",", ":"), ensure_ascii=False) together with
``relate.evidence.hashing.sha256_text``. This is a new, workflow-specific
contract, not an alias of a historical scientific schema, so the serializer
is imported and referenced under its real name rather than an ambiguous
``as canonical_json`` alias. ``canonical_json_compact_ascii`` is deliberately
not used here: this contract has no historical caller requiring \\uXXXX
escaping, and picking one explicit variant avoids the two-serializer
ambiguity documented in docs/architecture/migration-status.md.

Commitments never include wall-clock timestamps, latency, Python object
representations, or filesystem paths (unless a path is itself an explicit
scientific input) — see relate.workflows.trace for where timing lives
instead.

Schema identifiers are versioned and distinct from any historical scientific
schema (e.g. EDGE_SCHEMA_ID, CACHE_SCHEMA_ID in relate.family): this is a new
neutral contract, not a reuse of family-protocol identity.
"""

from __future__ import annotations

from collections.abc import Sequence

from relate.evidence.canonical_json import canonical_json_compact_unicode
from relate.evidence.hashing import sha256_text
from relate.workflows.models import JsonValue, StepStatus, WorkflowContext, validate_json_value

RUN_IDENTITY_SCHEMA_ID = "relate-workflow-run-identity-v1"
STEP_INPUT_SCHEMA_ID = "relate-workflow-step-input-v1"
STEP_OUTPUT_SCHEMA_ID = "relate-workflow-step-output-v1"


def run_identity_commitment(context: WorkflowContext) -> str:
    """Bind workflow name, workflow version, run_id, and explicit identity
    values into one deterministic commitment.

    repo_root, work_dir, and allowed_roles are deliberately excluded: the
    first two are filesystem paths not themselves scientific inputs, and
    allowed_roles is a visibility policy, not a run identity value.
    """
    payload = {
        "schema_id": RUN_IDENTITY_SCHEMA_ID,
        "workflow_name": context.workflow_name,
        "workflow_version": context.workflow_version,
        "run_id": context.run_id,
        "identity": dict(context.identity),
    }
    return sha256_text(canonical_json_compact_unicode(payload))


def step_input_commitment(
    *,
    context: WorkflowContext,
    step_name: str,
    step_version: str,
    prior_commitments: Sequence[str],
) -> str:
    """Bind workflow name/version, the run identity commitment, this step's
    name and version, and the ordered list of prior step output commitments.

    ``prior_commitments`` is serialized as a list, not a set: the underlying
    canonical serializer only sorts mapping keys, not list elements, so
    changing the order of prior commitments changes this commitment.
    """
    payload = {
        "schema_id": STEP_INPUT_SCHEMA_ID,
        "workflow_name": context.workflow_name,
        "workflow_version": context.workflow_version,
        "run_identity_commitment": run_identity_commitment(context),
        "step_name": step_name,
        "step_version": step_version,
        "prior_step_commitments": list(prior_commitments),
    }
    return sha256_text(canonical_json_compact_unicode(payload))


def step_output_commitment(
    *,
    step_name: str,
    step_version: str,
    input_commitment: str,
    status: StepStatus,
    commitment_payload: JsonValue,
    blocked_reason: str | None,
) -> str:
    """Bind step name/version, the input commitment, status, the step's
    explicit commitment payload, and the blocked reason (when blocked).

    ``commitment_payload`` is explicitly re-validated here (not merely
    trusted from a prior StepResult construction): this function is part of
    the public commitment contract and callers — including resume
    validation, which recomputes commitments from stored records — must get
    the same rejection of non-finite floats and non-JSON values regardless
    of call path.
    """
    payload = {
        "schema_id": STEP_OUTPUT_SCHEMA_ID,
        "step_name": step_name,
        "step_version": step_version,
        "input_commitment": input_commitment,
        "status": status.value,
        "commitment_payload": validate_json_value(commitment_payload),
        "blocked_reason": blocked_reason,
    }
    return sha256_text(canonical_json_compact_unicode(payload))

# Option C0 Family Review Publication Runbook

Status: Stage 2F noncanonical review boundary.

## Prerequisites

Start from a completed Stage 2E noncanonical family workflow. The workflow
must end at `determine_family_outcome` with status `COMPLETED`; blocked,
failed, partial, or tampered runs cannot produce a review packet.

Use the same workflow plan, context, completed run result, and durable family
store that produced the run. Changed evidence inherits the Stage 2E rule: it
requires a fresh run ID and fresh family store path.

## Packet Validation

`relate.family.review.build_family_review_packet` validates the completed
workflow chain with `relate.workflows.validate_completed_run`, recomputes the
workflow source identity, reopens the family store with the bound cache
identity, and checks durable phase commitments for resolved edges, graph
readiness, components, role analysis, and bounded outcome.

The packet contains bounded family-graph facts only: workflow/source
identities, allocation identities, evidence-bundle commitment, phase
commitments, bounded role-crossing analysis, bounded family outcome,
firewall declarations, and mechanically derivable materiality inputs.

The packet does not establish material contamination, apply a materiality
threshold, require reallocation, authorize D2, or authorize canonical
publication.

## Materiality Inputs

Stage 2F presents only values mechanically derivable from published metadata
and validated Stage 2E records: affected role pairs, affected aggregate rows,
largest crossing component, fit/iteration row fractions, and hard/conditional
cross-role edge counts.

Family-disjoint allocation feasibility is recorded as `NOT_ASSESSED`; Stage
2F does not introduce an allocation solver.

## Human Disposition

A reviewer records a `FamilyPublicationDisposition` with one of two values:
`AUTHORIZE_BOUNDED_REVIEW_PUBLICATION` or
`WITHHOLD_BOUNDED_REVIEW_PUBLICATION`.

Authorizing bounded review publication is not authorization of materiality,
reallocation, canonical execution, or D2.

The disposition binds the family protocol SHA, review-packet commitment,
publication scope, reviewer identity, timezone-aware timestamp, bounded
reason, and deterministic disposition ID. It asserts a reviewer identity; it
does not claim cryptographic authentication.

## Publication

`relate.family.publication.publish_family_review_bundle` writes an immutable
noncanonical bundle only for `AUTHORIZE_BOUNDED_REVIEW_PUBLICATION`.
Withholding never publishes.

Destinations under `<repo>/artifacts/canonical` are rejected using resolved
path containment. Existing targets are refused. No overwrite flag exists.
The logical bundle commitment and the published file SHA-256 are separate
identities.

## Verification

Verify:

- packet commitment with `family_review_packet_commitment(packet)`;
- disposition ID and disposition commitment from the disposition record;
- bundle commitment from the compact canonical bundle payload;
- file SHA with `sha256_file(destination)`.

Canonical family graph execution, canonical result publication, allocation
changes, model refits, C0 replay, C0 selection access, C1 reserve access, and
D2 remain gated for a later stage.

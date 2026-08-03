# ADR 005: Canonical Publication Authorization Is Not Publication

## Status

Accepted.

## Context

Stage 2I can identify completed canonical-input execution evidence that is
eligible for publication-authorization review. That eligibility is not itself
publication authority, and canonical publication must not be mixed with
materiality, allocation, reallocation, model refit, C0 replay, protected-row
access or D2.

## Decision

Stage 2J records are validation-only. A canonical publication request binds
one exact bounded family-result candidate to one exact repository-relative
destination beneath `artifacts/canonical/`, and the destination must be absent
when the request and authorization are validated.

Human authorization is a separate record with two valid outcomes:
authorize the exact future publication operation, or withhold it. The
authorization does not grant overwrite authority, directory-wide authority, raw
SQLite publication authority, trace publication authority, hidden-data access,
or any downstream scientific decision.

The validation record explicitly reports
`executable_publication_authority: false`. Actual canonical publication
requires a later Stage 2K executor boundary that binds its own executable
contract and preserves the one-shot destination-specific constraints.

## Consequences

Stage 2J can be reviewed without changing canonical artifacts. A valid
authorization can be used only as an input to a future executor design; it
cannot be run directly. Destination creation, parent-directory creation and
overwrite refusal remain responsibilities of the future executable boundary.

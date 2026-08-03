# ADR 003: Canonical Execution Requires Exact Authorization

Date: 2026-08-03

Status: accepted

## Context

Stage 2G exposes the family workflow lifecycle through a supported CLI and
adds records for requesting and authorizing a future canonical family
execution. The repository still must not execute the canonical family graph or
publish a canonical family result in this stage.

## Decision

Canonical execution must be requested and authorized as a separate,
identity-bound act.

Merging code does not authorize execution.

Bounded-review publication authorization does not authorize execution.

Execution authorization does not authorize canonical publication or downstream
scientific action.

## Consequences

The canonical execution request binds protocol identity, workflow source
identity, review-packet commitment, evidence-bundle commitment, canonical input
identities, requested run ID, allowed roles, and fresh noncanonical staging
paths.

The authorization binds exactly one request. Validation recomputes mutable
dependencies but performs no execution and creates no store.

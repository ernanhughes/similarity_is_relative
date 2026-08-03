# ADR 004: One-Shot Canonical Execution to Staging

Date: 2026-08-03

## Status

Accepted.

## Context

Stage 2G created exact canonical-execution request and authorization records,
but its v1 records did not bind an explicit SHA-256 for the firewall
publication file itself or a source identity for the code that would consume
the authorization. Those records remain valid historical, validation-only
records, but they are not exact enough to authorize execution.

## Decision

Canonical execution is a one-shot, identity-bound action. Stage 2H introduces
executable v2 request and authorization records that bind the workflow source
identity, canonical executor source identity, firewall-publication file SHA,
all canonical input paths and hashes, the prepared evidence bundle, the
review-packet commitment, the requested run ID, allowed roles, staging paths,
and continuing prohibitions.

The authorization is consumed by atomically claiming its exact work directory
with directory creation. Once claimed, the same request cannot be retried,
even if execution later blocks or fails.

Every result is staged outside `artifacts/canonical`. A completed execution
creates reviewable evidence but performs no canonical publication or
downstream scientific decision.

## Consequences

- v1 request and authorization records remain loadable and validation-only.
- v2 request and authorization records are required for execution.
- The executor writes only `canonical-execution-claim.json`,
  `canonical-execution-review-packet.json` when completed,
  `canonical-execution-receipt.json`, `canonical-execution-trace.json`, and
  bounded failure records under the authorized noncanonical work directory.
- Completion does not authorize publication, materiality, allocation changes,
  reallocation, model refit, C0 replay, protected-row access, or D2.

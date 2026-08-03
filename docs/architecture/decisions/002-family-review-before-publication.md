# ADR 002: Family Review Before Publication

Date: 2026-08-03

Status: accepted

## Context

Stage 2E can complete a noncanonical family workflow and produce bounded
family graph facts. Those facts are reviewable, but the frozen protocol does
not make workflow completion equivalent to publication approval, materiality,
reallocation, canonical execution, or D2 authorization.

## Decision

A completed family workflow produces reviewable bounded facts. It does not
publish automatically.

A separate human publication disposition is required for publication. That
disposition authorizes only publication of the bounded review artifact.

Canonical execution, materiality, reallocation, and D2 require later, separate
authorization.

## Consequences

Stage 2F adds deterministic review packets, explicit publication
dispositions, and immutable noncanonical publication bundles. It does not add
a workflow publication step, a canonical flag, a materiality threshold, an
allocation change, or a D2 gate bypass.

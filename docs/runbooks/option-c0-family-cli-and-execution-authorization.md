# Option C0 Family CLI and Execution Authorization

Status: Stage 2G supported boundary.

## Supported Commands

`relate-family run-noncanonical` runs the existing Stage 2E workflow only in
noncanonical mode from a `relate-family-noncanonical-run-config-v1` record. It
writes a review packet only when the workflow completes.

`relate-family make-publication-disposition` creates a Stage 2F bounded review
publication disposition.

`relate-family publish-review` publishes a bounded review bundle only from an
authorization disposition. It does not create the disposition.

`relate-family create-canonical-execution-request` creates an identity-bound
request for a future canonical execution. It verifies canonical inputs and
fresh noncanonical staging paths but does not execute.

`relate-family make-canonical-execution-authorization` creates a distinct human
authorization or withholding record for one exact request.

`relate-family verify-canonical-execution-authorization` revalidates the
request, authorization, review packet, evidence bundle, current source identity,
canonical input hashes and firewall declarations, and staging freshness. It
performs no writes and does not execute.

## Exit Semantics

- `0`: command succeeded, or canonical execution authorization verified as
  `AUTHORIZED`.
- `1`: invariant, validation, I/O, or execution failure.
- `3`: workflow blocked or canonical execution authorization verified as
  `WITHHELD`.

## Configuration

The noncanonical run config binds run ID, work directory, store path, allowed
roles, family protocol SHA, expected frozen identities, protocol input paths,
allocation manifest path, evidence-bundle path, and review-packet output path.
It has no canonical execution mode field.

## Canonical Execution Authorization

A canonical execution authorization is permission to execute one exact,
identity-bound request in a future stage. It does not itself execute the
workflow and does not authorize canonical publication, materiality,
reallocation, or D2.

The request requires canonical protocol inputs under `artifacts/canonical` and
fresh noncanonical staging paths. It contains machine-readable prohibitions for
canonical result publication, materiality determination, contamination
conclusion, allocation change, reallocation, model refit, C0 replay, D2, and
protected-row access.

## Remaining Gates

Canonical execution remains absent. Canonical publication remains absent.
Allocation, materiality, reallocation, and D2 remain gated.

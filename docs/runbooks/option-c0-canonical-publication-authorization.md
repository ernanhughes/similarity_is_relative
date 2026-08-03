# Option C0 Canonical Publication Authorization Runbook

Stage 2J creates validation-only records for a possible future canonical
publication. It does not publish, create a canonical parent directory, create a
canonical file, determine materiality, change allocation, authorize
reallocation, refit models, replay C0, access protected rows or start D2.

## Required Inputs

- A strict Stage 2I execution-review bundle with disposition
  `ACCEPT_EXECUTION_EVIDENCE_FOR_PUBLICATION_AUTHORIZATION_REVIEW`.
- The exact `canonical-execution-review-packet.json` produced by the reviewed
  completed canonical-input execution.
- One intended absent destination beneath `artifacts/canonical/`.

## Create Candidate

```bash
relate-family create-canonical-publication-candidate \
  --execution-review-bundle .writer/path/execution-review-bundle.json \
  --canonical-execution-review-packet .writer/path/canonical-execution-review-packet.json \
  --output .writer/path/canonical-publication-candidate.json
```

The candidate binds the bounded family review packet, its logical commitment,
its file SHA-256, the accepted execution-review bundle, the bundle commitment
and the bundle file SHA-256.

## Create Request

```bash
relate-family create-canonical-publication-request \
  --repo-root . \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json \
  --intended-canonical-destination artifacts/canonical/option-c0/.../result.json \
  --output .writer/path/canonical-publication-request.json
```

The destination must be a normalized repository-relative JSON file path beneath
`artifacts/canonical/`, must not be the canonical root itself, and must not
exist. Stage 2J does not create the destination or its parent.

## Authorize Or Withhold

```bash
relate-family make-canonical-publication-authorization \
  --repo-root . \
  --request .writer/path/canonical-publication-request.json \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json \
  --disposition AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION \
  --reviewer reviewer:example \
  --timestamp 2026-08-03T12:00:00+00:00 \
  --reason "authorize exact absent canonical destination" \
  --output .writer/path/canonical-publication-authorization.json
```

Use `WITHHOLD_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION` to withhold.
Withholding is a valid result and should validate as `WITHHELD`.

## Verify

```bash
relate-family verify-canonical-publication-authorization \
  --repo-root . \
  --request .writer/path/canonical-publication-request.json \
  --authorization .writer/path/canonical-publication-authorization.json \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json
```

Verification recomputes logical commitments, physical file SHA-256 values,
source identity, destination absence and cross-record bindings. Its output
includes `executable_publication_authority: false`.

## Remaining Boundary

Stage 2K must provide any executable canonical publication mechanism. Stage 2J
authorization alone cannot publish and cannot be interpreted as materiality,
allocation, reallocation, protected-row access or D2 authority.

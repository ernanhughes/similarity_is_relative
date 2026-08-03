# Option C0 One-Shot Canonical Publication Runbook

Stage 2K executes one authorized canonical publication. It publishes exactly
the bytes of the Stage 2J candidate file to exactly one absent canonical JSON
destination and writes noncanonical audit evidence.

## Prerequisites

- A Stage 2J canonical publication request.
- A Stage 2J canonical publication authorization with disposition
  `AUTHORIZE_EXACT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION`.
- The exact candidate file bound by Stage 2J.
- The exact accepted execution-review bundle bound by Stage 2J.

## Create V2 Request

```bash
relate-family create-executable-canonical-publication-request \
  --repo-root . \
  --stage-2j-request .writer/path/canonical-publication-request.json \
  --stage-2j-authorization .writer/path/canonical-publication-authorization.json \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json \
  --audit-work-dir .writer/path/canonical-publication-audit \
  --output .writer/path/executable-canonical-publication-request.json
```

The audit directory must be absent, inside the repository, and outside
`artifacts/canonical/`.

## Authorize V2

```bash
relate-family make-executable-canonical-publication-authorization \
  --request .writer/path/executable-canonical-publication-request.json \
  --disposition AUTHORIZE_EXACT_ONE_SHOT_CANONICAL_BOUNDED_FAMILY_RESULT_PUBLICATION \
  --reviewer reviewer:example \
  --timestamp 2026-08-03T12:00:00+00:00 \
  --reason "authorize exact one-shot canonical publication" \
  --output .writer/path/executable-canonical-publication-authorization.json
```

Withholding is valid and creates no files during execution.

## Verify

```bash
relate-family verify-executable-canonical-publication-authorization \
  --repo-root . \
  --stage-2j-request .writer/path/canonical-publication-request.json \
  --stage-2j-authorization .writer/path/canonical-publication-authorization.json \
  --request .writer/path/executable-canonical-publication-request.json \
  --authorization .writer/path/executable-canonical-publication-authorization.json \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json
```

Verification checks the Stage 2J chain, v2 authorization binding, file
SHA-256 values, publisher source identity, destination absence and audit
directory absence.

## Execute

```bash
relate-family execute-authorized-canonical-publication \
  --repo-root . \
  --stage-2j-request .writer/path/canonical-publication-request.json \
  --stage-2j-authorization .writer/path/canonical-publication-authorization.json \
  --request .writer/path/executable-canonical-publication-request.json \
  --authorization .writer/path/executable-canonical-publication-authorization.json \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json
```

The destination and audit directory are taken only from the authorized v2
request. The CLI has no override for either path.

## Terminal States

Successful completion writes:

- `canonical-publication-claim.json`;
- `canonical-publication-trace.json`;
- `canonical-publication-receipt.json`;
- the exact canonical destination file.

Failures after the audit directory claim write:

- `canonical-publication-failure.json`;
- `canonical-publication-trace.json` where possible.

If the canonical file was created before audit finalization failed, the failure
record reports `canonical_file_created: true` and includes the destination
SHA-256. The canonical file is not deleted as rollback.

## Continued Prohibitions

Stage 2K does not determine materiality, conclude material contamination,
change allocation, authorize reallocation, refit models, replay C0, access C0
selection or C1 reserve row contents, access protected rows or start D2. Stage
2L must review the publication evidence without further canonical mutation.

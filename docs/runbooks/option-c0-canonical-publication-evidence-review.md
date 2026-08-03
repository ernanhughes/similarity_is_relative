# Option C0 Canonical Publication Evidence Review Runbook

Stage 2L reviews a Stage 2K canonical publication attempt. It is read-only with
respect to canonical storage and writes only noncanonical review, disposition
and closure-bundle records.

## Required Files

- Stage 2J canonical publication request.
- Stage 2J canonical publication authorization.
- Stage 2K executable publication request.
- Stage 2K executable publication authorization.
- Canonical publication candidate file.
- Accepted execution-review bundle.

The audit directory and canonical destination are derived from the Stage 2K
executable request. Do not provide alternate paths.

## Review

```bash
relate-family review-canonical-publication-evidence \
  --repo-root . \
  --stage-2j-request .writer/path/canonical-publication-request.json \
  --stage-2j-authorization .writer/path/canonical-publication-authorization.json \
  --executable-request .writer/path/executable-canonical-publication-request.json \
  --executable-authorization .writer/path/executable-canonical-publication-authorization.json \
  --candidate .writer/path/canonical-publication-candidate.json \
  --execution-review-bundle .writer/path/execution-review-bundle.json \
  --output .writer/path/canonical-publication-evidence-review.json
```

The review validates the historical chain, strict audit records, final trace
SHA binding, terminal state and exact destination bytes.

## Terminal States

- `VALID_COMPLETED`: claim, trace, receipt and exact canonical destination are
  present; no failure exists.
- `VALID_FAILED_BEFORE_CANONICAL_CREATION`: failure and trace are present; no
  canonical destination exists.
- `VALID_CANONICAL_FILE_CREATED_AUDIT_FAILED`: the canonical file exists with
  exact authorized bytes, but completed receipt finalization is absent.
- `INCOMPLETE_TERMINAL_EVIDENCE`: the chain is identifiable but required audit
  evidence is unavailable. This is not completed publication.

## Closure Disposition

```bash
relate-family make-canonical-publication-closure-disposition \
  --report .writer/path/canonical-publication-evidence-review.json \
  --disposition CLOSE_COMPLETED_CANONICAL_PUBLICATION \
  --reviewer reviewer:example \
  --timestamp 2026-08-03T12:00:00+00:00 \
  --reason "close completed canonical publication evidence" \
  --output .writer/path/canonical-publication-closure-disposition.json
```

Use the failed-attempt or partial-success dispositions only for their matching
terminal states. Withholding is valid for every report and is the only closure
available for incomplete terminal evidence.

## Closure Bundle

```bash
relate-family write-canonical-publication-closure-bundle \
  --repo-root . \
  --report .writer/path/canonical-publication-evidence-review.json \
  --disposition .writer/path/canonical-publication-closure-disposition.json \
  --output .writer/path/canonical-publication-closure-bundle.json

relate-family verify-canonical-publication-closure-bundle \
  --bundle .writer/path/canonical-publication-closure-bundle.json
```

Closure bundles must be written outside `artifacts/canonical/` and refuse
overwrite.

## Continued Prohibitions

Stage 2L does not retry publication, repair evidence, replace canonical files,
determine materiality, conclude material contamination, change allocation,
authorize reallocation, refit models, replay C0, access protected rows or start
D2.

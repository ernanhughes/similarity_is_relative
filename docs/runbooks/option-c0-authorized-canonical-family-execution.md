# Option C0 Authorized Canonical Family Execution

An authorized canonical execution reads the exact frozen canonical inputs
and writes only to its authorised noncanonical staging directory.

Completing that execution does not authorize canonical publication,
materiality, reallocation, allocation changes, model refits, C0 replay,
or D2.

## Compatibility Policy

Stage 2G v1 request and authorization records are validation-only. They remain
loadable, reconstructable, commitment-checkable, displayable, and valid under
the v1 non-executing contract. They are not executable because they did not
bind the firewall-publication file SHA or the canonical executor source
identity.

Execution requires:

1. a new `relate-family-canonical-execution-request-v2`;
2. a new `relate-family-canonical-execution-authorization-v2`.

The executor rejects v1 records with a clear validation-only message. It never
silently upgrades v1 records.

## Generating V2 Records

Use `relate-family create-canonical-execution-request` with the request config,
review packet, evidence bundle, frozen canonical input paths, expected
identities, requested run ID, allowed roles, fresh work directory, and fresh
store path. The store path must be strictly beneath the work directory.

Use `relate-family make-canonical-execution-authorization` against that v2
request. The authorization disposition may only be
`AUTHORIZE_EXACT_CANONICAL_FAMILY_EXECUTION` or
`WITHHOLD_EXACT_CANONICAL_FAMILY_EXECUTION`.

## Bound Identities

The v2 request binds the Stage 2E workflow source identity and a distinct
canonical executor source identity. The executor identity is a deterministic
manifest over explicit execution-gate source files, not a directory scan and
not a branch or timestamp.

The firewall-publication file SHA is bound explicitly with
`sha256_file(canonical_input_paths.firewall_publication)`. It is recomputed
when the request is created, during authorization validation, and immediately
before execution.

The authorised runner source identity is derived from the workflow source
identity and canonical executor source identity. The canonical run identity
also binds the request commitment, authorization ID, review-packet commitment,
evidence-bundle commitment, and requested run ID.

## One-Shot Claim

Execution revalidates the v2 request and authorization, then claims the exact
authorized work directory with `mkdir(parents=True, exist_ok=False)`. The claim
record is written as:

```text
<work_dir>/canonical-execution-claim.json
```

Once this directory exists, the authorization is consumed. A retry requires a
new work directory, new store path, new request, and new authorization. There
is no `--retry`, `--force`, or `--overwrite` option.

After the claim is durable, every failure path is protected by the executor's
terminal-record block. A failure during identity recomputation, workflow-plan
construction, workflow execution, packet construction, or receipt writing must
leave the claim in place and make a best effort to write
`canonical-execution-failure.json` plus `canonical-execution-trace.json`.

## Staged Files

Completed executions stage:

```text
<work_dir>/canonical-execution-claim.json
<work_dir>/canonical-execution-review-packet.json
<work_dir>/canonical-execution-receipt.json
<work_dir>/canonical-execution-trace.json
<work_dir>/family-graph.sqlite3
```

Blocked executions retain the claim and store, write a blocked receipt and
trace, and do not write a review packet.

Failed executions retain the claim and any partial store, write a bounded
failure record and trace when possible, and do not write a completed receipt
or review packet.

Withheld authorizations perform no writes and do not consume the authorization.

## CLI

Run execution only with:

```text
relate-family execute-authorized-canonical \
  --repo-root <repo> \
  --request <request-v2.json> \
  --authorization <authorization-v2.json> \
  --review-packet <review-packet.json> \
  --evidence-bundle <evidence-bundle.json>
```

The command does not accept canonical input paths, staging paths, run ID,
protocol SHA, source identities, roles, or output destinations. Those values
must come from the authorized request.

Exit semantics:

- `0`: completed and staged for later review;
- `1`: invariant, validation, I/O, or execution failure;
- `3`: authorization withheld or workflow blocked.

## Verification

Verify the staged records by reconstructing the claim and receipt with
`canonical_execution_claim_from_record` and
`canonical_execution_receipt_from_record`, rebuilding the review packet
commitment, recomputing receipt file SHA-256 separately from the logical
receipt commitment, and checking `git diff -- artifacts/canonical` is empty.

No staged file is a canonical publication. Materiality, allocation changes,
reallocation, model refits, C0 replay, protected-row access, and D2 remain
gated future decisions.

# Option C0 Family-Connected Allocation Runbook

Status: protocol frozen; canonical family graph not executed.

## Preconditions

- Use the frozen protocol contract at
  `artifacts/canonical/option-c0/review-v1/family-protocol-v1/option-c0-family-connected-allocation-contract-v1.json`.
- Verify the protocol SHA-256 before any canonical run.
- Verify the allocation manifest, D1 result hash, and D1.1 classification hash
  match the contract identities.
- Do not access C0 selection or C1 reserve row contents.

## Future Runner Contract

The future canonical runner must use:

```text
.writer/option-c0/cache/option-c0-family-graph-v1.sqlite3
```

Required SQLite pragmas:

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
PRAGMA foreign_keys=ON;
```

The cache identity must include the frozen protocol SHA-256 and all input
identities. A cache bound to another protocol identity must be refused.

## Progress Reporting

The future runner must stream:

- phase
- completed and total
- percentage
- cache hits and misses
- request rate
- elapsed time
- ETA

## Publication

The future canonical graph publication must include component and edge
commitments, metadata snapshot hashes, incomplete metadata statuses, manual
review dispositions, and the bounded decision outcome. It must not collapse
family crossing, contamination, and reallocation into one decision.


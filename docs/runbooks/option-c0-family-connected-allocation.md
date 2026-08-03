# Option C0 Family-Connected Allocation Runbook

Status: protocol frozen; canonical family graph not executed.

## Preconditions

- Use the frozen protocol contract at
  `artifacts/canonical/option-c0/review-v1/family-protocol-v1/option-c0-family-connected-allocation-contract-v1.json`.
- Verify the protocol SHA-256 before any canonical run.
- Verify the allocation manifest, D1 result hash, and D1.1 classification hash
  match the contract identities.
- Populate the initial allocation table only from the canonical allocation
  manifest loader with the frozen expected SHA-256.
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
Existing caches fail closed when identity rows are missing, extra, partial, or
mismatched, or when data rows exist before a complete identity is adopted.
The allocation phase must persist the ordered allocation-table commitment, and
resolved reviewed edges must be stored only after candidate and disposition
records validate against the active protocol identity.

## Progress Reporting

The future runner must stream:

- phase
- completed and total
- percentage
- cache hits and misses
- request rate
- elapsed time
- ETA

The frozen protocol contract also specifies checkpoint cadence, phase status
values, resume cursor requirements, and phase commitment requirements.

## Publication

The future canonical graph publication must include component and edge
commitments, metadata snapshot hashes, incomplete metadata statuses, manual
review dispositions, and the bounded decision outcome. It must not collapse
family crossing, contamination, and reallocation into one decision.

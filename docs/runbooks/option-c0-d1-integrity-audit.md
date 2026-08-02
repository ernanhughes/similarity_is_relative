# Option C0-D1 Integrity Audit Runbook

Status: implementation command only. Do not publish a canonical audit result from
the implementation PR.

## Boundary

The D1 command reconstructs row content only for `c0_fit` and `c0_iteration`.
It may read published repository names and aggregate row counts for all
allocation roles to produce repository-family name heuristics.

It must not reconstruct, hash, inspect, or expose `c0_selection` or `c1_reserve`
row content.

## Command

```powershell
.\scripts\run-option-c0-d1-integrity-audit.ps1
```

The default result path is:

```text
runs/option-c0/d1-integrity-audit-v1/option-c0-d1-integrity-audit-v1.json
```

The command refuses to overwrite an existing output.

The public command enforces the canonical source identity, allocation manifest,
allocation context, and allocation role counts. Fixture inputs require the
Python-level `allow_test_fixture_inputs` override used only by tests.

## Cache

The local SQLite cache is:

```text
.writer/option-c0/cache/option-c0-d1-integrity-v1.sqlite3
```

It is recovery infrastructure only and must not be committed. Cache reuse is
keyed by the source identity hash, allocation manifest hash, visible
reconstruction implementation hash, visible roles, normalization identity,
near-duplicate algorithm and parameters, and cache schema version.

The cache uses WAL mode, `synchronous=FULL`, and foreign keys.

Visible-row reuse requires a completed phase commitment over every ordered row
identity and fingerprint. Near-pair reuse requires a completed phase commitment,
matching scan parameters, an ordered near-pair SHA-256, and recomputed Hamming
distances for every loaded pair.

## Progress

Progress is streamed to the console and preserved in:

```text
runs/option-c0/d1-integrity-audit-v1/logs/option-c0-d1-integrity-audit.log
```

Long phases report phase name, completed units, total units, percentage, cache
hits and misses where applicable, throughput, elapsed time, and ETA.

## Interpretation

Exact code and normalized-AST overlaps are evidence for human review. Near
duplicates and repository-family groups are heuristic candidates only. D1 never
emits a final material-contamination conclusion.

The near-duplicate index splits 64-bit SimHash into four exact 16-bit bands. By
the pigeonhole principle, the implementation treats radius 3 as the maximum
exhaustive radius. Larger radii are rejected.

The v1 manifest separates:

```text
registered candidate implementation: d36436209d95eca555215a83856f042d241a90f4
runtime source commit:                 13466976195abeed56367a449ebd5a6678e3ef7e
result publication commit:             07cf6fc5ea9c261b10df272215a8afb404612e76
```

Incomplete source manifests or incomplete bounded near scans receive incomplete
statuses and do not unblock D2.

The only permitted next action after the implementation merges is:

```text
RUN_AND_REVIEW_OPTION_C0_D1_INTEGRITY_AUDIT
```

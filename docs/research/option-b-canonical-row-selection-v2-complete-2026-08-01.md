# Option B canonical row-selection checkpoint v2

Date: 2026-08-01

## Status

```text
Option B contract: FROZEN
Primitive contract conformance: COMPLETE
Canonical row selection v2: REPRODUCED AND VERIFIED
Primitive tables v2: PUBLISHED
Selected manifests v2: REVERIFIED
Canonical embeddings: NOT GENERATED
Primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE EMBEDDING EXTRACTION
```

Two independent selections were run in fresh directories. All six v2 JSONL artifacts matched byte-for-byte. Stable keys are unique, no stable key or normalized AST crosses a split boundary, and each primitive table has exactly the selected-manifest key order.

## Artifact hashes

| Split | Selected rows | Selected SHA-256 | Primitive SHA-256 | v1 identity overlap |
|---|---:|---|---|---:|
| train | 20,000 | `132045dc559469f9b2a28e56f25f43f1b06a27308abbf98a5dfbf6e4205247af` | `f87629dcf8441aff5f9dace95535ee0e98316e57c1c0825d0baa7a8bdba7ad8a` | 2,239 |
| validation | 4,000 | `17fd47115e0cacaad073f3eefacca9e78a0cd5ed46c607e05f159c9e4363179d` | `a0172b434533c94a28b21885393562ea904ce7e48f430ded4654e40fec01fbeb` | 1,582 |
| test | 4,000 | `1ad0e468ce9081db49c8ab92c21b0b6ce7a3a0e473930643baaea17e1576cb8b` | `20eff2f32e3a4572f23c8d6e3f481188a194d6d8ce0513553831b418d6b32a57` | 1,653 |

The v1 comparison uses `(repository, function_id, code_sha256)` rather than v1 stable keys because PR 2 repaired the previously missing CodeSearchNet path field. Exact overlap and differences are recorded in the JSON report.

## v1 to v2 selection comparison

The eligible populations and frozen split limits are unchanged between
v1 and v2. PR 2 repaired the previously blank CodeSearchNet path field,
which is an input to the stable key. Populating that field changed the
stable-key hashes and therefore deterministically reordered the same
eligible populations before truncation.

| Split | v1 rows | v2 rows | Identity overlap | v1 only | v2 only |
|---|---:|---:|---:|---:|---:|
| train | 20,000 | 20,000 | 2,239 | 17,761 | 17,761 |
| validation | 4,000 | 4,000 | 1,582 | 2,418 | 2,418 |
| test | 4,000 | 4,000 | 1,653 | 2,347 | 2,347 |

All v1 selected rows use the legacy empty-path stable-key formula, and
all v2 selected rows use the repaired populated-path formula. For every
split, the v2 rows that would have fallen below the old stable-key cutoff
are exactly the overlapping v1 rows. There are zero unexplained v2-only
rows below that cutoff.

This confirms deterministic reselection caused solely by the provenance
repair. No dataset drift, filtering drift, stochastic selection, or
scientific result was observed.

## Scientific boundary

No embedding, probe, hard-negative, metric, or scientific decision was generated. The frozen threshold and two-outcome decision are unchanged.

## Next permitted stage

The next bounded stage is **PR 4 — predicted executor contract completion**. Canonical embedding extraction remains blocked until PRs 4–6 are merged.

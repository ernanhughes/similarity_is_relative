# Option C0 Canonical Repository Allocation Checkpoint

Date: 2026-08-02

## Status

```text
C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED_PENDING_REVIEW
scientific_result_observed = false
mechanism_result_observed = false
c1_rows_selected = false
candidate_registry_entries = 0
discovery_ledger_entries = 0
```

The complete eligible CodeSearchNet Python pool was reconstructed under the frozen Option B eligibility rules. Every repository represented in the canonical Option B selected manifests was excluded before whole-repository allocation.

## Counts

| Quantity | Count |
|---|---:|
| Eligible rows | `199146` |
| Eligible repositories | `11903` |
| Option B repositories excluded | `6579` |
| Repositories allocated | `5324` |

## Role allocation

| Role | Repositories | Eligible rows |
|---|---:|---:|
| `c0_fit` | `2117` | `8007` |
| `c0_iteration` | `1058` | `4110` |
| `c0_selection` | `545` | `2070` |
| `c1_reserve` | `1604` | `6357` |

The `c1_reserve` remains undivided. No final C1 calibration or test row identity exists.

## Independent verification

A standalone implementation that does not import the allocator independently reconstructed the eligible pool, Option B repository set, role quotas, repository order, complete allocation manifest, role counts and all commitments. Exact equality was required.

All verification checks passed:

- `eligible_pool_recomputed`
- `option_b_exclusion_recomputed`
- `allocation_exactly_equal`
- `role_counts_exactly_equal`
- `pairwise_role_disjointness`
- `option_b_repositories_excluded`
- `c1_reserve_undivided`
- `candidate_registry_empty`
- `discovery_ledger_empty`

## Commitments

```text
allocation context: a3ae0b5dcbef0ae8e5056900ba44eeb53b4fd53a20f7cea8d842f67197ab02ed
eligible pool: e1594d44ea79e00c982e8295b60e8b5f1657a9feb03c1c16839012077278d58f
Option B repository set: 6eaf4b1bb90ce1caf0c05959fbf123d66371eff8d8547ce7bc0b01ab96c520fa
configuration: 18226086a00f450331e5a4e4b1cee27b33ffc2691ac1db46d9ceca68f798ef26
```

## Boundary

This checkpoint contains no mechanism candidate, discovery observation, conformal threshold, risk???coverage metric, C1 row selection or Option C scientific result.

After review and merge, the next permitted stage is a separate C0 mechanism-implementation PR. C0 mechanism execution remains blocked until that implementation is reviewed.

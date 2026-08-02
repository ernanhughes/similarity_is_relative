# Option C0 Canonical Allocation Setup

Date: 2026-08-02

## Status

```text
C0_CANONICAL_ALLOCATION_SETUP_FROZEN_PENDING_EXECUTION
scientific_result_observed = false
mechanism_result_observed = false
c1_rows_selected = false
candidate_registry_entries = 0
discovery_ledger_entries = 0
```

This checkpoint freezes the canonical repository-allocation configuration and the
independent verification boundary before any Option C0 repository identities are
generated.

No allocation result is present in this setup commit.

## Frozen allocation configuration

The canonical configuration is:

```text
role                 weight    minimum repositories
c0_fit                  4                 64
c0_iteration            2                 32
c0_selection            1                 32
c1_reserve              3                 64
```

For a sufficiently large eligible pool, the target proportions are therefore:

```text
c0_fit         40%
c0_iteration   20%
c0_selection   10%
c1_reserve     30%
```

The reserve remains one undivided repository pool. It is not split into final
C1 calibration or test identities.

### Rationale

The C1 reserve receives thirty percent because it must later support two
repository-separated confirmatory roles selected only after the C1 contract
merges. The C0 selection role receives ten percent because it is a development
hypothesis-selection set, not confirmatory evidence.

Minimums are prospective failure guards:

- at least 64 repositories for C0 fitting;
- at least 32 repositories for C0 iteration;
- at least 32 repositories for C0 selection;
- at least 64 repositories in the undivided C1 reserve.

If the corpus remaining after whole-repository Option B exclusion cannot satisfy
all four minimums, allocation must fail. Repositories may not be borrowed from
another role and Option B repositories may not be reused.

## Allocation identity

```text
schema:
option-c0-repository-allocation-v1

domain:
option-c0-canonical-repository-allocation-v1:2026-08-02
```

The allocation order depends on cryptographic commitments to:

- the reviewed configuration;
- the frozen external identity;
- the complete reconstructed eligible pool;
- the complete set of Option B repositories;
- each repository identity.

Changing any of these inputs changes the allocation context and repository
ordering.

## Independent verification

The standalone verifier:

- does not import `option_c0_data_firewall`;
- independently reconstructs the eligible pool;
- independently verifies every Option B selected-manifest hash;
- independently recomputes the Option B repository set;
- independently recomputes role quotas and repository order;
- requires exact equality of the complete repository-allocation manifest;
- requires exact equality of role counts and commitments;
- requires the candidate registry and discovery ledger to be empty;
- requires `c1_rows_selected = false`.

It writes:

```text
option-c0-data-firewall-independent-v1.json
```

with status:

```text
C0_CANONICAL_REPOSITORY_ALLOCATION_INDEPENDENTLY_RECOMPUTED
```

## Execution boundary

The guarded execution script may:

1. reconstruct the complete eligible pool;
2. generate the canonical repository allocation;
3. create empty candidate and discovery ledgers;
4. independently recompute the allocation;
5. package the verified evidence;
6. commit and push the result to the existing allocation PR.

It may not:

- register a mechanism candidate;
- add a discovery observation;
- compute conformal thresholds;
- fit a direct compound model;
- compute risk–coverage metrics;
- access C0 iteration or selection results;
- divide the C1 reserve;
- select C1 calibration or test rows;
- make an Option C scientific decision.

## Expected completion state

After guarded execution and independent recomputation:

```text
C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED_PENDING_REVIEW
scientific_result_observed = false
mechanism_result_observed = false
c1_rows_selected = false
candidate_registry_entries = 0
discovery_ledger_entries = 0
```

Mechanism discovery remains blocked until the result-bearing allocation PR is
reviewed and merged.

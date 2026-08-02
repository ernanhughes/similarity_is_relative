# Option C0 Canonical Allocation Handoff

## Required starting state

```text
Option B: COMPLETE — REAL_PREMISE_SUPPORTED
Option C0 protocol: FROZEN
C0 data-firewall implementation: MERGED
Canonical C0 allocation: NOT GENERATED
Candidate registry: EMPTY
Discovery ledger: EMPTY
C0 mechanism result: UNOBSERVED
C1 rows: UNSELECTED
Option C scientific result: UNOBSERVED
```

Read before execution:

1. `docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`
2. `docs/research/option-c0-data-firewall-implementation-2026-08-02.md`
3. `docs/runbooks/option-c0-next-stage-handoff.md`
4. `src/relate/experiments/option_c0_data_firewall.py`
5. `tests/test_option_c0_data_firewall.py`

## Next PR — exact scope

The next PR is a one-time canonical allocation checkpoint. It may contain:

- a reviewed allocation-configuration JSON;
- the canonical C0 allocation command or guarded execution script;
- generated repository allocation and Option B exclusion manifests;
- aggregate counts and cryptographic commitments;
- a separate substantive verification of repository separation and artifact identities;
- a human-readable allocation checkpoint.

It must not contain:

- a support-propagation mechanism;
- a real candidate-registry entry;
- a real discovery-ledger observation;
- conformal calibration;
- a direct compound model;
- risk–coverage results;
- C0 iteration or selection metrics;
- final C1 calibration or test rows;
- an Option C scientific result.

## Required execution guards

The canonical allocation run must:

1. begin from the reviewed implementation merge commit;
2. require a clean worktree;
3. require an unused output directory;
4. verify the external identity and Option B selected-manifest hashes;
5. reconstruct the eligible pool under the frozen Option B eligibility rules;
6. exclude every Option B repository before allocation;
7. allocate whole repositories only;
8. publish one undivided `c1_reserve`;
9. leave `c1_rows_selected = false`;
10. stop before candidate or mechanism evaluation.

## Completion state

The canonical allocation PR must end at a status equivalent to:

```text
C0_CANONICAL_REPOSITORY_ALLOCATION_VERIFIED_PENDING_MECHANISM_IMPLEMENTATION
scientific_result_observed = false
mechanism_result_observed = false
c1_rows_selected = false
candidate_registry_entries = 0
discovery_ledger_entries = 0
```

Mechanism discovery remains blocked until that checkpoint is reviewed and merged.

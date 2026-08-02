# Handoff: Option C0 Iteration Published, Review Pending

**Date:** 2026-08-02  
**Evidence commit:** `07cf6fc`  
**Current phase:** post-iteration review  
**Scientific result:** not yet declared

## Completed

- The frozen C0 fit and iteration roles were reconstructed.
- Six registered candidates were evaluated exactly once on C0 iteration.
- Six `EVALUATED` events were appended to the six `REGISTERED` events.
- The complete result and publication checkpoint were committed and pushed.
- The discovery ledger remained empty pending interpretation.
- C0 selection remained inaccessible.
- C1 remained inaccessible and no C1 rows were selected.

## Current evidence state

```text
status: C0_ITERATION_RESULTS_PUBLISHED_PENDING_REVIEW
mechanism_result_observed: true
scientific_result_observed: false
candidate_registrations: 6
candidate_evaluations: 6
candidate_registry_entries: 12
discovery_ledger_entries: 0
c0_selection_accessed: false
c1_rows_selected: false
next_allowed_action: C0_ITERATION_RESULT_AND_DISCOVERY_REVIEW
```

## Read in this order

1. [`docs/results/option-c0-discovery-iteration-checkpoint-v1.md`](../results/option-c0-discovery-iteration-checkpoint-v1.md)
2. [`docs/reviews/option-c0-iteration-independent-review-guide.md`](../reviews/option-c0-iteration-independent-review-guide.md)
3. [`docs/blog/option-c0-found-a-selective-signal-not-yet-a-distinctive-mechanism.md`](../blog/option-c0-found-a-selective-signal-not-yet-a-distinctive-mechanism.md)
4. [`artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json)
5. [`artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl)
6. [`artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json)

## Neutral result summary

- The `all` conjunction produced sizeable low-error selective subsets.
- At beta 0.01, empirical residual mass accepted 1,756 of 4,110 rows with zero observed errors.
- At beta 0.025, it accepted 2,105 rows with two errors.
- Aggregate joint primitive interval coverage was close to nominal.
- The `any` and `two-of-three` queries were materially less favourable.
- Confidence ranking, independent primitive abstention and direct compound prediction remained highly competitive and sometimes stronger.

The current evidence therefore supports a query-dependent exploratory selective signal, not a promoted claim of distinctive support-composition superiority.

## Decisions still open

- Which observations belong in the discovery ledger?
- Is the candidate registry ready to close?
- Is any scientifically meaningful C1 contract justified?
- If C1 is justified, is its target broad superiority, conjunction-specific replication, non-inferiority, calibration or another explicitly bounded hypothesis?
- What result would close the Option C novelty line?

## Prohibited next steps

Do not:

- access C0 selection before registry closure;
- select or inspect C1 rows;
- describe C0 as a C1 result;
- promote `C-REFUSE-001` from C0 evidence;
- rerun the completed C0 iteration to search for a better narrative;
- alter the frozen candidate plan or historical protocol records after seeing the result.

## Permitted next sequence

1. independent result review and compact recomputation;
2. append classified discovery-ledger entries;
3. close the candidate registry;
4. publish one C0 exit outcome;
5. only after `C1_CONTRACT_JUSTIFIED`, prepare a documentation-only C1 contract.

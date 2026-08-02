# Option C0 Next-Stage Handoff

## Current repository state

```text
Option B: COMPLETE — REAL_PREMISE_SUPPORTED
Option C0 discovery protocol: FROZEN
C0 data firewall: NOT IMPLEMENTED
C0 candidate registry: NOT IMPLEMENTED
C0 discovery ledger: NOT IMPLEMENTED
C0 mechanism discovery: BLOCKED
C1 contract: BLOCKED
C1 calibration and test rows: UNSELECTED
Option C scientific result: UNOBSERVED
```

Read before changing code:

1. [`docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`](../experiments/09-option-c0-discovery-and-confirmation-protocol.md)
2. [`docs/research/option-c0-discovery-preservation-decision-2026-08-02.md`](../research/option-c0-discovery-preservation-decision-2026-08-02.md)
3. [`docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md`](../research/post-e01-publication-and-kill-test-decision-2026-08-01.md)
4. [`docs/results/option-b-real-code-premise-checkpoint-v1.md`](../results/option-b-real-code-premise-checkpoint-v1.md)
5. [`CLAIMS.md`](../../CLAIMS.md)

## Next PR — exact scope

Implement only:

1. reproducible Option C eligible-pool reconstruction;
2. whole-repository exclusion of every repository represented in Option B canonical selected manifests;
3. deterministic allocation into:
   - C0 fit;
   - C0 iteration;
   - C0 selection;
   - one unselected C1 reserve pool;
4. cryptographic commitments and aggregate counts for every role;
5. repository-overlap verification;
6. append-only candidate-registry schema and writer;
7. append-only discovery-ledger schema and writer;
8. tests for immutability, role separation and overwrite refusal;
9. a checkpoint document that stops before mechanism evaluation.

## Explicit exclusions

Do not implement or run:

- a propagated-support mechanism;
- conformal calibration;
- a direct compound model;
- risk–coverage metrics;
- supported, weak, absent or shifted regime experiments;
- C0 iteration or selection evaluation;
- final C1 calibration/test row selection;
- C1 thresholds or outcomes;
- any Option C scientific decision.

Do not alter:

- Option B canonical evidence;
- Option B selected rows;
- Option B model or embeddings;
- Option B query or threshold;
- B-PREM-001;
- the fifteen-working-day Option C total budget.

## Data-allocation requirements

The allocation implementation must:

- operate at repository granularity;
- produce no repository overlap across roles;
- exclude every repository appearing in Option B canonical selection;
- use deterministic stable keys and a frozen seed or hash rule;
- record all exclusions and shortfalls;
- refuse a role with insufficient repositories rather than borrow from another role;
- publish aggregate counts and cryptographic commitments;
- leave final C1 calibration and test identities unselected;
- refuse to overwrite an existing canonical allocation output.

The implementation may create a committed reserve-pool identity and a future deterministic selection function. It may not invoke that function before the C1 contract merges.

## Candidate registry requirements

The append-only registry schema must support:

- candidate ID;
- version;
- commit SHA;
- support-object definition;
- propagation rule;
- query form;
- confidence or nonconformity score;
- data roles used;
- hyperparameters;
- expected failure mode;
- status;
- timestamps;
- predecessor version;
- artifact hashes.

The registry writer must reject deletion or mutation of an existing evaluated version.

No actual mechanism candidate should be registered in the infrastructure PR except a clearly marked fixture used by tests.

## Discovery ledger requirements

The ledger schema must support:

- discovery ID;
- classification;
- first-observed timestamp;
- first-observed commit;
- first-observed data role;
- anticipated or unexpected status;
- observation;
- affected candidates or assumptions;
- possible explanations;
- action taken;
- C1-contract relevance;
- fresh-evidence requirement;
- artifact hashes.

Allowed classifications:

```text
PLANNED_MECHANISM_DIAGNOSTIC
EXPLORATORY_OBSERVATION
UNEXPECTED_FINDING
NEW_HYPOTHESIS_REQUIRING_FRESH_DATA
IMPLEMENTATION_OR_DATA_INTEGRITY_FINDING
```

No real discovery row should be fabricated in the infrastructure PR. Tests may use explicit fixtures.

## Required tests

At minimum, test:

- deterministic repository allocation;
- exact exclusion of Option B repositories;
- pairwise role disjointness;
- allocation changes when the source commitment changes;
- rejection of insufficient-role borrowing;
- refusal to select final C1 rows;
- refusal to overwrite a completed allocation;
- candidate-registry append semantics;
- rejection of evaluated-candidate mutation or deletion;
- discovery-ledger append semantics;
- allowed-classification enforcement;
- phase-label enforcement;
- artifact hash verification.

Run:

```text
ruff check .
python -m pytest -q
```

## Completion checkpoint

The implementation PR must end with:

```text
C0_DATA_FIREWALL_IMPLEMENTED_PENDING_CANONICAL_ALLOCATION
```

It must state:

```text
scientific_result_observed = false
mechanism_result_observed = false
c1_rows_selected = false
```

After that implementation is reviewed and merged, a separate one-time allocation checkpoint may reconstruct the eligible pool, publish role commitments and independently verify separation.

Mechanism discovery remains blocked until that checkpoint merges.

## Copyable prompt for the next conversation

```text
Work in ernanhughes/similarity_is_relative from current main.

Read:
- docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md
- docs/research/option-c0-discovery-preservation-decision-2026-08-02.md
- docs/runbooks/option-c0-next-stage-handoff.md
- CLAIMS.md

Implement only the first incomplete C0 stage: data-allocation, candidate-registry and discovery-ledger infrastructure.

Do not implement any propagated-support mechanism, conformal model, direct compound baseline, risk–coverage metric or C0 experiment. Do not select final C1 calibration/test rows. Do not alter Option B evidence.

Require repository-level separation, exclusion of all Option B repositories, deterministic commitments, append-only registry and ledger semantics, atomic outputs, overwrite refusal, focused tests, full pytest and Ruff.

Open a draft PR that stops at C0_DATA_FIREWALL_IMPLEMENTED_PENDING_CANONICAL_ALLOCATION with scientific_result_observed=false, mechanism_result_observed=false and c1_rows_selected=false.
```
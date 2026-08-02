# Option C0 Data-Firewall Infrastructure Checkpoint

Date: 2026-08-02

## Status

```text
C0_DATA_FIREWALL_IMPLEMENTED_PENDING_CANONICAL_ALLOCATION
scientific_result_observed = false
mechanism_result_observed = false
c1_rows_selected = false
```

This checkpoint implements the first incomplete stage authorised by the frozen Option C0 discovery protocol. It adds infrastructure only. No Option C mechanism, conformal method, risk–coverage metric, C0 development result, C1 row identity or scientific decision has been produced.

## Implemented scope

The implementation provides:

1. reproducible eligible-pool reconstruction using the frozen Option B parser, tokenizer-length and cross-split duplicate rules;
2. verified loading of every repository represented in the canonical Option B selected manifests;
3. whole-repository exclusion of those Option B repositories;
4. deterministic allocation into:
   - `c0_fit`;
   - `c0_iteration`;
   - `c0_selection`;
   - one undivided `c1_reserve`;
5. role-level repository counts, row counts and SHA-256 commitments;
6. an atomic allocation bundle writer with overwrite refusal;
7. bundle verification for hashes, row counts, role disjointness and Option B exclusion;
8. a hash-chained append-only candidate registry;
9. a hash-chained append-only discovery ledger;
10. explicit refusal of final C1 calibration or test row selection.

## Allocation contract

The allocator works only at repository granularity. A repository may appear in exactly one role.

The allocation order is derived from a domain-separated SHA-256 value over:

- the reviewed allocation configuration;
- the immutable source-identity commitment;
- the reconstructed eligible-pool commitment;
- the Option B repository-exclusion commitment;
- the repository identity.

Role quotas are computed deterministically from reviewed weights and minimum repository counts. When the available repository count cannot satisfy every minimum, allocation fails. It does not borrow repositories from another role.

The generated bundle contains:

```text
option-c0-data-firewall-v1.json
option-c0-repository-allocation-v1.jsonl
option-c0-option-b-excluded-repositories-v1.jsonl
```

The implementation refuses to write when the target directory already exists.

## Deferred C1 identities

The allocator creates one undivided `c1_reserve` repository pool. It does not divide that pool into calibration and test roles and contains no function capable of returning final C1 row identities.

The exported `select_c1_rows` guard raises `C1SelectionForbidden` unconditionally. Final C1 selection remains blocked until a later C1 contract freezes the selection algorithm and derives its seed from the C1 contract merge commit.

## Candidate registry

The candidate registry is event-sourced and append-only. Its hash chain covers:

- schema identity;
- sequence number;
- previous-entry SHA-256;
- complete event payload.

Supported events are:

```text
REGISTERED
EVALUATED
STATUS_CHANGED
```

A candidate definition is immutable after registration. Evaluated versions cannot be registered again, mutated or deleted. Selecting a candidate for C0 selection requires a prior evaluation event.

No real candidate is registered by this checkpoint.

## Discovery ledger

The discovery ledger is separately hash-chained and append-only. It accepts only the frozen C0 classifications:

```text
PLANNED_MECHANISM_DIAGNOSTIC
EXPLORATORY_OBSERVATION
UNEXPECTED_FINDING
NEW_HYPOTHESIS_REQUIRING_FRESH_DATA
IMPLEMENTATION_OR_DATA_INTEGRITY_FINDING
```

It accepts only C0 phase labels:

```text
C0_FIT
C0_ITERATION
C0_SELECTION
```

C1 calibration or test labels are rejected. Artifact identities must be valid lowercase SHA-256 values.

No real discovery entry is created by this checkpoint.

## Explicit exclusions

This checkpoint does not implement or run:

- a propagated-support mechanism;
- independent primitive conformal abstention;
- a direct compound model;
- conformal calibration;
- risk–coverage metrics;
- supported, weak, absent or shifted regimes;
- C0 iteration or C0 selection evaluation;
- final C1 calibration or test row selection;
- an Option C threshold or outcome.

Option B evidence, manifests, model, query, threshold and promoted claim remain unchanged.

## Tests

The focused infrastructure suite covers:

- deterministic allocation;
- exact Option B exclusion;
- pairwise role disjointness;
- allocation-context sensitivity to source identity;
- insufficient-role refusal;
- C1 row-selection refusal;
- atomic publication and overwrite refusal;
- allocation artifact verification;
- candidate append semantics;
- evaluated-candidate immutability and deletion refusal;
- candidate selection preconditions;
- discovery append semantics;
- classification enforcement;
- phase-label enforcement;
- artifact-hash verification;
- hash-chain tamper detection;
- eligible-pool reconstruction replay;
- Option B manifest-hash verification.

The implementation PR must pass:

```text
ruff check .
python -m pytest -q
```

## Next allowed action

After this implementation is reviewed, validated and merged, the next stage is a separate one-time canonical allocation checkpoint.

That checkpoint may:

1. commit the reviewed allocation configuration;
2. reconstruct the complete eligible pool;
3. publish the C0 role and undivided C1 reserve commitments;
4. independently verify Option B exclusion and pairwise separation.

It must stop before candidate registration or mechanism evaluation.

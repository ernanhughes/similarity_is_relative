# Option C0 Candidate-Plan Handoff

## Required starting state

```text
Option B: COMPLETE — REAL_PREMISE_SUPPORTED
C0 discovery protocol: FROZEN
C0 canonical repository allocation: MERGED AND VERIFIED
C0 mechanism harness: MERGED
C0 real candidates: NONE
C0 iteration results: NONE
C0 selection: UNSEEN
C1 reserve: UNDIVIDED
C1 rows: UNSELECTED
Option C scientific result: NONE
```

Read before changing code:

1. `docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`
2. `docs/results/option-c0-canonical-repository-allocation-checkpoint-v1.md`
3. `docs/research/option-c0-mechanism-harness-implementation-2026-08-02.md`
4. `artifacts/canonical/option-c0/option-c0-development-harness-contract-v1.json`
5. `src/relate/experiments/option_c0_mechanism_harness.py`
6. `src/relate/experiments/option_c0_selective_baselines.py`
7. `src/relate/experiments/option_c0_diagnostics.py`

## Next PR — exact scope

The next PR may implement only the initial C0 candidate-plan and fit/iteration execution setup.

It may contain:

- up to three exact development query forms;
- a bounded initial candidate set;
- explicit candidate versions and implementation commits;
- candidate specification artifacts and hashes;
- a new discovery-run candidate registry initialized from the canonical empty state;
- deterministic reconstruction of `c0_fit` and `c0_iteration` rows;
- a development feature-bundle schema;
- CodeBERT embedding extraction for visible roles using the frozen model identity;
- primitive-target and compound-target construction for the registered queries;
- guarded baseline and candidate runners;
- baseline-fidelity tests;
- runtime and memory recording;
- a one-time execution script that remains unrun until review.

## Candidate registration order

For every real candidate:

1. commit its implementation and specification;
2. compute the specification and implementation hashes;
3. append a `REGISTERED` event to the new discovery-run registry;
4. commit the registry event;
5. only then permit evaluation on `C0_ITERATION`;
6. append an `EVALUATED` event after the result artifacts exist.

A candidate version may not be rewritten after evaluation. Register a new version instead.

## Candidate-plan requirements

Every candidate must state:

- support-object definition;
- propagation rule;
- exact query form;
- confidence or nonconformity score;
- `C0_FIT` fitting and development-calibration procedure;
- `C0_ITERATION` evaluation procedure;
- all hyperparameters;
- expected failure mode;
- relation to any predecessor version;
- whether it is a propagation candidate or a required baseline.

The complete collection may use no more than three named query forms.

## Required baselines

The execution setup must faithfully include:

```text
independent primitive split-conformal abstention
direct compound split-conformal model
uncalibrated confidence baseline
oracle-support diagnostic
```

The direct compound model must receive a fair feature representation declared before iteration evaluation. It may not be weakened merely to create apparent propagation headroom.

## Data firewall

Permitted roles:

```text
C0_FIT
C0_ITERATION
```

Blocked roles:

```text
C0_SELECTION
C1_CALIBRATION
C1_TEST
```

The runner must refuse any repository not assigned to a visible role and verify the canonical allocation manifest before loading source rows.

No row, repository, metric or failure example from `c0_selection` may be inspected in this PR.

## Ledger paths

Do not mutate the empty ledgers inside:

```text
artifacts/canonical/option-c0/data-firewall-v1/
```

Those files are allocation-time evidence.

Create a new run namespace, for example:

```text
runs/option-c0/discovery-v1/
```

The result-bearing discovery checkpoint may later publish a byte-identical copy under a new canonical discovery directory.

## Required iteration diagnostics

When the reviewed runner is eventually executed, each candidate and baseline must publish:

- risk–coverage curve;
- selective risk at every visible anchor;
- empirical coverage diagnostics;
- accepted, refused and error counts;
- refusal reasons;
- supported, weak, absent and shifted strata;
- repository-level dispersion;
- oracle and direct-compound headroom;
- runtime and peak memory;
- failure examples with stable identities;
- all artifact hashes.

These are exploratory measurements only.

## Explicit exclusions

Do not:

- access `c0_selection`;
- split or inspect the C1 reserve;
- select C1 calibration or test rows;
- write a C1 success margin;
- promote a C0 measurement as a finding;
- omit a strong baseline;
- silently remove a failed candidate;
- mutate the canonical allocation checkpoint;
- execute a real candidate before its registration event is committed.

## Completion state before execution

The next setup PR should stop at:

```text
C0_INITIAL_CANDIDATE_PLAN_REGISTERED_PENDING_ITERATION_EXECUTION
scientific_result_observed = false
mechanism_result_observed = false
c0_selection_accessed = false
c1_rows_selected = false
```

The candidate and baseline implementations, feature procedure, registry and guarded runner must be reviewed before the first real C0 iteration result is produced.

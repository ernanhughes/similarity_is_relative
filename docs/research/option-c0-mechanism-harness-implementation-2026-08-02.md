# Option C0 Mechanism-Discovery Harness Checkpoint

Date: 2026-08-02

## Status

```text
C0_MECHANISM_HARNESS_IMPLEMENTED_PENDING_CANDIDATE_REGISTRATION
scientific_result_observed = false
mechanism_result_observed = false
c0_selection_accessed = false
c1_rows_selected = false
candidate_registry_entries = 0
discovery_ledger_entries = 0
```

This checkpoint implements the development laboratory authorised after the canonical repository allocation merged. It does not register or evaluate a real propagation candidate and does not alter either append-only ledger.

## Visible evidence boundary

The harness can load only repositories assigned to:

```text
c0_fit
c0_iteration
```

It refuses requests for:

```text
c0_selection
c1_reserve
C0_SELECTION
C1_CALIBRATION
C1_TEST
```

The loader verifies the canonical allocation-manifest SHA-256 and the published repository counts before returning visible assignments.

## Bounded query representation

The harness represents each primitive condition as a signed margin:

```text
margin > 0  => primitive condition true
margin <= 0 => primitive condition false
```

It supports three development operators:

```text
all
any
k_of_n
```

These are infrastructure-level logical combinators, not selected scientific query forms. The complete candidate collection may use at most three named query forms, and one query ID cannot silently change definition across candidate versions.

## Support propagation utilities

The harness includes reusable interval semantics:

- a primitive is definitely true when its lower support bound is above zero;
- a primitive is definitely false when its upper support bound is at or below zero;
- otherwise the primitive is unresolved;
- the query operator propagates those three-valued primitive states;
- the system accepts only when the compound truth value is logically determined.

It also includes a joint max-residual box utility. This is not a registered RELATE candidate. It becomes a candidate only if a later reviewed candidate plan gives it an identity, commit, query form, nonconformity score, expected failure mode and artifact commitments before C0 iteration evaluation.

## Required strong baselines

### Independent primitive split-conformal abstention

Each primitive receives its own finite-sample split-conformal absolute-residual radius. The resulting coordinate intervals are propagated through the query operator. Overlap with the decision boundary produces refusal.

### Direct compound split-conformal model

A logistic model is trained directly on the compound target. Its conformal wrapper uses the true-label nonconformity score:

```text
1 - predicted probability of the true label
```

A query is answered only when the conformal prediction set is a singleton.

### Uncalibrated confidence baseline

Examples are ranked deterministically by maximum class probability. This baseline is diagnostic only and must not be confused with calibrated coverage.

### Oracle-support diagnostic

The true signed margins are used to estimate attainable support headroom. Boundary cases can be refused using an explicit minimum-distance rule.

## Development-only diagnostics

The harness reports or supports:

- coverage;
- selective risk;
- accepted, refused and error counts;
- refusal reasons;
- repository-level risk dispersion;
- ranked risk–coverage curves at visible anchors;
- per-primitive and joint empirical interval coverage;
- supported, weak, absent and shifted regime stratification.

These outputs remain exploratory. No metric in this checkpoint is an Option C decision rule.

## Candidate-plan guard

A prospective candidate plan must record:

- candidate ID and version;
- implementation commit;
- support-object definition;
- propagation rule;
- query form;
- confidence or nonconformity score;
- fit, development-calibration and iteration-evaluation roles;
- hyperparameters;
- expected failure mode;
- predecessor version when applicable;
- timestamp and artifact hashes when converted to a registry payload.

The harness enforces:

```text
fit_data_role = C0_FIT
calibration_data_role = C0_FIT
evaluation_data_role = C0_ITERATION
```

It can verify that a candidate has a prior `REGISTERED` event before evaluation. It does not write that event itself.

## Ledger integrity

The empty files committed with the canonical allocation remain immutable evidence of the allocation-time state. Future candidate and discovery events must be written to a new discovery-run evidence directory and published under a new checkpoint. The allocation publication artifact must not be modified merely to begin C0 discovery.

No real candidate or discovery entry is created by this PR.

## Development harness contract

The committed contract freezes only the discovery laboratory:

- visible and blocked roles;
- the three logical query operators;
- the maximum of three query forms;
- the required baseline families;
- development-only alpha values;
- visible coverage anchors;
- required diagnostic categories;
- registration-before-iteration;
- continued refusal of C0 selection and C1 access.

It does not freeze:

- a selected propagation mechanism;
- a final query form;
- a C1 calibration method;
- a C1 matched-coverage rule;
- a material success margin;
- C1 calibration or test identities;
- an Option C outcome.

## Validation

The focused suite covers:

- contract validation;
- canonical allocation hash and count checks;
- visible-role loading;
- hidden-role refusal;
- all, any and k-of-n truth semantics;
- interval propagation;
- finite-sample conformal quantiles;
- independent primitive calibration;
- joint max-residual support;
- direct compound conformal prediction sets;
- deterministic confidence ranking;
- oracle support;
- repository and regime diagnostics;
- candidate role recording;
- three-query-form enforcement;
- registration-before-evaluation;
- result-free setup validation.

Required repository validation:

```text
ruff check .
python -m pytest -q tests/test_option_c0_mechanism_harness.py
python -m pytest -q
git diff --check
```

## Next allowed action

After this implementation is reviewed and merged, the next PR may freeze the initial C0 candidate plan and development feature-generation procedure.

It must:

1. define no more than three query forms;
2. identify every initial candidate and strong baseline before iteration results;
3. create a new append-only discovery-run candidate registry;
4. register every candidate before evaluating `c0_iteration`;
5. prepare a guarded fit/iteration runner;
6. continue to refuse `c0_selection` and all C1 evidence.

The next PR should be reviewed before any real candidate evaluation is run.

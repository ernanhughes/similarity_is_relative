# Option C0 Initial Candidate Plan

Date: 2026-08-02

## Status

```text
C0_INITIAL_CANDIDATE_PLAN_REGISTERED_PENDING_ITERATION_EXECUTION
scientific_result_observed = false
mechanism_result_observed = false
c0_selection_accessed = false
c1_rows_selected = false
candidate_registry_entries = 6
```

The canonical C0 repository firewall and mechanism harness are merged. This checkpoint freezes the first real candidate set and its visible-role execution procedure before any `C0_ITERATION` measurement is observed.

No C0 mechanism result appears in this PR.

## Frozen primitives

The candidate plan retains the three Option B primitives unchanged:

```text
cyclomatic_complexity
max_control_depth
distinct_call_sites
```

No Option B model, row, threshold, query or result is reused as Option C evidence.

## Query construction

Primitive thresholds and scales are not selected from iteration evidence.

The `C0_FIT` model-fit repository partition determines:

- threshold: per-primitive median;
- scale: per-primitive interquartile range, floored at `1.0`;
- quantile implementation: NumPy `method="linear"`;
- condition boundary: a signed margin is true iff `margin > 0`.

The exact query forms are:

1. `all_primitives_above_fit_median` — all three conditions;
2. `any_primitive_above_fit_median` — at least one condition;
3. `two_of_three_primitives_above_fit_median` — at least two conditions.

These are the maximum three query forms permitted by the C0 protocol.

## Internal C0_FIT partition

The canonical `c0_fit` role is divided deterministically at repository level:

```text
80% model fitting
20% development calibration
```

Repository order is the ascending SHA-256 order over:

```text
option-c0-fit-calibration-partition-v1
canonical allocation-context SHA-256
repository identity
```

The first `ceil(repository_count × 0.2)` repositories form the development-calibration partition. All remaining repositories form the model-fit partition.

No repository appears in both partitions.

`c0_iteration` remains evaluation-only. `c0_selection` and the C1 reserve remain inaccessible.

## Feature procedure

Both the propagated candidates and the direct-compound baseline use the frozen CodeBERT identity and canonical Option B embedding implementation:

- maximum token length `256`;
- right padding and truncation;
- attention-mask mean pooling;
- `float32` embedding output.

A standardization transform is fitted on C0_FIT model-fit embeddings only.

The three primitive readouts are Ridge regressions over the standardized embeddings. Ridge alpha is selected independently for each primitive using five repository-grouped folds on C0_FIT model-fit only. The alpha grid remains:

```text
0.01, 0.1, 1.0, 10.0, 100.0
```

Selection minimizes mean absolute error. Ties choose the smaller alpha.

The direct compound model receives the same standardized CodeBERT embeddings. It is not deliberately weakened to create propagation headroom.

## Candidate family 1 — joint max-residual box

For each query form, this candidate constructs an axis-aligned box in robust-scaled predicted primitive-margin space.

Development calibration computes:

1. absolute residual per primitive;
2. a per-coordinate median residual scale;
3. the maximum standardized coordinate residual per calibration row;
4. one finite-sample split-conformal quantile for each visible alpha.

The propagated query is accepted as true only when every primitive realization inside the box makes it true. It is accepted as false only when every realization makes it false. Otherwise it refuses.

Visible alpha grid:

```text
0.01, 0.025, 0.05, 0.1, 0.2
```

Expected failure mode: the axis-aligned box may over-refuse under correlated residuals or conceal directional residual structure.

## Candidate family 2 — empirical residual mass

For each query form, this candidate retains complete three-coordinate residual vectors from the C0_FIT development-calibration partition. Coordinates are never shuffled independently.

Each calibration residual vector is added to the predicted primitive-margin vector, producing an empirical query-support distribution.

The method:

- predicts by majority query support;
- accepts when query-true support is at most `beta` or at least `1 - beta`;
- refuses in the ambiguous middle region.

Visible beta grid:

```text
0.01, 0.025, 0.05, 0.1, 0.2
```

Expected failure mode: finite calibration residuals may not represent repository shift, and the support-mass rule is exploratory rather than distribution-free.

## Registered candidates

The append-only discovery-run registry contains six `REGISTERED` events:

| Family | Query | Version |
|---|---|---|
| joint max-residual box | all | `v1` |
| joint max-residual box | any | `v1` |
| joint max-residual box | two-of-three | `v1` |
| empirical residual mass | all | `v1` |
| empirical residual mass | any | `v1` |
| empirical residual mass | two-of-three | `v1` |

All six point to implementation commit:

```text
d36436209d95eca555215a83856f042d241a90f4
```

The registry is hash chained. No `EVALUATED` or `STATUS_CHANGED` event exists yet.

Evidence identities:

```text
candidate plan SHA-256:
f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94

candidate registry SHA-256:
a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282

registry head SHA-256:
d8c9e32008e80ebdc6a31af432f621f4ac9e80a5fa6bf5be4673febd28c89ea7
```

## Required baselines

Every query is compared with:

1. independent primitive split-conformal abstention;
2. a direct compound logistic model with split-conformal prediction sets;
3. uncalibrated direct-model confidence ranking;
4. an oracle-support diagnostic.

The execution runner also records risk–coverage curves, visible coverage anchors, empirical interval coverage, refusal reasons, regime strata, repository dispersion, runtime and peak memory.

All measurements remain exploratory.

## Execution boundary

The committed script:

```text
scripts/run-option-c0-discovery-iteration-v1.ps1
```

must remain unrun until this PR is reviewed and merged.

After merge, it will:

1. verify exact candidate-plan and registry hashes;
2. require the registered implementation commit in `main` ancestry;
3. run Ruff, focused tests and the complete suite;
4. create a fresh result branch;
5. execute one C0 iteration run;
6. append six `EVALUATED` events tied to the result hash;
7. preserve an empty discovery ledger until human result review;
8. publish an exploratory result checkpoint for review.

## Merge requirement

**Use a regular merge commit. Do not squash this PR.**

The candidate registry points to implementation commit `d36436209d95eca555215a83856f042d241a90f4`. A squash merge would leave that registered implementation identity outside `main` ancestry and cause the execution script to refuse.

## Explicit exclusions

This checkpoint does not:

- evaluate a candidate;
- produce a mechanism result;
- access C0 selection;
- inspect or divide the C1 reserve;
- select C1 rows;
- create a C1 success margin;
- promote any Option C claim;
- mutate the allocation-time empty ledgers.

## Next action

Review and merge this checkpoint with a regular merge commit. Only then run the one-time C0 iteration script.

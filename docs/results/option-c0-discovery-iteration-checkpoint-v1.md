# Option C0 Discovery Iteration Checkpoint v1

**Date:** 2026-08-02  
**Phase:** C0 iteration  
**Status:** `C0_ITERATION_RESULTS_PUBLISHED_PENDING_REVIEW`  
**Evidence branch:** `agent/option-c0-iteration-results-v1`  
**Evidence commit:** `07cf6fc`  
**Evidence role:** exploratory mechanism-development evidence only

## Executive status

The first registered Option C0 discovery iteration completed successfully.

It evaluated six registered candidates—three frozen compound queries crossed with two candidate mechanism families—on the repository-separated C0 iteration partition. The run committed the complete result, appended six `EVALUATED` events to the candidate registry and preserved an empty discovery ledger for post-result interpretation.

The checkpoint does **not** make an Option C scientific decision.

At publication time:

```text
candidate registrations:       6
candidate evaluations:         6
candidate registry entries:   12
discovery ledger entries:      0
mechanism result observed:   true
scientific result observed: false
C0 selection accessed:       false
C1 rows selected:            false
```

The next permitted action is:

```text
C0_ITERATION_RESULT_AND_DISCOVERY_REVIEW
```

The following remain prohibited:

```text
C0 selection access before registry closure
C1 reserve access
C1 row selection
Option C scientific decision
```

## Why this checkpoint exists

Option B established a narrow real-code premise: independently predicted AST primitive coordinates exposed a frozen structural relation materially better than raw CodeBERT cosine or Euclidean geometry.

Option C asks a different question:

> Can uncertainty or support around those predicted primitives be propagated through a compound query so the system accepts supported answers and refuses unsupported ones better than simpler abstention baselines?

C0 is the exploratory mechanism-development stage. C1, if justified later, will be the separately frozen confirmation stage. C0 evidence may determine what deserves confirmation, but cannot itself promote `C-REFUSE-001`.

## Data firewall

All allocation is by whole repository.

| Role | Repositories | Rows | Permitted use |
|---|---:|---:|---|
| C0 fit | 2,117 | 8,007 | model fitting, threshold fitting and calibration |
| C0 iteration | 1,058 | 4,110 | exploratory mechanism evaluation |
| C0 selection | 545 | 2,070 | inaccessible pending registry closure and review |
| C1 reserve | 1,604 | 6,357 | inaccessible; final C1 rows not selected |

The executed fit partition was deterministically divided into:

```text
model-fit rows:       6,390
calibration rows:     1,617
iteration rows:       4,110
```

No C0-selection or C1 row was loaded by the result runner.

## Frozen representation and primitives

```text
domain:             CodeSearchNet Python functions
representation:     microsoft/codebert-base, frozen
model revision:     3b0952feddeffad0063f274080e3c23d75e7eb39
embedding device:   CUDA
fixed batch shape:  10
```

The three AST-derived primitives were:

1. cyclomatic complexity;
2. maximum control nesting depth;
3. distinct call-site count.

The C0-fit medians and robust scales were:

| Primitive | Threshold | Scale | Selected Ridge alpha |
|---|---:|---:|---:|
| Cyclomatic complexity | 2 | 2 | 100 |
| Maximum control depth | 1 | 1 | 100 |
| Distinct call sites | 3 | 2 | 100 |

All three models selected the largest value in the registered Ridge grid. This is an exploratory diagnostic, not evidence that 100 is an optimal universal regularisation value.

## Registered compound queries

The six candidate registrations covered two mechanism families for each query:

1. `all_primitives_above_fit_median`;
2. `any_primitive_above_fit_median`;
3. `two_of_three_primitives_above_fit_median`.

Iteration label prevalence was approximately:

| Query | Positive prevalence |
|---|---:|
| All three | 6.52% |
| Any primitive | see canonical result |
| Two of three | see canonical result |

Prevalence matters when interpreting selective error and easy-example ranking. Reviewers should not infer distinctive support propagation from low risk alone.

## Candidate families

### Joint max-residual box

The method builds an axis-aligned joint uncertainty box in robust-scaled predicted-margin space. It accepts only when the full box implies one compound-query answer.

Registered alpha values:

```text
0.01, 0.025, 0.05, 0.10, 0.20
```

### Empirical residual mass

The method preserves complete joint calibration residual vectors, perturbs each predicted primitive vector by every retained residual and computes empirical true/false mass for the compound query. It accepts only when one outcome receives at least `1 - beta` mass.

Registered beta values:

```text
0.01, 0.025, 0.05, 0.10, 0.20
```

This family was explicitly exploratory and was not assigned a distribution-free guarantee.

## Required baselines

The result includes:

1. independent primitive conformal intervals;
2. a direct compound conformal model for each query;
3. uncalibrated confidence ranking;
4. oracle primitive-support headroom.

Any later claim of distinctive support composition must survive meaningful matched-coverage or matched-risk comparison against these baselines.

## Selected result summary

Percentages below are rounded from the canonical result. They are navigation aids, not a substitute for the complete risk–coverage curves and regime diagnostics.

### All three primitives above threshold

| Method and operating point | Accepted coverage | Selective errors | Selective risk |
|---|---:|---:|---:|
| Empirical residual mass, beta 0.01 | 42.73% | 0 | 0.000% |
| Empirical residual mass, beta 0.025 | 51.22% | 2 | 0.095% |
| Empirical residual mass, beta 0.05 | 58.39% | 16 | 0.667% |
| Joint box, alpha 0.05 | 21.8% | 0 | 0.000% |
| Joint box, alpha 0.10 | 37.4% | approximately 2 | approximately 0.13% |
| Independent primitive, alpha 0.05 | 40.7% | — | approximately 0.120% |
| Uncalibrated confidence near 50% coverage | 50.0% | 2 | approximately 0.097% |

The strongest descriptive observation is that the conjunction admits sizeable low-error selective subsets. The major qualification is that ordinary confidence ranking and independent primitive abstention are highly competitive at similar coverage.

### Any primitive above threshold

| Method and operating point | Accepted coverage | Selective risk |
|---|---:|---:|
| Empirical residual mass, beta 0.01 | approximately 28.3% | approximately 1.89% |
| Joint box, alpha 0.05 | approximately 21.0% | approximately 1.39% |
| Direct compound conformal, alpha 0.01 | approximately 38.3% | approximately 1.14% |

This query did not reproduce the exceptionally low-risk pattern seen for the conjunction. A 25-row shifted diagnostic stratum was especially difficult across several methods; because it is small, it should be recorded as a diagnostic rather than treated as a stable subgroup estimate.

### Two of three primitives above threshold

| Method and operating point | Accepted coverage | Selective risk |
|---|---:|---:|
| Empirical residual mass, beta 0.01 | approximately 22.9% | approximately 1.06% |
| Joint box, alpha 0.10 | approximately 24.1% | approximately 1.31% |
| Direct compound conformal, alpha 0.01 | approximately 60.3% | approximately 0.807% |
| Uncalibrated confidence near 50% coverage | 50.0% | approximately 0.195% |

The direct compound model and simple confidence ranking were stronger at these selected operating points. That is adverse evidence for a broad superiority interpretation of the registered support-composition candidates.

## Primitive interval calibration

The aggregate joint primitive interval coverage tracked nominal coverage closely:

| Alpha | Nominal joint coverage | Observed joint coverage |
|---:|---:|---:|
| 0.01 | 99.0% | 98.91% |
| 0.025 | 97.5% | 97.40% |
| 0.05 | 95.0% | 94.72% |
| 0.10 | 90.0% | 89.76% |
| 0.20 | 80.0% | 80.73% |

This reduces concern about a gross aggregate interval-calibration failure. It does not prove query-level selective validity, candidate superiority or correct behaviour under every regime.

## What the C0 result directly supports

The result directly supports these exploratory observations:

- frozen CodeBERT embeddings permit nontrivial primitive prediction on the C0 allocation;
- calibrated joint primitive intervals have aggregate coverage close to their nominal levels;
- the registered mechanisms can identify low-error accepted subsets for some query/operating-point combinations;
- the conjunction query is substantially easier to support selectively than the disjunction or two-of-three query under the registered mechanisms;
- simpler baselines remain highly competitive and sometimes clearly stronger;
- the effect is strongly query-dependent.

These are development observations. They are not promoted findings.

## What the result does not establish

C0 does not establish that:

- propagated primitive support is generally superior;
- either candidate family is distinctive beyond confidence ranking;
- either candidate family beats a directly trained compound model;
- the behaviour generalises beyond the frozen representation, language, primitives or thresholds;
- the low-risk conjunction subset will reproduce on fresh C1 evidence;
- a broad Boolean query algebra has been learned;
- `C-REFUSE-001` is supported;
- C1 is automatically justified.

## Provisional interpretation for review—not a project decision

A defensible provisional summary is:

> Predicted primitive support isolated useful low-risk subsets for some compound structural queries, especially the conjunction, but the effect was strongly query-dependent and the registered candidate families did not clearly outperform the strongest direct, independent-primitive or confidence-ranking baselines.

This wording is intentionally provisional. The discovery ledger is still empty, the candidate registry is not yet closed and no C0 exit outcome has been published.

## Questions external reviewers should answer

1. Does the conjunction result show anything beyond ordinary confidence ranking or class/easy-example selection?
2. Which comparisons are scientifically decisive: matched coverage, matched risk, a constrained operating point, or a curve-level endpoint?
3. Do the differences among `all`, `any` and `two-of-three` follow from query geometry, prevalence, primitive-error dependence or another mechanism?
4. Is any C1 contract scientifically justified?
5. If yes, should C1 test superiority, non-inferiority, calibration or simple replication?
6. Is the conjunction observation meaningful enough to select for confirmation, or would doing so be a post-hoc rescue of a broad failed idea?
7. What entries belong in the discovery ledger before the candidate registry closes?

See the [independent review guide](../reviews/option-c0-iteration-independent-review-guide.md) for a structured review procedure.

## Evidence identities

```text
result artifact:
artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json
SHA-256:
ca81076fd21ecf97fc33dcd2a1690a2cd29443cb9cf5c26eba49c00095a1df99

candidate registry:
artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl
SHA-256:
5ecef017282288d2715577396f162b2b3380828b64a1332ee45bf68b120990c9

publication checkpoint:
artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json

candidate-plan identity erratum:
artifacts/canonical/option-c0/candidate-plan-v1/option-c0-candidate-plan-identity-erratum-v1.json
SHA-256:
c1fa786fc5932bd5157ac2659ef8e6c58eb421d0d3200f339b6a096f362dc3dc

discovery ledger:
artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-ledger-v1.jsonl
bytes: 0
SHA-256:
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Next permitted sequence

1. Independently review and recompute the committed result summary.
2. Append genuinely planned or unexpected observations to the discovery ledger with explicit classifications.
3. Review all six evaluated candidates and close the candidate registry.
4. Publish exactly one C0 exit outcome:
   - `C1_CONTRACT_JUSTIFIED`
   - `C1_NOT_JUSTIFIED`
   - `C0_DATA_FIREWALL_FAILED`
   - `C0_BUDGET_EXHAUSTED`
5. Only `C1_CONTRACT_JUSTIFIED` permits a documentation-only C1 contract.
6. C1 rows remain unselected until that later contract freezes the selection procedure.

No reviewer should access C0 selection or C1 merely to resolve uncertainty about the interpretation above.

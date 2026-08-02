# Post-E01 Publication and Kill-Test Decision

Original decision date: 2026-08-01  
Option B outcome update: 2026-08-02

## Current decision status

```text
E01 closure: COMPLETE
E01 publication narrative: COMPLETE
Option B real-premise test: COMPLETE
Option B decision: REAL_PREMISE_SUPPORTED
Option C propagated refusal: AUTHORISED, CONTRACT NOT YET FROZEN
Former broad synthetic E02–E07 plan: CANCELLED
Remaining authorised RELATE research budget: MAXIMUM 15 WORKING DAYS
```

## Original decision

After the E01 independent audit, the project rejected the former six-stage E02–E07 roadmap and the proposed large synthetic factorisation matrix.

That design would have measured quantities largely determined by generator settings and risked repeating the failure mode identified in E01.

The bounded path was frozen as:

1. finalize and publish the E01 case study;
2. run Option B, one real frozen-representation premise test;
3. run Option C only if Option B passes;
4. stop the relevant RELATE line if either kill test fails.

The maximum remaining budget was 25 working days: ten for Option B and fifteen for conditional Option C.

## Option B — completed real-representation premise test

### Question

> Does a real frozen representation contain an objectively measurable compound relation that default cosine and Euclidean geometry expose materially worse than simple supervised primitive readouts?

### Frozen implementation

Option B used:

- the Python partition of CodeSearchNet;
- published repository-separated splits;
- frozen `microsoft/codebert-base` embeddings;
- 20,000 selected training functions;
- 4,000 validation functions;
- 4,000 test queries;
- cyclomatic complexity, maximum control depth and distinct call-site count;
- one AND-style Chebyshev compound relation;
- raw cosine and raw Euclidean controls;
- a predicted primitive executor with no compound supervision;
- 512,000 preregistered hard-negative pairs;
- a single two-outcome `0.10` continuation rule.

### Frozen decision rule

```text
raw_best = max(raw_cosine_hard_triplet_accuracy,
               raw_euclidean_hard_triplet_accuracy)

gap = predicted_executor_hard_triplet_accuracy - raw_best

gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

There was no inconclusive band and no secondary-metric rescue.

### Result

```text
raw cosine accuracy:       0.532458984375
raw Euclidean accuracy:    0.533314453125
predicted executor:        0.732851562500
raw best:                  0.533314453125
gap:                       0.199537109375
threshold:                 0.100000000000
outcome:                   REAL_PREMISE_SUPPORTED
```

The predicted primitive executor exceeded the strongest raw geometry by approximately 19.95 percentage points, almost twice the frozen threshold.

The result was independently recomputed. A separate implementation that did not import the evaluator reverified the frozen inputs and exactly reproduced all `4,000 × 5` primary query scores, the registered gap and the final outcome.

### Interpretation

Option B supports the bounded premise that a real frozen representation can contain recoverable structural relations that its default geometry materially underexposes.

It does not establish:

- a general composition algorithm;
- semantic binding;
- support propagation;
- calibrated refusal;
- novelty over a directly trained compound model;
- solved nearest-neighbour retrieval.

Exact recall remained low in absolute terms even though hard-negative ordering, oracle correlation, neighbour regret and constraint error improved substantially.

### Evidence

- [Human-readable Option B checkpoint](../results/option-b-real-code-premise-checkpoint-v1.md)
- [Option B result article](../blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)
- [Frozen Option B contract](../experiments/08-option-b-real-code-premise-test.md)
- [Canonical Option B evidence](../../artifacts/canonical/option-b/method-evaluation-v1/)

## Option C — authorised propagated-refusal test

Option B passed, so the post-E01 decision now authorises one Option C experiment with a maximum remaining budget of fifteen working days.

Option C is **not yet preregistered or implemented**.

### Question

> Does compound-level propagation of calibrated primitive support improve selective risk at matched coverage beyond independent per-primitive conformal abstention and a directly trained compound model with its own conformal wrapper?

### Minimum required baselines

The future contract must faithfully represent at least:

1. independent split-conformal primitive abstention;
2. a directly trained compound selective model with its own conformal wrapper;
3. propagated compound support;
4. an uncalibrated confidence baseline where technically appropriate.

Relevant post-hoc concept bottleneck and unseen-query composition methods must be reviewed before novelty language is allowed.

### Required prospective contract

Before any implementation begins, a documentation-only contract must freeze:

- the exact compound query or bounded query set;
- train, calibration, validation and test roles;
- supported, absent and shifted primitive regimes;
- the split-conformal calibration method;
- the propagated support rule;
- the independent primitive abstention rule;
- the direct compound baseline;
- selective-risk and coverage definitions;
- the matched-coverage comparison procedure;
- tie, empty-support and refusal handling;
- the primary material margin;
- the independent recomputation boundary;
- the novelty-line kill decision.

No Option B model, language, query, threshold, canonical row or hard-negative manifest may be changed to make Option C easier.

### Kill condition

If propagated support does not beat the strongest preregistered baseline by the frozen material margin on selective risk at matched coverage, the RELATE novelty line closes.

The Option B real-premise finding remains valid regardless of the Option C outcome.

## Updated stop rule

```text
OPTION B: PASSED
→ preserve and publish B-PREM-001;
→ authorise one separately contracted Option C experiment.

OPTION C FAILS
→ close RELATE novelty research;
→ preserve the Option B premise result;
→ publish the refusal null result and methodological record.

OPTION C PASSES
→ permit one bounded real-domain refusal pilot under a new decision record.
```

No additional synthetic roadmap is authorised by this decision.

## Methodological deliverable

The evidence-first process remains a separate output from RELATE's scientific claims.

The E01 and Option B sequence now supports at least these reusable rules:

1. attainable-ceiling gate;
2. discriminating-power review;
3. gate-lineage rule;
4. control-validity rule;
5. independent-verification taxonomy;
6. metric-continuity rule;
7. prospective artifact gate—freeze data and hard-negative evidence before method performance;
8. independent-decision gate—publish a primary result only after separate substantive recomputation.

These process rules remain publishable regardless of the Option C outcome.

## Canonical Option B identities

```text
Full result SHA-256:
31223e02b807bbecb6603a76921677a6f79bac88609243bb20cf11ec30a68158

Primary score array SHA-256:
dccf0698934142ceaf1fe0ccd5d35713600ef45f9719e3864468c40a5274dc70

Raw query-metrics SHA-256:
784ded45280c99325f2ac285244dd4905b5718688c765831cd07f26fb9e184a7

Independent verification SHA-256:
da1b9cf1244b47c71ac7adce91b7db502b4fd2d3b663e126d8cde7c87e239d6c
```

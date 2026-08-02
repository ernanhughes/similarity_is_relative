# Post-E01 Publication and Kill-Test Decision

Original decision date: 2026-08-01  
Option B outcome update: 2026-08-02  
Option C0 discovery-protocol update: 2026-08-02

## Current decision status

```text
E01 closure: COMPLETE
E01 publication narrative: COMPLETE
Option B real-premise test: COMPLETE
Option B decision: REAL_PREMISE_SUPPORTED
Option C0 discovery protocol: FROZEN, IMPLEMENTATION NOT STARTED
Option C1 confirmatory refusal: BLOCKED UNTIL C0 CHECKPOINT
Former broad synthetic E02–E07 plan: CANCELLED
Remaining authorised Option C budget: MAXIMUM 15 WORKING DAYS TOTAL
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

## Why Option C is split

Option B passed, so one bounded propagated-refusal investigation remains authorised.

The original Option C question is retained:

> Does compound-level propagation of calibrated primitive support improve selective risk at matched coverage beyond independent per-primitive conformal abstention and a directly trained compound model with its own conformal wrapper?

However, this question currently combines two different activities:

1. discovering a coherent support representation and propagation rule;
2. confirming that a selected rule beats strong calibrated alternatives.

Freezing a favourite propagation rule before development evidence exists would create a false form of rigour. It would prevent legitimate mechanism discovery while offering no guarantee that the frozen mechanism is the right abstraction.

The project therefore freezes the process in two phases:

```text
C0  bounded mechanism discovery and discriminating-power review
C1  separately frozen confirmatory refusal test
```

C0 may learn. C1 may support or reject C-REFUSE-001. C0 cannot.

## Option C0 — bounded discovery

### Budget

```text
maximum C0 budget: 5 working days
maximum Option C total: 15 working days
```

Unused C0 time may remain available to C1. The total may not exceed fifteen working days without a new explicit decision.

### Purpose

C0 determines:

- which support objects are coherent;
- which propagation families merit consideration;
- how supported, weak, absent and shifted primitives behave;
- where risk–coverage curves are non-degenerate;
- which baseline is strongest;
- whether attainable headroom exists;
- whether one mechanism can be specified precisely enough for C1.

### Data firewall

C0 and C1 use five repository-separated roles:

```text
C0 fit
C0 iteration
C0 selection
C1 calibration reserve
C1 test reserve
```

C1 reserve repositories must also be disjoint from every repository represented in the canonical Option B selected manifests.

Final C1 calibration and test rows are not selected during C0. C0 commits only a reserve pool, aggregate identities and a deterministic future selection algorithm.

The final C1 identities are derived after the C1 contract merges, using that merge commit as part of the frozen selection seed.

### Required discovery record

C0 must maintain:

- an append-only candidate registry;
- an append-only discovery ledger;
- complete identities for every evaluated candidate version;
- complete retention of failed and superseded candidates;
- development-only risk–coverage and calibration diagnostics;
- a baseline fidelity review;
- attainable-headroom analysis;
- one explicit C0 outcome.

### Required baselines

C0 must implement or faithfully represent at least:

1. independent split-conformal primitive abstention;
2. a directly trained compound model with its own conformal wrapper;
3. propagated-support candidates;
4. an uncalibrated confidence baseline where meaningful;
5. an oracle-support headroom diagnostic.

Relevant concept bottleneck, selective prediction, conformal and unseen-query composition prior art must be reviewed before novelty language is allowed in C1.

### C0 outcomes

Exactly one outcome is permitted:

```text
C1_CONTRACT_JUSTIFIED
C1_NOT_JUSTIFIED
C0_DATA_FIREWALL_FAILED
C0_BUDGET_EXHAUSTED
```

Only `C1_CONTRACT_JUSTIFIED` permits a later documentation-only C1 contract.

C0 measurements remain exploratory regardless of replay or artifact verification.

### Discovery-preservation rule

Unexpected observations must be preserved rather than discarded because they differ from the original expectation.

They may influence the C1 contract only when discovered before C1 freezes and when recorded explicitly in the discovery ledger.

They may not:

- be described as confirmed findings;
- inspect or select C1 evidence;
- rescue a failed C1 decision;
- inherit support from B-PREM-001.

An unexpected observation first found on C1 test evidence requires a new experiment identifier and fresh data before promotion.

### C0 protocol

The complete prospective protocol is:

- [Option C0 discovery and confirmation protocol](../experiments/09-option-c0-discovery-and-confirmation-protocol.md)
- [Option C0 discovery-preservation decision](option-c0-discovery-preservation-decision-2026-08-02.md)

## Option C1 — future confirmation

C1 is not yet contracted or implemented.

A C1 contract may be written only after C0 records `C1_CONTRACT_JUSTIFIED`.

The future contract must freeze:

- the selected propagation mechanism;
- the exact query or bounded query set;
- supported, weak, absent and shifted regimes;
- train and fitting roles;
- the final split-conformal or calibration method;
- independent primitive and direct compound baselines;
- selective-risk and coverage definitions;
- matched-coverage comparison procedure;
- tie, empty-support and refusal handling;
- the primary material margin;
- post-contract reserve selection;
- independent recomputation boundaries;
- the claim-scoped novelty-line decision.

No C1 implementation may begin in the C0 checkpoint PR.

## Updated stop rule

```text
OPTION B: PASSED
→ preserve and publish B-PREM-001;
→ authorise the bounded C0/C1 Option C sequence.

C0: C1_CONTRACT_JUSTIFIED
→ permit a documentation-only C1 contract;
→ keep C1 implementation blocked until that contract merges.

C0: C1_NOT_JUSTIFIED
or C0_DATA_FIREWALL_FAILED
or C0_BUDGET_EXHAUSTED
→ close the current RELATE propagated-refusal novelty route;
→ preserve Option B and all clearly labelled exploratory records.

C1 FAILS
→ close the current RELATE propagated-refusal novelty route;
→ preserve the Option B premise result;
→ publish the refusal null result and methodological record.

C1 PASSES
→ permit one bounded real-domain refusal pilot under a new decision record.
```

No additional synthetic roadmap or automatic rescue stage is authorised.

## Claim-scoped interpretation

A C0 or C1 failure means only that the current bounded RELATE propagated-support route did not justify or satisfy its confirmatory test.

It does not invalidate:

- B-PREM-001;
- the Option B canonical evidence;
- the E01 methodological findings;
- clearly labelled exploratory observations;
- unrelated future work under a new decision, identifier and fresh evidence.

## Methodological deliverable

The evidence-first process remains a separate output from RELATE's scientific claims.

The E01, Option B and C0 sequence now supports at least these reusable rules:

1. attainable-ceiling gate;
2. discriminating-power review;
3. gate-lineage rule;
4. control-validity rule;
5. independent-verification taxonomy;
6. metric-continuity rule;
7. prospective artifact gate;
8. independent-decision gate;
9. discovery-preservation rule;
10. phase-label rule;
11. deferred-holdout rule.

These process rules remain publishable regardless of the C0 or C1 outcome.

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

## Next permitted action

Implement only C0 data allocation, candidate-registry and discovery-ledger infrastructure.

Mechanism discovery remains blocked until the data firewall is reviewed. C1 remains blocked until C0 publishes one explicit outcome.
# Option B Real-Code Premise Checkpoint v1

Date: 2026-08-02

## Status

```text
Option B contract: COMPLETE
Canonical evidence: PUBLISHED
Independent primary recomputation: COMPLETE
Scientific result observed: TRUE
Decision: REAL_PREMISE_SUPPORTED
Option C: AUTHORISED, NOT YET CONTRACTED
```

This checkpoint is the human-readable companion to the canonical artifacts under:

```text
artifacts/canonical/option-b/method-evaluation-v1/
```

It records the result of the single real frozen-representation premise test authorised after the E01 composition line was closed.

## Registered question

> Does a frozen code representation that we did not train materially underexpose an objectively measurable compound structural relation under its default geometry?

Option B tested that question in real repository-separated Python code using a frozen external representation and objective AST-derived primitive labels.

It did not test calibrated refusal, support propagation, semantic binding, a general query algebra or novelty against a directly trained compound model.

## Frozen design

```text
dataset: CodeSearchNet Python partition
representation: microsoft/codebert-base, frozen
selected rows:
  train:      20,000
  validation:  4,000
  test:        4,000
embedding dimensions: 768
primitive relations:
  - cyclomatic complexity
  - maximum control nesting depth
  - distinct call-site count
compound query: joint similarity under Chebyshev distance
candidate pool: selected training functions
queries: every selected test function
hard-negative pairs: 128 per query
hard-negative pair total: 512,000
```

The predicted executor used independently predicted primitive vectors on both the query and candidate sides. Train-candidate predictions were out of fold. Primitive model selection used validation labels only. Test primitive labels were not available to probe fitting or model selection.

## Frozen primary decision

```text
raw_best = max(raw_cosine_hard_triplet_accuracy,
               raw_euclidean_hard_triplet_accuracy)

gap = predicted_executor_hard_triplet_accuracy - raw_best
```

Decision rule:

```text
gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

There was no inconclusive band and no secondary-metric override.

The primary estimate was the equal-weighted mean of per-query hard-negative triplet accuracy. Method-distance ties scored `0.5`. Oracle ties were excluded when the frozen manifest was built.

## Registered primary result

| Method | Hard-negative triplet accuracy |
|---|---:|
| Raw CodeBERT cosine | `0.532458984375` |
| Raw CodeBERT Euclidean | `0.533314453125` |
| Token-length diagnostic | `0.498683593750` |
| True-primitive oracle | `1.000000000000` |
| Predicted primitive executor | `0.732851562500` |

```text
raw best method: raw Euclidean
raw best:        0.533314453125
predicted:       0.732851562500
gap:             0.199537109375
threshold:       0.100000000000
outcome:         REAL_PREMISE_SUPPORTED
```

The predicted executor exceeded the strongest raw CodeBERT geometry by approximately **19.95 percentage points**. The registered gap was almost twice the required continuation threshold.

All 4,000 queries had informative pairs. Because every query contributed exactly 128 pairs, the equal-query and pair-weighted point estimates were identical for this run.

## Primitive recoverability

Each primitive selected ridge `alpha = 1.0` using validation MAE.

### Test-split diagnostics

| Primitive | MAE in robust-scaled units | R² | Spearman |
|---|---:|---:|---:|
| Cyclomatic complexity | `0.197698` | `0.807477` | `0.899833` |
| Maximum control depth | `0.243804` | `0.821459` | `0.893519` |
| Distinct call sites | `0.306464` | `0.763374` | `0.881927` |

These diagnostics show that the three objective properties were recoverable from the frozen representation. They were descriptive and did not replace the registered compound-query comparison.

## Secondary retrieval context

| Metric | Raw cosine | Raw Euclidean | Predicted executor | True oracle |
|---|---:|---:|---:|---:|
| Spearman with oracle distance | `0.111985` | `0.110453` | `0.723079` | `1.000000` |
| Recall@10 | `0.003250` | `0.003025` | `0.009075` | `1.000000` |
| Recall@50 | `0.009305` | `0.009210` | `0.033870` | `1.000000` |
| Neighbour regret@10 | `0.867825` | `0.868950` | `0.498850` | `0.000000` |
| Neighbour regret@50 | `0.917850` | `0.918590` | `0.485255` | `0.000000` |
| Constraint error@10 | `1.589625` | `1.590625` | `0.996375` | `0.015125` |
| Constraint error@50 | `2.145750` | `2.147125` | `1.351000` | `0.058375` |

The executor materially improved oracle-distance correlation, hard-negative ordering, neighbour regret and returned-candidate constraint error.

Exact nearest-neighbour recall remained low in absolute terms. This prevents an interpretation that the retrieval task is solved. The supported premise is narrower: default geometry materially underexposes a recoverable relation-specific structure.

## Repository and length diagnostics

Repository bootstrap was descriptive only and could not alter the registered point-estimate outcome.

The 2,000-repeat repository bootstrap interval for the gap was:

```text
95% descriptive interval: [0.1956579825, 0.2030583576]
```

Every token-length decile retained a positive executor gap. The smallest decile gap was approximately `0.12145`, still above the registered project-level threshold.

Leave-one-large-repository-out gaps remained close to `0.20`; among the ten recorded removals they ranged approximately from `0.19871` to `0.20006`.

These diagnostics indicate that the point estimate was not driven by one large repository or one token-length band. They remain contextual analyses rather than substitute decision rules.

## Independent verification

The independent verifier did not import the method-evaluation runner.

It separately:

- reverified canonical selected manifests and primitive tables;
- reverified train and test CodeBERT embedding arrays;
- reverified train and test predicted primitive arrays;
- reverified the complete frozen hard-negative stream;
- recomputed all primary query scores;
- compared the resulting `4,000 × 5` matrix with exact equality;
- recomputed all primary point estimates;
- recomputed `raw_best`, the registered gap and the final outcome.

Every primary query score and the final decision matched exactly.

## Canonical identities

```text
Implementation merge commit:
211e6f1a5fd827f55f89c69692acc9453f38f09f

Result publication merge commit:
78e7da18a15a393cbedf1fdb7d6023ea42a32967

Full result SHA-256:
31223e02b807bbecb6603a76921677a6f79bac88609243bb20cf11ec30a68158

Primary query-score file SHA-256:
658a5974daed34a6d75b57ff48ff3e6352b48c30cbad081f520168c66d39bc61

Primary query-score logical array SHA-256:
dccf0698934142ceaf1fe0ccd5d35713600ef45f9719e3864468c40a5274dc70

Raw query-metrics SHA-256:
784ded45280c99325f2ac285244dd4905b5718688c765831cd07f26fb9e184a7

Deterministic query-metrics gzip SHA-256:
7f81dc225b0b5d1a72d4fb80d05d34e809fc62e4cd37c0efa2fe5640b61898f9

Independent verification SHA-256:
da1b9cf1244b47c71ac7adce91b7db502b4fd2d3b663e126d8cde7c87e239d6c

Publication checkpoint SHA-256:
2061e36748925c83fb719ff446e84b264a606f4b1fd6eb528e5067812f4a9e60
```

## Promoted claim

The evidence supports the following bounded claim:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed a frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

This is claim-ledger row `B-PREM-001`.

## What is not established

Option B does not establish that:

- RELATE implements a general relational-composition algorithm;
- the three primitives are a complete semantic description of code;
- the executor reaches the attainable oracle;
- exact nearest-neighbour retrieval is solved;
- calibrated support propagates correctly through compound queries;
- the system can identify and refuse unsupported queries;
- the method outperforms a directly trained compound model;
- the remaining mechanism is novel.

## Consequence

Option B passed the gate required to continue the bounded RELATE programme.

The next permitted scientific stage is a separately contracted Option C refusal test asking whether propagated compound support beats:

1. independent per-primitive conformal abstention; and
2. a directly trained compound model with its own conformal wrapper;

on selective risk at matched coverage.

Option C is authorised but is not yet preregistered. No implementation should begin until its complete prospective contract and kill rule are reviewed and merged.

## Related records

- [Option B frozen contract](../experiments/08-option-b-real-code-premise-test.md)
- [Option B result article](../blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)
- [Post-E01 decision](../research/post-e01-publication-and-kill-test-decision-2026-08-01.md)
- [Canonical Option B evidence](../../artifacts/canonical/option-b/method-evaluation-v1/)

# The Embedding Knew More Than Its Geometry Showed

The first real RELATE premise test passed.

That sentence needs to be handled carefully, because this project has already learned how easy it is for a passing number to support a larger story than the experiment actually tested.

Option B does not prove a general composition algorithm. It does not prove calibrated refusal. It does not prove novelty.

It establishes something narrower and load-bearing:

> A real frozen code representation contained useful structural relations that its default cosine and Euclidean geometry materially underexposed.

That was the premise RELATE needed before there was any reason to continue.

## Why we needed a real test

The earlier E01 composition experiments looked successful.

Primitive predictors were trained independently. Their outputs were combined into weighted queries after training. The results passed the registered controls and then reproduced across five fresh synthetic worlds.

An independent audit later showed that the experiment had not asked a sufficiently difficult question.

The generator was saturated. The primitive predictors were already operating almost exactly at the true-latent ceiling. The strongest semantic-looking permutation control was mostly measuring weight separation among exchangeable axes. A confirmation stage had also changed the decision rule it appeared to replicate.

The measurements were real. The interpretation was too broad.

We closed the E01 composition line and cancelled the large synthetic roadmap that was supposed to follow it.

The next question became much simpler:

> Is there a real representational problem here at all?

If ordinary embedding geometry already exposed the relation well, there would be little motivation for a query executor, support propagation or refusal system.

Option B was designed to kill the project if that premise failed.

## What we froze

We removed as much experimenter control as possible.

The data came from the Python partition of CodeSearchNet. Repository-separated train, validation and test splits were preserved. The representation was the frozen `microsoft/codebert-base` model. The project did not train it and did not choose how strongly it encoded the registered properties.

We selected:

```text
20,000 training functions
 4,000 validation functions
 4,000 test functions
```

For each function, we computed three objective structural properties from the Python AST:

1. cyclomatic complexity;
2. maximum control nesting depth;
3. number of distinct normalized call sites.

The query was an AND-style structural relation:

> Retrieve functions that are jointly similar across all three properties.

The true query distance was Chebyshev distance over robust-scaled primitive values:

```text
d(q, c) = max_k |t_k(q) - t_k(c)|
```

A candidate was only close when its worst mismatch across the three registered properties was small.

The method under test predicted each primitive independently from the frozen CodeBERT embedding, then applied the same Chebyshev query to the predicted coordinates.

No compound-query labels were used to train the executor.

## Why the comparison was hard enough

The principal baselines were the representation's default geometries:

- cosine distance over normalized CodeBERT embeddings;
- Euclidean distance over unnormalized CodeBERT embeddings.

CodeBERT was pretrained for code understanding and code search. Raw cosine was therefore a credible competitor, not a deliberately weak baseline.

The primary test also avoided easy random triplets.

For every test query, training candidates were restricted to the same tokenizer-length decile. Candidates were ranked by the true structural oracle. We retained pairs separated by only 5 to 25 oracle positions, excluded oracle ties and deterministically selected 128 pairs per query.

That produced:

```text
4,000 queries
128 hard-negative pairs per query
512,000 frozen pairs in total
```

The complete manifest was generated, independently checked, committed and merged before any method performance was calculated.

The decision was frozen:

```text
raw_best = max(raw cosine accuracy, raw Euclidean accuracy)
gap = predicted executor accuracy - raw_best

pass when gap >= 0.10
fail when gap < 0.10
```

There was no inconclusive band. Secondary metrics could not rescue a failure.

## The result

The registered hard-negative triplet accuracies were:

| Method | Accuracy |
|---|---:|
| Raw CodeBERT cosine | `0.532458984375` |
| Raw CodeBERT Euclidean | `0.533314453125` |
| Token-length diagnostic | `0.498683593750` |
| Predicted primitive executor | `0.732851562500` |
| True-primitive oracle | `1.000000000000` |

The strongest raw baseline was Euclidean distance:

```text
raw best: 0.533314453125
```

The predicted executor achieved:

```text
0.732851562500
```

The registered gap was:

```text
0.199537109375
```

The required gap was:

```text
0.100000000000
```

The outcome was therefore:

```text
REAL_PREMISE_SUPPORTED
```

The executor beat the strongest default geometry by approximately **19.95 percentage points** on the frozen hard-negative test—almost twice the threshold required to continue.

## What the primitive models recovered

The three primitive readouts were not perfect, but they were strong enough to recover useful structure from the frozen representation.

On the test split:

| Primitive | R² | Spearman |
|---|---:|---:|
| Cyclomatic complexity | `0.8075` | `0.8998` |
| Maximum control depth | `0.8215` | `0.8935` |
| Distinct call sites | `0.7634` | `0.8819` |

That matters because Option B was not allowed an escape clause for weak primitive recovery. If the representation had not supported these readouts, the project would have failed the premise test.

## The secondary metrics tell a more complicated story

The primary result is strong. The retrieval problem is not solved.

The predicted executor's correlation with true oracle distance was approximately:

```text
0.723
```

Raw cosine and Euclidean were both close to:

```text
0.11
```

The executor also reduced neighbour regret and returned candidates with smaller worst-primitive mismatch.

But exact top-k overlap remained low:

| Method | Recall@10 | Recall@50 |
|---|---:|---:|
| Raw cosine | `0.00325` | `0.00931` |
| Raw Euclidean | `0.00303` | `0.00921` |
| Predicted executor | `0.00908` | `0.03387` |

The executor improved recall substantially relative to raw geometry, but the absolute numbers are still small.

This is an important limit on the claim.

Option B shows that the predicted primitive geometry orders difficult candidates much better and tracks the registered structural oracle much more closely. It does not show that it reconstructs the oracle's exact nearest-neighbour set.

The representation contained more usable relational information than its default geometry showed. The executor did not extract all of it perfectly.

## The result was not carried by one repository

The registered decision used the point estimate over all queries. Repository uncertainty was descriptive and could not change the pass or fail outcome.

Still, the diagnostics were reassuring.

A 2,000-repeat repository bootstrap placed the gap at approximately:

```text
[0.19566, 0.20306]
```

Every tokenizer-length decile retained a positive gap above `0.12`. Removing each of the ten largest test repositories one at a time left the gap close to `0.20`.

The result was not a single-repository accident or a narrow function-length effect.

## We recomputed it independently

The evaluator did not receive the last word.

A separate verifier reloaded and rehashed the frozen evidence, including:

- selected row manifests;
- true primitive tables;
- CodeBERT embedding arrays;
- predicted primitive arrays;
- the complete hard-negative pair stream.

It then reimplemented the primary distance calculations and scoring without importing the experiment evaluator.

It recomputed every value in the `4,000 × 5` primary query-score matrix and required exact equality.

The matrices matched exactly. The point estimates matched. The registered gap matched. The final decision matched.

This distinction matters.

Deterministic replay checks that the same machinery repeats itself. Independent metric recomputation checks that a different implementation reaches the same scientific answer from the frozen evidence.

Option B has the latter.

## What we can now say

We can now support this bounded statement:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed a frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

That is the first promoted real-domain claim in the repository.

It gives RELATE a real motivation:

- the underlying representation contains useful structural signals;
- its default geometry does not expose the registered relation well;
- separate primitive readouts can create a substantially better query-specific geometry without compound supervision.

This is not merely another synthetic positive control.

## What we still cannot say

Option B does not show that:

- RELATE has discovered a novel general composition algorithm;
- three AST scalars capture code semantics generally;
- predicted geometry reaches the true oracle;
- nearest-neighbour retrieval is solved;
- uncertainty estimates are calibrated;
- compound support propagates correctly;
- the system knows when to refuse;
- propagated refusal beats ordinary conformal baselines;
- the approach beats a directly trained compound model.

Those boundaries are not disclaimers added after the result. They were part of the frozen contract.

## Why the earlier failure mattered

The E01 failure changed how Option B was built.

Because E01 had saturated at its attainable ceiling, Option B reported the true oracle and the remaining headroom.

Because E01 had relied on easy triplets, Option B committed hard negatives before method evaluation and preserved recall, regret, neighbour rank and constraint metrics.

Because E01's control lineage had changed, Option B froze one threshold and one two-outcome rule from contract to final publication.

Because deterministic replay had not been enough to protect interpretation, Option B required an independent primary recomputation.

The process did not merely make the result more bureaucratic. It made the result worth believing.

## Where the project is now

Option B was the real-premise gate.

It passed.

That authorises one remaining bounded experiment: Option C.

Option C asks a different and more demanding question:

> Can calibrated primitive support be propagated through a compound query so that the system refuses unsupported cases better than simpler calibrated alternatives?

The required comparisons will include:

1. independent per-primitive conformal abstention;
2. a directly trained compound model with its own conformal wrapper; and
3. propagated RELATE support.

The primary evidence will be selective risk at matched coverage.

Option C is not implemented. Its contract, calibration splits, baselines, risk definition, coverage matching and kill threshold must be frozen before code is written.

A failure would close the novelty line while preserving the Option B finding.

A pass would justify one bounded real-domain refusal pilot under a new decision record.

## Evidence

```text
Full result SHA-256:
31223e02b807bbecb6603a76921677a6f79bac88609243bb20cf11ec30a68158

Primary query-score logical array SHA-256:
dccf0698934142ceaf1fe0ccd5d35713600ef45f9719e3864468c40a5274dc70

Raw query-metrics SHA-256:
784ded45280c99325f2ac285244dd4905b5718688c765831cd07f26fb9e184a7

Independent verification SHA-256:
da1b9cf1244b47c71ac7adce91b7db502b4fd2d3b663e126d8cde7c87e239d6c
```

Read the [human-readable result checkpoint](../results/option-b-real-code-premise-checkpoint-v1.md), the [frozen contract](../experiments/08-option-b-real-code-premise-test.md), and the [canonical evidence](../../artifacts/canonical/option-b/method-evaluation-v1/).

## Final classification

```text
E01 composition line: CLOSED
Option B real-premise test: COMPLETE
Option B decision: REAL_PREMISE_SUPPORTED
Promoted real-domain claim: B-PREM-001
Option C refusal test: AUTHORISED, NOT YET CONTRACTED
General composition claim: NOT ESTABLISHED
Calibrated refusal claim: NOT ESTABLISHED
```

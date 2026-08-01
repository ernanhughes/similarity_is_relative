# Option B — Real Frozen-Code Representation Premise Test

## Status

**Frozen design contract. No canonical embeddings, primitive models, triplet results or scientific decisions have been generated.**

This is the single real-representation kill test authorised by the post-E01 decision record.

Maximum budget from contract merge to final decision: **10 working days**.

## Research question

> Does a frozen code representation that we did not train materially underexpose an objectively measurable compound structural relation under its default geometry?

This experiment tests the load-bearing premise of the remaining RELATE programme. It does not test novelty, calibrated refusal or a general query algebra.

## Why this experiment comes now

E01 used planted synthetic relations and a generator controlled by the project. Independent recomputation showed that the experiment was saturated and that its strongest semantic-looking control measured weight separation rather than semantic identity.

Option B removes those design freedoms:

- the source code is real;
- the representation was pretrained by an external project;
- the primitive labels are computed from Python syntax rather than planted in the representation;
- repository boundaries determine the splits;
- the primary decision compares against default geometry directly;
- one failed threshold closes the RELATE research programme.

## Frozen domain

### Dataset

Use the **Python partition of CodeSearchNet**.

CodeSearchNet contains real open-source functions and provides repository-separated train, validation and test partitions. Preserve those published repository partitions. Do not randomly repartition functions.

Record before execution:

- dataset source and version;
- every source archive or parquet SHA-256;
- original repository identifier;
- original split;
- function identifier;
- raw-code SHA-256;
- normalized-AST SHA-256;
- filtering decision and reason.

### Eligibility

A function is eligible only when all of the following hold:

1. language is Python;
2. `ast.parse` succeeds under the frozen Python parser version;
3. the sample contains exactly one top-level function or method body supplied by CodeSearchNet;
4. the CodeBERT tokenizer produces between **32 and 256 non-padding tokens**, inclusive;
5. all three primitive extractors return finite values;
6. the normalized AST is not duplicated in another split.

When the same normalized AST occurs in more than one split, remove every cross-split occurrence rather than choosing one opportunistically.

### Frozen sample sizes

After filtering and cross-split deduplication, select deterministically by ascending SHA-256 of:

```text
repository + path + function identifier + raw-code SHA-256
```

Use at most:

```text
train       20,000
validation   4,000
test         4,000
```

If a split contains fewer eligible rows, use every eligible row and record the shortfall. Do not replace missing rows from another split.

## Frozen representation

Use:

```text
model: microsoft/codebert-base
architecture: frozen pretrained RoBERTa encoder
input: raw function code only
maximum sequence length: 256 tokens
pooling: attention-mask-weighted mean of final hidden states
embedding dtype on disk: float32
```

No model parameter may be updated.

Before canonical extraction, freeze and commit:

- resolved Hugging Face model revision;
- tokenizer revision;
- model configuration SHA-256;
- tokenizer-file hashes;
- `transformers`, `torch`, `tokenizers`, Python and platform versions;
- pooling implementation hash;
- one ten-sample embedding fixture with input and output hashes.

The resolved model revision must be committed in a documentation-only commit before the canonical embedding run.

## Objective primitive relations

Compute three scalar properties directly from the Python AST.

### P1 — cyclomatic complexity

```text
1
+ number of If nodes
+ number of For and AsyncFor nodes
+ number of While nodes
+ number of ExceptHandler nodes
+ number of boolean And/Or decision increments
+ number of comprehension filters
```

The implementation must specify the exact treatment of `match`, conditional expressions and chained boolean expressions in tests before canonical execution.

### P2 — maximum control nesting depth

Maximum nesting depth across the registered control nodes:

```text
If
For / AsyncFor
While
Try
With / AsyncWith
Match
comprehensions
```

The function body begins at depth zero. Nested functions and classes are not traversed when computing the enclosing function's value.

### P3 — distinct call-site count

Number of distinct normalized call expressions in the function body.

Normalize each call target to one of:

```text
name
attribute terminal name
<dynamic>
```

Examples:

```text
foo()          -> foo
obj.save()     -> save
factory()()    -> <dynamic>
```

Repeated calls to the same normalized target count once. Calls inside nested functions and classes are excluded.

### Primitive scaling

Fit robust scaling parameters on the training split only:

```text
z = (value - training median) / max(training IQR, 1.0)
```

Apply the frozen training median and IQR to validation and test.

## Primitive readouts

Fit one independent ridge regression per primitive from the frozen embedding.

Hyperparameter grid:

```text
alpha ∈ {0.01, 0.1, 1.0, 10.0, 100.0}
```

Select `alpha` independently for each primitive by validation MAE. Ties select the larger `alpha`.

No compound-query labels or test results may influence primitive training or model selection.

Report for every primitive:

- train, validation and test MAE;
- validation and test R²;
- Spearman correlation;
- selected alpha;
- coefficient and prediction hashes.

Primitive recoverability is descriptive in Option B. There is no minimum R² escape clause: poor primitive recovery counts against the premise.

## One frozen compound relation

### Semantic query

> Retrieve functions that are jointly similar in cyclomatic complexity, maximum control nesting depth and distinct call-site count.

### Oracle distance

For robust-scaled true primitive vector `t(x)`:

```text
d_oracle(q, c) = max_k |t_k(q) - t_k(c)|
```

This Chebyshev distance encodes an AND-style requirement: a candidate is only close when its worst primitive mismatch is small.

### Predicted-primitive executor

For independently predicted robust-scaled primitive vector `p(x)`:

```text
d_predicted(q, c) = max_k |p_k(q) - p_k(c)|
```

No compound supervision is used.

## Baselines

The frozen baselines are:

1. **raw cosine distance** over L2-normalized frozen CodeBERT embeddings;
2. **raw Euclidean distance** over unnormalized frozen CodeBERT embeddings;
3. **token-length distance**, absolute difference in tokenizer length;
4. **true-primitive oracle**, used as the target and attainable reference;
5. **predicted-primitive executor**, the method under test.

The scientific comparison is against the stronger of raw cosine and raw Euclidean on the primary metric. Token length is a nuisance diagnostic, not the principal baseline.

No directly trained compound model is included. Option B tests whether the foundational raw-geometry premise exists, not whether a new compound learner is competitive.

## Candidate pool and query set

- candidate pool: all selected training functions;
- queries: all selected test functions;
- validation queries may be used only for primitive alpha selection and implementation diagnostics declared before test execution;
- no test query may be removed after embeddings or metrics are inspected, except for a predeclared evidence-integrity failure such as a corrupt row.

## Frozen hard-negative manifest

The primary metric must not use uniformly random easy triplets.

For every test query:

1. place training candidates into the query's tokenizer-length decile;
2. compute true oracle distance within that decile;
3. sort candidates by oracle distance;
4. form candidate pairs whose oracle-rank separation is between **5 and 25 positions**, inclusive;
5. exclude oracle ties;
6. choose up to **128** pairs by deterministic SHA-256 order using manifest seed `8112026`.

If fewer than 32 eligible pairs exist for a query, retain the query with every eligible pair and flag it as sparse. Queries with zero informative pairs remain in retrieval metrics but contribute no hard-negative triplets.

Commit the complete manifest and its SHA-256 before computing method performance on the test split.

## Metrics

### Primary metric

Hard-negative triplet accuracy against the true-primitive Chebyshev oracle.

Ties in a method distance score receive `0.5`. Oracle ties are excluded by manifest construction.

### Required secondary metrics

Report, but do not use to rescue a failed primary decision:

- ordinary deterministic-manifest triplet accuracy;
- recall@10 and recall@50;
- neighbour regret@10 and @50 in oracle-distance units;
- oracle-neighbour predicted-rank median and p90;
- Spearman correlation with oracle distance;
- per-query constraint error: worst true primitive mismatch among returned top-k candidates;
- primitive recoverability metrics;
- method runtime and memory;
- result by repository-size quartile and token-length decile.

## Uncertainty

The independent unit is the repository, not the function or triplet.

Report:

- point estimate over all test queries;
- per-repository metric values for repositories with at least 20 eligible test queries;
- repository bootstrap 95% interval using the configured repetition count;
- leave-one-repository-out sensitivity for the ten largest eligible test repositories.

The point-estimate kill threshold remains primary. The interval is context and cannot turn a sub-threshold result into support.

## Frozen decision rule

Let:

```text
raw_best = max(raw_cosine_hard_triplet_accuracy,
               raw_euclidean_hard_triplet_accuracy)

gap = predicted_primitive_hard_triplet_accuracy - raw_best
```

### `REAL_PREMISE_SUPPORTED`

Only when:

```text
gap >= 0.10
```

### `REAL_PREMISE_FAILED`

When:

```text
gap < 0.10
```

There is no inconclusive band and no secondary-metric override.

A failure closes the RELATE research programme under the frozen post-E01 decision. The result may still be published as a real-domain negative finding and the evidence-first methodology may continue independently.

A pass authorises only the separately contracted Option C refusal experiment. It does not establish novelty, general composition, semantic binding or support-aware refusal.

## Discriminating-power review

Before implementation begins, reviewers must answer yes to all of the following:

1. Can raw cosine realistically meet or beat the predicted executor? **Yes.** CodeBERT was pretrained for code understanding and code search.
2. Can primitive probes fail? **Yes.** The model was not trained for these three AST scalars and remains frozen.
3. Did this project choose how strongly the representation encodes the primitives? **No.**
4. Did this project choose the real source-code distribution? **No.**
5. Would a negative result change the project decision? **Yes.** It closes RELATE.
6. Is the primary threshold frozen before embeddings and test metrics? **Yes.**
7. Is the experiment small enough that every primary result can be inspected? **Yes.** One representation, three primitives and one query.

Failure to obtain affirmative review before implementation blocks canonical execution.

## Evidence and verification contract

The implementation must produce:

- dataset manifest;
- filtered-row manifest;
- duplicate-removal report;
- primitive table;
- embedding matrix and hashes;
- primitive predictions and hashes;
- hard-negative manifest;
- complete result tree;
- compact result record;
- environment manifest;
- deterministic replay;
- independent metric recomputation reading frozen embeddings, primitive values, predictions and manifests without calling the experiment runner.

Verification success and scientific decision remain separate.

## Prior-art boundary

CodeBERT and later code-representation work already establish that pretrained code models can encode structural and semantic information and can be probed in frozen settings. CodeSearchNet already provides a repository-separated real-code benchmark.

Option B claims no novelty for:

- CodeBERT embeddings;
- linear probing;
- AST metric extraction;
- Chebyshev distance;
- repository-separated evaluation.

The only question is whether default geometry materially underexposes this frozen compound relation in this real representation.

Relevant starting references:

- Feng et al., **CodeBERT: A Pre-Trained Model for Programming and Natural Languages**, Findings of EMNLP 2020.
- Husain et al., **CodeSearchNet Challenge: Evaluating the State of Semantic Code Search**, 2019.
- Karmakar and Robbes, **What do Pre-trained Code Models Know about Code?**, 2021.

## Scope exclusions

Option B does not include:

- a second representation;
- a second programming language;
- multiple compound queries;
- support propagation;
- conformal prediction;
- abstention;
- compound-supervision budgets;
- a direct compound learner;
- query-algebra parsing as a scientific result;
- post-result threshold changes;
- exploratory rescue experiments.

Any extension requires a new decision after the frozen Option B result.

## Possible outcomes

```text
REAL_PREMISE_SUPPORTED
REAL_PREMISE_FAILED
```

Nothing else.
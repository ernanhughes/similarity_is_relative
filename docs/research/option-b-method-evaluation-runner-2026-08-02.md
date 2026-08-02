# Option B method-evaluation runner

Date: 2026-08-02

## Status

Implementation and review stage only.

The canonical method evaluation has **not** been executed by this pull request. No raw cosine, raw Euclidean, token-length, oracle, predicted-executor, secondary retrieval, registered gap, or final Option B outcome is included.

The scientific result remains unobserved until this implementation is reviewed and merged and the canonical command is run once from a fresh output directory.

## Prerequisite checkpoint

This stage begins only after the hard-negative publication checkpoint has merged:

```text
checkpoint_id = option-b-hard-negative-manifest-publication-v1
status = HARD_NEGATIVE_MANIFEST_PUBLISHED_PENDING_REVIEW
next_allowed_action = METHOD_EVALUATION_IMPLEMENTATION_REVIEW
scientific_result_observed = false
```

The evaluator verifies that checkpoint, the complete query stream, the deterministic gzip pair stream, the exact uncompressed pair-stream hash, the reproduced embedding checkpoint, the probe publication checkpoint, and all selected-row identities before calculating any method score.

## Frozen method set

The evaluator reports exactly:

1. raw cosine distance over the frozen CodeBERT embeddings;
2. raw Euclidean distance over the same unnormalised embeddings;
3. tokenizer-length absolute difference as a nuisance diagnostic;
4. true-primitive Chebyshev distance as the oracle reference;
5. predicted-primitive Chebyshev distance as the method under test.

The predicted executor uses the committed out-of-fold train-candidate predictions and committed test-query predictions. True candidate primitives are never substituted into the predicted executor.

## Primary metric

For each frozen hard-negative pair:

```text
score = 1.0  when method_distance(closer) < method_distance(farther)
score = 0.5  when method_distance(closer) = method_distance(farther)
score = 0.0  otherwise
```

Oracle ties were excluded during manifest construction.

The primary method accuracy is frozen as:

1. calculate the mean pair score separately for every query with at least one informative pair;
2. take the equal-weighted mean of those per-query accuracies.

Queries with zero pairs remain in every ordinary retrieval metric but do not create an undefined hard-triplet score. The evaluator reports their count explicitly.

The required secondary “ordinary deterministic-manifest triplet accuracy” is interpreted prospectively as the pair-weighted mean over the same committed manifest. It is not a second manifest or a new test set. The canonical manifest has exactly 128 pairs for every one of the 4,000 queries, so the query-equal and pair-weighted point estimates must agree to floating precision. The query-equal estimate remains primary.

Primary pair distances are calculated directly in float64 from each committed closer/farther pair. Predictions are not rounded. No full retrieval matrix is used to decide the Option B outcome.

## Frozen scientific decision

```text
raw_best = max(raw_cosine_accuracy, raw_euclidean_accuracy)

gap = predicted_executor_accuracy - raw_best
```

```text
gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

The comparison uses the direct float64 point estimates. There is no rounding before the threshold comparison, no inconclusive band, and no secondary-metric override.

## Required secondary retrieval metrics

For each query, retrieve from all selected training candidates. Candidate-distance ties are ordered by ascending canonical candidate stable key.

Report for every method:

- recall@10 and recall@50 against the true-oracle top-k set;
- neighbour regret@10 and @50, defined as the returned candidates’ mean oracle distance minus the oracle top-k mean distance;
- constraint error@10 and @50, defined as the worst true-primitive Chebyshev mismatch in the returned top-k;
- Spearman correlation between method and oracle distance over the complete candidate pool;
- predicted ranks of the oracle top-10 neighbours, pooled across queries, with median and p90;
- hard-negative method-tie counts and rates.

The oracle top-k and every method top-k use the same stable-key tie break. The true oracle must achieve hard-negative triplet accuracy exactly equal to one or execution fails.

## Primitive recoverability diagnostics

The final evaluation stage may now read true test primitives because fitting and manifest selection are complete and frozen.

For each primitive, report train, validation, and test:

- MAE in robust-scaled primitive units;
- R²;
- Spearman correlation;
- the already frozen selected alpha.

Train diagnostics use committed out-of-fold train-candidate predictions. Validation and test diagnostics use the committed final-model predictions. These metrics are descriptive and cannot replace the registered compound-retrieval decision.

## Repository dependence and uncertainty

The point estimate remains the query-equal primary decision input.

Repository bootstrap is frozen as follows:

- independent cluster: test repository;
- repetitions: `2000`;
- seed: `8112026`;
- sample all eligible repositories with replacement;
- include every eligible query in each sampled repository occurrence;
- recompute raw cosine, raw Euclidean, predicted-executor, and gap point estimates;
- report the 2.5% and 97.5% percentile values using NumPy’s linear quantile method.

The interval is descriptive only. It cannot rescue or overturn the point-estimate outcome.

Also report:

- per-repository metrics for repositories with at least 20 eligible test queries;
- leave-one-repository-out sensitivity for the ten largest eligible test repositories, ordered by descending query count and ascending repository name on ties;
- primary metrics by token-length decile;
- primary metrics by repository-size quartile.

Repository-size quartile boundaries are computed from the test-query counts of unique repositories using NumPy linear quantiles. Boundary ties are assigned to the higher quartile with `searchsorted(..., side="right")`; each query inherits its repository’s quartile.

## Runtime and memory

Record:

- input-verification time;
- primary-metric time;
- secondary-retrieval time;
- diagnostic-analysis time;
- total wall-clock time;
- peak process working-set or resident-set size when the platform exposes it;
- Python, platform, NumPy, SciPy, scikit-learn, and linear-algebra thread environment.

## Output tree

After this implementation is reviewed and merged, one canonical evaluation run will write:

```text
runs/option-b/method-evaluation-v1/
├── option-b-method-evaluation-v1.json
├── option-b-method-evaluation-compact-v1.json
├── option-b-method-query-metrics-v1.jsonl
├── option-b-method-primary-query-scores-v1.npy
└── option-b-method-evaluation-environment-v1.json
```

The result status will stop at:

```text
OPTION_B_METHOD_EVALUATION_COMPLETE_PENDING_INDEPENDENT_RECOMPUTATION
```

## Independent recomputation

A separate module and CLI recompute the complete primary query-score matrix and final decision without importing the evaluation runner.

It independently reloads and verifies:

- selected train/test manifests and primitive tables;
- reproduced train/test embedding arrays;
- committed train-candidate and test-query prediction arrays;
- committed query summaries and compressed pair stream;
- the evaluator’s primary query-score array and result record.

It recomputes all five hard-negative method scores, `raw_best`, the registered gap, and the exact two-outcome decision. Exact query-score equality is required.

The independent output status will be:

```text
OPTION_B_PRIMARY_DECISION_INDEPENDENTLY_RECOMPUTED
```

Only then may a dedicated canonical result-publication pull request be opened.

## CLI boundary

The reviewed commands are:

```text
relate-option-b-evaluate
relate-option-b-verify-evaluation
```

They expose file-location controls only. They expose no controls for:

- method set;
- threshold;
- query aggregation;
- tie scoring;
- retrieval k;
- bootstrap seed or repetitions;
- repository eligibility;
- quartile assignment;
- outcome labels.

## Text-artifact identity on Windows

Canonical JSON and JSONL blobs use LF. A `.gitattributes` rule freezes LF for Option B canonical text artifacts and marks `.npy` and `.gz` files binary. The verifier also recognises a checkout-only CRLF transformation by normalising CRLF to LF before comparing the already frozen canonical hash; it records when that compatibility path was required. No semantic or byte-identity change to the Git blob is accepted.

## Scientific boundary

This implementation pull request must not run either canonical command.

It contains no method result and makes no scientific decision. After merge, run the evaluator once, immediately run the independent recomputation, and publish the frozen result tree in a separate checkpoint pull request. No rescue experiment, threshold change, new method, new query, new language, or second representation is permitted under Option B after the result is observed.

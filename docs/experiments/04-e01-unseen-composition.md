# E01 — Unseen primitive composition

## Status

Preregistered implementation stage. No canonical result has been run or interpreted.

## Motivation

E00 established that a relation-specific direction can recover a known linear relation from a frozen representation and can remain stable under rotation. E01 asks the next question: can independently learned primitive relation operators be combined after training to answer compound queries that were never used to fit a compound model?

This experiment does not repair or reinterpret the failed E00 nonlinear gate. It begins a separate composition programme.

## Frozen design

- seed: `211`;
- samples: `6144`;
- dimensions: `64`;
- primitive latent relations: `a`, `b`, `c`;
- split: `60/20/20` train/validation/test;
- representation: latent primitive signals embedded in noise and transformed by one deterministic orthogonal rotation;
- primitive learners: independent ridge regressions fitted only to their own primitive targets;
- compound learners: none for the post-hoc method;
- oracle upper bound: a ridge model fitted directly to each compound target;
- raw controls: cosine and Euclidean distance;
- wrong-composition control: deterministic permutation of primitive weights;
- query/candidate evaluation: validation and test, using the frozen training split as the candidate pool.

## Unseen compounds

The following weight vectors are frozen before execution:

- `a_plus_b = (1.0, 1.0, 0.0)`;
- `a_plus_c = (1.0, 0.0, 1.0)`;
- `b_plus_c = (0.0, 1.0, 1.0)`;
- `a_plus_2b_minus_c = (1.0, 2.0, -1.0)`.

No compound target may be used to fit the primitive operators or select their hyperparameters.

## Composition rule

Each primitive ridge model predicts one scalar primitive value. For compound weights `w`, post-hoc composition predicts:

`compound_prediction = w_a * prediction_a + w_b * prediction_b + w_c * prediction_c`

Retrieval distance is absolute difference between compound predictions.

The direct oracle fits a ridge model to the compound target on the training split. It is an upper-bound comparator, not evidence of composition.

## Primary metrics

For each compound and split:

- triplet accuracy;
- Spearman distance correlation;
- recall at 10, 25, 50 and 100;
- additive neighbour regret at 10, 25, 50 and 100;
- oracle-neighbour predicted-rank median and p90.

## Composition regret

Composition regret is frozen as:

`oracle triplet accuracy - post-hoc composed triplet accuracy`

Negative values are retained rather than clipped.

## Stage decisions

This first E01 stage is a deterministic point-estimate and verification stage. It produces exactly four compound decisions:

- `SUPPORTED_POINT_ESTIMATE` when composed test triplet accuracy is at least `0.85`, composition regret is at most `0.05`, and composed triplet accuracy exceeds both raw controls and the wrong-composition control by at least `0.20`;
- `UNSUPPORTED_AT_THRESHOLD` when composed test triplet accuracy is below `0.70` or composition regret exceeds `0.15`;
- `INSUFFICIENT_EVIDENCE` otherwise.

The overall stage gate passes only when all four compounds are `SUPPORTED_POINT_ESTIMATE`.

## Publication boundary

Even if the point-estimate gate passes:

- `claim_promotion_allowed` remains `false`;
- no general composition claim is permitted;
- nulls, uncertainty, multi-seed replication, support calibration and abstention remain future gates;
- no claim may extend to real embeddings, language, proteins or nonlinear relations.

## Reproducibility

The runner must record hashes for configuration, rotation, splits, arrays, primitive coefficients, compound definitions, result tree and decision tree. The verifier must regenerate the complete experiment in a temporary directory and recursively compare the result tree.

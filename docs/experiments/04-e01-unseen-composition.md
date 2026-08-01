# E01.0 — Linear composition identity check

## Status

Implementation and algebraic-identity validation stage. The canonical seed-211 run passed deterministic replay under the original wording, but the result is not evidence of nontrivial relational-composition generalization.

## Motivation

E00 established that a supervised scalar direction can expose a known synthetic linear relation that raw cosine and Euclidean geometry do not expose well. Before attempting genuine relational composition, this stage checks that independently fitted primitive ridge predictors can be combined with signed weights and that the retrieval implementation reproduces the corresponding directly fitted ridge predictor.

This is an implementation identity check, not the scientific composition experiment.

## Why exact agreement is expected

With a fixed design matrix, split and ridge regularization, ridge coefficients are linear in the target. For primitive targets `y_a`, `y_b` and `y_c`, and frozen compound weights `w`, fitting ridge directly to

`y_compound = w_a * y_a + w_b * y_b + w_c * y_c`

produces the same coefficient vector as the weighted sum of the separately fitted primitive coefficients, up to numerical precision.

Therefore zero composition regret is expected by construction. It confirms the implementation and algebra, but it does not demonstrate that a learned system generalized to a novel compound relation.

## Frozen design

- seed: `211`;
- samples: `6144`;
- dimensions: `64`;
- primitive latent relations: `a`, `b`, `c`;
- split: `60/20/20` train/validation/test;
- representation: latent primitive signals embedded in noise and transformed by one deterministic orthogonal rotation;
- primitive learners: independent ridge regressions fitted only to their own primitive targets;
- direct comparator: ridge fitted to each weighted compound target;
- raw controls: cosine and Euclidean distance;
- wrong-composition control: deterministic permutation of primitive weights;
- query/candidate evaluation: validation and test, using the frozen training split as the candidate pool.

## Frozen weighted targets

- `a_plus_b = (1.0, 1.0, 0.0)`;
- `a_plus_c = (1.0, 0.0, 1.0)`;
- `b_plus_c = (0.0, 1.0, 1.0)`;
- `a_plus_2b_minus_c = (1.0, 2.0, -1.0)`.

No weighted compound target is used to fit or select a primitive model.

## Identity rule

Each primitive ridge model predicts one scalar primitive value. For compound weights `w`, the post-hoc prediction is:

`compound_prediction = w_a * prediction_a + w_b * prediction_b + w_c * prediction_c`

Retrieval distance is absolute difference between compound predictions.

The direct ridge comparator is not an oracle upper bound in the scientific sense. Under this frozen linear construction it is algebraically equivalent to the weighted primitive composition.

## Metrics

For each weighted target and split:

- triplet accuracy;
- Spearman distance correlation;
- recall at 10, 25, 50 and 100;
- additive neighbour regret at 10, 25, 50 and 100;
- oracle-neighbour predicted-rank median and p90;
- direct-minus-composed triplet difference, retained under the historical field name `composition_regret`.

## Identity decisions

The runner produces exactly four implementation decisions:

- `IDENTITY_CONFIRMED` when the composed method meets the frozen performance/control thresholds and direct-minus-composed triplet difference is at most `0.05`;
- `IDENTITY_NOT_CONFIRMED` when composed triplet accuracy is below `0.70` or the direct-minus-composed difference exceeds `0.15`;
- `IDENTITY_INCONCLUSIVE` otherwise.

The stage gate passes only when all four weighted targets are `IDENTITY_CONFIRMED`.

## Publication boundary

Even when the identity gate passes:

- `claim_promotion_allowed` remains `false`;
- no unseen relational-composition claim is permitted;
- the result establishes implementation correctness under linear ridge closure only;
- a later experiment must use a compound relevance geometry that is not algebraically reducible to weighted target regression;
- no claim may extend to real embeddings, language, proteins or nonlinear relations.

## Verification boundary

The verifier regenerates the experiment using the same runner and recursively compares the result tree. It is a deterministic replay verifier, not an independent mathematical implementation.

## Next experiment

The genuine composition stage should combine primitive relational geometries—for example weighted multi-criterion proximity, conjunction, filtering plus ranking, or separation on one primitive while remaining close on another—so that a directly trained compound comparator is not forced to equal a weighted sum of primitive ridge predictors.

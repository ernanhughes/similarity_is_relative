# E01.1 — Unseen relational conjunction

## Status

Preregistered deterministic point-estimate stage. No canonical result has been interpreted.

## Question

Can independently learned primitive relation predictors be composed after training into an unseen multi-criterion retrieval geometry?

E01.0 confirmed a linear ridge identity: weighted scalar targets force weighted ridge predictors to equal a directly fitted weighted ridge predictor. E01.1 removes that identity.

## Frozen design

- seed: `307`;
- samples: `6144`;
- dimensions: `64`;
- primitive relations: `a`, `b`, `c`;
- split: `60/20/20` train/validation/test;
- primitive learner: one independent ridge regression per primitive;
- representation: primitive latent variables embedded in nuisance dimensions and transformed by a deterministic orthogonal rotation;
- candidate pool: frozen training split;
- compound targets are never used for fitting or model selection.

## Compound relevance geometry

For primitive target vector `t(x) = [a(x), b(x), c(x)]` and non-negative weights `w`, the oracle compound distance is:

```text
d_w(x_i, x_j) = sqrt(sum_k w_k * (t_k(x_i) - t_k(x_j))^2)
```

The post-hoc composed distance applies the same geometry to the independently predicted primitive values.

Unlike scalar-sum retrieval, errors on different primitive relations cannot cancel merely because they have opposite signs.

## Frozen unseen compounds

- `a2_b = (2.0, 1.0, 0.0)`;
- `a3_c = (3.0, 0.0, 1.0)`;
- `b2_c = (0.0, 2.0, 1.0)`;
- `a_b2_c3 = (1.0, 2.0, 3.0)`.

## Controls

- raw cosine distance;
- raw Euclidean distance;
- scalar collapse: absolute difference of the weighted sum of predicted primitive values;
- wrong primitive alignment: apply the correct weights to cyclically permuted primitive predictions.

The scalar-collapse control is central. It tests whether reducing a conjunction to one scalar loses relational structure through cancellation.

## Metrics

For each compound on validation and test:

- triplet accuracy against oracle compound distance;
- Spearman correlation with oracle compound distance;
- exact recall at 10, 25, 50 and 100;
- additive oracle-distance regret at 10, 25, 50 and 100;
- oracle-neighbour predicted-rank median and p90.

Composition regret is:

```text
1.0 - posthoc_composed_triplet_accuracy
```

The perfect oracle geometry has triplet accuracy `1.0` by definition.

## Point-estimate decision

A compound is `SUPPORTED_POINT_ESTIMATE` only when:

- post-hoc test triplet accuracy is at least `0.88`;
- composition regret is at most `0.12`;
- post-hoc triplet accuracy exceeds every control by at least `0.10`.

A compound is `UNSUPPORTED_AT_THRESHOLD` when triplet accuracy is below `0.70` or composition regret exceeds `0.30`. Otherwise it is `INSUFFICIENT_EVIDENCE`.

The stage gate passes only when all four compounds are `SUPPORTED_POINT_ESTIMATE`.

## Publication boundary

Even if the gate passes, `claim_promotion_allowed` remains `false`. This is one deterministic synthetic point estimate. Permutation controls, query bootstrap uncertainty, fresh seeds, independent recomputation and abstention remain future gates.

## Verification class

The verifier is a deterministic replay verifier. It regenerates the complete experiment and compares the result tree. It does not constitute an independent mathematical implementation.

# E00.2 — Exact and Supervised Operator Matrix

## Purpose

Compare the frozen E00 ridge checkpoint against exact raw geometry and explicitly declared supervised transformations without regenerating the synthetic arrays.

This stage consumes `runs/e00/canonical-seed-17/manifest.json` and the six hashed `.npz` payloads produced by E00.1.

## Frozen methods

1. `raw_euclidean` — exhaustive Euclidean distance in the original representation;
2. `raw_cosine` — exhaustive cosine distance after row normalisation;
3. `ridge_predicted_distance` — the existing scalar-prediction baseline;
4. `diagonal_ridge_metric` — diagonal Mahalanobis distance with weights proportional to squared ridge coefficients;
5. `rank1_ridge_projection` — distance after projection onto the normalised ridge direction;
6. `pls_projection_rank4` — exhaustive Euclidean distance in a four-component supervised PLS projection;
7. `pls_projection_rank16` — exhaustive Euclidean distance in a sixteen-component supervised PLS projection.

The PLS methods are supervised low-rank projection baselines. They are not presented as novel metric-learning algorithms.

## Input boundary

The runner must:

- load the existing E00 manifest;
- verify all source array hashes before fitting any method;
- reuse the frozen train, validation and test assignments;
- record the source manifest SHA-256;
- refuse to regenerate synthetic data.

## Evaluation

Every method is evaluated by exact exhaustive search over training candidates for every test query.

Primary diagnostics:

- mean Spearman correlation between method distance and oracle target distance;
- deterministic triplet accuracy;
- exact recall@10, @25, @50 and @100;
- mean target-distance regret@10, @25, @50 and @100.

Binary XOR additionally reports matching-class precision@k and average precision.

## Interpretation boundaries

- Ridge or rank-one projection matching the best low-rank method means the synthetic scalar relation has collapsed to ordinary scalar prediction.
- Diagonal success on `axis_linear` and degradation on `rotated_linear` demonstrates basis dependence.
- Low-rank success after rotation demonstrates recoverable direction or subspace, not semantically meaningful coordinates.
- Failure on `absent` is required.
- Failure under `correlated_nuisance` is evidence of shortcut sensitivity, not absence of all signal.
- PLS matching ridge is a baseline result, not a RELATE contribution.

## Promotion boundary

This stage cannot promote a RELATE claim. It produces an operator comparison checkpoint that later permutation, bootstrap and certification stages must consume unchanged.

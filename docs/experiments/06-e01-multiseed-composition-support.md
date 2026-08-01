# E01.2 — Multi-Seed Composition and Support Gate

## Status

Design requirements frozen for implementation. No canonical result has been run or interpreted.

## Research question

Do post-hoc primitive-space compositions remain reliable across fresh seeds, stronger scalar and alignment controls, varying primitive quality, and unsupported-component conditions?

## Scientific role

E01.1 was a deliberately easy synthetic positive control. E01.2 is the first confirmatory composition gate.

Passing E01.2 would not by itself establish transfer to real embeddings or a novel algorithm. It would establish that the composition and refusal mechanisms survive a substantially stronger synthetic contract.

## Fresh seeds

Use at least five fresh dataset seeds, excluding seed `307` and every E01.0 seed.

Seeds must be committed before canonical execution.

Each seed regenerates:

- latent variables;
- frozen representation;
- orthogonal rotation;
- train, validation and test splits;
- triplet manifests;
- primitive-quality regimes.

## Frozen triplet manifests

For each seed and split, commit hashes for explicit triplet manifests containing:

- query index;
- candidate A index;
- candidate B index;
- oracle ordering;
- tie policy;
- generation seed.

Use multiple deterministic manifests or a sufficiently large frozen set. Metric implementations must consume the manifests rather than pairing candidate-pool halves implicitly.

## Primitive-quality regimes

The confirmatory matrix must include:

1. all primitives strong and linearly recoverable;
2. one strong and one weak primitive;
3. one absent primitive;
4. one nonlinear primitive outside the linear learner family;
5. two correlated primitives;
6. unequal primitive noise levels;
7. one primitive shifted at test time;
8. one primitive with insufficient training evidence.

Every primitive must report:

- validation and test `R²`;
- MAE;
- primitive triplet accuracy;
- uncertainty interval;
- support decision;
- shift decision where applicable.

## Compound relation families

### Weighted product-space score fusion

Retain the E01.1 weighted Euclidean geometry as the standard baseline.

### Conjunction

Evaluate queries equivalent to:

```text
close in a AND close in b
```

using max distance or explicit threshold intersection rather than only a weighted sum.

### Exclusion

Evaluate:

```text
close in a and b, but far in c
```

using explicit feasibility constraints and a ranking rule. Do not encode exclusion through an indefinite negative distance.

### Pareto retrieval

Return candidates not dominated across the requested primitive objectives. Record frontier size, oracle coverage and ranking within the frontier.

### Unsupported-component request

Construct compounds that require one absent, unsupported, unstable or insufficient-evidence primitive. The expected outcome is refusal or qualification, not a confident supported ranking.

## Required baselines

Every applicable compound must include:

1. raw cosine;
2. raw Euclidean;
3. declared scalar projection using `w`;
4. scale-matched scalar projection using `sqrt(w)`;
5. validation-selected linear scalar projection;
6. validation-selected rank-one metric trained for compound ranking;
7. a small validation-selected nonlinear scalar comparator;
8. every non-identity primitive permutation;
9. strongest wrong permutation;
10. random orthogonal transformations within primitive space;
11. weighted product-space score fusion;
12. directly trained compound metric from compound supervision;
13. true noisy-target oracle;
14. latent-space oracle and estimated noise ceiling.

No method may use test performance for hyperparameter or model selection.

## Terminology

E01.2 must not reuse the E01.1 frozen field name ambiguously.

Report separately:

- `oracle_triplet_disagreement = 1 - composed_triplet_accuracy`;
- `direct_compound_gap = direct_compound_triplet_accuracy - composed_triplet_accuracy`;
- `ceiling_fraction = composed_performance / estimated_attainable_performance` where mathematically appropriate;
- control margins for every baseline.

## Verification

Produce two classified verification paths:

1. **Deterministic replay** — rerun the experiment and compare complete result trees.
2. **Independent recomputation** — separate metric and decision code reads frozen arrays, predictions and triplet manifests and recomputes all primary results without calling the experiment runner.

Verification success remains independent of the scientific gate.

## Aggregate reporting

For every method, compound and primitive-quality regime report:

- per-seed value;
- mean;
- median;
- minimum;
- seed-level confidence interval;
- success count;
- worst seed;
- worst compound;
- worst regime.

## Provisional all-or-nothing gate

Exact numerical thresholds must be committed before execution. The gate must require all of the following classes of evidence:

- fresh-seed lower confidence bounds for supported positive-control compounds;
- bounded oracle disagreement;
- bounded gap against the directly trained compound comparator;
- superiority over the strongest scalar baseline;
- superiority over the strongest incorrect alignment;
- stability under rotation;
- correct unsupported or insufficient-evidence decisions when a required primitive is absent, weak, nonlinear for the chosen family, or shifted;
- successful conjunction and exclusion decisions under their own frozen contracts;
- deterministic replay pass;
- independent recomputation pass.

Failure of any required refusal condition blocks the complete support-aware composition claim.

## Publication boundary

Even a passing E01.2 result remains synthetic. It may support a replicated synthetic composition-and-refusal claim, but not:

- real-embedding transfer;
- protein or language applicability;
- universal metric-operator composition;
- novelty beyond all established conditional metric-learning approaches.

Those require later domain-specific experiments and prior-art comparisons.

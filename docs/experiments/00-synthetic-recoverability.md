# E00 — Synthetic Recoverability

## Purpose

Establish the mathematical boundary of RELATE before using a scientific dataset or building a visual interface.

The experiment creates synthetic frozen embeddings where the encoded relation is known exactly. It tests which operator families recover that relation, whether apparent coordinate meaning survives rotation, and whether the system fails honestly when the signal is nonlinear or absent.

## Frozen questions

1. Can exact raw cosine recover each relation?
2. Can a ridge probe followed by predicted-value distance recover it?
3. Can a diagonal Mahalanobis operator recover it in the native basis?
4. Does the same diagonal family remain effective after random orthogonal rotation?
5. Can a low-rank Mahalanobis operator recover rotated linear signal?
6. Do linear methods fail on nonlinear and absent signal?
7. Can a fixed certification rule distinguish supported, unsupported-at-threshold and insufficient-evidence regimes?

## Data contract

```yaml
experiment_id: e00-synthetic-recoverability
seed: 17
samples: 4096
dimensions: 64
train_fraction: 0.60
validation_fraction: 0.20
test_fraction: 0.20
noise_standard_deviation: 0.10
operator_ranks: [1, 4, 16]
retrieval_k: 10
retrieval_ks: [10, 25, 50, 100]
scalar_tolerance_fraction: 0.05
relative_error_minimum_denominator: 1.0e-8
```

The generator produces six regimes:

| Regime | Encoded relation | Expected boundary |
|---|---|---|
| `axis_linear` | linear scalar in one native coordinate | diagonal and low-rank methods should recover |
| `rotated_linear` | same signal after orthogonal rotation | low-rank should recover; raw diagonal interpretation should weaken |
| `weak_linear` | linear signal below dominant nuisance variance | task operator may improve over raw cosine |
| `nonlinear_xor` | relation depends on a nonlinear interaction | linear families should fail relative to a nonlinear probe |
| `absent` | labels independent of embeddings | all learned methods should remain at null |
| `correlated_nuisance` | nuisance predicts target in train but is decoupled in test | shortcut-dependent methods should fail out of distribution |

## Frozen splits and artifacts

The canonical generator persists train, validation and test assignments, relation values, rotation identity, generator configuration and source-array hashes. A verifier rejects any run where the arrays, splits, rotation or recomputed metrics differ from the manifest.

## Baselines and operator families

1. exact raw cosine;
2. exact raw Euclidean distance;
3. ridge prediction plus predicted-value distance;
4. diagonal Mahalanobis metric;
5. low-rank Mahalanobis metrics with ranks 1, 4 and 16;
6. nonlinear MLP probe for boundary diagnosis only;
7. label-permutation null;
8. random operator matched by rank or sparsity.

Exact exhaustive search is mandatory. Approximate search is not permitted in E00.

## Target-specific evaluation

E00 does not judge every target using one metric family.

### Continuous scalar regimes

The axis-aligned, rotated, weak, absent and nuisance-shift regimes report:

- Spearman correlation between oracle and predicted distances;
- exact oracle-neighbour recall at 10, 25, 50 and 100;
- retrieved and oracle-optimal mean target distance;
- **additive neighbour regret**, defined as retrieved mean distance minus oracle mean distance;
- relative neighbour error only when the oracle denominator exceeds the frozen minimum;
- NDCG at 10, 25, 50 and 100;
- deterministic conditional triplet accuracy;
- median and 90th-percentile predicted rank of the true oracle top-10 neighbours;
- the fraction of retrieved candidates inside a fixed target tolerance equal to 5% of the candidate target standard deviation.

When the oracle mean distance is zero or too small, relative neighbour error is recorded as `null`. Additive neighbour regret remains finite and is the primary oracle-relative distance measure.

### Binary relational regime

The XOR regime does not report scalar NDCG, scalar tolerance coverage or relative neighbour error. Because many candidates are exactly tied as valid matches, those values can look strong or explode numerically while the linear model is actually at chance.

Instead XOR reports:

- class precision at 10, 25, 50 and 100;
- class recall at the same cutoffs;
- average precision across the complete candidate ranking;
- exact oracle-set recall, triplet accuracy and true-neighbour rank as secondary diagnostics.

Metrics from different target types are not treated as directly comparable.

The legacy fields `recall_at_k`, `mean_oracle_distance` and `spearman` remain for compatibility. Every later confirmatory result must add paired bootstrap confidence intervals over test queries. The current baseline checkpoint records deterministic point estimates only and cannot promote a RELATE scientific claim.

## Independent metric verification

The verifier does not trust the runner's summary. It reloads the hashed arrays, reconstructs the frozen splits, retrains the declared ridge baseline, recomputes the target-specific metric tree and fails if any recorded value differs.

## Rotation test

A single frozen random orthogonal matrix is generated from seed 17 and hashed. Native and rotated embeddings receive identical split assignments and labels.

Interpretation:

- diagonal succeeds natively and fails after rotation: accidental axis alignment;
- low-rank survives rotation: recoverable subspace, not semantic coordinates;
- all linear methods fail: signal is absent, nonlinear, or below sample support.

## Certification contract

The initial certification output has three states:

- `supported`;
- `unsupported_at_threshold`;
- `insufficient_evidence`.

A relation may be `supported` only when the held-out lower confidence bound exceeds the frozen threshold, performance exceeds the permutation null, at least four of five confirmatory seeds pass, and no mandatory falsification check fails.

## Initial kill conditions

The raw-coordinate interpretation is rejected if diagonal performance is materially basis-dependent. The linear-operator hypothesis is bounded for a regime if the nonlinear probe materially outperforms every linear operator. Certification is rejected if the absent-signal regime is classified as supported.

## Publication boundary

The verified ridge checkpoint may be described as a successful execution and baseline audit. It may not be described as evidence that RELATE recovers, composes or certifies embedding relations until the registered operator suite, nulls and confidence intervals are complete.

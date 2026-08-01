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

Default canonical configuration:

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

## Frozen splits

The canonical generator must persist:

- row IDs;
- train, validation and test assignments;
- relation values or triplet labels;
- rotation matrix hash;
- nuisance state;
- generator configuration;
- source-array hashes.

A verifier must reject any run where split membership, labels, rotation or source arrays do not match the manifest.

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

## Evaluation

E00 does not rely on exact top-10 overlap alone. Continuous scalar targets can have many nearly equivalent neighbours, so a method may preserve the correct geometry while changing the identity of a few near-tied items.

For scalar-induced retrieval, every method reports:

- Spearman correlation between oracle and predicted candidate distances;
- exact oracle-neighbour recall at 10, 25, 50 and 100;
- mean true target distance among retrieved neighbours;
- mean distance of the oracle-optimal neighbours;
- relative neighbour error, defined as retrieved mean distance divided by oracle mean distance;
- NDCG at 10, 25, 50 and 100 using relevance derived monotonically from oracle distance;
- deterministic conditional triplet accuracy;
- median and 90th-percentile predicted rank of the true oracle top-10 neighbours.

The legacy fields `recall_at_k`, `mean_oracle_distance`, and `spearman` remain in the result artifact for compatibility. `mean_oracle_distance` retains its original meaning: the mean true/oracle distance of the neighbours retrieved by the evaluated method.

Interpretation:

- exact recall measures identity agreement with the oracle set;
- relative neighbour error measures the cost of near misses and equals 1.0 for oracle-optimal retrieval;
- NDCG awards graded credit to candidates that are nearly as relevant as the oracle neighbours;
- true-neighbour rank reveals whether missed oracle neighbours remain near the top or are displaced deeply;
- triplet accuracy measures whether the learned geometry answers the relational question "which candidate is closer?" correctly.

For relational or binary regimes, the same distance-ranking diagnostics are retained, with area under the precision-recall curve added when the complete operator suite is implemented.

Every confirmatory result must include paired bootstrap confidence intervals over test queries. The current baseline checkpoint records deterministic point estimates only and cannot promote a scientific claim.

## Independent metric verification

The verifier must not trust the runner's metric summary. It reloads the hashed arrays, reconstructs the frozen splits, retrains the declared ridge baseline, recomputes every metric, and compares the complete metric tree against the manifest. A hash-valid artifact with altered or stale metrics must fail verification.

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

A relation may be `supported` only when:

1. the held-out lower confidence bound exceeds the frozen performance threshold;
2. performance exceeds the 95th percentile of the permutation null;
3. at least four of five seeds pass independently in the later confirmatory run;
4. no mandatory falsification check fails.

The scaffold may implement one seed initially, but it must not mark a claim Verified until the confirmatory seed contract is completed.

## Initial kill conditions

The original raw-coordinate interpretation is rejected if diagonal performance is materially basis-dependent.

The linear-operator hypothesis is bounded or rejected for a regime if the nonlinear probe materially outperforms every linear operator.

Certification is rejected if the absent-signal regime is classified as supported.

The broader research programme is not killed by these expected boundaries; they determine which representations and operator families are scientifically defensible.

## Artifacts

Local payloads:

```text
runs/e00/<run-id>/arrays/
runs/e00/<run-id>/models/
runs/e00/<run-id>/bootstrap/
```

Committed compact evidence:

```text
docs/results/e00-synthetic-recoverability.json
docs/results/e00-synthetic-recoverability.md
artifacts/canonical/e00/manifest.json
```

## Publication boundary

Before a canonical verified run, the blog may say only:

> We designed a deterministic synthetic experiment to test recoverability, basis dependence and honest failure.

It may not say that RELATE recovers, composes or certifies embedding relations.

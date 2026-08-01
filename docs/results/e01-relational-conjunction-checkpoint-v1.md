# E01.1 Relational Conjunction Checkpoint v1

## Status

- Verification: `PASS`
- Verification class: `DETERMINISTIC_REPLAY`
- Scientific point-estimate gate: `PASS`
- Verified compounds: `4`
- Verified decisions: `4`
- Claim promotion: `BLOCKED`

This checkpoint freezes the first nontrivial relational-composition result in the repository.

E01.0 showed only that ridge predictors obey a linear identity when weighted scalar targets are added. E01.1 changed the question. Compound relevance was defined as weighted Euclidean distance across separate primitive-relation coordinates, so opposite primitive errors could no longer cancel through a scalar sum.

## Frozen compound queries

| Compound | Weights |
|---|---:|
| `a2_b` | `(2, 1, 0)` |
| `a3_c` | `(3, 0, 1)` |
| `a_b2_c3` | `(1, 2, 3)` |
| `b2_c` | `(0, 2, 1)` |

No compound target was used to fit or select the primitive ridge predictors.

## Test results

| Compound | Composed triplet accuracy | Composition regret | Scalar collapse | Wrong alignment | Raw cosine | Raw Euclidean |
|---|---:|---:|---:|---:|---:|---:|
| `a2_b` | `0.9253` | `0.0747` | `0.7653` | `0.6456` | `0.5386` | `0.5480` |
| `a3_c` | `0.9280` | `0.0720` | `0.7984` | `0.6279` | `0.5382` | `0.5491` |
| `a_b2_c3` | `0.9273` | `0.0727` | `0.7129` | `0.8227` | `0.5480` | `0.5641` |
| `b2_c` | `0.9221` | `0.0779` | `0.7655` | `0.6479` | `0.5390` | `0.5533` |

All four compounds received `SUPPORTED_POINT_ESTIMATE`.

## Why this result is not the E01.0 identity again

The composed method predicts the primitive values independently and then constructs a weighted distance in primitive space:

```text
d_w(i, j) = sqrt(sum_k w_k * (p_k(i) - p_k(j))^2)
```

The oracle uses the true primitive targets in the same geometry. The composed method therefore has nonzero regret because its independently learned primitive predictions are imperfect.

Observed regret ranged from approximately `0.0720` to `0.0779`. That is close to the true-target oracle, but not algebraically identical to it.

The scalar-collapse control instead reduces the compound to one weighted sum. It performed substantially worse on every compound, including `0.7129` on the three-relation query `a_b2_c3`, compared with `0.9273` for the correct primitive-space composition.

## Strongest and narrowest supported statement

Within this registered seed-307 synthetic point-estimate run:

> Independently learned primitive predictors were combined after training into four unseen weighted multi-relation retrieval geometries, and the resulting primitive-space compositions substantially exceeded raw embedding geometry, scalar collapse and incorrect primitive alignment.

## Publication boundary

This checkpoint does not establish:

- reliability across fresh dataset seeds;
- uncertainty bounds or permutation significance;
- robustness when primitive predictors are weak, missing or unsupported;
- calibrated abstention;
- transfer to real frozen embeddings;
- a general composition claim.

The stage gate passed, but `claim_promotion_allowed` remains `false`. The next scientific stage must use fresh preregistered seeds, uncertainty intervals and null controls.

## Frozen evidence identities

```text
Result:
e8144a17e2acaf3e1efda9522b5cb5775f37dbd63a0bb1611a97944a78d64c90

Decision tree:
f7ead1c9c70f276ee3c5dbe4689c50bcbb649c9fe6f272b5ca52c5fdae3a7a77

Configuration:
423e3b3b432165e84b7126319862c9e710fab6cc8ddbd78bef0d681b3892f4a5
```

The corresponding compact machine-readable record is [`e01-relational-conjunction-checkpoint-v1.json`](e01-relational-conjunction-checkpoint-v1.json).

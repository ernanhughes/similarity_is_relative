# E01.1 Relational Conjunction Checkpoint v1

## Status

- Verification: `PASS`
- Verification class: `DETERMINISTIC_REPLAY`
- Scientific point-estimate gate: `PASS`
- Verified compounds: `4`
- Verified decisions: `4`
- Claim promotion: `BLOCKED`
- Scientific classification: `SYNTHETIC_COMPOSITION_POSITIVE_CONTROL`

This checkpoint freezes the first non-collapsing synthetic composition result in the repository.

It validates the experiment harness and a weighted product-space score-fusion baseline. It does not establish a novel RELATE composition algorithm.

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

| Compound | Composed triplet accuracy | Frozen `composition_regret` field | Scalar collapse | Wrong alignment | Raw cosine | Raw Euclidean |
|---|---:|---:|---:|---:|---:|---:|
| `a2_b` | `0.9253` | `0.0747` | `0.7653` | `0.6456` | `0.5386` | `0.5480` |
| `a3_c` | `0.9280` | `0.0720` | `0.7984` | `0.6279` | `0.5382` | `0.5491` |
| `a_b2_c3` | `0.9273` | `0.0727` | `0.7129` | `0.8227` | `0.5480` | `0.5641` |
| `b2_c` | `0.9221` | `0.0779` | `0.7655` | `0.6479` | `0.5390` | `0.5533` |

All four compounds received `SUPPORTED_POINT_ESTIMATE` under the frozen E01.1 rule.

## Interpretation of the frozen regret field

The executable field called `composition_regret` is frozen and must not be rewritten. In E01.1 it equals:

```text
1 - triplet_accuracy against the true noisy-target product-space ordering
```

It is therefore most accurately interpreted as **oracle triplet disagreement** or **pairwise ranking error**. It is not regret relative to a directly trained compound model.

E01.2 must report these quantities separately:

- oracle triplet disagreement;
- performance gap against a directly trained compound comparator;
- performance relative to the latent/noise ceiling.

## Strongest bounded statement

Within this registered seed-307 synthetic point-estimate run:

> Independently predicted primitive coordinates were combined after training into four preregistered weighted product-space relations and exceeded the controls included in the frozen E01.1 contract.

This is a valid synthetic positive control for post-hoc composition. Weighted product-space score fusion is standard and remains a baseline for the eventual H-005 novelty claim.

## Known limitations exposed by review

- only one dataset seed was tested;
- the scalar-collapse control was not validation-optimised;
- only one cyclic wrong alignment was evaluated;
- the primitive relations were all easy, linear, independent and supported;
- primitive recoverability and the attainable noise ceiling were not separately reported;
- the triplet pairing procedure was deterministic but not frozen as an explicit manifest;
- no directly trained compound metric comparator was included;
- no Boolean conjunction, exclusion, Pareto retrieval or unsupported-component abstention was tested.

## Publication boundary

This checkpoint does not establish:

- reliability across fresh dataset seeds;
- superiority over the strongest scalar or directly trained compound baseline;
- a novel RELATE composition algorithm;
- learned metric-operator composition in general;
- robustness when primitive predictors are weak, missing or unsupported;
- calibrated abstention;
- transfer to real frozen embeddings.

The stage gate passed, but `claim_promotion_allowed` remains `false`.

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

# The First Composition Result That Was Not an Identity

The first composition experiment appeared to work perfectly.

Four unseen weighted targets were reconstructed after training. Every composed predictor matched a directly fitted ridge predictor exactly. Composition regret was zero.

That looked extraordinary for about five minutes.

Then the reason became obvious: ridge regression is linear in its target. If one model is trained to predict `a`, another to predict `b`, and a third to predict `c`, then applying weights to those fitted predictors reconstructs the ridge solution for the same weighted target. The experiment had verified an implementation identity, not discovered relational composition.

We kept that result. It became E01.0: a linear composition identity check.

The next experiment had to make cancellation impossible.

## The change in the question

A scalar sum such as

```text
2a + b
```

throws several relations onto one line. Two candidates can have very different primitive values and still share the same sum. An error in one primitive can cancel an error in another.

That is not what many compound similarity queries mean.

“Close in age and income,” for example, does not usually mean that being ten years too old can be cancelled by earning ten units too little. The two criteria remain separate.

E01.1 therefore defined each compound as a weighted distance across primitive-relation coordinates:

```text
d_w(i, j) = sqrt(sum_k w_k * (t_k(i) - t_k(j))^2)
```

The primitive predictors were still fitted independently. No compound target was used to train them. Only after training were their predicted coordinates combined into the frozen compound geometry.

This removed the E01.0 identity. The composed geometry could approach the true primitive-space oracle, but it was no longer algebraically forced to equal it.

## Four unseen weighted product-space queries

The seed-307 run froze four compound queries:

```text
a2_b      = (2, 1, 0)
a3_c      = (3, 0, 1)
b2_c      = (0, 2, 1)
a_b2_c3   = (1, 2, 3)
```

Each tuple specifies how strongly differences along `a`, `b` and `c` contribute to the compound distance.

The experiment compared the post-hoc primitive-space composition against four controls:

- raw cosine distance in the 64-dimensional representation;
- raw Euclidean distance;
- one declared scalar collapse into a weighted sum;
- one incorrect primitive alignment produced by cyclically permuting the learned primitive coordinates.

A compound passed only if its test triplet accuracy reached `0.88`, its frozen oracle-disagreement field stayed below `0.12`, and it exceeded every included control by at least `0.10`.

## All four point estimates passed

| Compound | Composed | Frozen `composition_regret` field | Scalar collapse | Wrong alignment | Raw cosine | Raw Euclidean |
|---|---:|---:|---:|---:|---:|---:|
| `a2_b` | `0.9253` | `0.0747` | `0.7653` | `0.6456` | `0.5386` | `0.5480` |
| `a3_c` | `0.9280` | `0.0720` | `0.7984` | `0.6279` | `0.5382` | `0.5491` |
| `a_b2_c3` | `0.9273` | `0.0727` | `0.7129` | `0.8227` | `0.5480` | `0.5641` |
| `b2_c` | `0.9221` | `0.0779` | `0.7655` | `0.6479` | `0.5390` | `0.5533` |

All four decisions were `SUPPORTED_POINT_ESTIMATE`.

The deterministic replay verifier regenerated all four compounds and all four decisions without error.

```text
Verification: PASS
Verification class: DETERMINISTIC_REPLAY
Scientific point-estimate gate: PASS
Claim promotion: blocked
```

## Why the nonzero disagreement matters

The previous experiment produced exactly zero disagreement. That was the warning sign: the post-hoc method and direct ridge comparator were two algebraically equivalent routes to the same scalar model.

Here the frozen field called `composition_regret` ranged from approximately `0.0720` to `0.0779`. In this experiment that field equals one minus triplet accuracy against the true noisy-target geometry. It is therefore better interpreted as oracle triplet disagreement or ranking error, not regret against a directly trained compound model.

The field name remains frozen for artifact stability. Future experiments will use clearer terminology and will separately compare against a directly trained compound comparator.

## Scalar collapse lost information

The same primitive predictions were available to both methods. One method kept the primitive coordinates separate and combined their squared differences. The other reduced them to a single weighted number and measured absolute distance on that line.

The declared scalar version was consistently worse. On `a_b2_c3`, scalar collapse achieved approximately `0.7129`; primitive-space composition achieved approximately `0.9273`.

This shows that the chosen one-dimensional collapse discarded information retained by the weighted product-space representation.

It does **not** yet show that every strong scalar alternative fails. E01.2 must include scale-matched scalar projections, a validation-selected rank-one projection, and a small nonlinear scalar comparator.

## Wrong relations can still look plausible

The three-relation compound produced the strongest wrong-alignment control: approximately `0.8227`.

The correct alignment exceeded the frozen margin by only about `0.1046`. Because E01.1 used only one cyclic permutation, this result is a warning rather than a completed adversarial test.

E01.2 must evaluate every non-identity primitive permutation and report the strongest incorrect alignment.

## What this point estimate showed

Within the registered seed-307 synthetic run, independently predicted primitive coordinates were combined after training into four unseen weighted product-space retrieval geometries. The resulting scores exceeded the controls included in the frozen E01.1 contract.

This is a valid non-collapsing synthetic composition positive control.

It is not evidence that RELATE has invented a novel composition algorithm. Weighted product-space score fusion is the baseline that a later RELATE mechanism must equal or surpass while adding constraints, exclusion, Pareto retrieval, support propagation or calibrated abstention.

This was one deliberately easy positive-control world: all three primitives were linearly encoded, independently recoverable, similarly distributed and supported. There are no fresh-seed confidence intervals, exhaustive wrong alignments, strong learned scalar baselines, missing-primitive tests, direct compound metric comparators, support calibration or abstention decisions.

The gate therefore passed while claim promotion remained blocked.

## Frozen evidence

```text
Result:
e8144a17e2acaf3e1efda9522b5cb5775f37dbd63a0bb1611a97944a78d64c90

Decision tree:
f7ead1c9c70f276ee3c5dbe4689c50bcbb649c9fe6f272b5ca52c5fdae3a7a77

Configuration:
423e3b3b432165e84b7126319862c9e710fab6cc8ddbd78bef0d681b3892f4a5
```

The result is frozen as [`e01-relational-conjunction-checkpoint-v1`](../results/e01-relational-conjunction-checkpoint-v1.md).

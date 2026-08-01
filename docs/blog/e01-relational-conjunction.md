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

This made the experiment nontrivial. The composed geometry could approach the true primitive-space oracle, but it was no longer algebraically forced to equal it.

## Four unseen relational conjunctions

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
- scalar collapse into one weighted sum;
- incorrect primitive alignment produced by permuting the learned primitive coordinates.

A compound passed only if its test triplet accuracy reached `0.88`, its regret relative to the true-target oracle stayed below `0.12`, and it exceeded every control by at least `0.10`.

## All four point estimates passed

The complete test result was:

| Compound | Composed | Regret | Scalar collapse | Wrong alignment | Raw cosine | Raw Euclidean |
|---|---:|---:|---:|---:|---:|---:|
| `a2_b` | `0.9253` | `0.0747` | `0.7653` | `0.6456` | `0.5386` | `0.5480` |
| `a3_c` | `0.9280` | `0.0720` | `0.7984` | `0.6279` | `0.5382` | `0.5491` |
| `a_b2_c3` | `0.9273` | `0.0727` | `0.7129` | `0.8227` | `0.5480` | `0.5641` |
| `b2_c` | `0.9221` | `0.0779` | `0.7655` | `0.6479` | `0.5390` | `0.5533` |

All four decisions were:

```text
SUPPORTED_POINT_ESTIMATE
```

The deterministic replay verifier regenerated all four compounds and all four decisions without error.

```text
Verification: PASS
Verification class: DETERMINISTIC_REPLAY
Scientific point-estimate gate: PASS
Claim promotion: blocked
```

## Why the nonzero regret matters

The previous experiment produced exactly zero regret. That was the warning sign: the post-hoc method and direct ridge comparator were two algebraically equivalent routes to the same scalar model.

Here the regret was not zero. It ranged from approximately `0.0720` to `0.0779`.

That is what we should expect from a meaningful comparison. The oracle measures compound distance using the true primitive targets. The composed method measures it using three independently estimated primitive coordinates. Prediction error in those coordinates creates a real gap.

The important fact is not that the gap vanished. It is that the independently learned primitive geometry retained enough information to answer the unseen compound queries with triplet accuracy above `0.92` in every case.

## Scalar collapse lost the relation

The scalar-collapse control was the most direct test of the original thesis.

The same primitive predictions were available to both methods. The difference was how they were represented and processed.

One method kept the primitive coordinates separate and combined their squared differences. The other reduced them to a single weighted number and then measured absolute distance on that line.

The scalar version was consistently worse.

On `a_b2_c3`, the three-relation compound, scalar collapse achieved approximately `0.7129`. Primitive-space composition achieved approximately `0.9273`.

Nothing new had been added to the frozen representation. Nothing new had been trained for the compound. The gain came from refusing to collapse a structured relation into one scalar before retrieval.

This is the clearest result in the project so far for the claim that similarity depends on the relational object and the operation applied to it—not merely on the original embedding row and a default distance function.

## Wrong relations can still look plausible

The three-relation compound also produced the strongest wrong-alignment control: approximately `0.8227`.

That deserves attention rather than concealment.

When all three primitive coordinates are active, permuting them can preserve a substantial amount of generic structure. The correct alignment still exceeded the frozen `0.10` margin, but only narrowly—by approximately `0.1046`.

This suggests an important next boundary. A useful composition system must not only outperform raw geometry. It must distinguish the requested primitive semantics from a plausible but incorrect rearrangement.

Multi-seed confirmation should therefore preserve wrong-alignment as a required control and examine its margin carefully rather than treating it as an incidental baseline.

## What we found—and what we did not

Within this registered synthetic seed-307 point-estimate experiment, independently learned primitive predictors were successfully combined after training into four unseen weighted multi-relation retrieval geometries.

The compositions substantially exceeded raw cosine, raw Euclidean distance, scalar collapse and incorrect primitive alignment. They approached, but did not equal, the true-target primitive-space oracle.

That is a real composition result.

It is not yet a general composition claim.

This was one synthetic dataset seed. There are no fresh-seed confidence intervals, permutation nulls, missing-primitive tests, support calibration or abstention decisions. The result does not yet transfer to scientific or language embeddings.

The gate therefore passed while claim promotion remained blocked.

The next stage is not to make the point estimate prettier. It is to ask whether the result survives fresh preregistered seeds and whether the system knows when one of the primitive relations is too weak to compose safely.

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

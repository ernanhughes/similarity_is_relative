# The Result Passed and the Experiment Failed

The most useful result in this repository may be the one that forced us to admit that a passing experiment was not informative enough.

E01.2a looked excellent on paper.

Five fresh seeds. Four preregistered weighted queries. Every included scalar and primitive-permutation margin positive. Deterministic replay passed. The measurements barely varied between seeds.

The result was numerically correct.

And after external review, we no longer believe it answered the question we cared about.

## What we thought we had shown

Our intended progression was straightforward.

First, learn several primitive relations independently from one frozen representation. Then combine those primitives after training into compound relational queries. Eventually, make the system refuse when a required primitive is absent or unsupported.

E01.1 supplied the first weighted product-space positive control. E01.2a repeated the measurement across five new random seeds and added stronger scalar and wrong-alignment controls.

We described that as a replicated synthetic composition result.

That description was technically defensible. It was also incomplete.

## The first problem: we changed the rule

E01.1 required the composed method to beat every included control by at least `0.10`.

Its wrong-alignment control was one fixed cyclic permutation.

E01.2a improved the control by trying all five non-identity permutations and selecting the strongest. But it also replaced the `0.10` margin requirement with a weaker rule: the lower seed-level confidence bound only had to remain above zero.

An external reviewer recomputed the original seed against all five wrong alignments and reported margins of:

| Compound | Margin |
|---|---:|
| `a2_b` | `0.0853` |
| `a3_c` | `0.1464` |
| `b2_c` | `0.0788` |
| `a_b2_c3` | `0.0374` |

Under the original E01.1 margin rule, only one of those four compounds would pass after adding the stronger control.

So E01.2a did replicate the measurements across fresh seeds. It did not replicate E01.1's original decision rule.

That is not fraud or an implementation error. It is a decision-lineage failure. The repository did not explain the change prominently enough, and the phrase “confirmation” concealed more than it revealed.

## The second problem: there was almost nothing left to learn

The synthetic generator placed three independent latent variables directly into the representation before applying an orthogonal rotation. Ridge regression recovered those primitives almost perfectly.

The compound oracle then applied weighted Euclidean distance to the true primitive values. Our method applied the same operation to the predicted primitive values.

The external reviewer replaced our predictions with the true noiseless latents and reported that the resulting triplet accuracies changed by only about `±0.0005`.

In other words:

```text
ceiling_fraction ≈ 1.000
```

We had interpreted the narrow cross-seed intervals as evidence that the composition procedure was unusually stable.

The better interpretation is that the generator was saturated. The method had almost no room to vary because primitive recovery was already at the attainable ceiling.

The experiment was reproducible, but it was not discriminating.

## The third problem: the semantic control did not measure semantics

The narrowest margin appeared on the three-coordinate query `a_b2_c3`. We initially treated that as evidence of semantic fragility: perhaps a wrong assignment of primitive identities could preserve much of the geometry.

The reviewer found a more basic cause.

The three primitives were independent, identically distributed Gaussian variables with similar recoverability. Permuting them did not create a different statistical world. It merely moved unequal weights among exchangeable axes.

The reported margin changed predictably with weight separation:

| Weights | Wrong-permutation margin |
|---|---:|
| `(1,1,1)` | `0.0000` |
| `(1,1.1,1.2)` | `0.0019` |
| `(1,2,3)` | about `0.039` |
| `(1,4,16)` | about `0.068` |

So the control did not verify semantic identity. It mostly measured how damaging it was to reassign unequal weights.

The semantic-binding problem remains real. This generator simply could not test it.

## Why this is still a good result

Failure is useful when it changes what we believe.

We now believe:

- E01.1 and E01.2a are saturated score-fusion positive controls;
- their measurements are valid but their scientific content is narrow;
- general primitive-operator composition remains untested;
- the complete E01.2 support-and-composition gate was never attempted;
- support-aware refusal should not be built on the current easy generator;
- the next experiment must measure headroom before it measures success.

The historical files and hashes will remain unchanged. We will attach an audit rather than rewrite the past.

That is the point of an evidence-first repository. The record should show not only what ran, but how our interpretation changed when stronger criticism arrived.

## The thesis changes

The project should no longer be framed primarily as a new composition metric.

The more defensible thesis is:

> **RELATE is a support-aware relational query runtime over frozen representations. It learns evidence-bearing primitive relations, executes declared compound queries over those primitives without retraining for every query, propagates uncertainty through the query, and refuses when the primitive evidence or query algebra is insufficient.**

This is not one universal distance function.

A weighted-distance query should use weighted distance. A conjunction may use a maximum or threshold intersection. Exclusion should use feasibility constraints. Pareto retrieval should use a partial order.

The question is whether an imperfect primitive interface can execute these declared queries usefully, whether it offers a real zero-compound-example advantage over direct compound training, and whether it knows when it cannot answer.

## The next experiment must be able to fail

The replacement generator will include primitives with deliberately different distributions, scales, noise, recoverability and shifts.

Some will be strong. Some weak. One absent. One outside the chosen learner family. One supported during development but unstable at test time.

Primitive quality will span useful but imperfect ranges rather than sitting at the ceiling.

Every query family will compare:

- the noiseless true-primitive executor;
- the predicted-primitive executor;
- a directly trained compound model under several supervision budgets;
- raw embedding geometry;
- conventional conditional metric learning;
- independent primitive thresholding.

We will restore actual retrieval metrics, use hard negatives, report ceiling fraction and direct-compound gap, and freeze kill conditions before implementation.

The composition direction should stop if a small amount of direct compound supervision removes the reuse advantage, if primitive quality explains everything, if unsupported queries receive confident answers, or if the effect disappears on a real frozen representation.

## A new gate before preregistration

The deepest lesson is that preregistration is not enough.

A study can be preregistered, deterministic, replayable, hash-addressed and numerically correct—and still be scientifically uninformative because the desired result is structurally inevitable.

Before freezing another experiment, we will require a discriminating-power review:

1. What outcome could realistically fail?
2. What is the attainable ceiling?
3. How close should the intended method be to that ceiling?
4. Does the strongest baseline receive comparable information and supervision?
5. Does the generator make the desired result inevitable?
6. Are the controls measuring the failure mode we claim they measure?
7. Would the result still be interesting if every threshold passed?

E01.2a passed its implemented rule.

The experiment failed to tell us enough.

That is not the end of the project. It is the point where the project became more honest—and possibly more interesting.

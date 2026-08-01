# The Composition Result Survived Five New Worlds

The first non-collapsing composition result in this project came from one synthetic world.

That was E01.1. Three independently learned primitive predictors were kept as separate coordinates and combined after training into four weighted product-space retrieval queries. All four point estimates passed.

The result was useful, but it left the obvious question unanswered:

> Was seed `307` simply a favourable world?

E01.2a was designed to answer that narrow question before the project attempted anything more ambitious.

## Five fresh worlds

The confirmation used five new dataset seeds:

```text
401
433
467
503
557
```

Seed `307` was excluded. Every seed regenerated the latent variables, frozen representation, orthogonal rotation, train/validation/test splits and explicit triplet manifests.

The primitive models were still trained independently. No compound target was used to fit those primitive predictors. The four compound queries were assembled only afterward:

```text
a2_b      = (2, 1, 0)
a3_c      = (3, 0, 1)
b2_c      = (0, 2, 1)
a_b2_c3   = (1, 2, 3)
```

The method under confirmation was weighted product-space distance over predicted primitive coordinates. This is a standard score-fusion baseline, not a claimed RELATE invention.

## The result was unusually stable

| Compound | Mean composed accuracy | 95% seed interval | Minimum seed | Successful seeds |
|---|---:|---:|---:|---:|
| `a2_b` | `0.9256` | `[0.9250, 0.9264]` | `0.9246` | `5/5` |
| `a3_c` | `0.9243` | `[0.9236, 0.9249]` | `0.9233` | `5/5` |
| `a_b2_c3` | `0.9285` | `[0.9282, 0.9287]` | `0.9280` | `5/5` |
| `b2_c` | `0.9256` | `[0.9250, 0.9261]` | `0.9248` | `5/5` |

All four frozen decisions were:

```text
SUPPORTED_MULTI_SEED
```

The deterministic replay verifier reproduced all five seeds, all four compounds and all four decisions without error.

```text
Scientific gate: PASS
Deterministic replay: PASS
Claim promotion for complete RELATE composition: BLOCKED
```

The low variation matters. This was not a result that barely survived averaging. The worst composed score among the twenty seed-compound combinations remained above `0.923`.

## Stronger scalar controls did not close the gap

E01.1 used one obvious scalar-collapse control. The progress review correctly argued that this was not enough.

E01.2a therefore included two declared scalar projections:

- weights `w`;
- scale-matched weights `sqrt(w)`.

For each compound, the strongest scalar result was used for the aggregate margin. Every seed-level confidence interval remained clearly above zero:

| Compound | Margin over strongest scalar, 95% interval |
|---|---:|
| `a2_b` | `[0.1563, 0.1626]` |
| `a3_c` | `[0.1245, 0.1259]` |
| `a_b2_c3` | `[0.2164, 0.2193]` |
| `b2_c` | `[0.1567, 0.1638]` |

Keeping primitive coordinates separate therefore retained information that both tested one-dimensional projections discarded.

This is now a replicated synthetic result rather than a single positive-control point estimate.

## The uncomfortable control became more important

The most revealing result was not the average accuracy. It was the strongest wrong primitive alignment.

E01.2a evaluated all five non-identity permutations of the three predicted primitive coordinates. For each compound and seed, it retained the strongest incorrect permutation.

The correct composition beat that adversary for all compounds, but the margins were not equally reassuring:

| Compound | Margin over strongest wrong alignment, 95% interval |
|---|---:|
| `a2_b` | `[0.0821, 0.0845]` |
| `a3_c` | `[0.1442, 0.1459]` |
| `a_b2_c3` | `[0.0368, 0.0382]` |
| `b2_c` | `[0.0817, 0.0840]` |

The three-relation query `a_b2_c3` was the strongest composition by absolute accuracy and by its margin over scalar collapse. It was also the easiest query for an incorrect semantic alignment to approximate.

That is not a contradiction. When all three coordinates are active, a permutation may preserve much of the generic product-space geometry even while assigning the wrong meaning to each axis.

The correct method still won. But a margin around `0.037` is a warning against treating retrieval accuracy as semantic verification.

## What this result supports

The bounded claim is now:

> Across five fresh registered synthetic seeds, independently predicted primitive coordinates supported four weighted product-space retrieval queries and exceeded the strongest included scalar and incorrect-alignment controls.

This advances the project from:

```text
The mechanism worked in one controlled positive case.
```

to:

```text
The same standard composition mechanism replicated across fresh controlled cases.
```

That is meaningful progress. It means the project can stop worrying that E01.1 was merely a lucky seed.

## What it still does not support

E01.2a did not test the full RELATE idea.

All primitive relations were strong, linear and supported. The experiment did not require the system to recognise that one component was weak, absent, shifted or outside the learner family.

It also did not test:

- Boolean-style conjunction;
- exclusion constraints;
- Pareto retrieval;
- direct compound supervision;
- calibrated abstention;
- independent recomputation;
- real pretrained embeddings.

Most importantly, weighted product-space score fusion remains a standard baseline. Replicating that baseline validates the harness and the feasibility of preserving primitive coordinates. It does not establish a novel RELATE algorithm.

## The target has become clearer

The next serious question is no longer whether separate predicted properties can be combined. They can, at least in this controlled synthetic setting.

The next question is:

> Can a composition system determine when the requested primitive semantics are actually supported—and refuse the compound when they are not?

That is where composition becomes more than score fusion.

A useful RELATE system must know the difference between:

```text
all required relations are supported
```

and:

```text
this ranking looks plausible even though one requested relation is absent or misidentified
```

E01.2a gives us a stable positive case. The next stage must build and test the negative boundary.

## Frozen evidence

```text
Result:
b2c2bf4484b57a087496e65fb6e7587a57b9b3530401dfd9cdf9cf7556e86168

Decision tree:
321914813b4f342bea9edc3e92c267a919bc91c466cc95a1d66730fc779e6b48

Configuration:
178711153b2b9115ed8f3abf384e33a2d4c11a6db6e5f962889c0cea6f320d81
```

The result is frozen as [`e01-multiseed-composition-checkpoint-v1`](../results/e01-multiseed-composition-checkpoint-v1.md).

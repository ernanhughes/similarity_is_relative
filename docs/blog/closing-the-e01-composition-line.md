# The Result Passed. The Experiment Failed.

The first composition result passed.

Then it replicated across five new synthetic worlds.

Then an independent audit showed that the experiment had not asked a sufficiently discriminating question.

That is the final result of E01.

Nothing in the historical evidence has been deleted. The result trees, hashes, decisions and replay records remain frozen. The numerical measurements were real. The later independent implementation reproduced them.

What changed was our interpretation of what those measurements established.

## The original question

The project began with a plausible idea:

> A frozen representation may contain useful relations that its default cosine or Euclidean geometry does not expose. If those relations can be recovered separately, perhaps they can be composed after training into new relational queries.

E01.0 appeared to confirm this immediately. Independently fitted ridge predictors could be weighted after training and exactly reproduce a ridge model trained on the corresponding weighted target.

That was not composition generalisation. It was an algebraic identity: ridge regression is linear in its target.

We preserved the failure and changed the experiment.

E01.1 kept the primitive predictions separate and evaluated weighted product-space distance:

```text
d_w(i,j) = sqrt(sum_k w_k * (p_k(i) - p_k(j))^2)
```

Four unseen weighted queries passed the frozen single-seed rule. E01.2a repeated the measurement across five fresh seeds, added stronger scalar controls and tested every non-identity primitive permutation. All four substage decisions passed again.

At that point the result looked stable, reproducible and carefully bounded.

It was also scientifically weak.

## The outside review

We asked other systems to review the repository, not merely the prose. One review independently recomputed the central E01 results and identified three problems that changed the project.

We did not accept those claims on authority. We implemented a separate repository-controlled audit that did not call the E01 experiment runners, replay verifiers or metric helpers.

The audit confirmed all three.

## Finding 1 — the decision rule did not replicate

E01.1 required the composed method to exceed every included control by at least `0.10`. Its wrong-alignment control was one frozen cyclic permutation.

When the independent audit applied all five non-identity permutations to the same seed-307 world, the margins became:

| Compound | Margin over strongest permutation | Original `0.10` rule |
|---|---:|---|
| `a2_b` | `0.0853` | fail |
| `a3_c` | `0.1464` | pass |
| `b2_c` | `0.0788` | fail |
| `a_b2_c3` | `0.0374` | fail |

Only one of four compounds retained the original rule.

E01.2a had improved the control set but changed the required margin to a seed-level confidence-interval lower bound greater than zero. It therefore replicated the measurement pattern under a new substage rule. It did not replicate E01.1's original pass/fail standard.

The correct historical statement is:

> E01.2a reproduced the E01.1 measurements across fresh seeds under a different decision rule.

That is narrower than the statement we originally made.

## Finding 2 — the method was already at the ceiling

The audit replaced the predicted primitive values with the true noiseless latent values and reran the declared queries.

The rankings barely changed. Median ceiling fractions were approximately one for every compound. The absolute triplet-accuracy differences were generally only a few ten-thousandths.

The primitive ridge probes were already recovering nearly everything recoverable under the injected target noise. Applying the declared weighted operation to those predictions was therefore almost indistinguishable from applying it to the true latents.

The narrow seed intervals did not show that a difficult mechanism was unusually robust.

They showed that repeated samples from a saturated generator produced essentially the same answer.

This was the central design failure. The experiment could pass cleanly because there was almost no headroom for it to fail.

## Finding 3 — the semantic control was not semantic

The three primitives were exchangeable independent Gaussian variables with similar noise and recoverability.

Permuting them did not create a meaningfully different semantic world inside the generator. It reassigned unequal weights among statistically identical axes.

The audit confirmed this directly:

```text
weights (1,1,1)       margin 0.00000
weights (1,1.1,1.2)   margin 0.00183
weights (1,1.5,2)     margin 0.02091
weights (1,2,3)       margin 0.03737
weights (1,4,16)      margin 0.06739
```

The narrow `0.037` margin was primarily a weight-separation effect. The experiment had not measured whether a learned coordinate was securely bound to a named relation.

The semantic-binding problem may still be real. E01 could not test it.

## Finding 4 — triplet accuracy hid the retrieval picture

Triplet accuracy was around `0.92–0.93`. Mean recall@10 ranged from roughly `0.16` to `0.35`.

The latent oracle showed nearly the same recall. That does not make the learned method uniquely poor. It shows that uniformly sampled triplet comparisons were a much easier metric than exact nearest-neighbour recovery.

The project had emphasized the metric that made the result look strongest and dropped several retrieval metrics between stages. That was not intentional, but intent does not change the evidential consequence.

Future retrieval work must preserve metric continuity and report hard negatives, recall, neighbour ranks, regret and attainable ceilings alongside pairwise ordering accuracy.

## What remains true

E01 still records several useful facts.

- The implementation can train separate primitive predictors and execute a declared weighted query afterward.
- Preserving separate predicted coordinates beats the specific registered one-dimensional collapses for a weighted product-space target.
- The historical measurements are numerically reproducible.
- The repository's evidence structure allowed a later review to overturn the interpretation without rewriting history.
- A result can be preregistered, deterministic, replayable and numerically correct while still lacking discriminating power.

Those are real findings and process lessons.

They are not evidence of a general composition algorithm.

## What is closed

The project will not continue trying to turn the E01 weighted-product-space mechanism into a novel general composition method.

The closed line does not support claims of:

- relational composition beyond standard score fusion;
- semantic relation-name verification;
- bounded regret against directly trained compound models;
- support-aware refusal;
- real-domain utility.

Historical artifacts remain frozen. The claim is closed, not erased.

## The methodological result

The strongest output of this work may be the research process rather than the model result.

E01 produced several rules that did not exist when the project began:

1. **Attainable-ceiling gate** — no performance result is interpreted without estimating how much headroom existed.
2. **Discriminating-power review** — before preregistration, identify a plausible failure outcome and show that success is not structurally inevitable.
3. **Gate-lineage rule** — a confirmation cannot be described as replicating a prior decision when the controls or thresholds changed.
4. **Control-validity rule** — a control must be shown to measure the claimed failure mode, not a correlated generator parameter.
5. **Independent-verification taxonomy** — deterministic replay, independent metric recomputation and independent data regeneration are different evidence classes.
6. **Metric-continuity rule** — a confirmation may not silently drop less favourable metrics from the stage it claims to confirm.

These rules would have caught or exposed the E01 problem earlier. They are now part of the project's durable output.

## What we decided next

We considered replacing E01 with a much larger synthetic matrix of imperfect primitives, query types, supervision budgets and refusal conditions.

We rejected that plan.

It would have repeated the same failure at larger scale: carefully measuring outcomes largely determined by generator knobs we selected ourselves.

The next path is deliberately smaller and bounded.

### Step B — test the real premise

After publishing this account, run one real frozen-representation experiment:

> Does default geometry actually expose an objectively measurable compound relation poorly when the representation and primitive encoding were not designed by us?

This stage has a maximum budget of **ten working days** from frozen contract to decision.

It will use one real frozen representation, one small objective primitive set and one preregistered compound query. It will compare raw cosine and Euclidean distance against primitive readouts using triplet accuracy, hard-negative accuracy, recall and neighbour regret.

A negative result closes the RELATE research programme.

A positive result supplies the first real motivation for continuing.

### Step C — test refusal only if B survives

If the real-premise test passes, the project may spend at most **fifteen additional working days** on one focused refusal experiment.

The question will be:

> Does propagated compound support outperform ordinary independent per-primitive conformal abstention and a directly trained compound model with its own conformal wrapper?

The primary outcome will be selective risk at matched coverage. If the simple baselines match the propagated method, the novelty line closes.

There is no longer an E02-to-E07 roadmap. There are two conditional kill tests.

```text
Publish
  ↓
B: real-representation premise test — 10 working days
  ├─ fail → close RELATE
  └─ pass
       ↓
C: propagated-refusal test — 15 working days
       ├─ fail → close RELATE
       └─ pass → permit one real-domain refusal pilot
```

## Final evidence

```text
Independent recomputation result:
61737040da7f7c7d2b70de064062bf4c79236d4e1e7ca500a36f44d254ac8454

Decision tree:
0df12d733bc40e99ff78a1feb2a19c744cc472523bccb0c0689809e2a1633583

Configuration:
6e236067860e3a671a3bb489393e8bef8c6f9aeb085c0b630826351ac4a427a6
```

The compact checkpoint is [`e01-independent-recomputation-checkpoint-v1`](../results/e01-independent-recomputation-checkpoint-v1.md).

## Final classification

```text
E01 weighted-product-space composition line: CLOSED
Historical numerical results: PRESERVED
General composition claim: NOT SUPPORTED
Evidence-first methodological result: ESTABLISHED FROM THE CASE STUDY
Next research action: OPTION B
Option C: CONDITIONAL ON B
Maximum remaining RELATE research budget: 25 WORKING DAYS
```

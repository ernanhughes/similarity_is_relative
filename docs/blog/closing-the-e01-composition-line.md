# Closing the E01 Composition Line

The result passed. Then the independent audit showed that the experiment had not asked a sufficiently discriminating question.

That is the final result of E01.

Nothing in the historical evidence is being deleted. The committed result trees, hashes, decisions and replay records remain exactly where they were. The change is interpretive: after exhaustive controls, latent-oracle ceilings and independently recomputed retrieval metrics, the weighted-product-space line no longer supports continued research as a general composition mechanism.

## What E01 originally appeared to show

E01.1 trained three primitive predictors independently and combined their outputs after training into four weighted product-space queries. All four passed the controls included in the frozen single-seed contract.

E01.2a repeated the measurement over five fresh generator seeds, tested every non-identity primitive permutation and again recorded four passing substage decisions.

The numerical results were real. Deterministic replay passed. The later independent implementation reproduced the headline measurements.

The failure was not fabricated numbers or defective indexing.

The failure was that the generator and gate could not discriminate the scientific claim we cared about.

## Finding 1 — the decision rule did not replicate

E01.1 required a margin of at least `0.10` over every included control. It included one cyclic wrong alignment.

When the independent audit applied all five non-identity permutations to the seed-307 world, the strongest-control margins became:

```text
a2_b      0.0853
a3_c      0.1464
b2_c      0.0788
a_b2_c3   0.0374
```

Only one compound retained the original rule.

E01.2a had strengthened the control set but changed the required margin to a seed-level confidence-interval lower bound greater than zero. It therefore replicated the measurements under a new substage rule. It did not replicate E01.1's original pass/fail standard.

## Finding 2 — the method was already at the ceiling

The independent audit replaced the predicted primitive values with the true noiseless latent values and reran the declared queries.

The rankings barely changed. Median ceiling fractions were approximately one for every compound.

The primitive ridge probes were already recovering nearly everything recoverable under the injected target noise. Applying the declared weighted distance to their predictions was consequently almost indistinguishable from applying it to the true latents.

The narrow seed intervals were therefore not evidence that a difficult mechanism was unusually robust. They were evidence that five samples from the same saturated generator produced essentially the same answer.

## Finding 3 — the semantic control was not semantic

The three primitives were exchangeable independent Gaussian variables. A wrong permutation did not create a different semantic world inside the generator. It reassigned unequal weights among statistically identical axes.

The audit confirmed this directly:

```text
weights (1,1,1)       margin 0.00000
weights (1,1.1,1.2)   margin 0.00183
weights (1,1.5,2)     margin 0.02091
weights (1,2,3)       margin 0.03737
weights (1,4,16)      margin 0.06739
```

The celebrated narrow `0.037` margin was primarily a weight-separation effect. The experiment had not measured whether a learned coordinate was securely bound to a named relation.

## Finding 4 — triplet accuracy hid the retrieval picture

Triplet accuracy was around `0.92–0.93`. Mean recall@10 ranged from roughly `0.16` to `0.35`.

The latent oracle showed nearly the same recall. That does not make the method uniquely bad. It shows that randomly sampled triplet comparisons were a much easier metric than exact nearest-neighbour recovery.

Future work must report both easy and hard triplets, recall, neighbour ranks, regret, constraint satisfaction, attainable ceilings and direct-compound gaps.

## What remains true

E01 still records several useful facts.

- The implementation can train independent primitive predictors and execute a declared weighted query afterward.
- Preserving separate coordinates beats the specific registered one-dimensional collapses for a weighted product-space target.
- The repository's verification and claims process allowed a later independent review to overturn the original interpretation without altering history.
- A result can be preregistered, deterministic, replayable and numerically correct while still lacking discriminating power.

Those are real lessons. They are not a general composition result.

## What is now closed

The project will not continue trying to turn the current E01 weighted-product-space mechanism into a novel general composition algorithm.

The closed line does not support claims of:

- unseen relational composition beyond standard score fusion;
- semantic identity verification;
- bounded regret against directly trained compound models;
- support-aware refusal;
- real-domain utility.

## What replaces it

The revised project thesis is narrower and more useful:

> RELATE is a support-aware relational query runtime over frozen representations. It learns evidence-bearing primitive relations, executes declared compound queries over those primitives, propagates uncertainty through the query, and refuses when the primitive evidence or registered query algebra is insufficient.

The next synthetic stage must deliberately create imperfect, heterogeneous and sometimes absent primitives. It must compare the modular executor against directly trained compound models at multiple supervision budgets. It must include decomposable and non-decomposable queries, hard negatives, ceilings, support boundaries and explicit kill conditions.

That is a new research line. It does not inherit success from E01.

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

## Classification

```text
E01 weighted-product-space composition line: CLOSED
Historical numerical results: PRESERVED
General composition claim: NOT SUPPORTED
Revised support-aware query-runtime research: PROPOSED
```

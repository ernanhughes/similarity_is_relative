# E01-A — Independent recomputation of the external-review findings

## Status

Prospective audit contract. This document must precede canonical execution and interpretation.

## Purpose

Recompute the material external-review findings through repository-controlled code without calling either E01 experiment runner or either replay verifier.

This stage does not create a new composition claim. It determines how the frozen E01.1 and E01.2a results must be interpreted.

## Frozen questions

1. What are the E01.1 seed-307 margins against every non-identity primitive permutation?
2. How many E01.1 compounds satisfy the original `0.10` margin rule when the strongest permutation is used?
3. How closely does predicted-primitive composition approach the noiseless-latent attainable oracle?
4. What top-k recall and neighbour regret accompany the reported triplet accuracies?
5. Is the wrong-permutation margin largely determined by weight separation when primitives are exchangeable?
6. How do the E01.1 and E01.2a decision rules classify the same recomputed measurements?

## Independence boundary

The recomputation must not import:

- `_weighted_relational_distance`;
- `_triplet_accuracy`;
- `_evaluate`;
- `_decision`;
- either experiment `run()` function;
- either replay verifier.

It may reuse only frozen public constants and low-level dataset-contract helpers where reproducing identical arrays is necessary. All primary distances, triplet comparisons, retrieval metrics, ceiling calculations, permutation sweeps and audit classifications must be implemented in the audit module.

## Frozen configurations

- E01.1 seed: `307`;
- E01.2a seeds: `401, 433, 467, 503, 557`;
- samples: `6144`;
- dimensions: `64`;
- train/validation/test: `60/20/20`;
- target noise standard deviation: `0.15`;
- ridge alpha: `1.0`;
- retrieval cutoffs: `10, 25, 50, 100`;
- E01.2a triplets per query: `256`.

## Required outputs

### E01.1 exhaustive control audit

For each compound report:

- predicted-primitive triplet accuracy;
- every non-identity permutation accuracy;
- strongest permutation and margin;
- original cyclic-control margin;
- original frozen E01.1 status;
- counterfactual status under the original rule with the exhaustive control set.

### Ceiling and headroom

For E01.1 and each E01.2a seed/compound report:

- predicted-primitive accuracy;
- latent-oracle accuracy against the noisy-target oracle;
- absolute gap to latent oracle;
- `ceiling_fraction = predicted_accuracy / latent_accuracy` where the denominator is positive;
- primitive test `R²` and MAE.

The latent oracle is the registered compound operation applied to the noiseless latent variables, evaluated against the noisy-target oracle. It is not a perfect oracle and must not be labelled one.

### Retrieval quality

For predicted-primitive and latent-oracle distances report:

- recall@10, 25, 50 and 100;
- neighbour regret@10, 25, 50 and 100;
- oracle-neighbour predicted-rank median and p90.

### Weight-separation audit

Using exchangeable primitives, evaluate the strongest-permutation margin for:

- `(1,1,1)`;
- `(1,1.1,1.2)`;
- `(1,1.5,2)`;
- `(1,2,3)`;
- `(1,4,16)`.

This is diagnostic evidence only. It does not establish semantic identifiability.

## Audit decisions

The output must make factual classifications only:

- `ORIGINAL_RULE_RETAINED`;
- `ORIGINAL_RULE_FAILS_WITH_EXHAUSTIVE_CONTROL`;
- `SATURATED_AT_LATENT_ORACLE` when every seed-compound has `abs(predicted_accuracy - latent_accuracy) <= 0.005` and median `ceiling_fraction >= 0.99`;
- `HEADROOM_PRESENT` otherwise;
- `WEIGHT_SEPARATION_DIAGNOSTIC_SUPPORTED` when the symmetric margin is numerically zero within `1e-12` and the margins are non-decreasing over the frozen weight grid;
- `WEIGHT_SEPARATION_DIAGNOSTIC_NOT_SUPPORTED` otherwise.

These audit labels are not claim-promotion statuses.

## Evidence output

Write:

```text
runs/e01/independent-recomputation/
  e01-independent-recomputation.json
  e01-independent-recomputation-with-hash.json
```

The record must include:

- configuration;
- Python, NumPy, SciPy and scikit-learn versions;
- array and split hashes;
- per-seed and per-compound measurements;
- the audit decision tree;
- a result hash.

## Publication boundary

No claim-ledger row changes until the canonical output has been run, reviewed and checkpointed in a separate PR. Historical E01 artifacts remain immutable.

# E01.2a Multi-Seed Composition Checkpoint v1

## Status

- Scientific gate: `PASS`
- Deterministic replay: `PASS`
- Fresh seeds: `5`
- Frozen compounds: `4`
- Supported multi-seed decisions: `4 of 4`
- Claim promotion for the complete RELATE composition claim: `BLOCKED`

This checkpoint freezes the first replicated synthetic weighted product-space composition result in the repository.

E01.2a repeated the E01.1 positive-control mechanism across five fresh generated worlds: seeds `401`, `433`, `467`, `503`, and `557`. Seed `307` was excluded. Primitive ridge models were trained independently, compound queries were assembled only after primitive training, and each seed used explicit deterministic triplet manifests.

## Aggregate results

| Compound | Mean composed | 95% seed interval | Minimum seed | Scalar-margin interval | Wrong-alignment-margin interval | Successful seeds |
|---|---:|---:|---:|---:|---:|---:|
| `a2_b` | `0.9256` | `[0.9250, 0.9264]` | `0.9246` | `[0.1563, 0.1626]` | `[0.0821, 0.0845]` | `5/5` |
| `a3_c` | `0.9243` | `[0.9236, 0.9249]` | `0.9233` | `[0.1245, 0.1259]` | `[0.1442, 0.1459]` | `5/5` |
| `a_b2_c3` | `0.9285` | `[0.9282, 0.9287]` | `0.9280` | `[0.2164, 0.2193]` | `[0.0368, 0.0382]` | `5/5` |
| `b2_c` | `0.9256` | `[0.9250, 0.9261]` | `0.9248` | `[0.1567, 0.1638]` | `[0.0817, 0.0840]` | `5/5` |

All four decisions were:

```text
SUPPORTED_MULTI_SEED
```

## What this establishes

Within the registered synthetic contract:

> Independently predicted primitive coordinates supported four preregistered weighted product-space retrieval queries across five fresh dataset seeds and exceeded the strongest included scalar and wrong-alignment controls.

This confirms that the E01.1 result was not peculiar to seed `307`. Separate primitive coordinates retained useful compound structure across fresh rotations, samples, splits and triplet manifests.

## The most important warning

The three-relation compound `a_b2_c3` produced the highest mean composed accuracy, approximately `0.9285`, and the largest margin over the strongest scalar comparator, approximately `0.218`.

It also produced the narrowest margin over the strongest incorrect primitive permutation: the seed-level 95% interval was only approximately `[0.0368, 0.0382]`.

That result is not a failure—the frozen lower-bound rule was above zero—but it sharply identifies the next problem. Strong generic relational structure can survive an incorrect semantic alignment. A future RELATE mechanism must verify primitive identity and support, not merely produce a high retrieval score.

## Classification

This is a **replicated synthetic weighted product-space score-fusion result**.

Weighted product-space composition over predicted properties is a standard baseline. This checkpoint is therefore not evidence that RELATE has introduced a novel composition algorithm.

It also does not establish:

- correct refusal when a primitive is weak, absent, shifted or unsupported;
- conjunction, exclusion or Pareto composition;
- superiority to a directly trained compound comparator;
- independent recomputation of the metrics and decisions;
- transfer to real frozen representations.

Those remain required stages before the broader composition-and-refusal claim can be promoted.

## Frozen evidence identities

```text
Result:
b2c2bf4484b57a087496e65fb6e7587a57b9b3530401dfd9cdf9cf7556e86168

Decision tree:
321914813b4f342bea9edc3e92c267a919bc91c466cc95a1d66730fc779e6b48

Configuration:
178711153b2b9115ed8f3abf384e33a2d4c11a6db6e5f962889c0cea6f320d81

Compound definitions:
4bd20892449b7630df3fb8557d49595b8129d6bbfbcc6a432a26723d0d134d08
```

The corresponding compact record is [`e01-multiseed-composition-checkpoint-v1.json`](e01-multiseed-composition-checkpoint-v1.json).

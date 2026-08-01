# E01 External-Review Audit — 2026-08-01

## Status

Research interpretation audit. Historical experiment outputs, decision trees, hashes and checkpoint files remain immutable.

This audit records a material change in interpretation after independent external review of E01.1 and E01.2a. It distinguishes:

1. facts directly confirmed from the committed repository;
2. numerical findings reported by an external clean-room reviewer;
3. conclusions adopted provisionally pending local recomputation;
4. changes required before another composition experiment.

## Executive conclusion

The E01 measurements remain numerically valid within their implemented contracts. No sign, indexing, tie-handling or permutation implementation bug has been identified.

The scientific interpretation is narrower than the existing status language suggested:

> E01.1 and E01.2a are saturated synthetic weighted product-space positive controls. They do not yet provide discriminating evidence that primitive relation operators compose generally, that semantic identity is certified, or that support-aware refusal works.

The E01 composition line is therefore paused for redesign.

## Confirmed from committed repository

### E01.1 decision rule

`docs/experiments/05-e01-relational-conjunction.md` required every supported compound to:

- reach test triplet accuracy at least `0.88`;
- have oracle triplet disagreement at most `0.12`;
- exceed every included control by at least `0.10`.

E01.1 included one fixed cyclic primitive permutation as its wrong-alignment control.

### E01.2a decision rule

E01.2a evaluated all five non-identity primitive permutations and selected the strongest wrong alignment. Its implementation required the lower seed-level confidence bound of the margin over that control to be greater than zero. It did not retain E01.1's `0.10` margin requirement.

Therefore:

> E01.2a reproduced the E01.1 measurement pattern across fresh seeds under a new substage decision rule. It did not replicate E01.1's original pass/fail rule.

### Complete E01.2 gate was not attempted

`docs/experiments/06-e01-multiseed-composition-support.md` defines a larger gate including:

- weak and absent primitives;
- nonlinear and shifted primitives;
- conjunction and exclusion;
- Pareto retrieval;
- learned scalar and directly trained compound baselines;
- noisy-target and latent-space ceilings;
- support-aware refusal;
- independent recomputation.

E01.2a implemented only the strong-positive weighted product-space subset.

Future status language must distinguish:

```text
E01.2a positive-control substage rule: PASS
Complete E01.2 scientific gate: NOT ATTEMPTED
```

### Bootstrap configuration mismatch

`MultiSeedCompositionConfig.bootstrap_repetitions` is recorded as `2000`, but `_seed_interval` executes `20000` resamples with a hard-coded seed. The result is not altered by this audit. The configuration hash did not fully describe execution, and the implementation must be corrected prospectively.

### Retrieval metric narrowing

E01.1 calculated recall, neighbour regret and oracle-neighbour rank metrics in addition to triplet accuracy and Spearman correlation. E01.2a retained only triplet accuracy and Spearman correlation.

The multi-seed stage therefore confirmed a narrower measurement set than the single-seed stage.

## External clean-room findings

The external reviewer reports independently reimplementing the primary distance, triplet and permutation calculations without calling repository metric functions. The reviewer reports exact reproduction of the committed E01.2a aggregate composed accuracies and no implementation bug in the principal metric pipeline.

The following numerical findings are external evidence until reproduced by this repository.

### Exhaustive E01.1 wrong-alignment recomputation

Reported margins against the strongest of all five non-identity primitive permutations:

| Compound | Reported margin |
|---|---:|
| `a2_b` | `0.0853` |
| `a3_c` | `0.1464` |
| `b2_c` | `0.0788` |
| `a_b2_c3` | `0.0374` |

Under E01.1's original `0.10` rule, only `a3_c` would satisfy the margin requirement after replacing the registered single permutation with the later exhaustive control set.

This does not rewrite the frozen E01.1 decision tree. It changes how the point estimate may be interpreted after stronger post-hoc challenge.

### Attainable ceiling

The reviewer reports that replacing ridge predictions with the true noiseless latent primitive values changes compound triplet accuracy by only approximately `±0.0005`, implying:

```text
ceiling_fraction ≈ 1.000
```

If locally reproduced, this means the generator gave the primitive executor almost no headroom to fail. The narrow cross-seed variation should then be interpreted primarily as saturation under one generator rather than robustness across materially different conditions.

### Weight-separation effect in permutation margins

The reviewer reports the following sweep:

| Weights | Reported strongest-permutation margin |
|---|---:|
| `(1,1,1)` | `0.0000` |
| `(1,1.1,1.2)` | `0.0019` |
| `(1,2,3)` | approximately `0.039` |
| `(1,4,16)` | approximately `0.068` |

The current primitives are exchangeable independent Gaussian variables. The permutation control therefore mainly reassigns unequal weights among statistically interchangeable axes. It is not a sufficient semantic-identity test.

### Top-k retrieval

The reviewer reports recall@10 values substantially below the headline triplet accuracies and reports that the noiseless-latent oracle obtains essentially the same values. These values must be reproduced locally before publication as repository evidence.

## Revised interpretation

### E01.1

E01.1 remains a replay-verified point estimate under its registered control set. It must not be described as surviving exhaustive wrong-alignment challenge. Its `4 of 4` result is specific to the registered single cyclic permutation.

### E01.2a

E01.2a remains a numerically reproducible five-seed positive-control result under its own implemented rule. Its correct classification is:

> Replicated synthetic, saturated weighted product-space positive control; non-discriminating for general composition.

It does not establish:

- a learned composition algorithm;
- semantic relation-name binding;
- support propagation;
- refusal;
- non-additive query execution;
- real-domain transfer.

### General composition claim

No current experiment has measured bounded regret against a directly trained compound model over an imperfect primitive interface with meaningful headroom.

The general composition claim remains untested.

## Research-process lesson

This audit adds a required pre-registration question:

# Discriminating-power review

Before freezing an experiment, answer:

1. What outcome could realistically fail?
2. What is the attainable ceiling?
3. How close is the intended method expected to be to that ceiling?
4. Does the strongest baseline receive comparable information and supervision?
5. Does the generator make the desired result structurally inevitable?
6. Are the controls measuring the claimed failure mode?
7. Would the result remain scientifically interesting if every threshold passed?

Preregistration can prevent threshold drift and selective interpretation. It cannot by itself prevent a perfectly reproducible experiment from having no headroom.

## Required next steps

1. Reproduce the exhaustive E01.1 permutation and latent-ceiling calculations locally.
2. Commit a compact external-review recomputation artifact with provenance.
3. Repair bootstrap configuration, environment capture, artifact ignore rules and independent recomputation.
4. Freeze a redesigned factorisation-sufficiency and query-algebra contract before implementation.
5. Do not build support-aware refusal on the current saturated generator.

## Historical evidence policy

No historical JSON result, decision tree, checkpoint or hash is modified by this audit. Corrections attach through this document, the claims ledger and subsequent research-state records.

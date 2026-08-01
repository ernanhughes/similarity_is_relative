# Similarity Is Relative

Research into whether frozen representations contain useful relational signals that their default similarity geometry fails to expose—and whether those signals can be queried, verified and rejected when unsupported.

This repository is evidence-first. Claims begin as falsifiable questions, become executable contracts and are promoted only after committed evidence, explicit decision rules and appropriately classified verification.

## Publication rule

Every sentence beginning with **“we found”**, **“RELATE improves”**, **“the embedding contains”**, or **“the operator supports”** must map to:

1. a row in [`CLAIMS.md`](CLAIMS.md);
2. a committed reproduction command;
3. a committed compact result record;
4. hashes of the evidence-bearing artifacts;
5. a declared falsification or revision condition.

Verification language is explicit:

- **deterministic replay** means the same implementation reproduced the result tree;
- **independent recomputation** requires separate substantive metric and decision code;
- neither term alone implies a scientific claim passed.

## Current thesis

The original E01 composition thesis has been closed.

The only prospective RELATE thesis remains:

> **A support-aware relational query system may expose objectively useful relations in a real frozen representation and refuse compound queries when calibrated primitive evidence cannot support them.**

This is proposed and untested. No future result inherits success from E01.

## Current decision

The former broad synthetic E02–E07 roadmap has been cancelled.

The bounded path is:

```text
PUBLISH  finalize the E01 audit narrative and methodological case study
B        one real frozen-representation premise test — maximum 10 working days
C        one propagated-refusal test — maximum 15 working days, only if B passes
STOP     close RELATE if either required kill test fails
```

Maximum remaining RELATE research budget: **25 working days**.

Read:

- [Post-E01 publication and kill-test decision](docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md)
- [Option B domain selection](docs/research/option-b-domain-selection-2026-08-01.md)
- [Option B frozen experiment contract](docs/experiments/08-option-b-real-code-premise-test.md)

## Option B frozen design

```text
domain: CodeSearchNet Python functions
representation: microsoft/codebert-base, frozen
primitives: cyclomatic complexity, maximum control nesting depth,
            distinct call-site count
query: joint similarity under true and predicted Chebyshev geometry
primary metric: hard-negative triplet accuracy
continuation threshold: predicted executor - strongest raw geometry >= 0.10
budget: 10 working days
```

A gap below `0.10` produces `REAL_PREMISE_FAILED` and closes RELATE. Secondary metrics cannot rescue the decision. A pass authorises only the separately contracted Option C refusal test.

## Current status

- E00 linear recovery and basis-dependence components: **replicated synthetic**
- E00 complete family-aware certification: **blocked**
- E00 nonlinear XOR recovery: **insufficient evidence**
- E01.0 ridge composition identity: **confirmed identity; no generalisation claim**
- E01.1 weighted-product-space measurement: **numerically reproducible historical positive control**
- E01.2a five-seed measurement: **numerically replicated under its substage rule**
- E01 independent recomputation: **complete**
- E01 original `0.10` rule under exhaustive permutations: **fails for 3 of 4 compounds**
- E01 attainable ceiling: **saturated at the true-latent oracle**
- E01 permutation diagnostic: **weight-separation effect, not semantic verification**
- E01 general or novel composition line: **closed**
- Broad synthetic factorisation roadmap: **cancelled**
- Option B real-code premise test: **design contract frozen; implementation not started**
- Option C propagated refusal: **conditional on B**
- Promoted real-domain or RELATE algorithmic findings: **none**

## E01 final closure

The independent audit reproduced the headline E01 measurements and changed their interpretation.

### Exhaustive E01.1 control result

| Compound | Margin over strongest permutation | Original `0.10` rule |
|---|---:|---|
| `a2_b` | `0.0853` | fail |
| `a3_c` | `0.1464` | pass |
| `b2_c` | `0.0788` | fail |
| `a_b2_c3` | `0.0374` | fail |

E01.2a reproduced the measurement pattern under a different substage rule; it did not replicate E01.1's original pass/fail rule.

### Saturation result

The predicted-primitive executor was effectively indistinguishable from applying the same query to the true noiseless latent primitives. Median ceiling fractions were approximately `1.0` for all four compounds.

The narrow cross-seed intervals reflected a saturated generator with almost no headroom.

### Weight-separation result

For exchangeable primitives, the strongest wrong-permutation margin increased monotonically with weight separation and was exactly zero for equal weights. The E01 permutation control therefore did not test semantic relation-name identity.

### Retrieval context

Mean recall@10 ranged from roughly `0.16` to `0.35`, despite triplet accuracies around `0.92–0.93`. The latent oracle showed almost the same retrieval profile.

### Final classification

```text
E01 weighted-product-space composition line: CLOSED
Historical numerical artifacts: PRESERVED
General composition claim: NOT SUPPORTED
Evidence-first methodological case study: READY FOR PUBLICATION
Next research action: OPTION B
Option C: CONDITIONAL ON B
```

Read:

- [Finalized E01 closure blog](docs/blog/closing-the-e01-composition-line.md)
- [Independent recomputation checkpoint](docs/results/e01-independent-recomputation-checkpoint-v1.md)
- [External-review audit](docs/audits/e01-external-review-audit-2026-08-01.md)
- [Research reset](docs/research/e01-research-reset-2026-08-01.md)
- [Post-E01 decision](docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md)

## Evidence identities

### E01 independent recomputation

```text
Result:
61737040da7f7c7d2b70de064062bf4c79236d4e1e7ca500a36f44d254ac8454

Decision tree:
0df12d733bc40e99ff78a1feb2a19c744cc472523bccb0c0689809e2a1633583

Configuration:
6e236067860e3a671a3bb489393e8bef8c6f9aeb085c0b630826351ac4a427a6
```

### Historical E01.1

```text
Result:
e8144a17e2acaf3e1efda9522b5cb5775f37dbd63a0bb1611a97944a78d64c90

Decision tree:
f7ead1c9c70f276ee3c5dbe4689c50bcbb649c9fe6f272b5ca52c5fdae3a7a77
```

### Historical E01.2a

```text
Result:
b2c2bf4484b57a087496e65fb6e7587a57b9b3530401dfd9cdf9cf7556e86168

Decision tree:
321914813b4f342bea9edc3e92c267a919bc91c466cc95a1d66730fc779e6b48
```

## E00 records

- [Baseline checkpoint](docs/results/e00-baseline-checkpoint-v1.md)
- [Operator-matrix checkpoint](docs/results/e00-operator-matrix-checkpoint-v1.md)
- [Five-seed confirmation attempt](docs/results/e00-multiseed-confirmation-attempt-v1.md)
- [E00 evidence audit and erratum](docs/audits/e00-evidence-audit-2026-08-01.md)

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

PowerShell entry points live under [`scripts/`](scripts/README.md).

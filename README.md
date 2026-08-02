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
- neither term alone implies that a scientific claim passed.

## Current thesis

The original E01 composition thesis is closed.

Option B has now established the real-premise half of the revised RELATE thesis:

> **A frozen representation can contain objectively useful structural relations that its default cosine and Euclidean geometry materially underexpose.**

The remaining prospective thesis is narrower and still untested:

> **A support-aware relational query system can propagate calibrated primitive evidence through a compound query and refuse when that evidence is insufficient, outperforming simpler calibrated abstention baselines at matched coverage.**

Option B does not establish support propagation, calibrated refusal, semantic binding, a general query algebra or algorithmic novelty. Those questions belong to a separately frozen Option C contract.

## Current decision

The former broad synthetic E02–E07 roadmap remains cancelled.

The bounded path is now:

```text
E01      synthetic composition line — CLOSED
B        real frozen-representation premise test — PASSED
C        propagated-refusal test — AUTHORISED, CONTRACT NOT YET FROZEN
STOP     close the novelty line if Option C fails its future frozen gate
```

The post-E01 decision originally allowed at most ten working days for Option B and fifteen additional working days for Option C. Option B is complete. No Option C implementation is authorised until its prospective contract, baselines, calibration procedure, selective-risk metric and kill threshold are reviewed and merged.

Read:

- [Option B result checkpoint](docs/results/option-b-real-code-premise-checkpoint-v1.md)
- [Option B result article](docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)
- [Option B frozen experiment contract](docs/experiments/08-option-b-real-code-premise-test.md)
- [Post-E01 publication and kill-test decision](docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md)
- [Finalized E01 closure article](docs/blog/closing-the-e01-composition-line.md)

## Option B result

Option B tested one frozen external representation and one preregistered real-code relation:

```text
domain: CodeSearchNet Python functions
representation: microsoft/codebert-base, frozen
primitives: cyclomatic complexity, maximum control nesting depth,
            distinct call-site count
query: joint similarity under Chebyshev distance
candidate pool: 20,000 selected training functions
queries: 4,000 selected test functions
hard negatives: 128 frozen pairs per query, 512,000 pairs total
primary metric: equal-weighted per-query hard-negative triplet accuracy
```

The frozen comparison was:

```text
raw_best = max(raw_cosine_accuracy, raw_euclidean_accuracy)
gap = predicted_executor_accuracy - raw_best

support when gap >= 0.10
failure when gap < 0.10
```

### Registered primary result

| Method | Hard-negative triplet accuracy |
|---|---:|
| Raw CodeBERT cosine | `0.532458984375` |
| Raw CodeBERT Euclidean | `0.533314453125` |
| Token-length diagnostic | `0.498683593750` |
| Predicted primitive executor | `0.732851562500` |
| True-primitive oracle | `1.000000000000` |

```text
raw best:  0.533314453125
gap:       0.199537109375
threshold: 0.100000000000
outcome:   REAL_PREMISE_SUPPORTED
```

The predicted executor exceeded the strongest raw embedding geometry by approximately **19.95 percentage points**, almost twice the preregistered continuation threshold.

### Independent verification

The standalone verifier:

- did not import the experiment evaluator;
- reverified the selected manifests, embedding arrays, primitive predictions and hard-negative stream;
- recomputed all `4,000 × 5` primary query-score values;
- required exact score-matrix equality;
- independently recomputed the point estimates, registered gap and final outcome.

The independently recomputed result matched exactly.

### Secondary context

The primary decision did not rely on secondary metrics, but they help interpret the result:

| Diagnostic | Raw cosine | Raw Euclidean | Predicted executor |
|---|---:|---:|---:|
| Spearman with oracle distance | `0.11198` | `0.11045` | `0.72308` |
| Recall@10 | `0.00325` | `0.00303` | `0.00908` |
| Neighbour regret@10 | `0.86783` | `0.86895` | `0.49885` |
| Constraint error@10 | `1.58963` | `1.59063` | `0.99638` |

The executor improved relation-specific ordering, rank correlation, regret and constraint error. Exact nearest-neighbour recall remained low in absolute terms, so Option B supports a representation-and-geometry premise rather than a claim that the retrieval problem is solved.

Repository bootstrap gave a descriptive 95% gap interval of approximately `[0.19566, 0.20306]`. Every token-length decile retained a positive gap above `0.12`, and leave-one-large-repository-out gaps remained close to `0.20`. These diagnostics were not allowed to rescue or overturn the registered point-estimate decision.

## What Option B establishes

The promoted claim is deliberately narrow:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed a frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

This result shows that:

- a real frozen representation contained recoverable structural signals not well expressed by its default geometry;
- separately predicted primitive coordinates provided useful query-specific geometry without compound supervision;
- the improvement was not explained by token length alone;
- the result survived exact independent recomputation and repository-level diagnostics.

It does **not** show that:

- RELATE has a general composition algorithm;
- the chosen primitives are semantically complete descriptions of code;
- predicted geometry matches the true oracle;
- exact nearest-neighbour retrieval is solved;
- uncertainty can be propagated correctly;
- RELATE refuses unsupported queries better than simpler calibrated methods;
- the method is novel relative to a directly trained compound model.

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
- Option B real-code premise test: **complete; independently verified; `REAL_PREMISE_SUPPORTED`**
- Option C propagated refusal: **authorised; prospective contract not yet frozen**
- Promoted real-domain finding: **B-PREM-001**
- Promoted refusal or novelty finding: **none**

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

The predicted-primitive executor was effectively indistinguishable from applying the same query to the true noiseless latent primitives. The exchangeable-primitives permutation margin was principally a weight-separation diagnostic rather than semantic verification.

Option B did not revive the closed E01 composition claim. It answered a different, narrower question in a real external representation.

## Evidence identities

### Option B canonical result

```text
Implementation merge commit:
211e6f1a5fd827f55f89c69692acc9453f38f09f

Publication merge commit:
78e7da18a15a393cbedf1fdb7d6023ea42a32967

Full result SHA-256:
31223e02b807bbecb6603a76921677a6f79bac88609243bb20cf11ec30a68158

Primary score array SHA-256:
dccf0698934142ceaf1fe0ccd5d35713600ef45f9719e3864468c40a5274dc70

Raw query-metrics SHA-256:
784ded45280c99325f2ac285244dd4905b5718688c765831cd07f26fb9e184a7

Independent verification SHA-256:
da1b9cf1244b47c71ac7adce91b7db502b4fd2d3b663e126d8cde7c87e239d6c
```

Canonical evidence:

- [`artifacts/canonical/option-b/method-evaluation-v1/`](artifacts/canonical/option-b/method-evaluation-v1/)
- [Human-readable Option B checkpoint](docs/results/option-b-real-code-premise-checkpoint-v1.md)

### E01 independent recomputation

```text
Result:
61737040da7f7c7d2b70de064062bf4c79236d4e1e7ca500a36f44d254ac8454

Decision tree:
0df12d733bc40e99ff78a1feb2a19c744cc472523bccb0c0689809e2a1633583

Configuration:
6e236067860e3a671a3bb489393e8bef8c6f9aeb085c0b630826351ac4a427a6
```

## Research records

### Option B

- [Frozen experiment contract](docs/experiments/08-option-b-real-code-premise-test.md)
- [Domain selection](docs/research/option-b-domain-selection-2026-08-01.md)
- [Canonical row-selection checkpoint](docs/research/option-b-canonical-row-selection-complete-2026-08-01.md)
- [Method-evaluation runner contract](docs/research/option-b-method-evaluation-runner-2026-08-02.md)
- [Result checkpoint](docs/results/option-b-real-code-premise-checkpoint-v1.md)
- [Result article](docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)

### E01

- [Finalized E01 closure article](docs/blog/closing-the-e01-composition-line.md)
- [Independent recomputation checkpoint](docs/results/e01-independent-recomputation-checkpoint-v1.md)
- [External-review audit](docs/audits/e01-external-review-audit-2026-08-01.md)
- [Research reset](docs/research/e01-research-reset-2026-08-01.md)
- [Post-E01 decision](docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md)

### E00

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

For the completed Option B pipeline:

```bash
python -m pip install -e ".[dev,option-b]"
relate-option-b --print-contract
```

The canonical Option B result must not be rerun or modified. Any Option C work begins with a new documentation-only prospective contract.

PowerShell entry points live under [`scripts/`](scripts/README.md).

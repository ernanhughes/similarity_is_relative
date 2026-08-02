# Similarity Is Relative

RELATE is evidence-first research into whether frozen representations contain useful relational signals that their default similarity geometry fails to expose—and whether those signals can be queried, verified and rejected when unsupported.

Claims begin as falsifiable questions, become executable contracts and are promoted only after committed evidence, explicit decision rules and appropriately classified verification.

## Current status

```text
E01  broad synthetic composition line              CLOSED
B    real frozen-representation premise test       PASSED AND INDEPENDENTLY VERIFIED
C0   bounded support-mechanism discovery            ITERATION RESULTS PUBLISHED, REVIEW PENDING
C0S  separately firewalled C0 selection             NOT ACCESSED
C1   separately frozen confirmation                 NOT SELECTED, NOT ACCESSED, NOT RUN
```

The completed C0 checkpoint reports:

```text
candidate registrations:       6
candidate evaluations:         6
candidate registry entries:   12
discovery ledger entries:      0
mechanism result observed:   true
scientific result observed: false
C0 selection accessed:       false
C1 rows selected:            false
status: C0_ITERATION_RESULTS_PUBLISHED_PENDING_REVIEW
```

The next allowed action is independent C0 result and discovery review. No Option C scientific decision has been made.

## Start here

### Current Option C0 result

- [Human-readable C0 checkpoint](docs/results/option-c0-discovery-iteration-checkpoint-v1.md)
- [Independent review guide](docs/reviews/option-c0-iteration-independent-review-guide.md)
- [Result article: selective signal, not yet a distinctive mechanism](docs/blog/option-c0-found-a-selective-signal-not-yet-a-distinctive-mechanism.md)
- [Canonical C0 result](artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json)
- [C0 publication checkpoint](artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json)
- [Candidate registry](artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl)
- [Discovery ledger](artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-ledger-v1.jsonl)

### Option B premise result

- [Human-readable Option B checkpoint](docs/results/option-b-real-code-premise-checkpoint-v1.md)
- [Option B result article](docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)
- [Frozen Option B contract](docs/experiments/08-option-b-real-code-premise-test.md)
- [Canonical Option B evidence](artifacts/canonical/option-b/method-evaluation-v1/)

### Project rules and history

- [Claim ledger](CLAIMS.md)
- [C0 discovery and confirmation protocol](docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md)
- [C0 canonical allocation](docs/research/option-c0-canonical-allocation-setup-2026-08-02.md)
- [C0 initial candidate plan](docs/research/option-c0-initial-candidate-plan-2026-08-02.md)
- [Post-E01 publication and kill-test decision](docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md)
- [E01 closure article](docs/blog/closing-the-e01-composition-line.md)

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

C0 measurements are exploratory. They may justify a later C1 contract, but they cannot support an Option C publication claim.

## Current thesis

The original E01 composition thesis is closed.

Option B established the real-premise half of the revised RELATE thesis:

> **A frozen representation can contain objectively useful structural relations that its default cosine and Euclidean geometry materially underexpose.**

The remaining prospective thesis is narrower and unconfirmed:

> **A support-aware relational query system can propagate calibrated primitive evidence through a compound query and refuse when that evidence is insufficient, outperforming simpler calibrated abstention baselines at matched coverage.**

Option C is split into:

```text
C0  bounded mechanism discovery with no promoted claim
C1  separately frozen confirmatory refusal experiment
```

C1 is not an automatic sequel. C0 must publish exactly one exit outcome, and only `C1_CONTRACT_JUSTIFIED` permits a later documentation-only C1 contract.

## Option B: the real-code premise

Option B tested one frozen external representation and one preregistered structural relation:

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

The promoted claim is deliberately narrow:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed the frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

A standalone verifier independently recomputed the complete primary score matrix and reproduced the exact result and decision.

Option B does **not** establish general composition, semantic binding, calibrated refusal, production utility or superiority to a direct compound model.

## Option C0: what was tested

C0 uses whole-repository separation:

| Role | Repositories | Rows | Status |
|---|---:|---:|---|
| C0 fit | 2,117 | 8,007 | used for fitting and calibration |
| C0 iteration | 1,058 | 4,110 | one registered exploratory evaluation completed |
| C0 selection | 545 | 2,070 | not accessed |
| C1 reserve | 1,604 | 6,357 | not accessed; final C1 rows not selected |

The frozen primitives were the same three used in Option B. C0 asked:

1. are all three primitives above their C0-fit medians?
2. is any primitive above its median?
3. are two of the three primitives above their medians?

Two candidate families were registered:

- a joint max-residual uncertainty box;
- empirical mass under complete joint residual vectors.

Required comparisons were:

- independent primitive conformal abstention;
- direct compound conformal prediction;
- uncalibrated confidence ranking;
- oracle primitive-support headroom.

## C0 result in one page

Percentages are rounded navigation summaries. Review the [complete checkpoint](docs/results/option-c0-discovery-iteration-checkpoint-v1.md) and canonical JSON before drawing conclusions.

### Conjunction: all three primitives

The strongest descriptive candidate result was empirical residual mass:

```text
beta 0.01:  42.73% coverage, 1,756 accepted rows, 0 errors
beta 0.025: 51.22% coverage, 2,105 accepted rows, 2 errors, 0.095% risk
```

The joint box also found zero-error subsets at lower coverage.

However, ordinary confidence ranking at roughly 50% coverage also made two errors, and the independent primitive baseline was highly competitive. The low-risk subset is real as an exploratory observation; the distinctiveness of the candidate mechanism is not established.

### Disjunction: any primitive

Selected candidate points had roughly 21–28% coverage and 1.4–1.9% selective risk. A direct compound conformal baseline achieved approximately 38.3% coverage at approximately 1.14% risk.

### Thresholded majority: two of three

Selected candidate points had roughly 23–24% coverage and 1.1–1.3% risk. The direct compound baseline and confidence ranking were stronger at selected operating points.

### Primitive interval calibration

Aggregate joint primitive interval coverage tracked nominal coverage closely:

| Alpha | Nominal | Observed |
|---:|---:|---:|
| 0.01 | 99.0% | 98.91% |
| 0.025 | 97.5% | 97.40% |
| 0.05 | 95.0% | 94.72% |
| 0.10 | 90.0% | 89.76% |
| 0.20 | 80.0% | 80.73% |

This argues against gross aggregate interval miscalibration. It does not prove useful query-level support propagation.

## Current neutral interpretation

> C0 produced a real, query-dependent selective signal. The conjunction admitted sizeable low-error accepted subsets, but the registered support-composition candidates did not clearly outperform the strongest confidence-ranking, independent-primitive or direct-compound baselines.

This is a provisional review summary, not a promoted claim.

### What C0 directly observed

- aggregate primitive interval coverage close to nominal;
- useful low-error selective subsets for some query/operating-point combinations;
- much stronger behaviour for `all` than for `any` or `two-of-three`;
- highly competitive simpler baselines;
- all three primitive Ridge fits selecting the largest registered alpha, 100.

### What C0 did not establish

- general support-aware composition;
- candidate-family superiority;
- superiority to direct compound prediction;
- a query-independent refusal mechanism;
- external generalisation;
- support for `C-REFUSE-001`;
- justification for C1.

## Evidence identities

### Option C0 iteration

```text
evidence branch:
agent/option-c0-iteration-results-v1

evidence commit:
07cf6fc

full result SHA-256:
ca81076fd21ecf97fc33dcd2a1690a2cd29443cb9cf5c26eba49c00095a1df99

candidate registry SHA-256:
5ecef017282288d2715577396f162b2b3380828b64a1332ee45bf68b120990c9

discovery ledger SHA-256:
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

The discovery ledger hash is the SHA-256 of an empty file. Interpretations are intentionally awaiting review.

### Option B canonical result

```text
implementation merge commit:
211e6f1a5fd827f55f89c69692acc9453f38f09f

publication merge commit:
78e7da18a15a393cbedf1fdb7d6023ea42a32967

full result SHA-256:
31223e02b807bbecb6603a76921677a6f79bac88609243bb20cf11ec30a68158

primary score array SHA-256:
dccf0698934142ceaf1fe0ccd5d35713600ef45f9719e3864468c40a5274dc70

independent verification SHA-256:
da1b9cf1244b47c71ac7adce91b7db502b4fd2d3b663e126d8cde7c87e239d6c
```

## What happens next

The permitted sequence is:

1. independently review and recompute the committed C0 result summary;
2. append classified observations to the discovery ledger;
3. review all six candidates and close the candidate registry;
4. publish exactly one C0 outcome:
   - `C1_CONTRACT_JUSTIFIED`
   - `C1_NOT_JUSTIFIED`
   - `C0_DATA_FIREWALL_FAILED`
   - `C0_BUDGET_EXHAUSTED`
5. only after `C1_CONTRACT_JUSTIFIED`, prepare a documentation-only C1 contract;
6. select final C1 rows only after that contract merges.

No one should access C0 selection or C1 merely to settle an unresolved interpretation of the C0 iteration result.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Option B/C0 dependencies:

```bash
python -m pip install -e ".[dev,option-b]"
```

PowerShell entry points live under [`scripts/`](scripts/README.md).

The canonical Option B result and completed C0 iteration must not be casually rerun or modified. Infrastructure improvements may be developed separately, but they do not alter the committed C0 evidence checkpoint.

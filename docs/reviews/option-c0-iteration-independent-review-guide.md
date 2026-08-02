# Option C0 Iteration Independent Review Guide

**Review target:** completed C0 exploratory iteration  
**Review date:** after 2026-08-02 result publication  
**Scientific decision:** not yet made  
**C0 selection:** inaccessible  
**C1 reserve:** inaccessible

## Purpose

This document tells an independent reviewer where the evidence lives, what has and has not happened, and which decisions are still open.

The review is intended to answer whether the completed exploratory result justifies closing the C0 candidate registry and, potentially, freezing a separate C1 confirmation contract. It is not a request to confirm the researchers' preferred interpretation.

## Read these files first

### 1. Human-readable result checkpoint

[`docs/results/option-c0-discovery-iteration-checkpoint-v1.md`](../results/option-c0-discovery-iteration-checkpoint-v1.md)

Use this for the experiment status, selected operating points, current boundaries and evidence identities.

### 2. Canonical result

[`artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json)

This is the complete evidence-bearing output. It includes:

- embedding-runtime identity;
- partition counts;
- primitive thresholds, scales and selected Ridge penalties;
- label prevalence;
- all candidate operating points;
- required baselines;
- risk–coverage curves;
- regime diagnostics;
- repository dispersion;
- primitive interval coverage.

Expected SHA-256:

```text
ca81076fd21ecf97fc33dcd2a1690a2cd29443cb9cf5c26eba49c00095a1df99
```

### 3. Publication checkpoint

[`artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json)

This records the evidence state and prohibited actions. Confirm that it says:

```text
status: C0_ITERATION_RESULTS_PUBLISHED_PENDING_REVIEW
candidate registrations: 6
candidate evaluations: 6
candidate registry entries: 12
discovery ledger entries: 0
mechanism result observed: true
scientific result observed: false
C0 selection accessed: false
C1 rows selected: false
```

### 4. Candidate registry

[`artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl)

Expected SHA-256:

```text
5ecef017282288d2715577396f162b2b3380828b64a1332ee45bf68b120990c9
```

Verify that the registry contains six immutable `REGISTERED` events followed by six matching `EVALUATED` events.

### 5. Discovery ledger

[`artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-ledger-v1.jsonl`](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-ledger-v1.jsonl)

At the initial review checkpoint this file is intentionally empty:

```text
bytes: 0
SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Interpretations proposed during review should be classified before they are appended. The empty file is evidence that the project did not write a preferred narrative into the canonical ledger before seeking review.

## Frozen antecedents

Reviewers who need the experimental design should inspect:

- [`docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`](../experiments/09-option-c0-discovery-and-confirmation-protocol.md)
- [`docs/research/option-c0-canonical-allocation-setup-2026-08-02.md`](../research/option-c0-canonical-allocation-setup-2026-08-02.md)
- [`docs/research/option-c0-initial-candidate-plan-2026-08-02.md`](../research/option-c0-initial-candidate-plan-2026-08-02.md)
- [`artifacts/canonical/option-c0/candidate-plan-v1/option-c0-initial-candidate-plan-v1.json`](../../artifacts/canonical/option-c0/candidate-plan-v1/option-c0-initial-candidate-plan-v1.json)

These are historical, pre-evaluation records. Do not edit them to reflect the result.

## Context from Option B

Option B established only the real-representation premise:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed the frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

Read:

- [`docs/results/option-b-real-code-premise-checkpoint-v1.md`](../results/option-b-real-code-premise-checkpoint-v1.md)
- [`docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md`](../blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)

Option B did not establish calibrated refusal, support propagation or superiority to a direct compound model. Do not allow Option B support to flow automatically into an Option C conclusion.

## Review sequence

### A. Verify evidence integrity

Check:

1. result and registry hashes;
2. candidate registration/evaluation pairing;
3. exact partition counts;
4. `c0_selection_accessed = false`;
5. `c1_rows_selected = false`;
6. empty discovery ledger;
7. no promoted Option C claim in [`CLAIMS.md`](../../CLAIMS.md).

An integrity failure should be classified separately from a weak scientific result.

### B. Recompute a compact comparison table

For every query and method, extract at least:

```text
accepted rows
coverage
errors
selective risk
refusal reasons
repository dispersion
regime-specific risk and coverage
```

Compare methods at meaningful matched coverage or matched risk. Do not compare one method's most favourable operating point to another method's arbitrary registered point without explaining the mismatch.

### C. Check prevalence and trivial strategies

For each query, inspect:

- positive prevalence in fit model, fit calibration and iteration;
- full-coverage error rate;
- whether accepted rows are overwhelmingly from one class;
- whether confidence ranking alone isolates essentially the same easy subset;
- whether a majority or constant prediction creates misleadingly low risk.

### D. Compare against all required baselines

A distinctive support-composition interpretation requires more than low selective risk.

Review:

1. independent primitive conformal abstention;
2. direct compound conformal prediction;
3. uncalibrated confidence ranking;
4. oracle support headroom.

The strongest current challenge is that simple confidence ranking is highly competitive for the conjunction and clearly strong for two-of-three, while the direct compound model is stronger at selected operating points for `any` and `two-of-three`.

### E. Interpret query differences

Assess separately:

- conjunction (`all`);
- disjunction (`any`);
- thresholded majority (`two-of-three`).

Possible explanations include class prevalence, distance from decision boundaries, correlated primitive errors, query geometry and the number of ways a compound predicate can change under uncertainty. These are hypotheses unless directly tested by the committed diagnostics.

### F. Decide what C0 established

Separate the review into:

1. direct observations;
2. plausible interpretations;
3. unsupported claims;
4. unexpected findings;
5. new hypotheses requiring fresh data.

Do not convert an unexpected C0 pattern into confirmation.

### G. Decide whether C1 is justified

Choose one:

```text
C1_CONTRACT_JUSTIFIED
C1_NOT_JUSTIFIED
C0_DATA_FIREWALL_FAILED
C0_BUDGET_EXHAUSTED
```

A recommendation for `C1_CONTRACT_JUSTIFIED` must specify a scientifically meaningful hypothesis rather than merely selecting the nicest C0 cell.

## Questions that must be answered before C1

1. Is the target general support-aware composition, conjunction-specific replication, or something else?
2. Is superiority over simpler baselines required, or would replication/non-inferiority be scientifically meaningful?
3. Which query and fixed operating point are selected without consulting C0 selection or C1?
4. What is the primary endpoint?
5. How are risk and coverage matched?
6. What is the material margin?
7. What is the minimum accepted-row requirement?
8. How is multiplicity handled?
9. What outcome counts as a limited positive rather than support for `C-REFUSE-001`?
10. What outcome closes the Option C novelty line?

## Candidate ledger classifications

Suggested classifications available to reviewers are:

- `PLANNED_MECHANISM_DIAGNOSTIC`
- `EXPLORATORY_OBSERVATION`
- `UNEXPECTED_FINDING`
- `NEW_HYPOTHESIS_REQUIRING_FRESH_DATA`
- `IMPLEMENTATION_OR_DATA_INTEGRITY_FINDING`

Examples of possible entries, subject to independent review:

- aggregate joint primitive interval coverage tracked nominal coverage;
- conjunction candidates isolated low-error selective subsets;
- simple confidence ranking matched or exceeded important candidate operating points;
- query behaviour differed substantially across `all`, `any` and `two-of-three`;
- all primitive Ridge models selected the maximum registered regularisation value;
- a small shifted stratum exhibited elevated error for the `any` query.

The classification and wording should make clear which entries were planned diagnostics and which were discovered after result inspection.

## Current neutral summary

The least committal accurate description is:

> C0 produced a real, query-dependent selective signal and a clean evidence checkpoint. It did not yet demonstrate that the registered support-composition mechanisms are superior to simpler confidence, independent-primitive or direct-compound baselines. C1 remains undecided and untouched.

## Review deliverable

An independent review should end with:

1. an integrity verdict;
2. a scientific interpretation;
3. arguments for and against proceeding;
4. one recommended C0 exit outcome;
5. the strongest reason that recommendation may be wrong;
6. proposed discovery-ledger entries;
7. if C1 is justified, a precise candidate for a later documentation-only C1 contract.

No reviewer should request access to C0 selection or C1 merely to settle an unresolved exploratory interpretation.

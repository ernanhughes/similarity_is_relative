# Option B next-conversation handoff

Use this document to start a fresh conversation after the pre-embedding audit PR is merged.

## Repository

```text
ernanhughes/similarity_is_relative
```

Use the current `main` branch as the authoritative source. Do not rely on assumptions from an earlier conversation.

## Read first

Before changing code, read:

```text
docs/audits/option-b-pre-embedding-review-and-remediation-2026-08-01.md
docs/experiments/08-option-b-real-code-premise-test.md
docs/research/option-b-canonical-row-selection-complete-2026-08-01.md
docs/runbooks/option-b-canonical-embeddings.md
```

Also inspect:

```text
src/relate/experiments/
tests/
artifacts/canonical/option-b/
```

Repository code, committed artifacts, and the remediation audit are authoritative.

## Current status

```text
Option B contract: FROZEN
Canonical row selection v1: REPRODUCED
Primitive tables v1: INVALIDATED BY REVIEW
Selected manifests: REQUIRE REVERIFICATION
External identity v1: RECORDED BUT NOT SUFFICIENTLY ENFORCED
Canonical embeddings: NOT GENERATED
Primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE EMBEDDING EXTRACTION
```

## Fixed scientific rule

```text
gap = predicted_executor_accuracy - max(raw_cosine_accuracy, raw_euclidean_accuracy)

gap >= 0.10  => REAL_PREMISE_SUPPORTED
gap < 0.10   => REAL_PREMISE_FAILED
```

Do not change the threshold, add an inconclusive band, introduce a rescue query, add a second model or language, or substitute a confidence-bound decision.

## Accepted blocking findings

1. The registered primitive extractor and implementation disagree, especially for `Try`, `With`, `AsyncWith`, and comprehensions.
2. Primitive tables and their checkpoint must be regenerated as versioned v2 artifacts after repair.
3. The predicted executor must use predicted primitive vectors on both query and candidate sides.
4. True primitives may be used only to define oracle distance and the hard-negative manifest.
5. Train-candidate prediction behaviour must be frozen before fitting; deterministic cross-fitting is preferred.
6. The recorded pooling hash identifies a different function from canonical extraction.
7. The frozen ten-row identity fixture is not currently enforced during extraction.
8. Dynamic padding and partial cache misses may make vectors depend on batch composition.
9. Existing chunk files have no complete extraction identity and can bypass SQLite validation.
10. Canonical embedding runs A and B must use separate output directories and separate SQLite databases or cache disabled for B.
11. Probe, final-evaluation, and independent-recomputation runners are not yet complete.

## Current task

Read the remediation audit and determine the first incomplete bounded stage.

Immediately after the audit PR, the next permitted implementation stage is:

```text
PR 2 — primitive contract conformance
```

That PR should:

- prospectively clarify comprehension complexity/depth and `elif` depth semantics;
- repair P1/P2 extraction to match the frozen intent;
- repair CodeSearchNet provenance/path extraction;
- pin recursion behaviour;
- add regression tests for every registered control construct;
- avoid generating embeddings, fitting probes, generating hard negatives, or computing scientific metrics.

Do not proceed into later stages in the same PR.

## Required working method

1. Verify the current `main` branch and recent merged PRs.
2. Read the audit before editing.
3. Inspect the exact affected symbols and existing tests.
4. Implement only the next bounded stage.
5. Run focused tests and the full suite where possible.
6. Open a draft PR describing:
   - exact scope;
   - files changed;
   - tests run;
   - canonical artifacts affected;
   - whether any frozen scientific rule changed;
   - the next permitted stage.
7. Update the audit only when a remediation stage is completed and supported by committed evidence.

## Copyable prompt

```text
We are continuing work on the GitHub repository ernanhughes/similarity_is_relative.

Use the current main branch as the authoritative source. Before changing code, read:

- docs/audits/option-b-pre-embedding-review-and-remediation-2026-08-01.md
- docs/experiments/08-option-b-real-code-premise-test.md
- docs/research/option-b-canonical-row-selection-complete-2026-08-01.md
- docs/runbooks/option-b-canonical-embeddings.md
- docs/runbooks/option-b-next-conversation-handoff.md

Also inspect src/relate/experiments/, tests/, and artifacts/canonical/option-b/.

The current gate is BLOCK BEFORE EMBEDDING EXTRACTION. No canonical embeddings, probes, hard-negative manifest, scientific metric, or final result exist.

Determine the first incomplete bounded stage in the remediation audit and implement only that stage. The next expected stage after the audit checkpoint is PR 2 — primitive contract conformance.

Do not alter the frozen model, language, query, raw baselines, 0.10 threshold, or point-estimate decision. Do not generate embeddings, fit probes, or compute scientific metrics in the primitive repair PR.

Run relevant tests and open a draft PR with exact scope, validation, artifact consequences, and the next permitted action.
```
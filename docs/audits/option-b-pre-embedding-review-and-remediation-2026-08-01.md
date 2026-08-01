# Option B pre-embedding review and remediation

Date: 2026-08-01

## Purpose

This document is the durable checkpoint for the external methodological and engineering review of the frozen Option B real-code premise experiment.

It records the accepted findings, the current scientific status, the changes required before canonical embedding extraction, and the bounded pull-request sequence that must be completed before the experiment may advance.

This document does not change the registered scientific question, model, language, primitive set, compound query, raw baselines, continuation threshold, or final decision rule.

## Authoritative sources

Future work must begin from the current `main` branch and read, at minimum:

- `docs/experiments/08-option-b-real-code-premise-test.md`
- `docs/research/option-b-domain-selection-2026-08-01.md`
- `docs/research/option-b-canonical-row-selection-complete-2026-08-01.md`
- `docs/runbooks/option-b-canonical-embeddings.md`
- this audit
- the current Option B implementation under `src/relate/experiments/`
- the current Option B tests under `tests/`
- the canonical records under `artifacts/canonical/option-b/`

Repository code and committed artifacts are authoritative. External reviews are evidence inputs, not authority by themselves.

## Frozen scientific decision

The registered decision remains:

```text
gap = predicted_executor_accuracy - max(raw_cosine_accuracy, raw_euclidean_accuracy)

gap >= 0.10  => REAL_PREMISE_SUPPORTED
gap < 0.10   => REAL_PREMISE_FAILED
```

The following remain prohibited:

- changing the `0.10` threshold after results;
- introducing an inconclusive band;
- adding a rescue query after failure;
- adding a second model or language to save the premise;
- replacing the point-estimate decision with a confidence-bound rule;
- promoting secondary diagnostics into the primary decision after results.

## Current status

```text
Option B contract: FROZEN
External identity v1: RECORDED BUT NOT SUFFICIENTLY ENFORCED
Canonical row selection v2: REPRODUCED AND VERIFIED
Primitive tables v2: PUBLISHED; v1 REMAINS INVALIDATED
Selected manifests v2: REVERIFIED
Canonical embeddings: NOT GENERATED
Embedding determinism: NOT TESTED
Primitive probes: NOT FIT
Probe/evaluation stage: NOT IMPLEMENTED AS A COMPLETE RUNNER
Hard-negative manifest: NOT GENERATED
Scientific metric: NOT OBSERVED
Scientific result: NOT OBSERVED
Current gate: BLOCK BEFORE EMBEDDING EXTRACTION
```

No scientific result has been contaminated because no canonical embedding, probe, manifest, primary metric, or final decision has yet been generated.

# Accepted blocking findings

## B1. Primitive implementation does not match the registered contract

The registered maximum control-depth primitive includes constructs that the current visitor does not consistently count, including `Try`, `With`, `AsyncWith`, and comprehensions.

Comprehension complexity and depth semantics also require a prospective clarification before repair. The clarification must specify:

- whether each comprehension generator contributes one cyclomatic increment;
- whether multiple generators are nested for depth;
- whether comprehension filters contribute complexity but not depth;
- how `elif` contributes to depth.

The implementation must then be brought into conformance with the clarified existing intent. The contract must not be weakened to match the current bug.

Required consequences:

- add pinning tests for every registered control construct;
- repair CodeSearchNet provenance/path extraction;
- pin recursion behaviour used during canonical selection;
- rerun selection twice in fresh directories;
- regenerate primitive tables and the canonical selection report as versioned v2 records;
- explicitly compare all selected-manifest hashes with v1;
- stop and investigate if selected membership or ordering changes unexpectedly.

## B2. Predicted executor semantics are incomplete and can permit oracle leakage

The predicted executor compares test queries with train candidates. The current probe helper produces test predictions only, leaving candidate-side primitive vectors unspecified.

The following interpretation is forbidden:

```text
predicted query primitives versus true candidate primitives
```

True candidate primitives would import oracle labels into the proposed method while raw baselines do not receive them. External measurement demonstrated that this mixed geometry can produce an apparent positive result from a probe with almost no predictive skill.

The contract must be prospectively clarified before any probe is fit:

```text
True primitives are used only to define oracle distance and the frozen hard-negative manifest.

The predicted executor uses predicted primitive vectors on both the query side and the candidate side.
```

Candidate-prediction behaviour must also be frozen before fitting. The preferred protocol is deterministic out-of-fold prediction for train candidates, so candidate vectors are not in-sample predictions from the probes that fitted those labels.

The probe contract must also freeze:

- deterministic fold assignment;
- alpha tie-breaking;
- refit policy after validation selection;
- no rounding of predicted primitives to the integer lattice;
- required output arrays for train candidates, validation rows, and test queries;
- row-order hashes;
- scaler, coefficient, intercept, selected-alpha, and prediction hashes.

## B3. The recorded pooling hash does not certify the executed implementation

Identity v1 hashes `option_b_real_code.embed_code`, while canonical extraction executes a separately defined nested `embed_batch` implementation.

This defeats the purpose of the pooling identity:

- editing the executed function may not change the recorded hash;
- SQLite may reuse vectors under a stale identity;
- editing the non-executed function may invalidate the cache unnecessarily.

Required correction:

- create one shared top-level canonical tokenization, model-inference, and pooling path;
- use it for identity capture, fixture generation, canonical extraction, tests, and cache identity;
- hash the implementation that actually executes;
- include a canonical tokenization configuration digest covering special-token, padding, truncation, maximum-length, side, pooling-policy, and output-dtype choices;
- publish immutable identity v2 rather than editing identity v1 in place.

## B4. The frozen fixture is recorded but not enforced

Canonical extraction currently checks identity status and manifest hashes but does not recompute the ten-row frozen embedding fixture.

A mandatory extraction preflight must:

1. load the exact pinned model and tokenizer revisions;
2. run the fixture snippets through the exact canonical embedding implementation;
3. verify per-row identities and the matrix hash;
4. abort before dataset reconstruction or canonical extraction on any mismatch.

Canonical reproduction should use the same pinned CPU environment unless another environment is separately demonstrated to reproduce the exact logical arrays.

## B5. Dynamic padding and partial-cache batches may make vectors cache-state dependent

The current code uses dynamic padding, while a partially populated cache sends only missing rows to the embedding backend. A clean full batch and a resumed missing-only subset can therefore execute different matrix shapes.

The intended fix is fixed padding:

```text
padding = max_length
max_length = 256
```

Before identity v2 is accepted, test the same fixed set of functions as:

- one batch;
- multiple smaller batches;
- one row at a time.

Exact logical-array equality must be demonstrated in the pinned canonical CPU environment. If exact equality fails, the determinism claim and verification protocol must be revised before canonical run A.

## B6. Existing chunk reuse is not identity safe

Current chunk files are reused when a path exists, without verifying model, tokenizer, pooling, manifest, stable keys, source hashes, shape, dtype, dimensions, finite values, or payload hashes.

Chunk reuse also precedes cache-mode handling, so `refresh` and `off` can still reuse stale files.

Required correction:

- compute a complete extraction fingerprint;
- include model and tokenizer revisions, tokenization digest, pooling identity, maximum length, padding regime, split manifest hash, and any remaining batch-sensitive setting;
- store chunks under the fingerprint or require a matching sidecar;
- record the split, range, stable-key-sequence hash, source-sequence hash, shape, dtype, dimensions, logical array hash, and file hash;
- reject every unverified pre-existing chunk;
- make `refresh` and `off` bypass old chunks;
- write chunks atomically through a temporary path and rename.

Local chunks produced by the current implementation must not be treated as canonical evidence.

# Accepted later-stage requirements

These do not block the primitive repair PR, but must be frozen or implemented before their respective stages.

## Probe stage

- robust scaling is fitted on train primitives only;
- ridge coefficients are fitted on train only;
- alpha selection uses validation only;
- test labels do not influence preprocessing, fitting, or selection;
- predictions are produced for train candidates, validation rows, and test queries;
- train-candidate predictions follow the prospectively frozen candidate protocol;
- prediction arrays and all fitted parameters are hash-addressed and row-order verified.

## Hard-negative manifest

- the manifest is generated from true robust-scaled primitives only;
- predictions and raw-baseline results are unavailable to manifest construction;
- every method receives the identical frozen manifest;
- no query is silently omitted;
- pair counts and exclusion reasons are recorded for every query;
- minimum-pair behaviour is frozen before predictions are inspected;
- the manifest is generated and hashed before method distances are evaluated.

## Primary metric and uncertainty

- the registered point estimate remains the scientific decision input;
- query-level scores are equal-weighted unless every query has exactly the same frozen pair count and this is verified;
- repository dependence is handled as required by the frozen contract;
- bootstrap intervals are descriptive and cannot rescue or overturn the point-estimate decision;
- `raw_best` remains the maximum of the two registered raw baselines;
- independent metric recomputation must read frozen artifacts without importing the experiment runner.

# Non-blocking but recommended improvements

- create an exact lockfile or canonical environment export;
- record Python, platform, tokenizers, datasets, transformers, torch, NumPy, CPU/BLAS, and thread settings;
- pin and record the recursion limit and recursion-excluded row identities;
- add cache schema versioning, inspection, row counts, and byte-size reporting;
- add SQLite busy timeout;
- make model/tokenizer loading lazy so a complete cache hit avoids model initialization;
- use separate databases and fresh output directories for embedding runs A and B;
- retain logical array hashes as the primary matrix identity and file hashes as serialization evidence;
- register a supervised surface-feature executor as a secondary diagnostic only;
- report primitive correlations, tie rates, repository concentration, pair-count distributions, and near-duplicate diagnostics without allowing them to alter the primary decision.

# Bounded remediation plan

Each stage must be a separate, reviewable pull request. Do not combine later scientific stages into an earlier repair PR.

## PR 1 — audit checkpoint

Documentation only.

- add this durable audit;
- add the new-conversation handoff document;
- record the current gate as `BLOCK BEFORE EMBEDDING EXTRACTION`;
- make no code or artifact changes.

## PR 2 — primitive contract conformance

- prospectively clarify comprehension and `elif` semantics;
- repair P1/P2 extraction;
- repair provenance/path extraction;
- pin recursion behaviour;
- add construct-level regression tests;
- do not regenerate canonical artifacts in the same PR unless the resulting diff remains independently reviewable.

## PR 3 — canonical selection and primitive checkpoint v2

- run selection A and B from fresh directories;
- compare all selected and primitive artifacts;
- verify stable-key uniqueness and cross-split boundaries;
- verify primitive-table and manifest key order exactly;
- publish versioned v2 primitive tables and selection report;
- explicitly supersede the invalid primitive portion of v1 without deleting history.

## PR 4 — predicted executor contract completion

Documentation and pure helper tests only.

- freeze predictions on both sides;
- restrict true primitives to oracle/manifest construction;
- freeze candidate cross-fitting or the explicitly chosen alternative;
- freeze alpha tie, refit, no-rounding, row-order, and artifact rules.

## PR 5 — embedding identity v2

- consolidate the canonical embedding implementation;
- use fixed padding;
- add batch-invariance tests;
- implement fixture preflight;
- publish identity v2;
- ensure cache identity references the executed implementation.

## PR 6 — chunk and cache recovery hardening

- add extraction fingerprints and chunk sidecars;
- validate all reused chunks;
- enforce cache modes;
- use atomic chunk writes;
- make model loading lazy;
- add stale-model, stale-pooling, stale-manifest, stale-row, wrong-shape, wrong-dtype, and corruption tests.

## Canonical embedding execution

Only after PRs 2–6 are merged and all tests pass:

1. generate run A with a fresh output directory and fresh SQLite database;
2. generate run B with a different fresh output directory and physically separate SQLite database or cache disabled;
3. compare logical array hashes, row-order hashes, shapes, dtypes, and environment records;
4. stop if any canonical identity differs;
5. publish a dedicated embedding checkpoint PR;
6. do not fit probes in the embedding checkpoint PR.

## Later bounded stages

After the embedding checkpoint:

1. implement and review probe fitting;
2. fit and freeze probes once;
3. implement manifest generation and inclusion rules;
4. generate and freeze the hard-negative manifest;
5. implement primary evaluation and independent recomputation;
6. run the registered decision once;
7. run secondary diagnostics only after the primary result is frozen.

# Next permitted action

Completed stages:

- PR 2 — primitive contract conformance;
- PR 3 — canonical selection and primitive checkpoint v2.

The next implementation PR is:

```text
PR 4 — predicted executor contract completion
```

Canonical embedding extraction remains blocked.

# Completion rule for this audit

This audit remains the project handoff document until every remediation item is either:

- completed and linked to a merged PR and committed artifact; or
- explicitly rejected in a documented decision that explains why it is unnecessary and preserves the frozen scientific contract.

Future conversations must read this document before proposing the next stage.
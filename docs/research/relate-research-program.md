# RELATE Research Programme

Date: 2026-08-04  
Status: research orientation; does not promote a scientific claim

## Purpose

This document states the durable RELATE research question, separates established evidence from proposed applications and gives future experiments a stable conceptual frame.

It is not an experiment contract. When this document conflicts with a frozen contract, canonical artifact or the claim ledger, the frozen and canonical record governs.

## Core question

RELATE asks:

> Do frozen representations contain useful relational signals that their default similarity geometry underexposes, and can those signals be queried, verified and refused when unsupported?

The programme rejects the assumption that an embedding has one universally meaningful similarity geometry.

For a representation `z(x)`, raw cosine supplies one global ordering. A relation-specific query instead asks whether another measurable structure can be recovered from `z(x)` and used to compare items according to a declared purpose.

Examples include:

- similar control-flow structure;
- equivalent data transformation;
- shared architectural role;
- the same concept expressed through different vocabulary;
- the same causal argument applied to different subjects.

The query defines the relation. The embedding is evidence-bearing input, not the final definition of similarity.

## Operational model

The general RELATE shape is:

```text
artifact
  -> frozen representation
  -> independently testable primitive relations
  -> declared query-specific executor
  -> support and uncertainty checks
  -> ranking, qualification or refusal
```

A future operator is scientifically interesting only when each step is independently testable.

### Frozen representation

The underlying encoder is fixed for the experiment. RELATE does not alter it to make the target result easier.

### Primitive relation

A primitive is a named, externally defined and independently measurable property or relation. Examples in Option B were cyclomatic complexity, maximum control nesting depth and distinct call-site count.

A primitive predictor is not automatically evidence of model understanding. It establishes only that the declared signal is recoverable under the frozen procedure and evaluation.

### Query-specific executor

The executor combines or constrains primitive outputs according to a declared query. The query may be additive, conjunctive, thresholded, exclusionary, lexicographic or partially ordered.

Standard score fusion is not automatically a novel RELATE contribution. The contribution must be established against relevant direct and learned baselines.

### Support and refusal

An executor can always produce numbers. RELATE must distinguish producing a ranking from having evidence that the requested relation is supported.

A support-aware system should identify at least:

- supported primitives;
- weakly supported primitives;
- absent signal under the tested representation;
- signal present but outside the declared operator family;
- support that breaks under distribution shift;
- compound queries whose required evidence is incomplete.

Refusal is therefore part of the scientific question, not a user-interface accessory.

## Current evidence ladder

### E00 — synthetic recoverability and boundaries

The E00 line established bounded synthetic results for recoverable linear relations, rotation retention, basis dependence, absent-relation controls, nonlinear-family limits and shortcut instability.

These results validate parts of the experimental harness. They do not establish real-domain utility.

### E01 — closed composition line

E01 produced reproducible weighted product-space positive controls. Independent review showed that the line did not establish the intended general composition thesis:

- much of the task reduced to predicting explicit scalar properties and applying standard score fusion;
- the synthetic generator was non-discriminating in important regimes;
- semantic permutation controls exposed identity ambiguity;
- support propagation and refusal were not tested.

The E01 line is closed. Its numerical records remain valid within their contracts, but future experiments inherit no general-composition success from them.

### Option B — supported real-domain premise

Option B tested one frozen CodeBERT representation, one language, three objective AST primitives and one frozen structural conjunction on repository-separated Python code.

The predicted primitive executor achieved `0.732851562500` hard-negative triplet accuracy, compared with `0.532458984375` for raw cosine and `0.533314453125` for raw Euclidean. The `0.199537109375` best-raw gap passed the frozen `0.10` continuation threshold and was independently recomputed.

This supports one bounded premise:

> A real frozen representation can contain recoverable structural relations that its default geometry materially underexposes.

It does not establish general composition, semantic binding, calibrated refusal, solved retrieval or production utility.

### Option C0/C1 — active support-and-refusal route

Option C0 is bounded exploratory mechanism discovery. It may compare propagation candidates and calibrated baselines using development-only roles, but it cannot promote `C-REFUSE-001`.

Option C1 remains blocked unless C0 publishes `C1_CONTRACT_JUSTIFIED`. A future C1 contract must freeze the selected mechanism, reserve selection, matched-coverage evaluation, material margin, baselines and independent recomputation boundary before confirmatory evidence is accessed.

## Relationship to established approaches

RELATE overlaps with several established research families. Novelty must not be claimed merely because one of these mechanisms is implemented.

### Metric learning

Learned similarity metrics and conditional subspaces already replace raw cosine with task-specific geometry. RELATE must compare against these approaches when the relevant experiment permits training a direct metric.

### Concept bottlenecks and probing

Predicting named properties and reasoning over them is established. RELATE must demonstrate value beyond ordinary property prediction, such as reusable query execution, evidence lineage, support propagation or calibrated refusal.

### Direct compound prediction

A model trained directly for the target compound relation is a mandatory baseline for the support-and-refusal line. Modular primitive execution may trade some accuracy for reuse, interpretability or unseen-query flexibility; that trade must be measured rather than assumed.

### Selective prediction and conformal methods

Abstention, risk-coverage evaluation and conformal calibration are established. RELATE's claim, if supported, must concern the propagation and verification of relation-specific evidence, not the invention of abstention itself.

## Application programme: code

Code is the first application because useful relations can often be defined independently of the embedding.

Candidate relations include:

- control-flow equivalence;
- data-flow role;
- side-effect profile;
- exception behaviour;
- API and dependency interaction;
- algorithmic family;
- architectural responsibility;
- duplicated business-rule identity;
- behaviour-preserving rewrites;
- behaviour-changing edits hidden by textual resemblance.

### What Option B supports

Option B supports only the bounded structural premise recorded in `B-PREM-001`.

### What remains to test

Future code experiments must separately test whether relation-specific execution improves tasks such as:

- conceptual duplicate retrieval across repositories;
- finding alternative implementations of the same transformation;
- locating functions with the same architectural role;
- distinguishing textually similar functions with different effects;
- retrieving behaviourally related code under repository and time shift.

Each task requires objective labels, a frozen query definition, strong direct baselines and an explicit stop rule.

## Application programme: writing

Writing is a proposed second application. It is scientifically harder because the target relations are often author-relative and cannot be derived from syntax alone.

Candidate relations include:

- same concept, different vocabulary;
- same causal model, different topic;
- repeated or conflicting argument;
- shared rhetorical function;
- shared narrative function;
- metaphorical recurrence;
- character-motivation continuity;
- concept evolution across drafts.

### Required evidence sources

A credible writing experiment should prefer:

- explicit author annotations;
- manuscript and sentence lineage;
- selected and rejected rewrites;
- declared chapter or scene functions;
- locked thematic and character decisions;
- blinded human comparison judgments;
- held-out documents or chapters.

Model-generated labels may assist annotation, but they cannot serve as the sole ground truth for a claim that the model then appears to recover.

### Minimum writing claim boundary

The first writing experiment should not claim that RELATE understands themes or author intent. A defensible first claim would concern retrieval agreement with held-out author or human judgments on one narrowly defined conceptual relation.

## Research-source boundary

Conversations, external reviews and model critiques are valuable research inputs. They contain hypotheses, applications, alternative explanations and failed ideas.

They are not authoritative scientific state.

```text
conversation statement
  -> extracted hypothesis, criticism or decision candidate
  -> repository review
  -> frozen contract when appropriate
  -> evidence
  -> claim-ledger decision
```

No chat summary may silently revise a canonical result, reopen a closed claim or promote an application hypothesis.

## Scientific nonclaims

Until new evidence is produced, RELATE must not claim that:

- embeddings contain all relations relevant to a domain;
- primitive probes reveal how the encoder internally reasons;
- relation-specific execution is always better than direct supervision;
- a support score is calibrated merely because it is interpretable;
- one code result transfers to writing;
- a model-generated concept taxonomy is author-grounded;
- the architecture reset advances the scientific state machine.

## Durable success criteria

A strong RELATE result should satisfy all of the following:

1. **External target:** the relation is defined independently of the embedding.
2. **Frozen representation:** the encoder and input identities are fixed before confirmation.
3. **Strong baselines:** raw geometry, learned metrics and direct compound alternatives are included where relevant.
4. **Discriminating regime:** the task is not saturated and controls can fail meaningfully.
5. **Support boundary:** weak, absent, nonlinear-out-of-family and shifted cases are distinguished.
6. **Retrieval continuity:** ranking metrics, local-neighbour metrics and selective metrics match the publication language.
7. **Provenance:** inputs, predictions, decisions and artifacts are committed and hashed.
8. **Independent verification:** the primary result is recomputed without importing the decisive evaluator.
9. **Stop rule:** failure closes or revises the exact claim rather than triggering an automatic rescue experiment.
10. **Bounded interpretation:** the publication claim says no more than the evidence establishes.

## Governing records

- [`CLAIMS.md`](../../CLAIMS.md)
- [`docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md`](post-e01-publication-and-kill-test-decision-2026-08-01.md)
- [`docs/experiments/08-option-b-real-code-premise-test.md`](../experiments/08-option-b-real-code-premise-test.md)
- [`docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`](../experiments/09-option-c0-discovery-and-confirmation-protocol.md)
- [`docs/research/next-scientific-program.md`](next-scientific-program.md)

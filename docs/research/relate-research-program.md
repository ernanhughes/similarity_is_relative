# RELATE Research Programme

Date: 2026-08-04  
Status: research orientation; does not promote a scientific claim

## Purpose

This document states the durable RELATE research question, separates established evidence from proposed applications and gives future experiments a stable conceptual frame.

It is not an experiment contract. When it conflicts with a frozen contract, canonical artifact or the claim ledger, the frozen and canonical record governs.

## Core question

RELATE asks:

> Do frozen representations contain useful relational signals that their default similarity geometry underexposes, and can those signals be recovered, verified and refused when unsupported?

The programme rejects the assumption that an embedding has one universally meaningful similarity geometry.

For a representation `z(x)`, raw cosine supplies one global ordering. A relation-specific query instead asks whether another externally defined structure can be recovered from `z(x)` and used to compare items according to a declared purpose.

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
  -> default-geometry diagnosis
  -> independently testable relational evidence
  -> declared relation-specific recovery
  -> support and uncertainty checks
  -> ranking, qualification or refusal
```

A future method is scientifically interesting only when every stage is independently testable.

### Frozen representation

The encoder is fixed for the experiment. RELATE does not fine-tune it to make the target result easier unless a separately declared baseline explicitly permits that comparison.

### External relation

The target relation must be defined independently of the embedding and recovery model.

Examples include objective program behaviour, normalized specifications, AST properties, revision lineage or author-grounded conceptual judgments.

### Default-geometry diagnosis

Option E studies the regime where cosine is uninformative or misleading under a prospectively frozen rule. Low cosine is not itself evidence of a hidden relation. It identifies an opportunity stratum only after the target relation has been established externally.

### Relation-specific recovery

A recovery model or executor attempts to expose the declared relationship from the frozen representation.

A high score establishes nothing by itself. The method must be compared with direct learned alternatives, and its output must remain separate from calibrated support.

### Support and refusal

RELATE must distinguish producing a ranking from having evidence that the ranking is supportable.

A support-aware system should identify at least:

- strongly supported relation evidence;
- weak relation evidence;
- absent signal under the tested representation;
- signal present but outside the declared operator family;
- support that fails under distribution shift;
- compound requests whose required evidence is incomplete.

Refusal is part of the scientific question, not a user-interface accessory.

## The three quantities

Option E keeps these quantities separate:

```text
C = default cosine or raw geometry
R = relation-specific recovered score
S = calibrated support for acting on R
```

A useful hidden-relation case requires:

```text
C weak or misleading
R strong
S strong and calibrated
external label confirms the relation
```

A strong `R` with weak `S` is a refusal case, not a success.

## Relationship to Hallucination Energy

The relationship is conceptual:

> Hallucination Energy measures semantic content unsupported by attached evidence; RELATE Option E measures relational evidence supported by a frozen representation but underexposed by its default geometry.

The two projects address opposite evidence failures:

```text
Hallucination Energy
  output exceeds evidence
  -> detect unsupported semantic residual

RELATE Option E
  default geometry underuses evidence
  -> detect supported relational residual
```

They are not exact mathematical inverses. Option E learns from external labels and therefore faces shortcut, misbinding and calibration risks that must be tested directly.

## Current evidence ladder

### E00 — synthetic recoverability and boundaries

E00 established bounded synthetic results for recoverable linear relations, rotation retention, basis dependence, absent-relation controls, nonlinear-family limits and shortcut instability.

These results validate parts of the experimental harness. They do not establish real-domain utility.

### E01 — closed composition line

E01 produced reproducible weighted product-space positive controls. Independent review showed that the line did not establish the intended general-composition thesis:

- much of the task reduced to predicting explicit scalar properties and applying standard score fusion;
- the generator was non-discriminating in important regimes;
- semantic permutation controls exposed identity ambiguity;
- support and refusal were not tested.

The E01 line is closed. Its numerical records remain valid within their contracts, but later work inherits no general-composition success from them.

### Option B — supported real-domain premise

Option B tested one frozen CodeBERT representation, one language, three objective AST primitives and one frozen structural conjunction on repository-separated Python code.

The predicted primitive executor achieved `0.732851562500` hard-negative triplet accuracy, compared with `0.532458984375` for raw cosine and `0.533314453125` for raw Euclidean. The `0.199537109375` best-raw gap passed the frozen `0.10` continuation threshold and was independently recomputed.

This supports one bounded premise:

> A real frozen representation can contain recoverable structural relations that its default geometry materially underexposes.

It does not establish general composition, semantic binding, calibrated refusal, solved retrieval or production utility.

### Historical Option C — closed before confirmation

Option C0/C1 framed the problem as propagated support under matched coverage. That protocol produced useful architecture and methodological records, but no C1 confirmatory contract or result.

The route is closed under `C-REFUSE-001`. Its frozen records and protected roles remain historical and immutable.

### Option E — active recovery-and-refusal programme

Option E sharpens the operational problem:

> In cases where cosine fails to expose an externally verified relation, can relation-specific recovery find supported evidence for that relation and refuse unsupported alternatives?

Option E uses two named stages:

```text
E-DISCOVERY
  bounded stratum, mechanism and discriminating-power discovery

E-CONFIRM
  separately frozen one-shot confirmation, only if justified
```

E-DISCOVERY must end with exactly one outcome:

```text
E_CONFIRMATION_JUSTIFIED
E_CONFIRMATION_NOT_JUSTIFIED
E_DATA_FIREWALL_FAILED
E_BUDGET_EXHAUSTED
```

Only the first outcome permits a later documentation-only E-CONFIRM contract. No E-DISCOVERY measurement can promote `E-RECOVER-001`.

## Relationship to established approaches

RELATE overlaps with several established research families. Novelty must not be claimed merely because one of these mechanisms is implemented.

### Metric learning

Learned similarity metrics and conditional subspaces already replace raw cosine with task-specific geometry. Option E must compare against these approaches where direct metric training is permitted.

### Concept bottlenecks and probing

Predicting named properties and reasoning over them is established. RELATE must demonstrate value beyond ordinary property prediction, such as reusable relation execution, evidence lineage, support discrimination, calibrated refusal or transfer to new queries.

### Direct relation prediction

A model trained directly for the target relation is a mandatory baseline. Modular recovery may trade some accuracy for reuse, interpretability, unseen-query flexibility or better refusal, but those advantages must be measured rather than assumed.

### Selective prediction and conformal methods

Abstention, risk–coverage evaluation and conformal calibration are established. Option E's possible contribution concerns support-aware recovery in a default-geometry failure regime, not the invention of abstention.

### Retrieval and reranking

Cross-encoders, lexical systems, graph methods and task-specific rerankers are strong alternatives. A RELATE application result must beat or complement relevant systems rather than compare only with raw cosine.

## Application programme: code

Code remains the first application because useful relations can often be defined independently of the embedding.

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

### First recommended Option E code relation

The strongest first application is conceptual duplicate retrieval under externally checkable equivalence.

The dataset should contain:

- true relations with low cosine;
- high-cosine surface false positives;
- easy positives;
- true negatives;
- weak, absent, out-of-family and shifted cases.

Ground truth may come from hidden behavioural tests, normalized specifications, refactoring lineage, accepted task solutions or adjudicated business-rule equivalence.

### What Option B supports

Option B supports only the bounded structural premise recorded in `B-PREM-001`.

It does not prove conceptual duplication, business-rule identity or useful nearest-neighbour retrieval.

## Application programme: writing

Writing is a proposed later application. It is scientifically harder because target relations are often author-relative.

Candidate relations include:

- same concept, different vocabulary;
- same causal model, different topic;
- repeated or conflicting argument;
- shared rhetorical function;
- shared narrative function;
- metaphorical recurrence;
- character-motivation continuity;
- concept evolution across drafts.

A credible writing experiment should prefer:

- explicit author annotations;
- manuscript and sentence lineage;
- selected and rejected rewrites;
- declared scene or argument functions;
- locked thematic and character decisions;
- blinded human comparison judgments;
- held-out documents or chapters.

Model-generated labels may assist annotation but cannot serve as the sole ground truth.

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

- low cosine implies hidden useful information;
- embeddings contain every relation relevant to a domain;
- a high recovered score proves a relation exists;
- primitive probes reveal how the encoder internally reasons;
- relation-specific recovery is always better than direct supervision;
- a support score is calibrated merely because it is interpretable;
- Option B established conceptual retrieval;
- the Hallucination Energy analogy establishes mathematical equivalence;
- a code result transfers to writing;
- architecture work advances the scientific state machine.

## Durable success criteria

A strong RELATE result should satisfy all of the following:

1. **External target:** the relation is defined independently of the embedding.
2. **Frozen representation:** encoder and input identities are fixed before confirmation.
3. **Prospective opportunity stratum:** cosine failure is defined without final-test selection.
4. **Strong baselines:** raw geometry, learned metrics and direct relation alternatives are included.
5. **Discriminating regime:** the task is not saturated and controls can fail meaningfully.
6. **Support boundary:** weak, absent, out-of-family and shifted cases are distinguished.
7. **Metric continuity:** ranking, local retrieval and selective metrics match the publication language.
8. **Provenance:** inputs, labels, predictions, decisions and artifacts are committed and hashed.
9. **Independent verification:** the primary result is recomputed without importing the decisive evaluator.
10. **Stop rule:** failure closes or revises the exact claim rather than triggering an automatic rescue stage.
11. **Bounded interpretation:** publication language says no more than the evidence establishes.

## Governing records

- [`CLAIMS.md`](../../CLAIMS.md)
- [`docs/research/cosine-failure-and-relational-recovery.md`](cosine-failure-and-relational-recovery.md)
- [`docs/research/next-scientific-program.md`](next-scientific-program.md)
- [`docs/experiments/08-option-b-real-code-premise-test.md`](../experiments/08-option-b-real-code-premise-test.md)
- [`docs/results/option-b-real-code-premise-checkpoint-v1.md`](../results/option-b-real-code-premise-checkpoint-v1.md)
- [`docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`](../experiments/09-option-c0-discovery-and-confirmation-protocol.md) — historical

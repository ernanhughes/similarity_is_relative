# Option E — Cosine Failure and Relational Recovery

Date: 2026-08-04  
Status: authorised research-programme decision and pre-implementation design; not a frozen confirmatory contract; no Option E scientific result has been observed

## Executive decision

RELATE will begin a new scientific line under **Option E**.

Option E does not continue under the Option C, C0, C1, D2, E00 or E01 identifiers. The existing Option C0/C1 propagated-refusal route is closed before confirmatory execution and remains part of the historical record. Its frozen protocols, exploratory artifacts, blocked roles and protected reserves must not be rewritten, re-labelled as Option E evidence or treated as successful predecessors.

Option E begins from a sharper question:

> When raw cosine similarity is uninformative for an externally verified relationship, can RELATE recover evidence of that relationship from the frozen representation, and can calibrated support distinguish genuine hidden signal from weak, absent, out-of-family or shifted signal more effectively than strong calibrated alternatives?

The target is not to outperform cosine everywhere. The target is the **cosine-failure regime**: cases where the default geometry says little or returns the wrong ordering, but the frozen representation may still contain useful relation-specific evidence.

## Why a new identifier is required

The former Option C question focused on propagating calibrated primitive support through a compound query. That remains relevant, but the project had not yet stated the operational retrieval situation clearly enough.

Option E changes the centre of the experiment:

```text
former emphasis
  support propagation in the abstract

Option E emphasis
  externally verified relation
  + weak or ineffective default cosine geometry
  + recovery from the remaining representation
  + calibrated evidence that permits retrieval or refusal
```

This is a material reframing. It therefore requires a new experiment identifier and fresh prospective records. No success is inherited from E01, Option B or Option C beyond the exact bounded premises already recorded in `CLAIMS.md`.

Option B supplies only the continuation premise:

> A real frozen representation can contain a recoverable structural relation that raw cosine and Euclidean geometry materially underexpose.

Option E asks whether that premise can become a support-aware recovery method in a deliberately selected cosine-failure regime.

## The search setting

Let:

- `X` denote the requested concept, relation or search intent;
- `Y = {y_1, ..., y_n}` denote the candidate documents, passages, functions or other artifacts;
- `z(·)` denote a frozen representation;
- `C_X(y)` denote raw cosine similarity between the encoded query and candidate;
- `R_X(y)` denote a relation-specific recovered score;
- `S_X(y)` denote calibrated support for acting on that recovered score.

The ordinary search system exposes only:

```text
X + Y -> frozen embeddings -> cosine ranking
```

Option E studies:

```text
X + Y
  -> frozen embeddings
  -> cosine-failure identification
  -> relation-specific recovery
  -> calibrated support
  -> retrieve, qualify or refuse
```

A low cosine score does not prove that the embedding contains no information about the requested relation. It proves only that the relation is weakly expressed under that one default geometry.

## The three quantities must remain separate

Option E must not collapse its evidence into one attractive score too early.

### Default similarity

`C_X(y)` measures what the default embedding geometry exposes.

### Recovered relation

`R_X(y)` measures the relationship learned or executed for the declared query.

### Support

`S_X(y)` measures whether the evidence required by the recovered relation is sufficiently supported for the system to act.

The decisive pattern is not merely:

```text
R_X(y) > C_X(y)
```

It is:

```text
cosine is weak or misleading
relation-specific recovery is strong
support is calibrated and strong
external ground truth confirms the relationship
```

A high recovered score with weak support is not a success. It is a refusal case.

## Required decision quadrants

Option E must distinguish at least these four basic outcomes.

| Default cosine | Recovered relation | Calibrated support | Interpretation |
|---|---|---|---|
| low | high | high | hidden relation recovered |
| low | high | low | unsupported score; refuse |
| low | low | high | supported evidence of no target relation |
| high | low | high | surface similarity or cosine false positive |

The second row is central. A learned operator can always produce a number. Without support, RELATE would merely replace cosine with another system capable of confident error.

## The cosine-failure stratum

Option E's primary opportunity set must be frozen prospectively.

A known positive pair may enter the cosine-failure stratum only through a rule fixed using permitted development evidence, such as:

- the positive candidate's cosine rank is worse than a frozen rank threshold;
- the cosine score falls below a frozen threshold;
- cosine fails a frozen hard-negative ordering rule;
- cosine misses a frozen local-retrieval criterion.

The final confirmatory stratum must not be selected by searching for test cases where RELATE happens to perform well.

Low cosine alone is not a positive label. The relationship must be established independently of the frozen embedding and independently of the recovery model.

## External relation evidence

The target relation must come from evidence outside the embedding geometry.

For code, candidate sources include:

- functions that satisfy the same hidden behavioural tests;
- implementations linked to the same normalized specification;
- behaviour-preserving refactoring lineage;
- independently adjudicated duplicated business rules;
- multiple accepted solutions to one bounded programming task;
- externally measured control-flow, data-flow, side-effect or exception properties.

For writing, later candidate sources include:

- explicit author links between passages;
- sentence and chapter lineage;
- selected and rejected rewrites;
- declared argument, concept or narrative-function identities;
- blinded author or reader judgments.

Model-generated similarity labels may assist annotation, but they cannot be the sole ground truth for a claim that the model then appears to recover.

## Required evaluation strata

Option E discovery must include more than hidden positives.

### 1. Hidden positives

Externally verified related pairs that raw cosine ranks poorly.

### 2. Surface false positives

Pairs with high cosine but no target relationship, such as similar vocabulary, identifiers or boilerplate with different behaviour or meaning.

### 3. Easy positives

True relationships that raw cosine already retrieves. These test whether Option E damages cases where default geometry is sufficient.

### 4. True negatives

Pairs with neither cosine support nor the externally verified target relation.

### 5. Weak-signal cases

The target signal is recoverable only weakly or inconsistently.

### 6. Absent-signal cases

The target relation is not present in the frozen representation under the tested evidence procedure.

### 7. Out-of-family cases

The signal exists but is outside the declared operator or probe family, for example a nonlinear relation tested with a linear recovery family.

### 8. Shifted cases

The relationship appears supported during fitting or development but fails under repository, time, organization, style or generator shift.

These cases must not be collapsed into one generic low-confidence bucket.

## Relationship to Hallucination Energy

Option E and Hallucination Energy express related but opposite evidence problems.

### Hallucination Energy

Hallucination Energy asks whether a generated claim contains semantic content outside the span of its attached evidence.

```text
output exceeds evidence
  -> measure unsupported semantic residual
  -> reject, qualify or seek more evidence
```

### Option E

Option E asks whether a default similarity geometry fails to expose relational evidence that remains recoverable from the frozen representation.

```text
default geometry underuses evidence
  -> measure supported relational residual
  -> recover, qualify or refuse
```

The concise relationship is:

> Hallucination Energy measures semantic content unsupported by attached evidence; RELATE Option E measures relational evidence supported by a frozen representation but underexposed by its default geometry.

They are not exact mathematical inverses. Hallucination Energy begins with an explicit evidence set. Option E learns or executes a relation-specific recovery mechanism from external labels, which creates shortcut and misbinding risks. Option E therefore requires hard negatives, absent-signal cases, out-of-family controls, shift tests, calibration and direct learned baselines.

## Option E scientific question

The programme-level question is:

> Among query–candidate pairs for which raw cosine geometry is uninformative or misleading, can a relation-specific executor recover externally verified relationships, and can calibrated support distinguish genuine hidden signal from weak, absent, out-of-family or shifted signal more effectively than strong calibrated alternatives at matched coverage?

This programme question is not yet a confirmatory claim. The exact relation, dataset, thresholds, material margin and primary metric must be frozen later.

## Option E stages

Option E uses named stages rather than C0/C1 or the historical E00/E01 identifiers.

```text
E-DISCOVERY
  bounded mechanism, stratum and discriminating-power discovery

E-CONFIRM
  separately frozen one-shot confirmation, only if justified
```

### E-DISCOVERY

E-DISCOVERY may learn and compare candidate mechanisms on permitted development roles. It cannot promote `E-RECOVER-001`.

It must answer:

1. Which externally defined relation will be tested first?
2. Can a non-degenerate cosine-failure stratum be constructed without test-set selection?
3. Which primitive or relational evidence objects are recoverable?
4. Which support representation distinguishes strong, weak, absent, out-of-family and shifted cases?
5. Does propagated or structured support have headroom over strong direct alternatives?
6. Which metrics describe useful retrieval rather than only global pairwise ordering?
7. Can one mechanism and one decision rule be specified precisely enough for independent recomputation?

E-DISCOVERY must end with exactly one outcome:

```text
E_CONFIRMATION_JUSTIFIED
E_CONFIRMATION_NOT_JUSTIFIED
E_DATA_FIREWALL_FAILED
E_BUDGET_EXHAUSTED
```

`E_CONFIRMATION_JUSTIFIED` selects a hypothesis for confirmation. It is not a scientific success result.

### E-CONFIRM

E-CONFIRM may begin only after a documentation-only confirmatory contract is reviewed and merged.

The contract must freeze:

- the target relation and external label source;
- the frozen representation;
- the exact cosine-failure rule;
- the recovery mechanism;
- the support object and calibration procedure;
- the query and candidate construction;
- the direct and modular baselines;
- accepted, qualified and refused outcomes;
- risk, coverage and retrieval metrics;
- matched-coverage comparison;
- material margin;
- final reserve selection;
- primary and secondary decision rules;
- independent recomputation boundary;
- permitted publication language for every outcome.

E-CONFIRM runs once. A failed primary rule cannot be rescued by secondary metrics under the same identifier.

## Required baselines

E-DISCOVERY must implement or faithfully represent at least:

1. raw cosine similarity;
2. raw Euclidean distance;
3. a normalized or whitened geometry baseline where appropriate;
4. independent calibrated support for each primitive relation;
5. the candidate propagated or structured support mechanism;
6. a directly trained compound or pair model with its own conformal or selective wrapper;
7. an uncalibrated confidence diagnostic;
8. an oracle-relation diagnostic;
9. an oracle-support or attainable-headroom diagnostic.

For a developer-facing code study, lexical and AST-only retrieval baselines should also be included.

A direct model is not an inconvenience to be weakened. It is the strongest simple explanation for why supervised relation recovery might work.

## Required measurements

Option E must report both recovery and refusal behaviour.

### Recovery

- hard-negative triplet or pairwise ordering accuracy;
- recall@1, recall@5 and recall@10;
- mean reciprocal rank;
- average precision or nDCG when multiple positives exist;
- oracle-neighbour regret;
- performance specifically within the cosine-failure stratum;
- performance on high-cosine false positives;
- repository, time or domain-transfer breakdown.

### Support and refusal

- selective risk against coverage;
- risk at frozen coverage points;
- coverage at frozen risk limits;
- false-support rate;
- false-refusal rate;
- support calibration error;
- accepted-case retrieval quality;
- absent-signal false acceptance;
- out-of-family false acceptance;
- shift survival;
- oracle headroom;
- gap from the strongest calibrated direct baseline.

Global triplet accuracy alone is insufficient.

## New data firewall

Option E must create fresh role identities.

```text
E fit
E iteration
E selection
E confirmation calibration reserve
E confirmation test reserve
```

Rules:

1. The final confirmation roles remain unseen during E-DISCOVERY.
2. The final confirmation rows are selected only after the E-CONFIRM contract merges.
3. Option B repositories used in its canonical selected manifests remain excluded where the new contract requires independent repository evidence.
4. Option C protected role identities and reserves are not renamed or reused as Option E evidence.
5. Every allocation, overlap decision and exclusion is committed and hashed before model fitting.
6. If the available corpus cannot support a non-degenerate cosine-failure stratum, E-DISCOVERY must stop rather than relax the definition after inspection.

## Candidate and discovery records

E-DISCOVERY requires:

- an append-only candidate registry;
- an append-only discovery ledger;
- complete retention of failed and superseded mechanisms;
- source and configuration identities;
- explicit expected failure modes;
- a record of every change made after observing E iteration evidence;
- closure of the candidate set before E selection evidence is accessed.

Unexpected observations may influence a later E-CONFIRM contract only when recorded before that contract freezes. They cannot be described as confirmed findings.

## Proposed claim

The proposed claim identifier is:

```text
E-RECOVER-001
```

Proposed claim language:

> In a preregistered cosine-failure stratum over a frozen representation, relation-specific recovery combined with calibrated support can identify externally verified relationships while refusing unsupported, out-of-family or shifted cases more effectively than the strongest registered calibrated baseline at matched coverage.

This language is intentionally broad enough to define the programme and too broad to publish without a later relation-specific E-CONFIRM contract. The confirmatory contract must narrow it to one dataset, relation, representation, query form and primary metric.

## Strong failure outcomes

Option E should be considered informative even when it fails.

Valid negative conclusions include:

- the frozen representation contains no useful recoverable evidence in the registered cosine-failure stratum;
- relation-specific recovery improves scores but not useful retrieval;
- the direct compound model matches or exceeds the modular executor;
- calibrated support cannot distinguish genuine recovery from absent or out-of-family signal;
- gains disappear under repository or time shift;
- the cosine-failure stratum is too small, unstable or selection-sensitive for confirmation;
- the proposed mechanism has no attainable headroom over strong baselines.

A failure closes or narrows `E-RECOVER-001`. It does not invalidate `B-PREM-001`.

## Scientific nonclaims

Until E-CONFIRM succeeds, RELATE must not claim that:

- low cosine implies hidden useful information;
- a high recovered score proves the requested relation exists;
- the embedding contains every relation relevant to the domain;
- primitive probes reveal the encoder's internal reasoning process;
- modular recovery is superior to direct supervision;
- a support score is calibrated because it is interpretable;
- Option B proved conceptual retrieval;
- the Hallucination Energy analogy establishes mathematical equivalence;
- results in code transfer to writing.

## First implementation slice

The next implementation must build neutral Option E foundations before fitting a preferred mechanism.

### Stage 1 — records and contracts

Implement typed records for:

- external relation labels;
- query and candidate identities;
- frozen representation identity;
- raw-geometry scores;
- cosine-failure membership and reason;
- recovery scores;
- primitive support records;
- compound support records;
- accepted, qualified and refused decisions;
- metric and stratum summaries.

### Stage 2 — cosine-failure stratum builder

Implement a deterministic builder that:

- consumes only permitted development roles;
- applies a frozen or explicitly versioned threshold rule;
- records ranks, scores and membership reasons;
- supports hidden positives, surface false positives, easy positives and true negatives;
- refuses uncommitted data or changed representation identities;
- produces immutable manifests and overlap checks.

### Stage 3 — baseline evaluator

Implement the evaluator before the novel method:

- raw cosine;
- raw Euclidean;
- local retrieval metrics;
- hard-negative construction;
- direct pair or compound baseline interface;
- selective-risk and coverage interface;
- oracle and attainable-headroom diagnostics.

### Stage 4 — support interfaces

Implement capability interfaces for:

- primitive calibration;
- independent primitive abstention;
- compound support propagation;
- direct-model calibration;
- refusal policy;
- out-of-family and shift diagnostics.

### Stage 5 — E-DISCOVERY workflow

Only after the records, strata, baselines and support interfaces are reviewed should the project implement candidate mechanisms and access E iteration evidence.

The first implementation PR must stop before:

- accessing any E selection or confirmation reserve evidence;
- selecting a winning propagation mechanism;
- freezing an E-CONFIRM metric or margin;
- publishing a scientific result;
- altering Option B or historical Option C artifacts.

## Suggested capability boundaries

Scientific identifiers belong in workflow and evidence records. Reusable implementation should remain capability-based.

A likely direction is:

```text
src/relate/domain/relational_recovery.py
src/relate/evaluation/cosine_failure.py
src/relate/evaluation/retrieval.py
src/relate/evaluation/selective.py
src/relate/support/primitive.py
src/relate/support/compound.py
src/relate/support/refusal.py
src/relate/workflows/option_e/
tests_current/domain/
tests_current/evaluation/
tests_current/support/
tests_current/workflows/option_e/
```

These paths are directional. Empty packages should not be created before their first coherent capability exists.

## Evidence required before any E finding

Before E-DISCOVERY execution:

```text
CLAIMS.md proposed row
Option E discovery contract
external relation-label contract
representation identity
allocation and overlap commitments
cosine-failure definition
baseline and metric definitions
candidate-registry schema
discovery-ledger schema
exit outcomes
```

During execution:

```text
append-only trace
candidate versions
configuration commitments
input, prediction and manifest hashes
environment and source identity
failed and superseded candidate retention
```

After E-DISCOVERY:

```text
compact exploratory result
human-readable checkpoint
one explicit E-DISCOVERY outcome
claim-ledger update
no confirmatory language
```

After a permitted E-CONFIRM run:

```text
compact confirmatory result
independent primary recomputation
claim-ledger decision
explicit support, null or closure conclusion
bounded publication language
```

## Immediate next action

The next repository stage is **Option E foundation implementation**:

1. add the Option E proposed claim and close the unexecuted C confirmatory route;
2. implement external relation-label and query/candidate identity records;
3. implement the deterministic cosine-failure stratum contract and builder;
4. implement raw retrieval and selective-evaluation interfaces;
5. test identity, overlap, immutability and refusal invariants;
6. stop before mechanism fitting or protected evidence access.

## Final principle

RELATE should not ask only:

> Can another learned score beat cosine?

Option E asks:

> When cosine fails, what independently verified relational evidence remains in the representation, what simpler model could explain the recovery, how do we know the evidence is supported, and when must the system refuse to act?

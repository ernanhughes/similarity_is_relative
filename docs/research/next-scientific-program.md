# Next Scientific Programme

Date: 2026-08-04  
Status: active Option E roadmap; does not itself freeze an E-CONFIRM contract

## Executive decision

RELATE has enough architecture and enough bounded evidence to return to scientific implementation.

The next work is not another weighted-score-fusion experiment and not a continuation under Option C, D2 or the historical E00/E01 identifiers.

The active route is:

```text
Option E foundation
  -> E-DISCOVERY contract and fresh allocation
  -> bounded E-DISCOVERY execution
  -> one explicit discovery outcome
  -> E-CONFIRM contract only if justified
  -> one-shot E-CONFIRM
  -> stop, close, narrow or permit one bounded application pilot
```

The governing programme document is:

- [`cosine-failure-and-relational-recovery.md`](cosine-failure-and-relational-recovery.md)

## Programme A — Option E foundation

### Scientific question

> When raw cosine similarity is uninformative for an externally verified relationship, can RELATE recover evidence of that relationship from the frozen representation, and can calibrated support distinguish genuine hidden signal from weak, absent, out-of-family or shifted signal more effectively than strong calibrated alternatives?

The first implementation stage builds the machinery required to ask that question without yet choosing a winning mechanism.

## A0 — records and identities

Implement typed, strictly validated records for:

- external relation labels;
- query identity;
- candidate identity;
- relation identity and version;
- frozen representation identity;
- raw cosine and Euclidean score records;
- cosine-failure membership and reason;
- recovered relation scores;
- primitive support;
- compound support;
- accepted, qualified and refused decisions;
- stratum summaries;
- retrieval and selective metrics.

Every record must support deterministic serialization, commitment and strict parsing.

### Required invariants

- a relation label cannot be generated solely from the tested embedding;
- a query and candidate cannot silently change representation identity;
- cosine-failure membership must record the exact rule and parameters;
- a recovered score cannot be interpreted as support;
- a refusal decision must retain the support evidence that caused it;
- records from historical Option C cannot be parsed as Option E records merely by changing an identifier.

## A1 — deterministic cosine-failure strata

Build the opportunity set before fitting a preferred recovery method.

The stratum builder must represent at least:

1. hidden positives;
2. high-cosine surface false positives;
3. easy positives;
4. true negatives.

Later E-DISCOVERY regimes must also represent:

5. weak signal;
6. absent signal;
7. signal present but outside the declared operator family;
8. distribution shift.

### Membership rules

A positive may enter the cosine-failure stratum only through a versioned prospective rule such as:

- cosine rank worse than frozen `K`;
- cosine score below a frozen threshold;
- failure of a frozen hard-negative ordering condition;
- failure of a frozen local-retrieval condition.

The builder must record:

- raw score;
- raw rank;
- rule version;
- membership reason;
- relation-label provenance;
- query and candidate commitments;
- representation identity;
- source-role identity.

No final confirmation example may be selected because RELATE later performs well on it.

## A2 — baseline evaluator before recovery models

Implement the evaluator before implementing the proposed novel method.

### Raw and retrieval baselines

- raw cosine;
- raw Euclidean;
- normalized or whitened geometry where appropriate;
- lexical retrieval for code or text applications;
- AST-only or structural retrieval for code applications;
- direct pair, triplet or compound model interface;
- metric-learning baseline interface;
- oracle relation diagnostic.

### Retrieval metrics

- hard-negative triplet or pairwise accuracy;
- recall@1, recall@5 and recall@10;
- mean reciprocal rank;
- average precision or nDCG where multiple positives exist;
- oracle-neighbour regret;
- performance inside the cosine-failure stratum;
- performance on high-cosine false positives;
- repository, time or domain breakdown.

Global triplet accuracy alone is not sufficient.

## A3 — selective and support interfaces

Implement capability boundaries for:

- primitive calibration;
- independent primitive abstention;
- compound support propagation;
- direct-model calibration;
- accepted, qualified and refused outcomes;
- false-support and false-refusal calculation;
- risk–coverage curves;
- risk at frozen coverage;
- coverage at frozen risk;
- calibration diagnostics;
- out-of-family diagnostics;
- shift diagnostics;
- oracle-support headroom.

These should be interfaces and neutral evaluators first. The first PR must not encode one preferred Option E mechanism as though it were already selected.

## A4 — evidence and workflow boundaries

Option E should reuse stable evidence and workflow capabilities while preserving scientific identity.

Likely capability direction:

```text
relate.domain.relational_recovery
  -> relation labels, queries, candidates and decisions

relate.evaluation.cosine_failure
  -> raw geometry, stratum construction and summaries

relate.evaluation.retrieval
  -> local and global retrieval metrics

relate.evaluation.selective
  -> risk, coverage and calibration metrics

relate.support
  -> primitive, compound and refusal interfaces

relate.workflows.option_e
  -> Option E orchestration and evidence publication
```

The capability packages must not import historical experiment runners. Historical modules may later adapt to clean capabilities, never the reverse.

## First implementation PR boundary

The first Option E implementation PR should contain only:

1. domain records and parsers;
2. deterministic commitments;
3. cosine-failure rule models;
4. stratum membership and summary logic;
5. raw retrieval metrics;
6. selective-evaluation interfaces;
7. evidence schemas;
8. unit and property tests.

It must stop before:

- fitting primitive recovery models;
- fitting a direct compound model;
- selecting a support propagation method;
- accessing E selection evidence;
- selecting E confirmation rows;
- writing an E-CONFIRM contract;
- publishing a scientific result.

## Programme B — E-DISCOVERY

E-DISCOVERY begins only after a prospective discovery contract and new data allocation are reviewed.

### New data roles

```text
E fit
E iteration
E selection
E confirmation calibration reserve
E confirmation test reserve
```

### Firewall requirements

- final confirmation roles remain unseen during discovery;
- final confirmation rows are selected only after the E-CONFIRM contract merges;
- Option B canonical repositories are excluded where the new contract requires independent repository evidence;
- historical Option C roles and reserves are not renamed or reused;
- repository, file and row overlap checks are committed before model fitting;
- a non-viable cosine-failure stratum causes a stop rather than post-hoc relaxation.

### Required candidate families

At minimum, E-DISCOVERY must faithfully compare:

1. independent calibrated support for primitive relations;
2. at least one propagated or structured support candidate;
3. a directly trained relation or compound model with its own calibrated selective wrapper;
4. an uncalibrated confidence diagnostic;
5. an oracle relation diagnostic;
6. an oracle-support headroom diagnostic.

Permitted support families may include:

- coordinate-wise worst support;
- interval or set propagation;
- joint residual or nonconformity support;
- sampling-based uncertainty propagation;
- learned post-hoc support combination, separated from the direct relation baseline.

Every candidate version must be registered before first evaluation and retained after rejection or supersession.

### Required regimes

- all required relations strongly supported;
- one relation weakly supported;
- one relation absent;
- one relation present but out of family;
- one relation shifted at evaluation;
- contradictory or empty compound support;
- high recovered score with weak support;
- high cosine with externally false relation.

### Required metrics

- selective risk against coverage;
- false-support rate;
- false-refusal rate;
- calibration error;
- accepted-case retrieval quality;
- cosine-failure recovery performance;
- high-cosine false-positive rejection;
- out-of-family false acceptance;
- shift survival;
- direct-model comparison;
- oracle headroom.

### E-DISCOVERY outcome

Exactly one outcome is permitted:

```text
E_CONFIRMATION_JUSTIFIED
E_CONFIRMATION_NOT_JUSTIFIED
E_DATA_FIREWALL_FAILED
E_BUDGET_EXHAUSTED
```

`E_CONFIRMATION_JUSTIFIED` requires:

- one target relation and stratum can be defined precisely;
- one recovery and support mechanism can be specified without unresolved ambiguity;
- the regime is non-degenerate;
- strong baselines are faithful;
- attainable headroom exists;
- final reserve selection can remain deferred;
- a meaningful primary margin can be frozen;
- independent recomputation is feasible.

E-DISCOVERY results are exploratory. They cannot support `E-RECOVER-001`.

## Programme C — E-CONFIRM

E-CONFIRM may begin only after `E_CONFIRMATION_JUSTIFIED` and a documentation-only contract PR.

The contract must freeze:

- external relation definition and label source;
- frozen representation;
- cosine-failure rule;
- query and candidate construction;
- selected recovery method;
- selected support representation;
- calibration method;
- direct and modular baselines;
- accepted, qualified and refused semantics;
- primary selective metric;
- matched-coverage comparison;
- material margin;
- secondary retrieval metrics;
- tie and empty-support handling;
- final reserve-selection algorithm;
- independent recomputation implementation boundary;
- permitted publication language for every outcome.

### Required failure capability

E-CONFIRM must fail when:

- the recovery method does not outperform the strongest registered baseline under the frozen primary rule;
- the gain appears only because coverage is lower;
- the direct calibrated relation model matches or exceeds the method;
- high relation scores receive false support in absent or out-of-family cases;
- support fails under the registered shift;
- local retrieval remains unusable despite pairwise improvement;
- the primary result cannot be independently recomputed.

### Consequences

```text
E-CONFIRM FAILS
  -> close or narrow E-RECOVER-001;
  -> preserve B-PREM-001;
  -> publish the negative result and evidence record.

E-CONFIRM PASSES
  -> permit one bounded real-domain application pilot;
  -> do not claim generality across relations, models or domains.
```

## Programme D — first code application

The preferred first Option E application is conceptual duplicate retrieval under externally checkable equivalence.

### Candidate question

> Among function pairs whose external behaviour or specification establishes equivalence but whose frozen code-embedding cosine is weak, can Option E recover the relationship and refuse unsupported alternatives better than strong direct and retrieval baselines?

### Candidate ground truth

- hidden behavioural tests;
- normalized specifications;
- accepted implementations of the same bounded task;
- behaviour-preserving refactoring lineage;
- independently adjudicated duplicate business rules.

### Mandatory hard negatives

- same identifiers, different behaviour;
- similar boilerplate, different side effects;
- same API vocabulary, different role;
- same control structure, different transformation;
- copied code with a material behavioural change.

This study should be designed during Option E foundation but not executed before E-DISCOVERY has a valid contract and firewall.

## Programme E — writing after code

Writing should begin with dataset construction, not with a model claim.

The first relation should be narrow, for example:

> Two passages express the same author-defined concept despite differing topic, vocabulary or narrative setting.

Required evidence includes author annotations, lineage, selected and rejected revisions, declared scene or argument functions and blinded judgments.

Hard negatives must include same-topic different-claim passages, similar vocabulary with opposing conclusions and model-retrieved pairs rejected by the author.

A writing experiment receives a new contract and does not inherit a code result.

## Programme F — publication strategy

### Paper 1 — methodological case study

The first draft already exists:

- [`docs/papers/when-the-experiment-passes-but-the-claim-fails.md`](../papers/when-the-experiment-passes-but-the-claim-fails.md)

It combines E01 closure, Option B, independent recomputation and evidence-first claim governance.

### Paper 2 — Option E recovery and refusal

Only an E-CONFIRM result can support a paper centred on cosine-failure recovery and calibrated refusal. A negative result remains publishable when the protocol, baselines and evidence are strong.

### Paper 3 — application study

A code or writing paper must stand on its own labels, contract and baselines. Option B may motivate the study but cannot prove the application claim.

## Required artifacts for Option E

### Before E-DISCOVERY

```text
CLAIMS.md proposed row
Option E discovery contract
external relation-label contract
representation identity
fresh allocation and overlap commitments
cosine-failure rule
baseline definitions
metric definitions
candidate-registry schema
discovery-ledger schema
exit outcomes
```

### During E-DISCOVERY

```text
append-only trace
candidate versions
configuration commitments
input, label, prediction and manifest hashes
environment and source identity
failed and superseded candidate retention
```

### After E-DISCOVERY

```text
compact exploratory result
human-readable checkpoint
one explicit discovery outcome
claim-ledger update
no confirmatory claim language
```

### After E-CONFIRM

```text
compact confirmatory result
independent primary recomputation
claim-ledger decision
explicit support, null or closure conclusion
bounded publication language
```

## Immediate next actions

1. Review and merge the Option E documentation decision.
2. Implement Option E records, commitments and strict parsers.
3. Implement the deterministic cosine-failure stratum models and builder.
4. Implement raw retrieval and selective-evaluation interfaces.
5. Add identity, overlap, immutability and refusal-invariant tests.
6. Stop before mechanism fitting.
7. Draft the E-DISCOVERY contract only after the neutral foundation is reviewed.

## Final principle

RELATE should not ask only:

> Can another learned score beat cosine?

It should ask:

> When cosine fails, what independently verified relational evidence remains in the representation, what simpler baseline could explain the recovery, how do we know the evidence is supported, and when must the system refuse to act?

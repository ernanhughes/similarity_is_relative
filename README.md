# Similarity Is Relative

RELATE is evidence-first research into whether frozen representations contain useful relational signals that their default similarity geometry fails to expose—and whether those signals can be queried, verified and rejected when unsupported.

Claims begin as falsifiable questions, become executable contracts and are promoted only after committed evidence, explicit decision rules and appropriately classified verification.

## Current state

```text
E01                       CLOSED
Option B                  PASSED AND INDEPENDENTLY VERIFIED
C0 v1                     PRESERVED; EXPLORATORY AND DESCRIPTIVE ONLY
C0-D1                     COMPLETE
C0-D1.1                   COMPLETE; FAMILY CLASSIFICATION INCONCLUSIVE
family protocol           FROZEN
canonical family graph    NOT IMPLEMENTED OR EXECUTED
allocation                UNCHANGED
C0 selection              BLOCKED; ROW CONTENTS NOT ACCESSED
C1 reserve                BLOCKED; ROW CONTENTS NOT ACCESSED
D2                         NOT STARTED
architecture reset        IN PROGRESS
historical tests           QUARANTINED
```

The published C0 v1 artifact remains immutable. The family-connected allocation protocol is frozen, but its canonical graph runner is deliberately deferred until RELATE has clean domain, persistence, workflow and CLI boundaries.

The architecture reset does **not** advance the scientific state machine.

## Start here

### Architecture reset

- [Current system map](docs/architecture/current-system-map.md)
- [Refactor preservation contract](docs/architecture/refactor-preservation-contract.md)
- [ADR 001: capability-based packages](docs/architecture/decisions/001-capability-based-packages.md)
- [Historical-test quarantine](tests_current/README.md)

### Current C0 integrity state

- [C0-D remediation plan](docs/audits/option-c0-d-remediation-plan-2026-08-02.md)
- [D1 audit result](artifacts/canonical/option-c0/review-v1/d1-integrity/option-c0-d1-integrity-audit-v1.json)
- [D1.1 overlap classification](artifacts/canonical/option-c0/review-v1/d1-integrity/option-c0-d1-overlap-classification-v1.json)
- [Frozen family-connected allocation protocol](docs/protocols/option-c0-family-connected-allocation-protocol-v1.md)
- [Family protocol runbook](docs/runbooks/option-c0-family-connected-allocation.md)
- [Family protocol contract](artifacts/canonical/option-c0/review-v1/family-protocol-v1/option-c0-family-connected-allocation-contract-v1.json)
- [Original C0 v1 result](artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json)

### Option B supported premise

- [Human-readable checkpoint](docs/results/option-b-real-code-premise-checkpoint-v1.md)
- [Frozen experiment contract](docs/experiments/08-option-b-real-code-premise-test.md)
- [Canonical evidence](artifacts/canonical/option-b/method-evaluation-v1/)

### Project rules

- [Claim ledger](CLAIMS.md)
- [Option C0 discovery and confirmation protocol](docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md)
- [Publication and kill-test decision](docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md)

## Option B result

Option B tested repository-separated Python functions, frozen `microsoft/codebert-base` embeddings and three AST-derived primitives:

- cyclomatic complexity;
- maximum control nesting depth;
- distinct call-site count.

```text
raw cosine:                0.532458984375
raw Euclidean:             0.533314453125
predicted primitive model: 0.732851562500
best-raw gap:              0.199537109375
outcome:                   REAL_PREMISE_SUPPORTED
```

The promoted claim remains narrow:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed the frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

Option B does **not** establish general composition, semantic binding, calibrated refusal, production utility or superiority to direct compound prediction.

## Why the architecture reset is happening

The repository evolved as a sequence of experiments. Over time, experiment-labelled modules accumulated data loading, embeddings, model fitting, calibration, diagnostics, provenance, persistence, recovery and command-line behaviour.

The active C0 command now passes through several corrective wrappers that replace module globals at runtime. The family protocol and D1 audit are also very large modules combining domain rules, persistence, orchestration and publication.

New code will be organized by stable capability:

```text
domain
data
representations
models
support
evaluation
family
evidence
workflows
cli
```

Historical experiment modules and canonical artifacts remain available as provenance and compatibility references.

## Next implementation stage

After the architecture foundation is reviewed, the first code stage is neutral evidence infrastructure:

- canonical JSON serialization;
- hashing;
- atomic publication;
- immutable overwrite refusal;
- manifest helpers;
- SQLite pragma and identity helpers.

It must not execute the family graph, alter scientific calculations, access hidden rows or regenerate canonical evidence in place.

## Validation status

The historical `tests/` suite is preserved but disabled during the reset. New tests are written under `tests_current/` as stable capability interfaces emerge.

A passing `pytest` currently means only that the active reset-era suite passed. It does **not** mean the complete historical system has been behaviourally reverified.

```bash
python -m pip install -e ".[dev,option-b]"
ruff check .
pytest
```

## Publication rule

Every sentence beginning with **“we found”**, **“RELATE improves”**, **“the embedding contains”**, or **“the operator supports”** must map to:

1. a row in [`CLAIMS.md`](CLAIMS.md);
2. a committed reproduction command;
3. a committed compact result record;
4. hashes of evidence-bearing artifacts;
5. a declared falsification or revision condition.

C0 measurements remain exploratory and cannot support an Option C publication claim.

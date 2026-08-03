# RELATE Current System Map

Date: 2026-08-03

Status: architecture reset in progress; historical tests quarantined; scientific execution paused.

## Purpose

This document records the implementation that exists before the architecture reset. It describes the current runtime rather than the desired design. It is intentionally separate from the scientific contracts and canonical evidence.

The repository began as an experiment workspace. Successive experiments, corrections, audits and recovery layers became permanent runtime structure. The result preserves scientific history well, but the software boundaries now follow chronology rather than responsibility.

## Current governing research state

```text
E01                       closed
Option B                  passed and independently verified
C0 v1                     preserved, exploratory and descriptive only
C0-D1                     completed
C0-D1.1                   completed; family classification inconclusive
family protocol           frozen
canonical family graph    not implemented or executed
allocation                unchanged
C0 selection              blocked and not accessed
C1 reserve                blocked and not accessed
D2                         not started
```

The architecture reset does not change any of those states.

## Current package shape

The reusable package is dominated by experiment-labelled modules:

```text
src/relate/
├── experiments/
│   ├── e00*.py
│   ├── e01*.py
│   ├── option_b_*.py
│   └── option_c0_*.py        (historical facades; re-export from relate.family.*)
├── family/                   (Stage 2A domain + Stage 2B persistence)
│   ├── __init__.py
│   ├── models.py             (EDGE_SCHEMA_ID, EdgeRule, AllocationEntry, ManualReviewDisposition,
│   │                          EvidenceCandidate, EvidenceEdge, SourceEvidenceRecord)
│   ├── rules.py              (EDGE_RULES, taxonomy tuples, edge_rules_contract)
│   ├── repositories.py       (normalize_repository, allocation operations, canonical constants)
│   ├── sources.py            (source-evidence construction, payload firewall, public_metadata_snapshot)
│   ├── edges.py              (candidate, disposition, edge construction and validation)
│   ├── graph.py              (Stage 2D — UnionFind, component_id, build_components:
│   │                          pure connected-component construction)
│   ├── commitments.py        (Stage 2D — component_commitment, edge_commitment:
│   │                          graph-specific SHA-256 commitments)
│   ├── outcome.py            (Stage 2D — graph_completeness, family_graph_outcome:
│   │                          bounded completeness and outcome decision)
│   └── store.py              (Stage 2B persistence + Stage 2D — component-membership
│                              and phase-commitment APIs, deterministic list readers)
├── evidence/
│   ├── canonical_json.py
│   ├── hashing.py
│   ├── atomic_io.py
│   ├── immutable.py
│   └── sqlite.py
├── workflows/                 (Stage 2C — generic, domain-neutral workflow kernel)
│   ├── __init__.py
│   ├── errors.py              (WorkflowDefinitionError, WorkflowCommitmentError,
│   │                           WorkflowExecutionError, WorkflowResumeError)
│   ├── models.py               (JsonValue, WorkflowContext, WorkflowDefinition,
│   │                           StepStatus, StepResult, StepExecutionRecord,
│   │                           WorkflowRunResult, WorkflowCheckpoint)
│   ├── step.py                 (WorkflowStep protocol)
│   ├── commitments.py           (deterministic run/step commitment chain)
│   ├── trace.py                 (WorkflowTraceEvent, WorkflowTraceSink, InMemoryTraceSink)
│   └── runner.py                (WorkflowRunner: ordering, blocking, failure, resume)
├── verification/
├── publication/
└── audits/
```

`relate.workflows` imports only the Python standard library and
`relate.evidence`:

```text
relate.workflows
    -> relate.evidence
```

It contains no family-graph workflow, no canonical-graph execution, and no
persistence. It must never import `relate.experiments`, `relate.family`, or
`relate.cli` (enforced by `tests_current/workflows/test_dependency_boundaries.py`).
The future composition direction, once a family workflow exists, is:

```text
family workflow composition
    -> relate.workflows
    -> relate.family
    -> relate.evidence
```

`relate.workflows.commitments` and `relate.family.commitments` (Stage 2D)
are deliberately separate and must not be conflated: the former binds
workflow execution steps and results; the latter binds scientific graph
records (resolved edges, connected components). Neither imports the other.

Most console commands point directly into `relate.experiments`. Data reconstruction, identity validation, embeddings, model fitting, support logic, diagnostics, evidence writing, recovery and command-line parsing are therefore exposed as experiment implementation details.

## Current Option C0 execution chain

The public C0 discovery command currently resolves through a chain of corrective wrappers:

```text
relate-option-c0-discover
    -> option_c0_canonical_recovery_entrypoint
    -> option_c0_recovery_entrypoint
    -> option_c0_diagnostic_entrypoint
    -> option_c0_discovery_entrypoint
    -> option_c0_discovery_runner
```

The wrappers replace module-level callables at runtime and restore them afterward. They correct or add:

- fixed-batch cache recovery;
- progress reporting;
- diagnostic argument ordering;
- source versus embedding identity separation;
- embedding implementation selection.

This preserved the reviewed historical run, but it is not an acceptable basis for new code. New workflows must use explicit dependency construction rather than monkey-patching module globals.

## Current high-risk modules

### `option_c0_family_connected_protocol.py`

As of Stage 2A this module re-exports pure family-domain symbols from `relate.family.*`.
As of Stage 2B it additionally re-exports `CACHE_SCHEMA_ID`, `FamilyGraphCache`, and
`FamilyGraphCacheIdentity` from `relate.family.store`. As of Stage 2D it additionally
re-exports `UnionFind`, `build_components`, `component_id` (from `relate.family.graph`)
and `family_graph_outcome`, `graph_completeness` (from `relate.family.outcome`) directly,
and keeps only thin wrappers for `component_commitment`/`edge_commitment` (from
`relate.family.commitments`) that supply the default `protocol_sha256`. It retains only
historical-only responsibilities:

- frozen protocol constants (`SCHEMA_ID`, D1 SHAs, allocation SHAs — `CACHE_SCHEMA_ID` now
  originates in `relate.family.store`);
- `default_cache_identity` (source-hash-sensitive wrapper around `make_cache_identity`;
  cannot move without changing its meaning — see migration-status.md Stage 2B);
- `protocol_contract` — full protocol contract assembly;
- frozen-input verification (`validate_frozen_protocol_inputs`, `validate_firewall_booleans`);
- atomic protocol publication (`write_protocol_contract`);
- CLI entry point.

These remaining responsibilities must be separated before the canonical family graph runner
is implemented. See Stage 2E (family input verification and explicit workflow composition).

### `option_c0_d1_integrity_audit.py`

This module currently contains:

- visible-row reconstruction;
- source and AST normalization;
- exact duplicate analysis;
- SimHash candidate generation and comparison;
- repository-family heuristics;
- resumable SQLite state;
- Git execution-source manifests;
- environment capture;
- decision orchestration;
- artifact publication;
- command-line parsing.

Its completed canonical artifact remains immutable. The implementation may later become a compatibility workflow over clean components.

### `option_c0_discovery_runner.py`

This module combines data reconstruction, partitioning, embeddings, model fitting, query transforms, candidates, baselines, diagnostics and artifact writing. Several later entrypoints modify its globals at runtime.

## Duplicated infrastructure

The following capabilities are implemented repeatedly across experiment modules:

- canonical JSON serialization;
- SHA-256 hashing;
- atomic JSON and directory publication;
- immutable overwrite refusal;
- source and artifact manifests;
- SQLite identity binding;
- retry-safe persistence;
- progress reporting;
- command-line setup;
- path and hash validation.

The first implementation extraction should consolidate these as evidence infrastructure without changing scientific calculations.

## Historical version families

The active source tree contains chronological implementation variants, including examples such as:

```text
option_b_identity.py
option_b_identity_v2.py

option_b_selection.py
option_b_selection_v2.py
option_b_selection_resilient.py

option_b_embedding.py
option_b_embeddings.py
option_b_embeddings_hardened.py
option_b_embedding_preflight.py
option_b_embedding_reproduction.py

option_c0_discovery_entrypoint.py
option_c0_diagnostic_entrypoint.py
option_c0_recovery_entrypoint.py
option_c0_canonical_recovery_entrypoint.py
```

These files remain part of the reproducibility record. New architecture must not use chronological suffixes as its primary abstraction.

## Current evidence and historical boundaries

The following areas are records, not implementation workspaces:

```text
artifacts/canonical/
docs/experiments/
docs/results/
docs/audits/
docs/research/
tests/
```

They may be indexed, referenced and verified, but must not be silently rewritten to fit the new architecture.

The historical `tests/` directory is quarantined. It is not active validation during the reset. New tests belong under `tests_current/` and should target stable capability interfaces.

## Desired dependency direction

The new system should converge on this dependency direction:

```text
cli
  -> workflows
      -> domain + data + representations + models + support + evaluation
          -> evidence infrastructure
```

Rules:

1. Domain modules do not import workflows, CLIs or experiment modules.
2. Evidence infrastructure does not know Option B, C0 or experiment identifiers.
3. Workflows orchestrate components but do not implement scientific primitives internally.
4. CLIs parse arguments and invoke workflows only.
5. Historical experiment modules may import clean modules as compatibility facades.
6. Clean modules must not import historical experiment modules.

## Target package map

```text
src/relate/
├── domain/
│   ├── records.py
│   ├── primitives.py
│   ├── queries.py
│   └── decisions.py
├── data/
│   ├── codesearchnet.py
│   ├── allocation.py
│   ├── repository_splits.py
│   └── deduplication.py
├── representations/
│   ├── interfaces.py
│   ├── codebert.py
│   ├── identities.py
│   └── cache.py
├── models/
│   ├── primitive_probes.py
│   ├── direct_compound.py
│   └── selection.py
├── support/
│   ├── conformal.py
│   ├── primitive.py
│   ├── compound.py
│   └── refusal.py
├── evaluation/
│   ├── retrieval.py
│   ├── selective.py
│   ├── risk_coverage.py
│   └── diagnostics.py
├── family/
│   ├── models.py
│   ├── rules.py
│   ├── sources.py
│   ├── validation.py
│   ├── graph.py
│   └── decisions.py
├── evidence/
│   ├── canonical_json.py
│   ├── hashing.py
│   ├── atomic_io.py
│   ├── manifests.py
│   ├── provenance.py
│   └── sqlite.py
├── workflows/
│   ├── option_b/
│   └── option_c0/
├── cli/
└── experiments/
    └── historical compatibility facades
```

This map is directional, not a requirement to create empty packages immediately. A package should appear only when its first coherent capability is extracted.

## Extraction order

1. Shared evidence infrastructure.
2. Family domain models and rules.
3. Family persistence adapter.
4. Family graph construction and decision logic.
5. Explicit family workflow and CLI.
6. Representation and identity infrastructure.
7. C0 workflow without runtime monkey patches.
8. Model, support and evaluation capabilities.
9. Historical compatibility facades and eventual retirement decisions.

## Immediate next implementation stage

**Stage 2E — Family input verification and explicit workflow composition**

Extract frozen-input and protocol-level firewall verification from the
historical module; create explicit family workflow steps; compose those
steps using `relate.workflows`; use the clean family domain, store, graph,
and outcome capabilities; support blocked review or metadata states; remain
noncanonical until separately authorized. Still no canonical family graph
execution or publication.

Previous immediate-next note (now completed as Stage 2D): `UnionFind`,
`build_components`, `component_id` moved to `relate.family.graph`;
`component_commitment`, `edge_commitment` moved to `relate.family.commitments`
(with explicit-`protocol_sha256` signatures and historical wrappers);
`graph_completeness`, `family_graph_outcome` moved to `relate.family.outcome`;
`relate.family.store` gained `put`/`get_component_memberships`,
`put`/`get`/`list_phase_commitments`, and deterministic list readers for
allocation repositories, evidence candidates, and resolved edges. No schema
change, no protocol payload or SHA change. See migration-status.md Stage 2D
and capability-continuity.md.

Previous immediate-next note (completed as Stage 2C): a domain-neutral
workflow kernel (`relate.workflows`) was created — explicit steps, immutable
context, deterministic commitments, injected tracing, blocked/failure/resume
semantics — without importing `relate.experiments` or `relate.family` and
without implementing any family-specific workflow step. See
migration-status.md Stage 2C and capability-continuity.md.

Previous immediate-next note (completed as Stage 2B): `FamilyGraphCache`,
`FamilyGraphCacheIdentity`, and `default_cache_identity`'s explicit constructor
(`make_cache_identity`) were extracted from `option_c0_family_connected_protocol` into
`relate.family.store` without executing the canonical graph or changing the protocol
payload or SHA. See migration-status.md Stage 2B and capability-continuity.md.

Previous immediate-next note (completed as Stage 2A): the family domain extraction
PR extracted pure family-domain capabilities from `option_c0_family_connected_protocol`
into `relate.family.*` without changing the protocol payload or SHA.

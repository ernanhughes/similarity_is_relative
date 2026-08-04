# RELATE Refactor Preservation Contract

Date: 2026-08-03

Status: prospective architecture-refactor contract.

## Purpose

RELATE is being reorganized from experiment-shaped code into capability-based modules. The reorganization may change internal Python paths, object boundaries and orchestration, but it must not silently change the scientific record or imply validation that has not occurred.

This contract governs every architecture-reset pull request until it is explicitly replaced.

## Refactor class

The architecture reset is a software reorganization, not a scientific experiment and not a result replay.

It may:

- create stable capability packages;
- move or copy implementation behind compatibility facades;
- replace hidden global mutation with explicit dependencies;
- consolidate generic infrastructure;
- introduce new tests under `tests/`;
- deprecate historical runtime entrypoints after an explicit migration decision.

It may not, without a separate prospective scientific or remediation contract:

- change a primitive definition;
- change a query or threshold;
- change a dataset role or repository allocation;
- change a candidate mechanism or baseline;
- change metric semantics;
- inspect C0 selection row contents;
- inspect or select C1 reserve rows;
- execute the canonical family graph;
- execute D2, D3, D4 or D5;
- promote, weaken or reinterpret a scientific claim.

## Immutable scientific record

The following are immutable during the reset:

```text
artifacts/canonical/
CLAIMS.md claim status and evidence identities
frozen experiment contracts
dated result checkpoints
audit results
published allocation manifests
candidate and discovery ledgers
published protocol identities
```

A refactor PR must not rewrite a canonical artifact merely because its generator moves.

If regenerated output differs, the difference is evidence of behaviour change. It must be investigated and classified; it must not be accepted as formatting cleanup.

## Frozen current state

```text
Option B outcome                         REAL_PREMISE_SUPPORTED
Option B independent verification       complete
C0 v1 artifact                          preserved; descriptive only
C0 diagnostic comparison                invalidated pending remediation
D1 audit                                complete
D1.1 family classification              inconclusive
family protocol                         frozen
canonical family graph                  not executed
allocation                              unchanged
C0 selection row contents               not accessed
C1 reserve row contents                 not accessed
D2                                      not started
historical tests                        quarantined
```

Architecture changes do not advance this state machine.

## Required PR classification

Every reset PR must declare one primary class:

1. `DOCUMENTATION_ONLY`
2. `INFRASTRUCTURE_EXTRACTION`
3. `DOMAIN_EXTRACTION`
4. `WORKFLOW_REPLACEMENT`
5. `COMPATIBILITY_MIGRATION`
6. `LEGACY_RETIREMENT`

The PR description must state:

- which production behaviour is intended to remain unchanged;
- which old modules remain authoritative during the PR;
- which new modules become authoritative after merge;
- which active tests exist under `tests/`;
- which historical tests or artifacts informed the migration;
- whether canonical regeneration was attempted;
- whether any scientific execution occurred.

## Dependency rule

The allowed long-term dependency direction is:

```text
cli -> workflows -> capabilities -> evidence infrastructure
```

Historical experiment modules may depend on clean capability modules while compatibility is retained.

Clean capability modules must not import historical experiment modules.

A new module under `domain`, `data`, `representations`, `models`, `support`, `evaluation`, `family`, `evidence`, `workflows` or `cli` may not use runtime monkey-patching as an integration mechanism.

## Compatibility rule

Compatibility is explicit and temporary.

A historical public command or import may remain available through a thin facade. A compatibility facade must:

- contain no new scientific algorithm;
- contain no copied implementation when delegation is possible;
- make the delegated clean component visible in the source;
- avoid replacing module globals at runtime;
- have a named retirement or review condition.

No new corrective wrapper may be added to the existing C0 entrypoint chain.

## Evidence-infrastructure rule

Generic infrastructure must be experiment-neutral.

The following belong in `relate.evidence` or another neutral infrastructure package:

- canonical serialization;
- hashing;
- atomic writes;
- immutable publication;
- manifest construction and verification;
- provenance records;
- SQLite connection, pragma and identity helpers.

These modules must not encode Option B, C0, D1, family-protocol or claim-specific decision rules.

## Behaviour comparison during the test quarantine

The historical test suite is disabled and cannot be cited as passing validation.

Until replacement tests exist, refactor PRs must use the strongest applicable combination of:

- direct source comparison;
- small deterministic characterization fixtures;
- contract regeneration in a temporary location;
- exact canonical JSON comparison;
- hash comparison;
- command import and argument-parsing checks;
- explicit code review of old-to-new delegation;
- new focused tests under `tests/`.

A green `pytest` means only that the active `tests/` suite passed.

## Regeneration policy

Canonical artifacts are not routinely regenerated during early extraction.

When a generator has been fully migrated, a dedicated compatibility check may regenerate output into a temporary noncanonical path and compare it to the committed artifact.

Permitted outcomes:

- exact equality;
- canonical equality after excluding fields already declared nondeterministic by the frozen contract;
- documented mismatch that blocks migration completion.

A mismatch may not be resolved by overwriting the canonical artifact.

## Source-identity policy

Some historical evidence binds exact implementation paths and commits. Moving code does not rewrite history.

The historical source manifest continues to identify the implementation that produced the historical result. New clean implementations receive new source identities only when used in a later authorised execution.

Do not alter historical manifests to claim that the new implementation produced an old result.

## Firewall preservation

Every refactor touching C0 data or workflow code must preserve these fail-closed properties:

```text
c0_selection row-content access = forbidden
c1_reserve row-content access    = forbidden
final C1 row selection           = forbidden
```

Infrastructure APIs should make allowed roles explicit rather than relying on callers to remember exclusions.

## Stop conditions

A refactor PR must stop and be reclassified if it discovers:

- changed scientific output;
- different row membership or order;
- different primitive values;
- different model predictions;
- different acceptance masks;
- different metric values;
- a firewall bypass;
- canonical hash drift;
- a previously unknown implementation or data-integrity defect.

Such a discovery must be recorded separately. It cannot be buried inside an architectural cleanup commit.

## Completion conditions for the reset

The architecture reset is complete only when:

- new scientific work no longer depends on `relate.experiments` implementations;
- public CLIs invoke explicit workflows;
- workflows receive explicit dependencies;
- no active runtime uses monkey-patching;
- stable capability modules have focused replacement tests;
- historical commands are either thin facades or explicitly retired;
- the canonical family graph runner can be implemented without adding logic to a god module;
- repository documentation names one authoritative current path for each capability.

## First authorised extraction

After this contract merges, the first authorised code stage is `INFRASTRUCTURE_EXTRACTION` for neutral evidence utilities only.

It must stop before changing family-domain rules, C0 model code, scientific diagnostics or canonical execution.

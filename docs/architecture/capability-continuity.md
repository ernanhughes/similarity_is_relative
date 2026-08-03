# RELATE Capability Continuity Ledger

Date: 2026-08-03

Status: living document, updated at each architecture-reset stage.

## Purpose

This ledger tracks the scientific process the family-connected allocation
protocol must continue to support while its implementation is reorganized
from `relate.experiments.option_c0_family_connected_protocol` into
capability-based packages. The architecture reset moves and reshapes code;
it does not remove, weaken, or informally replace any of the capabilities
below. Where a capability has not yet been extracted, that is recorded as a
known limitation rather than marked complete.

See also [current-system-map.md](current-system-map.md),
[refactor-preservation-contract.md](refactor-preservation-contract.md), and
[migration-status.md](migration-status.md) for the surrounding contract and
per-symbol migration record.

## Capability table

| # | Original capability | Historical implementation | Clean destination | Current status | Preservation evidence | Future workflow step | Known limitation |
|---|---|---|---|---|---|---|---|
| 1 | Verify frozen scientific inputs | `validate_frozen_protocol_inputs`, `validate_firewall_booleans` in `option_c0_family_connected_protocol.py` | historical module — pending later extraction | Unchanged | Source untouched by Stage 2B or 2C; hashes and firewall-boolean checks identical | A "verify frozen inputs" `WorkflowStep` can now be expressed explicitly: it would call the historical validators and return `StepResult.completed(...)` or `StepResult.blocked(...)` if a hash mismatches, using the Stage 2C kernel | Reads canonical artifact files directly; not yet behind a workflow-step interface |
| 2 | Bind a family run to exact identities | `default_cache_identity` (historical, source-hash sensitive) | `relate.family.store.FamilyGraphCacheIdentity` + `make_cache_identity` (**Stage 2B, this PR**) | **Complete** | `historical.FamilyGraphCacheIdentity is store.FamilyGraphCacheIdentity`; identical field names/order/`as_mapping()`; `default_cache_identity` still binds `sha256_file(__file__)` of the historical module; `tests_current/family/test_store_identity.py` | "bind run identity" step calling `make_cache_identity` with the workflow's own explicit source identity | `default_cache_identity` remains source-hash sensitive by design; a future workflow must supply its own executing-source identity, not inherit the historical file hash |
| 3 | Preserve the hidden-row firewall | `FORBIDDEN_PAYLOAD_PATTERNS` / `validate_payload_firewall` (moved to `relate.family.sources` in Stage 2A); `firewall_booleans` block in `protocol_contract()` (historical) | `relate.family.sources` (payload firewall, Stage 2A); protocol-level firewall verification remains historical | Partially complete | `tests_current/family/test_sources.py`; `protocol_contract()["firewall_booleans"]` values unchanged; protocol SHA unchanged | A "verify firewall" `WorkflowStep` can return `StepResult.blocked("hidden-row firewall field is true: ...")` using the Stage 2C blocked-execution contract instead of raising, making a firewall failure an honest blocked outcome rather than an exception | Not touched by Stage 2B or 2C; protocol-level firewall check is still inline in the historical module |
| 4 | Register allocation repositories without reading protected row contents | `FamilyGraphCache.put_allocation_repositories` / `put_canonical_allocation_manifest` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestAllocationRegistration`; validation delegated to `relate.family.repositories.validate_canonical_allocation_entries` (Stage 2A, unchanged) | "register allocation" step | `put_canonical_allocation_manifest` now reads its expected SHA-256 from `self.identity.allocation_manifest_sha256` instead of the historical module-global constant, to avoid the store importing `relate.experiments` — see migration-status.md for why this is behavior-preserving |
| 5 | Register bounded source evidence | `make_source_record` / `validate_source_record` (Stage 2A, `relate.family.sources`); `FamilyGraphCache.put_source_record` / `get_source_record` / `get_source_registry` | `relate.family.sources` (validation, Stage 2A) + `relate.family.store` (persistence, **Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestSourceRecordPersistence` | "register source evidence" step | None |
| 6 | Store evidence candidates | `FamilyGraphCache.put_evidence_candidate` / `get_evidence_candidate` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestEvidenceCandidatePersistence` | "record candidate" step | None |
| 7 | Store manual review dispositions | `FamilyGraphCache.put_manual_review_disposition` / `get_manual_review_disposition` / `get_final_disposition_for_candidate` | `relate.family.store.FamilyGraphCache` (Stage 2B) | **Complete** | `tests_current/family/test_store_records.py::TestManualReviewDispositionPersistence` | A "resolve required reviews" `WorkflowStep` can call `put_manual_review_disposition` and return `StepResult.blocked("manual review required")` (Stage 2C blocked-execution contract) when a disposition is still `UNRESOLVED`, rather than treating an incomplete review queue as an error | None |
| 8 | Store resolved family edges | `FamilyGraphCache.put_resolved_edge` / `get_resolved_edge` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestResolvedEdgePersistence` | "record resolved edge" step | None |
| 9 | Store connected-component memberships | `component_memberships` table schema only; no put/get method exists in the historical module either before or after Stage 2B | Table moved to `relate.family.store.FamilyGraphCache` schema (Stage 2B); no persistence API yet | **Schema only** | `tests_current/family/test_store_schema.py::test_component_memberships_composite_primary_key` | "record components" workflow step, composed via a `WorkflowStep` once the family store gains this API (Stage 2D or later) | **Gap, not introduced by Stage 2B or 2C**: there is no `put_component_memberships` / `get_component_memberships` method anywhere in the codebase today. A future stage must add one without inventing new graph science. The generic workflow kernel (Stage 2C) does not fill this gap — it only gives a future step a place to call such a method from |
| 10 | Record deterministic phase commitments | Implicit `phase_commitments` write inside `put_allocation_repositories` (phase `"initial_allocation"` only); no generic put/get phase-commitment method | Table + the one implicit write moved to `relate.family.store.FamilyGraphCache` (Stage 2B) | **Partial** | `tests_current/family/test_store_records.py::test_phase_commitment_recorded_after_allocation` | "record phase commitment" workflow step, once the family store gains a generic writer (Stage 2D or later) | **Gap, not introduced by Stage 2B or 2C**: only the allocation phase is auto-committed; there is no generic writer for arbitrary phases. `relate.workflows` (Stage 2C) introduces a *generic, in-memory* deterministic step-commitment chain (`StepExecutionRecord`, `step_input_commitment`, `step_output_commitment`) that is conceptually adjacent but not wired to `FamilyGraphCache.phase_commitments` — see "Stage 2C" below |
| 11 | Resume safely from completed phases | No family-specific resume validation exists; `FamilyGraphCache` only supports reopening under an identical cache identity (see item 2) | historical module / `relate.family.store` — no family-specific resume contract yet | **Not implemented for the family capability** | `tests_current/family/test_store_resume.py` covers cache-identity reopen durability only, not phase-level resume | `relate.workflows.WorkflowCheckpoint` and `WorkflowRunner`'s resume-prefix validation (**Stage 2C, this PR**) now provide a generic, tested resume contract; a future family workflow step sequence can adopt it once `relate.family.store` exposes phase read/write methods (Stage 2D or later) | **Gap partially addressed at the generic level in Stage 2C**: the workflow kernel's resume validation is domain-neutral and not yet connected to `FamilyGraphCache.phase_commitments` — that connection is explicitly out of scope for Stage 2C |
| 12 | Reject conflicting or tampered state | Per-method conflict checks (`ValueError` on tampered/conflicting content) throughout `FamilyGraphCache` | `relate.family.store.FamilyGraphCache` (Stage 2B) | **Complete for persistence** | `tests_current/family/test_store_records.py` conflict-rejection tests for source records, candidates, dispositions, and resolved edges; `tests_current/family/test_store_identity.py` identity-mismatch tests | Same conflict semantics available to any future workflow step; `relate.workflows` (Stage 2C) adds an analogous but generic guarantee — tampered or stale step commitments in a resume checkpoint are rejected (`WorkflowResumeError`), independent of any family-specific state | None |
| 13 | Calculate and publish an auditable family result later | `build_components`, `component_commitment`, `edge_commitment`, `UnionFind`, `family_graph_outcome`, `write_protocol_contract` | historical module — pending later extraction (graph-extraction stage) | Unchanged | Source untouched by Stage 2B or 2C; `git diff -- artifacts/canonical` empty; protocol SHA unchanged | "compute family components" / "calculate family outcome" / "publish protocol contract" steps, composed as `WorkflowStep` objects in a future family workflow (Stage 2D or later) | Still combines graph algorithm, outcome decision, and atomic publication in one module; not addressed by Stage 2B or 2C |
| 14 | Continue into D2 only after family and allocation decisions are complete | `prohibited_actions` / `decision_rules` in `protocol_contract()`; D2 not started anywhere in the repository | N/A — policy statement enforced by protocol contract, not a persistence capability | Unchanged | Protocol SHA unchanged; D2 not started; C0 selection and C1 reserve row contents not accessed by Stage 2B or 2C | A future family workflow can express this as an explicit `WorkflowStep` that returns `BLOCKED` until D2 is authorised, using the kernel's blocked-execution contract (Stage 2C) | None; Stage 2C does not touch this boundary and does not start D2 |

## Capability-count reconciliation

The Stage 2B pull request described 14 required capabilities, matching the
same 14-item enumeration used to scope Stage 2C. When this ledger was first
written, two of those fourteen items — "record deterministic phase
commitments" and "resume safely from completed phases" — were merged into a
single row (the previous row 10), leaving the table with 13 rows. No
capability was accidentally omitted, and "14" was not an incorrect count:
the two items are genuinely distinct (one is about writing a durable
commitment, the other is about validating a prior state before continuing),
they were simply combined editorially because the historical implementation
happens to satisfy neither of them beyond one shared implicit write. This
document now splits them back into rows 10 and 11, restoring the original
14-row enumeration with no invented capability.

## Summary

Stage 2B completed the clean persistence boundary for capabilities 2 and
4–8, 9 (schema only), 10 (partial), and 12: cache identity, allocation
registration, source evidence, candidates, review dispositions, resolved
edges, and per-record conflict rejection all now originate in
`relate.family.store` with identical schema, identity, and conflict
semantics. Capabilities 9 and 10 (component memberships and generic phase
commitments) were already incomplete in the historical module before Stage
2B — that stage relocated their table definitions and the one existing
implicit write unchanged, but did not add new persistence methods, since
doing so would be new capability surface rather than a move.

Stage 2C adds a generic, domain-neutral workflow kernel (`relate.workflows`)
that gives capabilities 1, 3, 7, 10, 11, 12, and 14 a concrete orchestration
vocabulary to be expressed in later stages — explicit steps, immutable
context, deterministic commitments, an injected trace sink, honest blocked
outcomes, fail-closed failures, and a validated resume-prefix contract. It
does **not** implement any family-specific step, does not connect to
`FamilyGraphCache`, and does not fill the component-membership or
generic-phase-commitment gaps recorded in capabilities 9 and 10. Those
remain open until a future stage adds the corresponding family-store methods
and composes them into `WorkflowStep` objects.

Capabilities 1, 3 (protocol-level half), and 13 remain fully in the
historical module, scheduled for later extraction stages (graph
construction, explicit family workflow, and CLI).

The architecture reset therefore preserves a valid path forward for every
capability required by the family-connected allocation protocol: completed
capabilities have a clean, tested home; incomplete ones are named as gaps
with an explicit future step, not silently dropped or assumed solved.

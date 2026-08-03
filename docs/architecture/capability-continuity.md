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
| 1 | Verify frozen scientific inputs | `validate_frozen_protocol_inputs`, `validate_firewall_booleans` in `option_c0_family_connected_protocol.py` | `relate.family.verification` + `relate.family.workflow.steps.VerifyFamilyInputsStep` (**Stage 2E**) | **Complete for clean verification** | `tests_current/family/test_verification.py`; `tests_current/family_workflow/test_composition.py`; historical wrapper remains compatible | `verify_family_inputs` | Hash/firewall violations raise fail-closed; they are not `BLOCKED` |
| 2 | Bind a family run to exact identities | `default_cache_identity` (historical, source-hash sensitive) | `relate.family.store.FamilyGraphCacheIdentity` + `make_cache_identity` (**Stage 2B, this PR**) | **Complete** | `historical.FamilyGraphCacheIdentity is store.FamilyGraphCacheIdentity`; identical field names/order/`as_mapping()`; `default_cache_identity` still binds `sha256_file(__file__)` of the historical module; `tests_current/family/test_store_identity.py` | "bind run identity" step calling `make_cache_identity` with the workflow's own explicit source identity | `default_cache_identity` remains source-hash sensitive by design; a future workflow must supply its own executing-source identity, not inherit the historical file hash |
| 3 | Preserve the hidden-row firewall | `FORBIDDEN_PAYLOAD_PATTERNS` / `validate_payload_firewall` (moved to `relate.family.sources` in Stage 2A); `firewall_booleans` block in `protocol_contract()` (historical) | `relate.family.sources` + `relate.family.verification` + `VerifyFamilyInputsStep` (**Stage 2E**) | **Complete for verification** | `tests_current/family/test_sources.py`; `tests_current/family/test_verification.py`; protocol SHA unchanged | `verify_family_inputs` | Firewall violations are invariant/security failures and raise; incomplete metadata/review are the blocked states |
| 4 | Register allocation repositories without reading protected row contents | `FamilyGraphCache.put_allocation_repositories` / `put_canonical_allocation_manifest` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestAllocationRegistration`; validation delegated to `relate.family.repositories.validate_canonical_allocation_entries` (Stage 2A, unchanged) | "register allocation" step | `put_canonical_allocation_manifest` now reads its expected SHA-256 from `self.identity.allocation_manifest_sha256` instead of the historical module-global constant, to avoid the store importing `relate.experiments` — see migration-status.md for why this is behavior-preserving |
| 5 | Register bounded source evidence | `make_source_record` / `validate_source_record` (Stage 2A, `relate.family.sources`); `FamilyGraphCache.put_source_record` / `get_source_record` / `get_source_registry` | `relate.family.sources` (validation, Stage 2A) + `relate.family.store` (persistence, **Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestSourceRecordPersistence` | "register source evidence" step | None |
| 6 | Store evidence candidates | `FamilyGraphCache.put_evidence_candidate` / `get_evidence_candidate` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestEvidenceCandidatePersistence` | "record candidate" step | None |
| 7 | Store manual review dispositions | `FamilyGraphCache.put_manual_review_disposition` / `get_manual_review_disposition` / `get_final_disposition_for_candidate` | `relate.family.store.FamilyGraphCache` (Stage 2B) | **Complete** | `tests_current/family/test_store_records.py::TestManualReviewDispositionPersistence` | A "resolve required reviews" `WorkflowStep` can call `put_manual_review_disposition` and return `StepResult.blocked("manual review required")` (Stage 2C blocked-execution contract) when a disposition is still `UNRESOLVED`, rather than treating an incomplete review queue as an error | None |
| 8 | Store resolved family edges | `FamilyGraphCache.put_resolved_edge` / `get_resolved_edge` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestResolvedEdgePersistence` | "record resolved edge" step | None |
| 9 | Store connected-component memberships | `component_memberships` table schema only; no put/get method existed before Stage 2D | `relate.family.store.FamilyGraphCache.put_component_memberships` / `get_component_memberships` (**Stage 2D, this PR**); components themselves built by `relate.family.graph.build_components` (Stage 2D) | **Complete** | `tests_current/family/test_store_components.py`; `tests_current/family/test_graph.py` | "record components" `WorkflowStep` calling `put_component_memberships` with `build_components`' output (Stage 2E or later) | None — whole-graph replace semantics compare the complete existing and incoming sets before writing, so a partial old/new graph can never be observed |
| 10 | Record deterministic phase commitments | Implicit `phase_commitments` write inside `put_allocation_repositories` (phase `"initial_allocation"` only, upsert semantics); no generic put/get phase-commitment method before Stage 2D | `relate.family.store.FamilyGraphCache.put_phase_commitment` / `get_phase_commitment` / `list_phase_commitments` (**Stage 2D, this PR**); the original `initial_allocation` upsert path is untouched | **Complete** | `tests_current/family/test_store_phase_commitments.py` | "record phase commitment" `WorkflowStep` (Stage 2E or later) | The new generic API uses reject-on-conflict semantics (consistent with every other `put_*` method), deliberately different from the untouched `initial_allocation` upsert path — this is a documented, intentional asymmetry, not an inconsistency to resolve |
| 11 | Resume safely from completed phases | No family-specific resume validation existed before Stage 2E | `relate.family.workflow` composed with `WorkflowRunner` checkpoints and `FamilyGraphCache` phase readers (**Stage 2E**) | **Complete for in-memory workflow resume** | `tests_current/workflows/test_resume.py`; `tests_current/family_workflow/test_identity.py`; `tests_current/family_workflow/test_composition.py` | Completed-prefix resume through `WorkflowRunner.run(..., resume_from=...)` | Durable checkpoint storage is intentionally not added; changed evidence requires a fresh run and fresh store |
| 12 | Reject conflicting or tampered state | Per-method conflict checks (`ValueError` on tampered/conflicting content) throughout `FamilyGraphCache` | `relate.family.store.FamilyGraphCache` (Stage 2B; extended to component memberships and phase commitments in Stage 2D) | **Complete for persistence** | `tests_current/family/test_store_records.py`, `test_store_components.py`, `test_store_phase_commitments.py` conflict-rejection tests; `tests_current/family/test_store_identity.py` identity-mismatch tests | Same conflict semantics available to any future workflow step; `relate.workflows` (Stage 2C) adds an analogous but generic guarantee — tampered or stale step commitments in a resume checkpoint are rejected (`WorkflowResumeError`), independent of any family-specific state | None |
| 13 | Calculate and publish an auditable family result later | `build_components`, `component_commitment`, `edge_commitment`, `UnionFind`, `family_graph_outcome`, `graph_completeness`, `write_protocol_contract` | Calculation/workflow half: `relate.family.graph`, `relate.family.commitments`, `relate.family.outcome`, `relate.family.analysis`, `relate.family.workflow` (**Stage 2D/2E**). Bounded review-publication boundary: `relate.family.review`, `relate.family.publication` (**Stage 2F**). Exact canonical-input execution to noncanonical staging: `relate.family.authorization`, `relate.family.execution`, `relate.cli.family` (**Stage 2G/2H**). Execution evidence review: `relate.family.execution_review` (**Stage 2I**). Canonical publication candidate/request/human authorization: `relate.family.canonical_publication_authorization` (**Stage 2J**). One-shot executable canonical publication: `relate.family.canonical_publication` (**Stage 2K**). Historical protocol writer remains historical | **One-shot executable canonical publication complete; overwrite and replay are structurally rejected; publication evidence review remains future work** | `tests_current/family/test_graph.py`, `test_graph_commitments.py`, `test_outcome.py`, `test_role_crossing_analysis.py`, `test_family_analysis_commitments.py`; `tests_current/family_workflow/*`; `tests_current/family_review/*`; `tests_current/family_authorization/*`; `tests_current/family_execution/*`; `tests_current/family_execution_review/*`; `tests_current/family_publication_authorization/*`; `tests_current/family_canonical_publication/*`; protocol SHA unchanged | Later canonical publication evidence review remains future work | Materiality remains undetermined; allocation/reallocation, model refit, C0 replay, protected-row access, and D2 remain gated |
| 14 | Continue into D2 only after family and allocation decisions are complete | `prohibited_actions` / `decision_rules` in `protocol_contract()`; D2 not started anywhere in the repository | N/A — policy statement enforced by protocol contract, not a persistence capability | Unchanged and gated | Protocol SHA unchanged; D2 not started; C0 selection and C1 reserve row contents not accessed by Stage 2B through 2H | A future family workflow can express this as an explicit `WorkflowStep` that returns `BLOCKED` until D2 is authorised, using the kernel's blocked-execution contract (Stage 2C) | Stage 2H execution completion is not D2 authorization |

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
4–8, and 12 (partially): cache identity, allocation registration, source
evidence, candidates, review dispositions, resolved edges, and per-record
conflict rejection all originate in `relate.family.store` with identical
schema, identity, and conflict semantics.

Stage 2C added a generic, domain-neutral workflow kernel (`relate.workflows`)
that gives capabilities 1, 3, 7, 10, 11, 12, and 14 a concrete orchestration
vocabulary to be expressed in later stages — explicit steps, immutable
context, deterministic commitments, an injected trace sink, honest blocked
outcomes, fail-closed failures, and a validated resume-prefix contract. It
did **not** implement any family-specific step or connect to
`FamilyGraphCache`.

Stage 2D completed capabilities 9, 10, 12 (fully), and 13 (the calculation
half): `relate.family.graph` gives component construction (`UnionFind`,
`build_components`, `component_id`) a clean, tested destination;
`relate.family.commitments` does the same for graph-specific SHA-256
commitments (`component_commitment`, `edge_commitment`); `relate.family.outcome`
does the same for bounded completeness and the frozen outcome decision
(`graph_completeness`, `family_graph_outcome`); and `relate.family.store`
gained public `put`/`get_component_memberships` and
`put`/`get`/`list_phase_commitments` APIs, closing the two gaps Stage 2B
had explicitly left open. Capability 11 (resume safely from completed
phases) is now **partial** rather than fully open: the persistence half
(reading completed phases) and the generic validation half (the Stage 2C
checkpoint contract) both exist, but nothing yet composes them for the
family capability specifically — that composition is Stage 2E's job.

Stage 2F completed the bounded noncanonical review-publication boundary for
capability 13 without advancing canonical publication. A completed Stage 2E
workflow can now be validated into a deterministic review packet, reviewed by
an explicit human publication disposition, and written immutably to a
noncanonical destination. Capability 14 remains gated: D2 authorization is not
created by workflow completion, packet construction, or review publication.

Stage 2G adds the supported `relate-family` CLI and exact canonical execution
request/authorization records. This advances the operational boundary but does
not mark canonical execution complete: the authorization can be created and
verified, but no command or clean module consumes it to execute. Capability 14
remains gated.

Stage 2H adds executable v2 request/authorization contracts and a one-shot
authorized canonical-input executor. Capability 13 advances only to canonical
input execution capability: completed runs create noncanonical staged evidence,
not canonical publication. The v1 records remain validation-only; v2 binds the
firewall-publication file SHA, canonical executor source identity, authorised
runner source identity, canonical run identity, one-shot claim, receipt, and
trace. Capability 14 remains gated: execution completion does not authorize
materiality, allocation changes, reallocation, model refit, C0 replay,
protected-row access, or D2.

Stage 2I adds execution evidence review. A completed staged execution can now
be inspected for request/authorization chain integrity, terminal-state shape,
trace and receipt consistency, and bounded scientific-payload equivalence with
the authorized rehearsal packet. Valid completed equivalent evidence may become
eligible for a later publication-authorization review, but this eligibility is
not publication authorization. Canonical publication, materiality, allocation
changes, reallocation, model refit, C0 replay, protected-row access, and D2
remain gated.

Stage 2J adds canonical publication candidate, request, human authorization,
and validation records. These records bind one exact bounded family-result
candidate to one exact absent canonical destination, keep logical commitments
separate from file SHA-256 values, and validate withholding as a first-class
outcome. They are explicitly non-executable:
`executable_publication_authority` remains false and no canonical artifact is
written. Executable canonical publication remains future Stage 2K work.

Stage 2K adds the one-shot executable publication boundary. A distinct v2
request and v2 authorization bind the Stage 2J chain, exact candidate file
bytes, canonical destination, noncanonical audit directory and publisher source
identity. Canonical creation uses no-replace semantics; replay is rejected by
the audit directory and canonical destination. Publication evidence review is
not yet complete, and publication still does not determine materiality or
authorize allocation, reallocation, model refit, C0 replay, protected-row
access or D2.

The historical `write_protocol_contract` remains a protocol-contract writer,
not a family-result publication boundary. The supported CLI and canonical
authorization process remain later-stage work. The CLI and `main` remain
historical throughout Stage 2F.

The architecture reset therefore preserves a valid path forward for every
capability required by the family-connected allocation protocol: completed
capabilities have a clean, tested home; incomplete ones are named as gaps
with an explicit future step, not silently dropped or assumed solved.

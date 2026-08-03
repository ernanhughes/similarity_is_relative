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
| 1 | Verify frozen scientific inputs | `validate_frozen_protocol_inputs`, `validate_firewall_booleans` in `option_c0_family_connected_protocol.py` | historical module — pending later extraction | Unchanged | Source untouched by Stage 2B; hashes and firewall-boolean checks identical | "verify frozen inputs" step | Reads canonical artifact files directly; not yet behind a workflow-step interface |
| 2 | Bind a family run to exact identities | `default_cache_identity` (historical, source-hash sensitive) | `relate.family.store.FamilyGraphCacheIdentity` + `make_cache_identity` (**Stage 2B, this PR**) | **Complete** | `historical.FamilyGraphCacheIdentity is store.FamilyGraphCacheIdentity`; identical field names/order/`as_mapping()`; `default_cache_identity` still binds `sha256_file(__file__)` of the historical module; `tests_current/family/test_store_identity.py` | "bind run identity" step calling `make_cache_identity` with the workflow's own explicit source identity | `default_cache_identity` remains source-hash sensitive by design; a future workflow must supply its own executing-source identity, not inherit the historical file hash |
| 3 | Preserve the hidden-row firewall | `FORBIDDEN_PAYLOAD_PATTERNS` / `validate_payload_firewall` (moved to `relate.family.sources` in Stage 2A); `firewall_booleans` block in `protocol_contract()` (historical) | `relate.family.sources` (payload firewall, Stage 2A); protocol-level firewall verification remains historical | Partially complete | `tests_current/family/test_sources.py`; `protocol_contract()["firewall_booleans"]` values unchanged; protocol SHA unchanged | "verify firewall" step | Not touched by this PR; protocol-level firewall check is still inline in the historical module |
| 4 | Register allocation repositories without reading protected row contents | `FamilyGraphCache.put_allocation_repositories` / `put_canonical_allocation_manifest` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestAllocationRegistration`; validation delegated to `relate.family.repositories.validate_canonical_allocation_entries` (Stage 2A, unchanged) | "register allocation" step | `put_canonical_allocation_manifest` now reads its expected SHA-256 from `self.identity.allocation_manifest_sha256` instead of the historical module-global constant, to avoid the store importing `relate.experiments` — see migration-status.md for why this is behavior-preserving |
| 5 | Register bounded source evidence | `make_source_record` / `validate_source_record` (Stage 2A, `relate.family.sources`); `FamilyGraphCache.put_source_record` / `get_source_record` / `get_source_registry` | `relate.family.sources` (validation, Stage 2A) + `relate.family.store` (persistence, **Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestSourceRecordPersistence` | "register source evidence" step | None |
| 6 | Store evidence candidates | `FamilyGraphCache.put_evidence_candidate` / `get_evidence_candidate` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestEvidenceCandidatePersistence` | "record candidate" step | None |
| 7 | Store manual review dispositions | `FamilyGraphCache.put_manual_review_disposition` / `get_manual_review_disposition` / `get_final_disposition_for_candidate` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestManualReviewDispositionPersistence` | "record review" step | None |
| 8 | Store resolved family edges | `FamilyGraphCache.put_resolved_edge` / `get_resolved_edge` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py::TestResolvedEdgePersistence` | "record resolved edge" step | None |
| 9 | Store connected-component memberships | `component_memberships` table schema only; no put/get method exists in the historical module either before or after this PR | Table moved to `relate.family.store.FamilyGraphCache` schema (**Stage 2B, this PR**); no persistence API yet | **Schema only** | `tests_current/family/test_store_schema.py::test_component_memberships_composite_primary_key` | "record components" step (Stage 2C or later) | **Gap, not introduced by this PR**: there is no `put_component_memberships` / `get_component_memberships` method anywhere in the codebase today. A future stage must add one without inventing new graph science |
| 10 | Record deterministic phase commitments; resume safely from completed phases | Implicit `phase_commitments` write inside `put_allocation_repositories` (phase `"initial_allocation"` only); no generic put/get phase-commitment method | Table + the one implicit write moved to `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Partial** | `tests_current/family/test_store_records.py::test_phase_commitment_recorded_after_allocation`; `tests_current/family/test_store_resume.py::TestPhaseCommitmentResume` | "record phase commitment" / "inspect completed phases" step (Stage 2C or later) | **Gap, not introduced by this PR**: only the allocation phase is auto-committed; there is no generic reader/writer for arbitrary phases yet |
| 11 | Reject conflicting or tampered state | Per-method conflict checks (`ValueError` on tampered/conflicting content) throughout `FamilyGraphCache` | `relate.family.store.FamilyGraphCache` (**Stage 2B, this PR**) | **Complete** | `tests_current/family/test_store_records.py` conflict-rejection tests for source records, candidates, dispositions, and resolved edges; `tests_current/family/test_store_identity.py` identity-mismatch tests | Same conflict semantics available to any future workflow step | None |
| 12 | Calculate and publish an auditable family result later | `build_components`, `component_commitment`, `edge_commitment`, `UnionFind`, `family_graph_outcome`, `write_protocol_contract` | historical module — pending later extraction (graph-extraction stage) | Unchanged | Source untouched by Stage 2B; `git diff -- artifacts/canonical` empty; protocol SHA unchanged | "compute family components" / "calculate family outcome" / "publish protocol contract" steps | Still combines graph algorithm, outcome decision, and atomic publication in one module; not addressed by this PR |
| 13 | Continue into D2 only after family and allocation decisions are complete | `prohibited_actions` / `decision_rules` in `protocol_contract()`; D2 not started anywhere in the repository | N/A — policy statement enforced by protocol contract, not a persistence capability | Unchanged | Protocol SHA unchanged; D2 not started; C0 selection and C1 reserve row contents not accessed by this PR | Explicit D2 gate in a future workflow contract | None; this PR does not touch this boundary |

## Summary

Stage 2B (this PR) completes the clean persistence boundary for capabilities
2 and 4–8, and 11: cache identity, allocation registration, source evidence,
candidates, review dispositions, and resolved edges all now originate in
`relate.family.store` with identical schema, identity, and conflict
semantics. Capabilities 9 and 10 (component memberships and generic phase
commitments) were already incomplete in the historical module before this
PR — Stage 2B relocated their table definitions and the one existing
implicit write unchanged, but does not add new persistence methods, since
doing so would be new capability surface rather than a move. Capabilities
1, 3 (protocol-level half), 12, and 13 remain in the historical module,
scheduled for later extraction stages (graph construction, explicit
workflow, and CLI).

The architecture reset therefore preserves a valid path forward for every
capability required by the family-connected allocation protocol: completed
capabilities have a clean, tested home; incomplete ones are named as gaps
with an explicit future step, not silently dropped or assumed solved.

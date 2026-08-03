# Migration Status

Records responsibility moves made during the RELATE architecture reset.
Each entry covers one extracted symbol, naming its old location, new home,
compatibility alias, and residual risks.

---

## Stage A — Evidence Infrastructure

**Branch:** `stage-a-evidence-infrastructure`

**New package:** `src/relate/evidence/`

---

### Serialization

#### `canonical_json_compact_unicode`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbol | `canonical_json` |
| new module | `relate.evidence.canonical_json` |
| new symbol | `canonical_json_compact_unicode` |
| compatibility facade | `from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json` at top of old module |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `option_c0_family_connected_protocol` (via alias), `option_c0_d1_overlap_classification` (not yet migrated) |
| deletion eligibility | not yet — alias required while callers remain |
| notes | `ensure_ascii=False`. Produces different bytes from `canonical_json_compact_ascii` for any non-ASCII content. Must not be silently unified with the ASCII variant. |

#### `canonical_json_compact_ascii`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_d1_integrity_audit` |
| old symbol | `_canonical_json` |
| new module | `relate.evidence.canonical_json` |
| new symbol | `canonical_json_compact_ascii` |
| compatibility facade | `from relate.evidence.canonical_json import canonical_json_compact_ascii as _canonical_json` at top of old module |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `option_c0_d1_integrity_audit` (via alias); `option_c0_discovery_runner`, `option_c0_data_firewall`, `option_c0_data_firewall_independent`, `option_c0_embedding_cache` (not yet migrated) |
| deletion eligibility | not yet — alias required while callers remain |
| notes | `ensure_ascii=True`. Non-ASCII characters are `\uXXXX`-escaped. Produces different bytes from `canonical_json_compact_unicode` for any non-ASCII content. Must not be silently unified with the Unicode variant. |

#### Serializer unification risk

The two historical serializers differ on `ensure_ascii`. They were NOT silently
unified. Any value containing non-ASCII characters will produce different byte
sequences. Both are preserved as explicitly named compatibility variants.

---

### Hashing

#### `sha256_bytes`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_d1_integrity_audit` |
| old symbol | `_sha256_bytes` |
| new module | `relate.evidence.hashing` |
| new symbol | `sha256_bytes` |
| compatibility facade | `from relate.evidence.hashing import sha256_bytes as _sha256_bytes` |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `option_c0_d1_integrity_audit` (via alias); `option_b_identity`, `option_b_identity_v2`, `option_b_selection`, `option_c0_data_firewall`, `option_c0_data_firewall_independent` (not yet migrated) |
| deletion eligibility | not yet |

#### `sha256_text`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbol | `sha256_text` |
| new module | `relate.evidence.hashing` |
| new symbol | `sha256_text` |
| compatibility facade | `from relate.evidence.hashing import sha256_text` (name unchanged) |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `option_c0_family_connected_protocol` (direct import); no other module defined this variant |
| deletion eligibility | not yet |

#### `sha256_file`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol`, `relate.experiments.option_c0_d1_integrity_audit` |
| old symbol | `sha256_file` / `_sha256_file` |
| new module | `relate.evidence.hashing` |
| new symbol | `sha256_file` |
| compatibility facade | `from relate.evidence.hashing import sha256_file` / `sha256_file as _sha256_file` |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | Both target modules (via aliases); `option_b_embeddings`, `e00_operator_matrix`, `option_c0_d1_overlap_classification`, `option_c0_discovery_entrypoint`, `option_b_probe_runner`, `option_b_hard_negative_manifest` (not yet migrated — some use `read_bytes()` shortcut which is functionally identical for small files) |
| deletion eligibility | not yet |
| notes | All streamed implementations produce identical output. The `option_b_identity` and `option_b_identity_v2` variants use `path.read_bytes()` followed by `sha256_bytes`; these produce identical digests but are not streamed. Migration of those callers is safe but not performed in this PR. |

---

### Atomic I/O

#### `atomic_write_json`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_d1_integrity_audit` |
| old symbol | `_atomic_write_json` |
| new module | `relate.evidence.atomic_io` |
| new symbol | `atomic_write_json` |
| compatibility facade | `from relate.evidence.atomic_io import atomic_write_json as _atomic_write_json` |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `option_c0_d1_integrity_audit` (via alias); `option_c0_discovery_runner`, `option_b_probe_runner`, `option_b_hard_negative_manifest`, `option_b_method_evaluation`, `option_b_embeddings_hardened`, `option_b_method_evaluation_independent`, `option_b_embedding_reproduction` (not yet migrated) |
| deletion eligibility | not yet |
| notes | The extracted implementation matches the D1 audit version (binary write, fsync + directory fsync, UUID temp name). Other historical implementations use text write mode or pid-named temp files or skip fsync. All produce identical JSON content; durability differences are not observable in tests. Unifying onto the most robust implementation is safe. |

#### `_fsync_directory`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_d1_integrity_audit` |
| old symbol | `_fsync_directory` |
| new module | `relate.evidence.atomic_io` |
| new symbol | `fsync_directory` |
| compatibility facade | absorbed into `atomic_write_json`; no longer an external alias |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | none (was only called internally by `_atomic_write_json`) |
| deletion eligibility | eligible — was module-private and is fully replaced |

---

### Immutable Write Protection

#### `refuse_overwrite`

| Field | Value |
|---|---|
| old module | various (inline pattern: `if path.exists(): raise FileExistsError(...)`) |
| old symbol | (inline, no shared name) |
| new module | `relate.evidence.immutable` |
| new symbol | `refuse_overwrite` |
| compatibility facade | not yet wired — callers still use inline checks |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `option_c0_family_connected_protocol`, `option_c0_d1_integrity_audit`, `option_c0_discovery_runner`, `option_c0_d1_overlap_classification`, `option_c0_data_firewall`, `option_c0_data_firewall_independent`, `option_b_method_evaluation`, `option_b_method_evaluation_independent` |
| deletion eligibility | not yet — callers not migrated in this PR |
| notes | Inline patterns are functionally equivalent. Wiring callers is a separate step. |

---

### SQLite Helpers

#### Stage B integration: `FamilyGraphCache`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old class or symbol | `FamilyGraphCache.__init__` (inline PRAGMA execute calls), `FamilyGraphCache._verify_pragmas` (inline), `FamilyGraphCache._bind_identity` (inline) |
| responsibility | WAL pragma enforcement, pragma verification, cache identity binding |
| new evidence utility | `relate.evidence.sqlite.enforce_wal_pragmas`, `verify_wal_pragmas`, `bind_cache_identity` |
| integration type | caller delegates to helper; exception type preserved (RuntimeError wraps ValueError in `_verify_pragmas`) |
| compatibility alias retained | no alias needed — methods remain, bodies replaced |
| schema changed | no |
| identity keys changed | no |
| transaction behaviour changed | no |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining duplicate callers | none — all three methods migrated |
| deletion eligibility | inline bodies deleted; methods remain as thin wrappers |
| known uncertainty | `_verify_pragmas` converts `ValueError` → `RuntimeError` to preserve the historical exception type |

#### Stage B integration: `IntegrityAuditCache`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_d1_integrity_audit` |
| old class or symbol | `IntegrityAuditCache.__init__` (inline PRAGMA execute calls), `IntegrityAuditCache.verify_pragmas` (inline) |
| responsibility | WAL pragma enforcement and verification |
| new evidence utility | `relate.evidence.sqlite.enforce_wal_pragmas`, `verify_wal_pragmas` |
| integration type | caller delegates to helper; `verify_pragmas` wraps helper to preserve error message |
| compatibility alias retained | no alias needed |
| schema changed | no |
| identity keys changed | no — `IntegrityAuditCache` uses a `contexts` table (sha256 key / payload), not a `cache_identity` key-value table; `bind_cache_identity` is **not** applicable |
| transaction behaviour changed | no |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining duplicate callers | none |
| deletion eligibility | inline bodies deleted |
| known uncertainty | `bind_cache_identity` deliberately not integrated: `IntegrityAuditCache` stores context identity as a full row with `sha256` primary key and `payload_json`, not as a flat key/value table. Forcing the neutral helper would alter the schema. |

#### Stage B integration: `OptionC0EmbeddingCache`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_embedding_cache` |
| old class or symbol | `OptionC0EmbeddingCache.__init__` (inline PRAGMA execute calls), module-level `sha256_bytes` (inline) |
| responsibility | WAL pragma enforcement; byte hashing |
| new evidence utility | `relate.evidence.sqlite.enforce_wal_pragmas`; `relate.evidence.hashing.sha256_bytes` |
| integration type | direct import replacement |
| compatibility alias retained | no alias needed — `sha256_bytes` name preserved via direct import |
| schema changed | no |
| identity keys changed | no — `OptionC0EmbeddingCache` has no `cache_identity` table; `bind_cache_identity` is **not** applicable |
| transaction behaviour changed | no |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining duplicate callers | none |
| deletion eligibility | inline body deleted; `import hashlib` removed |
| known uncertainty | none |

---

## Stage B — Remaining SHA-256 Migration

### Completed hashing migrations

All migrations in this stage replace inline definitions with thin aliases or direct imports
from `relate.evidence.hashing`. No byte output changes.

#### `_sha256_bytes` migration

| Module | Old symbol | New import |
|---|---|---|
| `option_b_identity` | inline `_sha256_bytes` | `from relate.evidence.hashing import sha256_bytes as _sha256_bytes` |
| `option_b_identity_v2` | inline `_sha256_bytes` | `from relate.evidence.hashing import sha256_bytes as _sha256_bytes` |
| `option_b_selection` | inline `_sha256_bytes` | `from relate.evidence.hashing import sha256_bytes as _sha256_bytes` |
| `option_c0_data_firewall` | inline `_sha256_bytes` | `from relate.evidence.hashing import sha256_bytes as _sha256_bytes` |
| `option_c0_data_firewall_independent` | inline `_sha256_bytes` | `from relate.evidence.hashing import sha256_bytes as _sha256_bytes` |
| `option_c0_embedding_cache` | inline `sha256_bytes` | `from relate.evidence.hashing import sha256_bytes` |

All removed inline definitions were `hashlib.sha256(value).hexdigest()` — byte-identical to `sha256_bytes`.

**Structured hashing NOT migrated** (categories 4–6, remain unchanged):
- `_sha256_json` in `option_c0_data_firewall` and `option_c0_data_firewall_independent` (domain compound: serialiser + hash)
- `hashlib.sha256(...)` in sort-key lambdas (structured partitioning hashes)
- `_write_jsonl` incremental hash in `option_b_selection` (streaming incremental)
- `array_hash` functions throughout (structured: includes dtype/shape metadata)
- `_stable_key_hash` / `_stable_key_sequence_hash` in probe runner / hard-negative manifest (structured: serialized sequence)
- `manifest_sha256` in `option_c0_d1_overlap_classification` (structured: compound serialiser + hash)

#### `_sha256_file` / `sha256_file` migration

| Module | Old symbol | New import |
|---|---|---|
| `option_b_identity` | inline `_sha256_file` (read\_bytes) | `from relate.evidence.hashing import sha256_file as _sha256_file` |
| `option_b_identity_v2` | inline `_sha256_file` (read\_bytes) | `from relate.evidence.hashing import sha256_file as _sha256_file` |
| `option_b_embeddings` | inline `sha256_file` (streaming) | `from relate.evidence.hashing import sha256_file` |
| `option_b_probe_runner` | inline `_sha256_file` (streaming) | `from relate.evidence.hashing import sha256_file as _sha256_file` |
| `option_b_hard_negative_manifest` | inline `_sha256_file` (streaming) | `from relate.evidence.hashing import sha256_file as _sha256_file` |
| `option_c0_d1_overlap_classification` | inline `sha256_file` (streaming) | `from relate.evidence.hashing import sha256_file` |
| `option_c0_discovery_runner` | inline `_sha256_file` (streaming) | `from relate.evidence.hashing import sha256_file as _sha256_file` |
| `option_c0_discovery_entrypoint` | inline `_sha256_file` (read\_bytes) | `from relate.evidence.hashing import sha256_file as _sha256_file` |
| `e00_operator_matrix` | inline `sha256_file` (streaming) | `from relate.evidence.hashing import sha256_file` |

Both historical implementations (read\_bytes and streaming) produce byte-identical output to
`relate.evidence.hashing.sha256_file` for all file sizes including multi-chunk files.

#### Remaining callers (deliberately not migrated)

The following callers were inspected but not migrated in this PR. Reasons are documented.

| Module | Symbol | Reason not migrated |
|---|---|---|
| `option_c0_discovery_runner` | `_sha256_json` | Domain-specific compound: `_canonical_json(value).encode()` then hash. Ordering and encoding are protocol-sensitive. |
| `option_b_selection` | `_write_jsonl` incremental | Incremental streaming hash — not a neutral file or byte hash. |
| `option_b_probe_runner` | `_stable_key_hash`, `_pair_selection_sha256`, incremental pair hash | Structured / incremental hashes with custom payloads. |
| `option_b_hard_negative_manifest` | `_stable_key_sequence_hash`, struct hashes | Structured hashes — include serialized sequence data. |
| `option_c0_data_firewall` | `_sha256_json`, sort-key `hashlib.sha256` | Domain compound and partitioning hashes; semantics differ. |
| `option_c0_data_firewall_independent` | `_sha256_json`, sort-key `hashlib.sha256` | Same as above. |
| `option_c0_d1_overlap_classification` | `manifest_sha256` inline | Compound: canonical JSON serialisation then hash; protocol-specific. |

---

## Serializer Comparison Table

Both variants share: `sort_keys=True`, `separators=(",", ":")`, no indent.

| Variant | `ensure_ascii` | Non-ASCII output | Used by |
|---|---|---|---|
| `canonical_json_compact_unicode` | `False` | literal UTF-8 | family_connected_protocol, d1_overlap_classification |
| `canonical_json_compact_ascii` | `True` | `\uXXXX` escaped | d1_integrity_audit, discovery_runner, data_firewall, data_firewall_independent, embedding_cache |

These produce **different bytes** for values containing non-ASCII characters.
They were **not** silently unified.

---

## Unresolved Risks

None identified in Stage A or Stage B. All extracted functions produce byte-identical output
to their historical counterparts. No canonical files were touched.

Stage B stop-condition checks:
- No cache identity keys changed.
- No transaction boundaries changed.
- No protocol payload or SHA changed (confirmed: `git diff -- artifacts/canonical/` is empty).
- `_verify_pragmas` exception type preserved (RuntimeError) via explicit wrapper.
- `IntegrityAuditCache.verify_pragmas` message preserved via explicit wrapper.
- `bind_cache_identity` deliberately not integrated into `IntegrityAuditCache` or
  `OptionC0EmbeddingCache` because neither has a flat key/value identity table.
- Structured, incremental and domain-compound hashes remain untouched.

---

## Stage 2A — Family Domain Extraction

**Branch:** `architecture/family-domain-extraction`

**New package:** `src/relate/family/`

**PR classification:** `DOMAIN_EXTRACTION`

### Summary of what moved

Pure family-domain capabilities were extracted from the 2338-line monolith
`relate.experiments.option_c0_family_connected_protocol` into a clean package
with no imports from `relate.experiments`, `relate.workflows` or `relate.cli`.

The historical module was rewritten to re-export all moved symbols explicitly
so that every existing caller continues to work without modification.

### Allowed dependency direction (achieved)

```text
historical protocol module
    -> relate.family.*
        -> relate.evidence.*
```

No reverse imports. No circular imports inside `relate.family`.

---

### Moved symbol groups

#### `relate.family.models`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `EDGE_SCHEMA_ID`, `EdgeRule`, `AllocationEntry`, `ManualReviewDisposition`, `EvidenceCandidate`, `EvidenceEdge`, `SourceEvidenceRecord` |
| new module | `relate.family.models` |
| responsibility | Pure immutable frozen dataclasses; no external dependencies |
| compatibility facade | Explicit re-export in historical module |
| clean module imports experiments | no |
| scientific behaviour changed | no |
| protocol payload changed | no |
| protocol SHA changed | no |
| canonical artifacts changed | no |
| remaining historical responsibility | None for these symbols |
| future extraction stage | Stage 2B (family persistence) |
| known uncertainty | None |

#### `relate.family.rules`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `EDGE_RULES`, `HARD_CONNECTING_EDGE_TYPES`, `CONDITIONAL_CONNECTING_EDGE_TYPES`, `NONCONNECTING_EDGE_TYPES`, `CONNECTING_EDGE_TYPES`, `ALL_EDGE_TYPES`, `edge_rules_contract` |
| new module | `relate.family.rules` |
| responsibility | Frozen edge-rule taxonomy and rule-derived constants |
| compatibility facade | Explicit re-export; `historical.EDGE_RULES is clean.EDGE_RULES` (same object) |
| clean module imports experiments | no |
| scientific behaviour changed | no |
| protocol payload changed | no |
| protocol SHA changed | no |
| canonical artifacts changed | no |
| remaining historical responsibility | None for these symbols |
| future extraction stage | Stage 2B |
| known uncertainty | `CONFIDENCE_CATEGORIES` appears in both `rules.py` and `sources.py`; each has an independent use and both duplicate the historical value |

#### `relate.family.repositories`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `normalize_repository`, `repository_owner`, `load_allocation_manifest`, `allocation_repository_commitment`, `validate_canonical_allocation_entries`, `ROLE_ORDER`, `REPOSITORY_PATTERN`, `ALLOCATION_REPOSITORY_COUNT`, `ALLOCATION_REPOSITORY_COMMITMENT_SHA256`, `ALLOCATION_ROLE_REPOSITORY_COUNTS`, `ALLOCATION_ROLE_ROW_COUNTS` |
| new module | `relate.family.repositories` |
| responsibility | Pure repository identity and allocation-domain operations |
| compatibility facade | Explicit re-export |
| clean module imports experiments | no |
| scientific behaviour changed | no |
| protocol payload changed | no |
| protocol SHA changed | no |
| canonical artifacts changed | no |
| remaining historical responsibility | None for these symbols |
| future extraction stage | Stage 2B |
| known uncertainty | None |

#### `relate.family.sources`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `validate_payload_firewall`, `payload_hash`, `validate_source_identity`, `validate_source_registry`, `validate_evidence_source_bundle`, `source_bundle_commitment`, `make_source_record`, `source_record_from_record`, `validate_source_record`, `public_metadata_snapshot`, `parse_timestamp`, `HASH_PATTERN`, `LOCATOR_PATTERN`, `ALLOWED_EVIDENCE_SOURCES`, `METADATA_STATUSES`, `PUBLIC_METADATA_FIELDS`, `MAX_EVIDENCE_STRING_LENGTH`, `FORBIDDEN_PAYLOAD_PATTERNS` |
| new module | `relate.family.sources` |
| responsibility | Pure source-evidence construction and validation |
| compatibility facade | Explicit re-export |
| clean module imports experiments | no |
| scientific behaviour changed | no |
| protocol payload changed | no |
| protocol SHA changed | no |
| canonical artifacts changed | no |
| remaining historical responsibility | None for these symbols |
| future extraction stage | Stage 2B |
| known uncertainty | `validate_payload_firewall` and `payload_hash` are listed under `edges.py` in the problem statement but were placed in `sources.py` to avoid a circular import: `sources.py` needs `payload_hash` for `public_metadata_snapshot`, and `edges.py` imports `sources.py`. Placing them in `edges.py` would create `sources→edges→sources`. The boundary is functionally equivalent. |

#### `relate.family.edges`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `derive_edge_id`, `validate_rule_payload`, `validate_rule_semantics`, `validate_source_payload_binding`, `make_evidence_candidate`, `validate_evidence_candidate`, `evidence_candidate_from_record`, `make_manual_review_disposition`, `validate_manual_review_disposition`, `manual_review_disposition_from_record`, `resolve_evidence_candidate`, `make_evidence_edge` (wrapped — see below), `validate_evidence_edge`, `validate_resolved_edge`, `evidence_edge_from_record`, `PROTOCOL_VERSION`, `REVIEW_DISPOSITIONS` |
| new module | `relate.family.edges` |
| responsibility | Pure edge, candidate and review construction and validation |
| compatibility facade | Explicit re-export; `make_evidence_edge` wrapped (see below) |
| clean module imports experiments | no |
| scientific behaviour changed | no |
| protocol payload changed | no |
| protocol SHA changed | no |
| canonical artifacts changed | no |
| remaining historical responsibility | None for these symbols |
| future extraction stage | Stage 2B |
| known uncertainty | `make_evidence_edge` in the clean package accepts `protocol_sha256` as an explicit keyword argument. The historical module wraps it and supplies `protocol_contract()["protocol_sha256"]`. This keeps the clean domain module free from any dependency on the historical module. |

---

### Symbols deliberately left in the historical module

| Symbol | Reason |
|---|---|
| `FamilyGraphCacheIdentity` | `default_cache_identity` uses `sha256_file(Path(__file__))`, making the default runner source identity file-path-sensitive. Moving it to `relate.family` would change the hash. Deferred to Stage 2B. |
| `default_cache_identity` | Depends on `FamilyGraphCacheIdentity` and `__file__` |
| `FamilyGraphCache` | SQLite persistence — not a pure domain capability |
| `protocol_contract` | Assembles the full protocol contract from frozen inputs; references canonical artifact path |
| `verify_protocol_contract` | Canonical-input verification; reads artifact files |
| `verify_firewall_artifact` | Firewall artifact verification |
| `graph_component_*`, `family_outcome_*` | Graph construction and outcome calculation |
| `atomic_write_protocol` | File publication |
| `main`, argument parser | CLI entry point |
| `SCHEMA_ID`, `CACHE_SCHEMA_ID`, `D1_*`, `ALLOCATION_MANIFEST_SHA256`, `ALLOCATION_CONTEXT_SHA256` | Historical-only protocol constants; not pure domain |

---

### Cycles avoided

- `payload_hash` / `validate_payload_firewall` placed in `sources.py` (not `edges.py`) to
  avoid `sources → edges → sources` circular import.
- No circular imports were created inside `relate.family`.

---

### Apparently pure function deferred

- `FamilyGraphCacheIdentity` appears structurally pure but references `sha256_file(__file__)`.
  Moving it would change the default cache identity for future runs. Deferred to Stage 2B.

---

### Current callers inspected

| Caller | Uses | Action |
|---|---|---|
| `tests_current/integration/test_family_graph_cache_evidence.py` | `FamilyGraphCache`, `FamilyGraphCacheIdentity` | Both kept in historical module; no change required |
| `src/relate/evidence/canonical_json.py` | Reference in comments only | No action |

---

### Callers updated

None. The historical module continues to expose the same names via explicit re-exports.
No external caller required modification.

---

### Protocol compatibility verification

- Protocol SHA preserved exactly: `a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08`
- `git diff -- artifacts/canonical` is empty (confirmed)
- `historical.EvidenceEdge is clean.EvidenceEdge` → True (same Python object)

---

### Tests added

```text
tests_current/family/
  __init__.py
  test_repositories.py   — normalize, owner, commitment, manifest, validation
  test_rules.py          — taxonomy ordering, partition, required fields, contract
  test_sources.py        — source records, payload firewall, timestamps, metadata
  test_edges.py          — candidates, dispositions, edges, round-trip
  test_protocol_compatibility.py — object identity, data equality, no forbidden imports
```

---

### Recommended next PR

**Stage 2B — Family persistence extraction**

Move `FamilyGraphCache`, `FamilyGraphCacheIdentity`, `default_cache_identity` and their
SQLite schema into a clean `relate.family.store` module without executing the canonical graph.

---

## Stage 2B — Family Persistence Extraction

**Branch:** `architecture/family-persistence-extraction`

**New module:** `src/relate/family/store.py`

**PR classification:** `PERSISTENCE_EXTRACTION`

### Summary of what moved

`FamilyGraphCacheIdentity`, `CACHE_SCHEMA_ID`, `FamilyGraphCache` (full SQLite
schema, connection lifecycle, and every `put_*`/`get_*` method), and a new
explicit identity constructor `make_cache_identity` were extracted from
`relate.experiments.option_c0_family_connected_protocol` into
`relate.family.store`. The historical module was rewritten to import and
re-export these names, and to keep only `default_cache_identity` — the
source-hash-sensitive wrapper that cannot move without changing its meaning.

### Allowed dependency direction (achieved)

```text
historical protocol module
    -> relate.family.store
        -> relate.family.edges, relate.family.repositories, relate.family.sources
            -> relate.family.models
        -> relate.evidence.canonical_json, relate.evidence.sqlite
```

`relate.family.store` does not import `relate.experiments`, `relate.workflows`,
or `relate.cli`.

---

### Moved symbols

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `CACHE_SCHEMA_ID`, `FamilyGraphCacheIdentity`, `FamilyGraphCache` (all methods) |
| new module | `relate.family.store` |
| new symbols | `CACHE_SCHEMA_ID`, `FamilyGraphCacheIdentity`, `FamilyGraphCache`, `make_cache_identity` (new) |
| responsibility | Family-graph SQLite schema, connection lifecycle, identity binding, and record persistence/retrieval |
| compatibility facade | `from relate.family.store import (CACHE_SCHEMA_ID, FamilyGraphCache, FamilyGraphCacheIdentity, make_cache_identity)` at top of historical module |
| schema changed | no |
| identity keys changed | no |
| transaction semantics changed | no |
| scientific behaviour changed | no |
| canonical identity changed | no |
| workflow capability supported | initialise store; register allocation; register source evidence; record candidate; record review; record resolved edge; inspect stored records; enforce identity binding |
| remaining historical callers | `option_c0_family_connected_protocol` (`protocol_contract()`'s `cache_schema.identity_fields` reads `FamilyGraphCacheIdentity.__annotations__`; `default_cache_identity` calls `make_cache_identity`) |
| future extraction | Stage 2C — minimal workflow contracts; a later stage may add `put_component_memberships` / `put_phase_commitment` (generic) once a workflow needs them — see capability-continuity.md items 9–10 |
| known uncertainty | None found; see "Methods moved" and "Source-identity problem" below for full detail |

#### Methods moved with the class

Every method that was part of `FamilyGraphCache`'s responsibility moved, not
just the ones named in the extraction brief:

```text
__init__, close, __enter__, __exit__
_verify_pragmas, _create_schema, _bind_identity, _has_data_rows
put_allocation_repositories, put_canonical_allocation_manifest
put_evidence_candidate, get_evidence_candidate
put_manual_review_disposition, get_manual_review_disposition,
    get_final_disposition_for_candidate
put_resolved_edge, get_resolved_edge
put_source_record, get_source_record, get_source_registry
```

Nothing was left behind partially — the entire class body moved as one unit.

---

### Source-identity problem

The historical `default_cache_identity(family_protocol_sha256)` derives
`family_runner_source_identity = sha256_file(Path(__file__))`. `__file__` in
the historical module resolves to
`src/relate/experiments/option_c0_family_connected_protocol.py`. Moving this
function's body unchanged into `relate.family.store` would silently change
`__file__` to resolve to `store.py` instead, changing the resulting identity
value and misattributing store.py as the source that produced historical
runs.

To avoid that:

- `relate.family.store.make_cache_identity` takes every identity field,
  including `family_runner_source_identity`, as an explicit required keyword
  argument. It has no default and no opinion on how the caller derives its
  value.
- `default_cache_identity` remains in the historical module, unchanged in
  behaviour: it still computes `sha256_file(Path(__file__))` of *that*
  module and passes every field to `make_cache_identity` explicitly.
- A future workflow step must supply its own explicit
  `family_runner_source_identity` (e.g. the hash of the workflow module that
  actually executes the run) rather than inheriting the historical
  experiment module's identity. See capability-continuity.md item 2.

Verified in `tests_current/family/test_store_identity.py::TestHistoricalDefaultWrapper`:
`default_cache_identity`'s `family_runner_source_identity` equals
`sha256_file(Path(historical.__file__))` and is different from
`sha256_file(Path(relate.family.store.__file__))`.

---

### `ALLOCATION_MANIFEST_SHA256` — a second source-identity-shaped problem

`FamilyGraphCache.put_canonical_allocation_manifest` historically read the
module-global constant `ALLOCATION_MANIFEST_SHA256` (a frozen protocol
constant, defined in the historical module alongside `D1_RESULT_SHA256` and
`ALLOCATION_CONTEXT_SHA256`) as the expected manifest hash. That constant is
protocol-specific, not a generic persistence concern, so it could not be
imported into `relate.family.store` without creating a
`store -> relate.experiments` import — one of the explicit stop conditions
for this stage.

Resolution: `put_canonical_allocation_manifest` now reads the expected hash
from `self.identity.allocation_manifest_sha256` instead of the module
global. This is behaviour-preserving, not a redesign, because:

- `self.identity` is always bound during `__init__`, and `_bind_identity`
  already enforces (via `bind_cache_identity`) that a cache's stored
  identity exactly matches the identity it was opened with on every reopen;
- for every historical caller, `identity.allocation_manifest_sha256` was
  always set to `ALLOCATION_MANIFEST_SHA256` via `default_cache_identity`,
  so the effective value checked is unchanged for all existing callers;
- the method's public signature (`put_canonical_allocation_manifest(self,
  canonical_path)`) is unchanged, so no caller needed to change.

This mirrors the same design principle as the cache-identity source-identity
fix: a clean store must not hold an implicit opinion about which frozen
protocol produced its expected values — it reads that from the identity it
was explicitly constructed with. Verified in
`tests_current/family/test_store_records.py::TestAllocationRegistration`,
which computes the expected SHA-256 directly from the canonical manifest
file rather than importing the historical constant.

---

### Compatibility verification

- `historical.FamilyGraphCache is relate.family.store.FamilyGraphCache` → confirmed
- `historical.FamilyGraphCacheIdentity is relate.family.store.FamilyGraphCacheIdentity` → confirmed
- `historical.CACHE_SCHEMA_ID == relate.family.store.CACHE_SCHEMA_ID` → confirmed (same string)
- `historical.make_cache_identity is relate.family.store.make_cache_identity` → confirmed
- Protocol SHA preserved exactly: `a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08`
- `git diff -- artifacts/canonical` is empty (confirmed)
- All 60 quarantined tests in `tests/test_option_c0_family_connected_protocol.py` were
  run standalone (not re-enabled as an active suite) against the extracted code and
  passed unchanged, as an additional compatibility check per the preservation contract's
  "strongest applicable combination" guidance

---

### Tests added

```text
tests_current/family/
  test_store_identity.py       — identity mapping, reopen accept/reject, explicit
                                  constructor vs. historical source-sensitive wrapper
  test_store_schema.py         — exact table set, columns, keys, WAL pragmas
  test_store_records.py        — allocation, source record, candidate, disposition,
                                  and resolved-edge persistence, replay, and conflict
  test_store_resume.py         — close/reopen, identity enforcement across reopen,
                                  phase-commitment durability, partial-state inspection
  test_store_compatibility.py  — object identity, schema/record/exception equivalence
                                  through both import paths, protocol SHA unaffected
```

### Known limitations carried forward (not fixed in this PR)

- `component_memberships` and generic `phase_commitments` have no put/get API
  anywhere in the codebase (historical or clean); only their table schema and
  the one implicit allocation-phase write moved. See
  capability-continuity.md items 9–10.
- `build_components`, `component_commitment`, `edge_commitment`, `UnionFind`,
  `family_graph_outcome`, and `write_protocol_contract` remain in the
  historical module, unchanged, per "Do not move yet."

---

## Recommended Next Architecture Stage (immediately after Stage 2B)

**Stage 2C — Minimal workflow contracts and execution model**

Create only the small orchestration concepts RELATE needs — explicit steps, context,
results, commitments and tracing — without importing a general-purpose workflow
framework. This lets a future workflow compose the capabilities now available in
`relate.family.store` (initialise store, register allocation, register source
evidence, record candidate, record review, record resolved edge, inspect completed
phases, resume from committed state) into an explicit sequence, replacing the
historical monkey-patched `option_c0_*_entrypoint` chain for the family capability.
This stage should not build the canonical family-graph runner itself, execute the
graph, or start D2.

---

## Stage 2C — Minimal Workflow Contracts and Execution Model

**Branch:** `architecture/minimal-workflow-kernel`

**New package:** `src/relate/workflows/`

**PR classification:** `WORKFLOW_INFRASTRUCTURE`

### Summary

Created a small, deterministic workflow kernel: explicit ordered steps, an
immutable run context, a deterministic step-commitment chain, an injected
trace sink, honest blocked outcomes, fail-closed failures, and validated
completed-prefix resume. This is orchestration infrastructure only — no
family-specific step, no canonical-graph execution, and no persistence
change of any kind.

| Field | Value |
|---|---|
| new module | `src/relate/workflows/` (`__init__.py`, `errors.py`, `models.py`, `step.py`, `commitments.py`, `trace.py`, `runner.py`) |
| responsibility | Ordering, commitment chaining, trace recording, stop behaviour, and resume-prefix validation for explicit, already-constructed step objects |
| domain neutral | yes |
| imports experiments | no |
| imports family | no |
| scientific behaviour changed | no |
| canonical identity changed | no |
| persistence added | no |
| family workflow implemented | no |
| resume contract added | yes — `WorkflowCheckpoint` + `WorkflowRunner._validate_resume`; in-memory/serializable object contract only, no SQLite or file persistence |
| trace contract added | yes — `WorkflowTraceEvent` / `WorkflowTraceSink` protocol + `InMemoryTraceSink` / `NullTraceSink`; no SQLite tables, logging integrations, or network publication |
| known uncertainty | none found; see "Stop-condition checks" below |
| future consumer | a Stage 2D+ family workflow module composing `relate.family.store` operations as `WorkflowStep` objects |

### Existing concepts searched for and found (recorded per the extraction brief)

A repository-wide search for `workflow`, `runner`, `step`, `phase`,
`checkpoint`, `commitment`, `trace`, `resume`, and `stage_results` found **no
existing generic workflow/orchestration kernel**. The only overlapping
implementations are domain-specific and predate this stage:

- `IntegrityAuditCache` in `option_c0_d1_integrity_audit.py` implements its
  own `phases` / `phase_checkpoints` SQLite tables with
  `mark_phase_complete` / `load_phase_checkpoint` / `save_phase_checkpoint`
  methods. This is a persistence-backed, D1-audit-specific resume mechanism.
  It is unrelated to and not touched by the new in-memory
  `WorkflowCheckpoint` contract — the two solve the same general problem
  (resuming partial work) at different layers for different capabilities,
  and this PR does not attempt to unify them.
- `FamilyGraphCache.phase_commitments` (`relate/family/store.py`, Stage 2B)
  is a single implicit write (`"initial_allocation"` phase only), not a
  generic phase/checkpoint mechanism. See capability-continuity.md items 9–10.
- `option_c0_d1_integrity_audit.py`'s `ProgressReporter` and
  `option_c0_recovery_entrypoint.py`'s `ProgressReporter` /
  `install_phase_progress` are one-off console progress loggers, unrelated
  to workflow orchestration or resume.
- `option_c0_family_connected_protocol.py`'s `protocol_contract()` embeds a
  `progress_contract` dict (`phase_status_enum`, `checkpoint_cadence`,
  `phase_commitment_requirements`) as **documentation of intent**, not
  executable code. It reads as an aspirational spec for something like this
  workflow kernel, but was never implemented. This PR does not change that
  dict or wire it to `relate.workflows` in any way.

No existing abstraction conflicts with this design; nothing needed to be
reconciled or replaced.

### Public API

```text
relate.workflows
  JsonScalar, JsonValue, validate_json_value, tuple_to_json_list
  WorkflowContext, WorkflowDefinition
  StepStatus, StepResult, StepExecutionRecord
  WorkflowRunStatus, WorkflowRunResult, WorkflowCheckpoint, generate_run_id
  WorkflowStep
  RUN_IDENTITY_SCHEMA_ID, STEP_INPUT_SCHEMA_ID, STEP_OUTPUT_SCHEMA_ID
  run_identity_commitment, step_input_commitment, step_output_commitment
  WorkflowTraceEvent, WorkflowTraceEventType, WorkflowTraceSink,
  InMemoryTraceSink, NullTraceSink
  WorkflowRunner
  WorkflowError, WorkflowDefinitionError, WorkflowCommitmentError,
  WorkflowExecutionError, WorkflowResumeError
```

### Commitment design

Uses `relate.evidence.canonical_json.canonical_json_compact_unicode`
(`sort_keys=True`, `ensure_ascii=False`) and `relate.evidence.hashing.sha256_text`,
referenced under their real names rather than an ambiguous `as canonical_json`
alias, because this is a new contract with no historical caller — see the
module docstring in `relate/workflows/commitments.py` for the full reasoning.
Three versioned, workflow-specific schema identifiers were introduced —
`relate-workflow-run-identity-v1`, `relate-workflow-step-input-v1`,
`relate-workflow-step-output-v1` — distinct from any historical scientific
schema ID (e.g. `EDGE_SCHEMA_ID`, `CACHE_SCHEMA_ID`).

```text
run_identity_commitment  = sha256(canonical_json({
    schema_id, workflow_name, workflow_version, run_id, identity
}))
# repo_root, work_dir, and allowed_roles are excluded: paths are not
# scientific inputs, and allowed_roles is a visibility policy.

step_input_commitment  = sha256(canonical_json({
    schema_id, workflow_name, workflow_version,
    run_identity_commitment, step_name, step_version,
    prior_step_commitments (ordered list, not sorted)
}))

step_output_commitment = sha256(canonical_json({
    schema_id, step_name, step_version, input_commitment,
    status, commitment_payload, blocked_reason
}))
```

Timestamps and latency are never part of any commitment; they live only in
`WorkflowTraceEvent` (see `relate/workflows/trace.py`). `commitment_payload`
is explicitly re-validated inside `step_output_commitment` (not merely
trusted from a prior `StepResult` construction) so that resume validation,
which recomputes commitments directly from stored records, gets the same
non-finite-float and non-JSON-value rejection as fresh execution.

### Bug caught and fixed during self-review

The first draft of `step_output_commitment` passed `commitment_payload`
straight into `canonical_json_compact_unicode(...)` without calling
`validate_json_value` on it first. Because Python's `json.dumps` allows
`Infinity`/`NaN`/`-Infinity` by default (non-standard JSON, but not
rejected), a non-finite float would have silently produced a commitment
instead of raising `WorkflowCommitmentError`, and an arbitrary object would
have raised a raw `TypeError` instead of the kernel's own error type. Fixed
by validating `commitment_payload` explicitly inside `step_output_commitment`
itself, so the guarantee holds for every call path, not only calls that go
through `StepResult`.

### Execution, blocked, and failure semantics

- `WorkflowRunner.run` executes `WorkflowDefinition.steps` in declared
  order, threading a growing list of prior output commitments into each
  step's input commitment.
- A step returning `StepResult.blocked(...)` stops the run immediately;
  the runner returns `WorkflowRunResult(status=BLOCKED, ...)` with every
  record collected so far, including the blocked one. Later steps never run.
- Any exception raised by `step.execute(...)` (or a step returning something
  other than a `StepResult`) is caught, a `STEP_FAILED` trace event is
  recorded, and `WorkflowExecutionError` is raised with `.cause` (the
  original exception, also set as `__cause__`), `.failed_step_name`, and
  `.partial_records` (every record completed before the failure). The
  failed step itself never produces a record. There is no automatic retry
  and no swallowed exception.
- `WorkflowRunResult.completed_checkpoint()` returns only `COMPLETED`
  records — a blocked step is never part of a checkpoint. Constructing a
  `WorkflowCheckpoint` directly with a non-`COMPLETED` record raises
  `WorkflowDefinitionError` at the object's own `__post_init__`, independent
  of any specific runner or context.

### Resume validation

`WorkflowRunner.run(context, resume_from=checkpoint)` validates, in order:
workflow name match, workflow version match, run identity (`run_id`) match,
checkpoint length not exceeding the declared step count, and then for every
checkpointed record in position order: step name/version match against the
declared step at that position, `COMPLETED` status, and exact recomputation
of both the input and output commitments from the context and the record's
own stored `StepResult`. Any mismatch raises `WorkflowResumeError`. A fully
valid prefix is skipped without re-executing those steps; a fully complete
checkpoint returns `COMPLETED` with zero step executions.

This is deliberately **not** connected to `FamilyGraphCache.phase_commitments`
in this PR — Stage 2C defines and tests the in-memory checkpoint contract
only, per the extraction brief.

### Trace design

`WorkflowTraceSink.record(event)` receives a `STEP_STARTED` event before a
step runs and exactly one of `STEP_COMPLETED` / `STEP_BLOCKED` /
`STEP_FAILED` after. Events carry commitments and bounded metadata
(`blocked_reason`, `failure_message`) but never the step's `output` payload,
avoiding accidental leakage of protected data into traces by default.
`timestamp` and `latency_seconds` are present for observability but are
never fed back into any commitment. `InMemoryTraceSink.events` returns a
defensive tuple copy; `NullTraceSink` discards everything.

### Dependency-boundary verification

- `tests_current/workflows/test_dependency_boundaries.py` parses every
  `.py` file under `src/relate/workflows/` with `ast` and asserts no import
  of `relate.experiments`, `relate.family`, or `relate.cli`.
- Manual grep confirms the same; the only textual mentions of
  `relate.experiments` inside the new package are in docstrings explaining
  what must *not* be imported.
- `relate.workflows` imports only the Python standard library and
  `relate.evidence.canonical_json` / `relate.evidence.hashing`.

### Tests added

```text
tests_current/workflows/
  test_models.py                — immutable context, defensive copies, workflow/step
                                   validation, JSON-value validation, result invariants
  test_commitments.py           — determinism, mapping-order independence, prior-step
                                   order/version/identity/payload/blocked-reason
                                   sensitivity, Unicode stability, non-finite/unsupported
                                   value rejection
  test_runner.py                — ordered execution, single execution per step, prior
                                   result visibility, commitment chaining, no mutable
                                   context leakage, trace ordering
  test_blocked_execution.py     — bounded reason requirement, blocked run status, blocked
                                   record retention, later-step suppression, checkpoint
                                   exclusion of blocked steps
  test_failure_execution.py     — cause preservation, failed-step name, partial-record
                                   retention, no completed record for the failed step,
                                   later-step suppression, failure trace emission
  test_resume.py                — valid prefix acceptance, next-step execution, full-
                                   prefix no-op, and rejection of every invalid variant
                                   (name/version/identity/version/order/gap/unknown
                                   step/tampered commitments/blocked-as-completed)
  test_trace.py                 — timestamp/latency independence from commitments,
                                   start/finish delivery, commitment presence, payload
                                   omission, defensive sink copies
  test_dependency_boundaries.py — no forbidden imports anywhere in the package
```

### Compatibility and scientific verification

- `git diff -- artifacts/canonical` empty (confirmed)
- `historical.protocol_contract()["protocol_sha256"]` still equals
  `a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08` (confirmed)
- `relate.family.store` schema, cache identity keys, and allocation logic
  untouched by this PR (no files under `src/relate/family/` were modified)
- No canonical family graph executed; no C0 selection or C1 reserve row
  content accessed; D2 not started

### Stop-condition checks

None of the listed stop conditions were triggered:

- commitments never required serializing an arbitrary Python object (the
  one near-miss — non-finite floats bypassing validation — was caught and
  fixed before merge, see "Bug caught and fixed during self-review" above);
- the workflow kernel never needed to import family or experiment code;
- resume validation is fully deterministic (pure recomputation and
  comparison, no I/O, no clock);
- prior results are represented via a read-only `MappingProxyType` view
  rebuilt per step, not mutable shared state;
- no commitment includes a timestamp or latency;
- no persistence change was required or made;
- no family-store schema change was required or made;
- no hidden-row access was needed anywhere in this PR;
- no canonical artifact changed; no protocol SHA changed;
- no scientific code changed to make the kernel work;
- the one existing "workflow-shaped" prior implementation
  (`IntegrityAuditCache`'s phase/checkpoint tables) is domain-specific and
  does not materially conflict with this generic, non-persistent design —
  see "Existing concepts searched for and found" above.

---

## Recommended Next Architecture Stage (immediately after Stage 2C)

**Stage 2D — Family Graph and Outcome Capability Extraction**

Extract `UnionFind`, component construction, component commitments, edge
commitments, graph completeness checks, and bounded family outcome
calculation from `option_c0_family_connected_protocol.py` into clean
`relate.family` modules. Add only the minimal clean family-store interfaces
required for component memberships and phase commitments (capability-
continuity.md items 9 and 10) — no more than what the graph-extraction and
persistence work actually needs. This stage must still not execute the
canonical family graph, and should not yet compose these capabilities into
a `relate.workflows`-based family workflow (that remains a later stage).

---

## Stage 2D — Family Graph and Outcome Capability Extraction

**Branch:** `architecture/family-graph-outcome-extraction`

**New modules:** `src/relate/family/graph.py`, `src/relate/family/commitments.py`,
`src/relate/family/outcome.py`

**PR classification:** `GRAPH_CAPABILITY_EXTRACTION`

### Summary

Extracted the remaining pure graph-construction, graph-specific commitment,
and bounded-outcome logic from `option_c0_family_connected_protocol.py` into
three clean modules, and added the first public persistence API for
`component_memberships` and a general-purpose `phase_commitments` API to
`relate.family.store`. This completes the clean destination for every
graph/outcome capability named in the continuity ledger; no canonical
family graph was implemented, executed, or published.

### Moved symbols

#### `relate.family.graph`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `UnionFind`, `component_id`, `_reject_duplicate_edges`, `build_components` |
| new module | `relate.family.graph` |
| responsibility | Pure connected-component construction over resolved family edges; no database access, file I/O, or CLI |
| compatibility facade | `from relate.family.graph import UnionFind, build_components, component_id` at top of historical module; no wrapper needed |
| scientific behaviour changed | no |
| graph semantics changed | no |
| protocol payload changed | no |
| protocol SHA changed | no |
| store schema changed | no |
| new store interfaces | n/a (this module) |
| remaining historical responsibility | none for these symbols |
| future workflow consumer | a "build family components" `WorkflowStep` (Stage 2E or later) |
| known uncertainty | `_reject_duplicate_edges` has no external callers (grep-confirmed) and is not re-exported from the historical module; it is used internally by `relate.family.commitments.edge_commitment` via a direct intra-package import |

#### `relate.family.commitments`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `component_commitment`, `edge_commitment` |
| new module | `relate.family.commitments` |
| responsibility | Deterministic SHA-256 commitments over resolved edges and connected components |
| compatibility facade | Historical module keeps thin wrappers (`component_commitment`, `edge_commitment`) that supply `protocol_contract()["protocol_sha256"]` as the default, exactly as `make_evidence_edge` was wrapped in Stage 2A |
| scientific behaviour changed | no |
| graph semantics changed | no |
| edge/component commitment changed | no — same serializer (`canonical_json_compact_unicode`), same field order, same sorting, same SHA-256 construction |
| protocol payload changed | no |
| protocol SHA changed | no |
| store schema changed | no |
| new store interfaces | n/a (this module) |
| remaining historical responsibility | the two wrapper functions only (protocol_contract() lookup) |
| future workflow consumer | "calculate family outcome" / commitment-recording steps (Stage 2E or later) |
| known uncertainty | Both clean functions require `protocol_sha256` explicitly (no default) to avoid importing `relate.experiments.protocol_contract`. This is a signature change from the historical module's own `component_commitment` (which had no `protocol_sha256` parameter at all) and `edge_commitment` (which had `protocol_sha256: str \| None = None`). The **historical module's own call signature is unchanged** — this only affects direct callers of the new `relate.family.commitments` functions, which did not exist before this PR. See "Source-identity note" in `commitments.py`'s docstring. |

#### `relate.family.outcome`

| Field | Value |
|---|---|
| old module | `relate.experiments.option_c0_family_connected_protocol` |
| old symbols | `graph_completeness`, `family_graph_outcome` |
| new module | `relate.family.outcome` |
| responsibility | Bounded graph-completeness checks and the frozen family-outcome decision; never concludes contamination, materiality, reallocation, or D2 authorization |
| compatibility facade | `from relate.family.outcome import family_graph_outcome, graph_completeness` at top of historical module; no wrapper needed (neither function ever read `protocol_contract()`) |
| scientific behaviour changed | no |
| outcome semantics changed | no — all four frozen outcome strings, and every payload field, are byte-for-byte identical |
| protocol payload changed | no |
| protocol SHA changed | no |
| store schema changed | no |
| new store interfaces | n/a (this module) |
| remaining historical responsibility | none for these symbols |
| future workflow consumer | "analyse role crossings" / "calculate bounded outcome" steps (Stage 2E or later) |
| known uncertainty | There is no current implementation anywhere in the repository of "cross-role component detection" or "role-pair summaries" that computes `cross_role_connecting_components` from components and allocation roles. `family_graph_outcome` has always only consumed an already-computed integer. This module does not invent that missing computation — see capability-continuity.md for this recorded gap |

### Repository-wide search for overlapping concepts

Searched for `UnionFind`, `build_components`, `component_commitment`,
`edge_commitment`, `family_graph_outcome`, `graph completeness`,
`cross-role`, `component_memberships`, `phase_commitments`, `connecting
edges`, `unresolved candidates`, `metadata completeness`. Findings:

- All symbol definitions and callers existed only in
  `option_c0_family_connected_protocol.py` and the quarantined
  `tests/test_option_c0_family_connected_protocol.py`. No other production
  module defines or calls any of them.
- `component_id` also appears as a SQLite **column name** in the
  `component_memberships` table (`relate/family/store.py`) and in one test
  assertion (`tests_current/family/test_store_schema.py:94`) — unrelated to
  the Python function of the same name; not a caller.
- "cross_role" appears extensively in `option_c0_d1_integrity_audit.py` and
  `option_c0_d1_overlap_classification.py`, but those are D1 duplicate/
  overlap-detection diagnostics with their own unrelated `cross_role_*`
  dict keys (hash/row/repository counts for the D1 audit) — not the family
  graph's `cross_role_connecting_components` concept, and not touched by
  this PR.

No capability was found with an implementation this PR failed to account
for.

### Store: new persistence interfaces (`relate/family/store.py`)

Stage 2B recorded two gaps: `component_memberships` had schema only, and
`phase_commitments` had only one implicit write. This PR adds:

| Method | Behaviour |
|---|---|
| `put_component_memberships(components)` | Whole-graph replace: compares the *complete* existing membership set to the *complete* incoming set before writing anything. Identical replay accepted; any other existing set rejected outright (never partially overwritten). Validates every repository already exists in `allocation_repositories`, rejects empty/malformed component IDs, rejects a repository appearing in two components. Input shape matches `relate.family.graph.build_components`'s output exactly. |
| `get_component_memberships()` | Returns the same shape as `build_components`' output, grouped and ordered deterministically by `component_id` then `repository`. |
| `put_phase_commitment(phase, *, status, commitment_sha256, metadata)` | **New, general-purpose, reject-on-conflict** API for phases other than `initial_allocation`. Validates non-empty phase/status and a well-formed SHA-256. Identical replay accepted; conflicting replay rejected. |
| `get_phase_commitment(phase)` / `list_phase_commitments()` | Return `PhaseCommitmentRecord` (new frozen dataclass with a defensively-copied `metadata` mapping), ordered deterministically by `phase` for the list form. |
| `list_allocation_repositories()`, `list_evidence_candidates()`, `list_resolved_edges()` | Deterministic readers (sorted by natural key) exposing already-persisted data, so a future graph/outcome workflow step never needs `store.connection.execute(...)` directly. |

**The existing implicit `"initial_allocation"` write inside
`put_allocation_repositories` is completely unchanged** — it still uses its
original `INSERT ... ON CONFLICT DO UPDATE` (upsert) path. `put_phase_commitment`
is a deliberately separate method with reject-on-conflict semantics
(consistent with every other `put_*` method in the store), added *alongside*
the existing behaviour rather than replacing it, per the extraction brief's
explicit instruction not to silently change that historical transaction
path.

`PhaseCommitmentRecord` is **not** the Stage 2C `WorkflowCheckpoint` and is
never used to persist one — the two remain distinct concepts (see
`commitments.py`'s and `store.py`'s docstrings).

No `CREATE TABLE` statement changed. `git diff` on `_create_schema()` is empty.

### Compatibility verification

- `historical.UnionFind is clean.UnionFind` → confirmed
- `historical.build_components is clean.build_components` → confirmed
- `historical.component_id is clean.component_id` → confirmed
- `historical.family_graph_outcome is clean.family_graph_outcome` → confirmed
- `historical.graph_completeness is clean.graph_completeness` → confirmed
- `historical.component_commitment(...)` and `historical.edge_commitment(...)`
  (using the implicit `protocol_contract()` fallback) produce byte-identical
  output to the clean functions called with the explicit protocol SHA
- Protocol SHA preserved exactly: `a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08`
- `git diff -- artifacts/canonical` is empty (confirmed)
- All 60 quarantined tests in `tests/test_option_c0_family_connected_protocol.py`
  were run standalone (not re-enabled) against the extracted code and passed
  unchanged

### Tests added

```text
tests_current/family/
  test_graph.py               — UnionFind, component_id, build_components: isolated
                                 repos, connecting/nonconnecting/rejected edges,
                                 transitive closure, ordering, duplicates, unknown
                                 endpoints, full allocation coverage
  test_graph_commitments.py   — edge/component commitment determinism, order
                                 independence, content/membership sensitivity,
                                 Unicode stability, rejection, historical-wrapper
                                 equivalence
  test_outcome.py             — every frozen outcome string, fail-closed priority
                                 ordering, the never-concludes-contamination
                                 invariant across parametrized inputs, graph_completeness
  test_store_components.py    — component-membership insertion, replay, conflict,
                                 unknown-repository rejection, no partial state,
                                 close/reopen persistence
  test_store_phase_commitments.py — phase-commitment insertion, replay, conflict,
                                 malformed-hash rejection, deterministic metadata
                                 serialization, list ordering, initial_allocation
                                 compatibility
  test_graph_compatibility.py — object identity, behavioural equivalence, exception
                                 equivalence, protocol SHA unaffected, dependency
                                 boundary checks
```

### Stop-condition checks

None of the listed stop conditions were triggered:

- graph output, component ordering, and component IDs are unchanged for
  identical synthetic inputs (verified via `test_graph_compatibility.py` and
  direct comparison in `test_graph.py`);
- edge and component commitments are unchanged (verified in
  `test_graph_commitments.py`);
- no frozen outcome string or payload field changed;
- completeness checks agree between the old and new code paths (same
  function objects);
- no graph logic required reading protected row contents;
- no clean family module needed to import an experiment module — resolved
  the one near-miss (`component_commitment`/`edge_commitment`'s implicit
  `protocol_contract()` lookup) with the explicit-parameter + historical-wrapper
  pattern, exactly as done for `make_evidence_edge` in Stage 2A;
- no store schema change occurred;
- `initial_allocation` phase semantics are unchanged (still the original
  upsert path; the new `put_phase_commitment` is additive, not a replacement);
- no idempotent replay became conflicting, and no conflicting replay was
  accepted, for any of the new or existing store methods;
- protocol payload and SHA are unchanged;
- no canonical files changed;
- graph extraction was cleanly separable from publication and CLI behaviour
  (`protocol_contract`, `write_protocol_contract`, `main`, and the argument
  parser all remain untouched in the historical module).

---

## Stage 2E — Family Input Verification and Explicit Workflow Composition

Stage 2E extracts frozen-input verification and composes the first explicit
noncanonical family workflow. The workflow sequence is fixed:
`verify_family_inputs`, `register_allocation`, `register_prepared_evidence`,
`resolve_candidates`, `assess_graph_readiness`, `build_family_components`,
`analyse_role_crossings`, `determine_family_outcome`.

The composed workflow is noncanonical only. It rejects any configured work,
store, allocation, firewall, D1, or D1.1 path contained under
`artifacts/canonical` using resolved path containment, while the historical
verification wrapper remains able to read canonical files for compatibility.
No canonical graph execution or publication step exists.

Identity schemas added:

- `relate-family-workflow-source-manifest-v1` binds an explicit sorted list of
  execution-critical source files by repository-relative POSIX path and file
  SHA-256. It contains no timestamps or absolute paths. Composition recomputes
  this value and rejects a caller-supplied mismatch.
- `relate-family-evidence-bundle-v1` binds prepared source records,
  candidates, dispositions, and incomplete metadata count. Dispositions are
  checked against the configured family protocol SHA before durable writes.
- `relate-family-role-crossing-analysis-v1` binds bounded role-crossing facts
  and the family protocol SHA.
- `relate-family-bounded-outcome-v1` binds the frozen bounded family outcome
  and the family protocol SHA.

`allowed_roles` now has behavioral meaning: every allocation role processed by
the workflow must be explicitly authorized, and unknown or empty role sets are
rejected. Allocation repository commitment is verified at the input boundary
and after allocation registration.

Resolved-edge and graph-readiness phases are now durably recorded via
`FamilyGraphCache.put_phase_commitment`. Blocked readiness records an
`INCOMPLETE` family phase before returning `BLOCKED`; invariant, identity,
hash, firewall, stale evidence, and tampered component failures raise through
the generic runner as `WorkflowExecutionError`.

Changed-evidence/store rule: a changed evidence bundle changes the workflow
run identity commitment and requires a fresh workflow run ID and fresh family
store path. Identical replay may reuse the same store; a changed bundle must
not resume the old checkpoint chain or reuse populated durable state.

Hard/exact decision: authoritative support exists in
`docs/protocols/option-c0-family-connected-allocation-protocol-v1.md`, whose
Decision Rule names `hard_or_exact_fit_iteration_crossing_observed` and whose
Evidence Model lists `EXACT_AST_WITH_CORROBORATING_PROVENANCE` as the exact
conditional connecting edge. The implementation therefore includes it in the
hard-or-exact taxonomy without changing the frozen edge rules or protocol
payload.

Historical compatibility remains bounded to verification facades and the
historical CLI. The workflow does not publish, does not alter allocation, does
not access C0 selection or C1 reserve row contents, does not infer materiality,
does not authorize reallocation, and does not start D2.

---

## Recommended Next Architecture Stage (immediately after Stage 2E)

## Stage 2F — Family Review and Publication Boundary

Stage 2F introduces the explicit boundary between a completed Stage 2E
noncanonical workflow and any publication.

New modules:

- `relate.workflows.validation` — public non-executing validation for a
  completed workflow result and commitment chain.
- `relate.family.review` — deterministic `relate-family-review-packet-v1`
  packets for bounded family facts only.
- `relate.family.publication` — human publication dispositions
  (`relate-family-publication-disposition-v1`) and immutable noncanonical
  publication bundles (`relate-family-publication-bundle-v1`).

The review packet validation chain checks the exact Stage 2E workflow name,
version, step order and step versions; validates the completed workflow
commitment chain; recomputes workflow source identity; reopens the bound
family store; recomputes resolved-edge, component, role-analysis and bounded
outcome commitments; checks durable phase commitments; and rejects canonical
work/store paths.

The packet is machine-readable about scope:

- `publication_scope = BOUNDED_FAMILY_RESULT_ONLY`;
- `packet_contains = BOUNDED_FAMILY_GRAPH_FACTS_ONLY`;
- `not_concluded` includes material contamination, materiality threshold,
  reallocation required, and D2 authorization.

Mechanically derived materiality inputs now include affected role pairs,
aggregate rows, largest crossing component, affected C0 fit/iteration row
fractions, and hard/conditional cross-role edge counts. Allocation feasibility
is explicitly `NOT_ASSESSED`; no solver or materiality threshold was added.

Publication requires a human disposition of
`AUTHORIZE_BOUNDED_REVIEW_PUBLICATION`. `WITHHOLD_BOUNDED_REVIEW_PUBLICATION`
cannot publish. The disposition authorizes only immutable noncanonical bounded
review publication. It does not authorize materiality, reallocation, canonical
execution, canonical publication, or D2.

Destination enforcement rejects any resolved target or parent under
`artifacts/canonical`, refuses existing targets, writes through
`atomic_write_json`, and returns a receipt with logical bundle commitment and
published file SHA-256 as separate identities.

Historical publication compatibility: `write_protocol_contract` remains the
historical frozen-protocol writer. Stage 2F does not extract or alter it, so
its output bytes and overwrite behavior remain unchanged.

Canonical family graph execution, canonical family result publication,
allocation changes, reallocation, materiality, and D2 remain gated.

---

## Recommended Next Architecture Stage (immediately after Stage 2F)

**Stage 2G — Supported Family CLI and Canonical Execution Authorization**

Provide a thin supported entrypoint and explicit authorization gate. Canonical
execution itself must remain a separately reviewed act rather than an
automatic consequence of merging code.

---

## Longer-Term Follow-On (not the immediate next stage)

**Stage C — Domain decomposition of capability stores**

Split `FamilyGraphCache`, `IntegrityAuditCache` and `OptionC0EmbeddingCache` into separate
capability packages, completing the boundary established in Stage A and Stage B. Also wire
`relate.evidence.immutable.refuse_overwrite` into the remaining inline `if path.exists(): raise`
patterns. Migrate `_sha256_json` compound functions in data-firewall modules once the serializer
and hashing steps are cleanly separated by domain decomposition.

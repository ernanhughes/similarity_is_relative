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

## Recommended Next Architecture Stage (post-Stage 2B)

**Stage C — Domain decomposition of capability stores**

Split `FamilyGraphCache`, `IntegrityAuditCache` and `OptionC0EmbeddingCache` into separate
capability packages, completing the boundary established in Stage A and Stage B. Also wire
`relate.evidence.immutable.refuse_overwrite` into the remaining inline `if path.exists(): raise`
patterns. Migrate `_sha256_json` compound functions in data-firewall modules once the serializer
and hashing steps are cleanly separated by domain decomposition.

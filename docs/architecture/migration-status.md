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

## Recommended Next Architecture Stage

**Stage C — Domain decomposition of capability stores**

Split `FamilyGraphCache`, `IntegrityAuditCache` and `OptionC0EmbeddingCache` into separate
capability packages, completing the boundary established in Stage A and Stage B. Also wire
`relate.evidence.immutable.refuse_overwrite` into the remaining inline `if path.exists(): raise`
patterns. Migrate `_sha256_json` compound functions in data-firewall modules once the serializer
and hashing steps are cleanly separated by domain decomposition.

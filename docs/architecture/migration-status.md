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

#### `enforce_wal_pragmas` / `verify_wal_pragmas` / `bind_cache_identity`

| Field | Value |
|---|---|
| old module | various (inline in class `__init__` and instance methods of `FamilyGraphCache`, `IntegrityAuditCache`, `OptionC0EmbeddingCache`) |
| old symbol | (inline, no shared module-level name) |
| new module | `relate.evidence.sqlite` |
| new symbol | `enforce_wal_pragmas`, `verify_wal_pragmas`, `bind_cache_identity` |
| compatibility facade | not yet wired — class methods still contain inline pragma code |
| scientific behaviour changed | no |
| canonical identity affected | no |
| remaining callers | `FamilyGraphCache.__init__` / `_verify_pragmas`, `IntegrityAuditCache.__init__` / `verify_pragmas`, `OptionC0EmbeddingCache.__init__` |
| deletion eligibility | not yet — class method wiring is a later step |
| notes | Wiring these helpers into existing class methods requires touching class structure; deferred to a later capability decomposition PR. |

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

None identified in this PR. All extracted functions produce byte-identical output
to their historical counterparts. No canonical files were touched.

---

## Recommended Next Extraction Stage

**Stage B — Remaining hashing callers**

Migrate `_sha256_file` in `option_b_identity`, `option_b_identity_v2`, `option_b_probe_runner`,
`option_b_hard_negative_manifest`, `option_c0_discovery_entrypoint`, and
`option_c0_d1_overlap_classification` to use `relate.evidence.hashing`.

Also wire `enforce_wal_pragmas` and `verify_wal_pragmas` into the three SQLite cache classes
to replace their inline pragma code, and wire `bind_cache_identity` into `FamilyGraphCache._bind_identity`.

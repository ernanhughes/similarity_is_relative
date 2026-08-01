# Option B chunk and cache recovery hardening

Date: 2026-08-02

## Status

```text
Canonical selection v2: COMPLETE
Predicted executor contract: COMPLETE
Embedding identity v2: COMPLETE
Chunk/cache recovery hardening: COMPLETE IN IMPLEMENTATION
Canonical embeddings v2: NOT GENERATED
Primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE EMBEDDING PUBLICATION
```

## Extraction fingerprint

Every split run receives a complete SHA-256 fingerprint covering:

- the immutable identity-v2 file hash and identity ID;
- frozen model repository and revision;
- executed embedding-implementation hash;
- tokenization-configuration hash and payload;
- pooling policy, output dtype and maximum length;
- split and canonical selection-manifest hash;
- ordered stable-key and source-code hash sequences;
- row count and batch size;
- Python, NumPy, Torch, Transformers, Tokenizers, device, CUDA runtime and GPU identity.

Changing any material input creates a different fingerprint and therefore a different
chunk namespace and SQLite embedding-cache key.

## Chunk recovery

Chunks are stored under:

```text
chunks/<extraction-fingerprint>/<split>/<start>-<end>.npy
chunks/<extraction-fingerprint>/<split>/<start>-<end>.json
```

A chunk is reusable only in `read-write` mode and only when its sidecar verifies:

- fingerprint, split and row range;
- ordered stable-key and source-code hash sequences;
- rows, shape, dtype and dimensions;
- finite float32 values;
- logical array SHA-256;
- exact `.npy` file SHA-256.

A missing, malformed, stale or tampered sidecar or payload is never reused. The row-level
v2 SQLite cache may still satisfy the recomputation when its independently verified
fingerprint and payload identities match.

Legacy unfingerprinted chunks are outside the new namespace and cannot be canonical
evidence.

## Cache recovery

The hardened path uses a new `embeddings_v2` SQLite table. It does not read the legacy
embedding table. Each vector is keyed by:

```text
stable key
source-code SHA-256
complete extraction-fingerprint SHA-256
```

Reads verify dtype, dimensions, finite values, raw payload SHA-256 and logical array
SHA-256. Corrupt or mismatched rows are treated as misses and recomputed.

Source-code cache behaviour remains tied to the frozen dataset revision, selection
manifest and code hash.

## Cache modes

- `read-write` may reuse only fully verified v2 chunks and cache rows.
- `refresh` bypasses all chunk and embedding-cache reads, recomputes, and replaces v2 rows.
- `off` bypasses all cache and chunk reads.
- New chunks and final matrices are written atomically through temporary files and
  `os.replace`.

## Scientific boundary

This stage hardens recovery only. It does not generate or publish the canonical A/B
embedding checkpoint, fit probes, create hard negatives, evaluate retrieval, calculate
the registered gap, or observe the scientific result.

The frozen decision remains:

```text
gap = predicted_executor_accuracy - max(raw_cosine_accuracy, raw_euclidean_accuracy)

gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

## Next permitted stage

After this PR is merged, run two independent embedding extractions in fresh output
directories and separate SQLite databases. Both runs must pass identity-v2 fixture
preflight and produce matching logical array hashes for train, validation and test.

The next bounded stage is **PR 7 — independent embedding runs and checkpoint**.

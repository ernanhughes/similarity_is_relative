# Option B embedding identity v2

Date: 2026-08-01

## Status

```text
Canonical selection v2: COMPLETE
Predicted executor contract: COMPLETE
Embedding identity v2 implementation: COMPLETE
Embedding identity v2 artifact: NOT YET PUBLISHED
Chunk/cache recovery hardening: NOT COMPLETE
Canonical embeddings v2: NOT GENERATED
Primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE EMBEDDING EXTRACTION
```

## Shared canonical implementation

Identity capture and canonical extraction now execute the same top-level functions in
`option_b_embedding.py`. The recorded implementation hash covers tokenizer-side
configuration, canonical tokenization, model inference, attention-mask mean pooling,
and ordered batch assembly.

The frozen tokenization and pooling configuration is:

```text
add_special_tokens = true
padding = max_length
truncation = true
max_length = 256
padding_side = right
truncation_side = right
return_tensors = pt
pooling = attention-mask mean pooling
output_dtype = float32
```

A separate digest covers this complete configuration payload.

## Identity-v2 capture

Identity v2 inherits the exact model and dataset revisions from immutable identity v1;
it does not ask the Hub for newer revisions. Capture is restricted to CPU and records:

- the identity-v1 predecessor file hash;
- exact model and dataset revisions;
- tokenizer file hashes;
- canonical tokenization configuration and digest;
- the implementation hash of the functions that actually execute;
- ten fixture code identities and per-row embedding hashes;
- the fixture matrix hash and environment versions.

The fixture must be exactly equal when evaluated as one ten-row batch, two five-row
batches, and ten one-row batches. Identity publication aborts if exact logical-array
invariance is not demonstrated.

## Mandatory extraction preflight

Every embedding extraction loads the pinned tokenizer and model and recomputes the
identity-v2 fixture before it may reconstruct CodeSearchNet rows or access the SQLite
or chunk layers. Any implementation, tokenization, code-row, per-vector, or matrix
hash mismatch aborts extraction.

The extractor now consumes canonical selection v2 and writes versioned v2 embedding
names. Existing v1 identity and embedding records remain immutable historical records.

## GPU boundary

Identity v2 is captured on the pinned CPU path. A CUDA extraction is acceptable only
if its mandatory fixture preflight reproduces the exact CPU logical-array hashes. A
faster GPU run that does not reproduce those hashes is not canonical evidence and must
not proceed to dataset reconstruction.

## Publish the identity artifact

From a clean checkout of this branch:

```powershell
python -m pip install -e ".[dev,option-b]"

relate-option-b-freeze-v2 `
    --output "runs/option-b/identity/option-b-embedding-identity-v2.json" `
    --device cpu
```

If capture succeeds, inspect the artifact and promote it without editing:

```powershell
Copy-Item `
    "runs/option-b/identity/option-b-embedding-identity-v2.json" `
    "artifacts/canonical/option-b/option-b-embedding-identity-v2.json"
```

Then run the focused and complete checks:

```powershell
python -m pytest -q `
    tests/test_option_b_embedding.py `
    tests/test_option_b_identity_v2.py `
    tests/test_option_b_embeddings.py

python -m pytest -q
ruff check .
```

The identity artifact, its exact file hash, and passing checks must be committed before
this PR is ready for merge.

## Scientific boundary

This stage does not generate canonical train, validation, or test embeddings; fit any
probe; generate hard negatives; calculate retrieval accuracy; calculate the registered
gap; or observe the scientific result.

## Next permitted stage

After identity v2 is published and this PR is merged, the next bounded stage is
**PR 6 — chunk and cache recovery hardening**. Canonical embedding extraction remains
blocked until PR 6 is complete.

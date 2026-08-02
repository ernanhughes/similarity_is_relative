# Option B independent embedding reproduction

Date: 2026-08-02

## Status

```text
Canonical selection v2: COMPLETE
Predicted executor contract: COMPLETE
Embedding identity v2: COMPLETE
Chunk/cache recovery hardening: COMPLETE
CUDA environment preflight: NOT YET RUN
Embedding run A: NOT YET RUN
Embedding run B: NOT YET RUN
Independent embedding checkpoint: NOT YET PUBLISHED
Primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE PROBE FITTING
```

## Scope

This stage produces and verifies the frozen CodeBERT embedding arrays only. It does not
fit primitive probes, generate predicted primitive vectors, construct hard negatives,
evaluate retrieval accuracy, calculate the registered gap, or inspect the scientific
result.

## Environment preflight

Before starting a full GPU extraction, the candidate CUDA environment must reproduce the
immutable CPU identity-v2 fixture exactly:

```powershell
relate-option-b-embed-preflight `
    --identity "artifacts/canonical/option-b/option-b-embedding-identity-v2.json" `
    --device cuda
```

A successful preflight reports:

```text
EMBEDDING_ENVIRONMENT_PREFLIGHT_VERIFIED
EMBEDDING_FIXTURE_PREFLIGHT_VERIFIED
```

Failure is a hard stop. Do not weaken fixture equality and do not start a CUDA canonical
run. If CUDA cannot reproduce the CPU fixture exactly, both independent canonical runs
must use CPU and the final verifier must be called with `--required-device cpu`.

## Independent run requirements

Run A and Run B must use:

- different fresh output directories;
- different fresh SQLite databases;
- the same identity-v2 artifact;
- the same canonical selection-v2 manifests;
- the same batch size;
- the same device and exact runtime identity;
- `cache-mode refresh`;
- zero resumed chunks;
- zero SQLite embedding-cache hits;
- one recomputation for every selected row.

The extraction fingerprint intentionally excludes the output directory and cache path.
Therefore independent runs under the same scientific and runtime inputs must have the same
per-split extraction fingerprints.

## Run A

```powershell
$RunA = "runs/option-b/embeddings-a"
$CacheA = ".writer/option-b/cache/embeddings-a.sqlite3"

Remove-Item $RunA -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $CacheA -Force -ErrorAction SilentlyContinue
Remove-Item "$CacheA-shm", "$CacheA-wal" -Force -ErrorAction SilentlyContinue

relate-option-b-embed `
    --identity "artifacts/canonical/option-b/option-b-embedding-identity-v2.json" `
    --selection-dir "artifacts/canonical/option-b/selection" `
    --output-dir $RunA `
    --cache-db $CacheA `
    --cache-mode refresh `
    --batch-size 16 `
    --device cuda
```

Do not begin Run B until Run A exits successfully and its report status is
`EMBEDDING_RUN_COMPLETE_PENDING_INDEPENDENT_REPRODUCTION`.

## Run B

```powershell
$RunB = "runs/option-b/embeddings-b"
$CacheB = ".writer/option-b/cache/embeddings-b.sqlite3"

Remove-Item $RunB -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $CacheB -Force -ErrorAction SilentlyContinue
Remove-Item "$CacheB-shm", "$CacheB-wal" -Force -ErrorAction SilentlyContinue

relate-option-b-embed `
    --identity "artifacts/canonical/option-b/option-b-embedding-identity-v2.json" `
    --selection-dir "artifacts/canonical/option-b/selection" `
    --output-dir $RunB `
    --cache-db $CacheB `
    --cache-mode refresh `
    --batch-size 16 `
    --device cuda
```

## Independent verification

The reproduction verifier does not import the embedding extractor. It independently:

- verifies identity-v2 and selection-v2 bytes;
- recomputes manifest row-order and source-order hashes;
- verifies both run reports and fixture-preflight status;
- verifies refresh mode, separate caches, zero chunk reuse and zero cache hits;
- recomputes every extraction fingerprint from its payload;
- loads and verifies every `.npy` matrix against its report;
- requires identical runtime identities and per-split fingerprints;
- requires equal logical array hashes and exact `numpy.array_equal` matrices.

```powershell
$Checkpoint = `
    "runs/option-b/embedding-reproduction/" + `
    "option-b-independent-embedding-reproduction-v2.json"

relate-option-b-verify-embeddings `
    --run-a-report `
        "runs/option-b/embeddings-a/option-b-canonical-embeddings-v2.json" `
    --run-b-report `
        "runs/option-b/embeddings-b/option-b-canonical-embeddings-v2.json" `
    --identity `
        "artifacts/canonical/option-b/option-b-embedding-identity-v2.json" `
    --selection-dir "artifacts/canonical/option-b/selection" `
    --required-device cuda `
    --output $Checkpoint
```

The successful checkpoint status is:

```text
CANONICAL_EMBEDDINGS_V2_REPRODUCED
```

## Canonical evidence promotion

Only reports and hashes are committed. The large `.npy` matrices, chunks and SQLite
caches remain local and must not be added to Git.

```powershell
$CanonicalDir = "artifacts/canonical/option-b/embeddings"
New-Item -ItemType Directory -Path $CanonicalDir -Force | Out-Null

Copy-Item `
    "runs/option-b/embeddings-a/option-b-canonical-embeddings-v2.json" `
    "$CanonicalDir/option-b-embedding-run-a-v2.json" `
    -Force

Copy-Item `
    "runs/option-b/embeddings-b/option-b-canonical-embeddings-v2.json" `
    "$CanonicalDir/option-b-embedding-run-b-v2.json" `
    -Force

Copy-Item $Checkpoint `
    "$CanonicalDir/option-b-independent-embedding-reproduction-v2.json" `
    -Force
```

The copied reports and checkpoint must remain byte-identical to the generated files.

## Scientific boundary

The frozen decision rule remains untouched:

```text
gap = predicted_executor_accuracy - max(raw_cosine_accuracy, raw_euclidean_accuracy)

gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

This stage does not calculate any term in that expression.

## Next permitted stage

After the A/B checkpoint is generated, promoted and reviewed, the next bounded stage is
**primitive probe fitting and prediction publication** under the already frozen predicted
executor contract. Test primitive labels remain unavailable to fitting and selection.

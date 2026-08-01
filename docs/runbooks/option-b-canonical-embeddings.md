# Option B canonical embedding extraction

## Scope

This stage extracts frozen CodeBERT embeddings for the already committed canonical train, validation and test row manifests.

It does not fit primitive probes, build hard negatives, evaluate retrieval accuracy or make a scientific claim.

CodeBERT remains frozen. The command performs inference only; it does not train or fine-tune the model.

## Preconditions

The repository must contain:

```text
artifacts/canonical/option-b/option-b-external-identity-v1.json
artifacts/canonical/option-b/selection/option-b-canonical-row-selection-v1.json
artifacts/canonical/option-b/selection/option-b-selected-train-v1.jsonl
artifacts/canonical/option-b/selection/option-b-selected-validation-v1.jsonl
artifacts/canonical/option-b/selection/option-b-selected-test-v1.jsonl
```

The command verifies the committed manifest hashes before loading the model.

## Local SQLite cache

The default local cache is:

```text
.writer/option-b/cache/option-b.sqlite3
```

`.writer/` is ignored by Git and must never be promoted as a canonical artifact.

The database stores:

- verified selected source code, keyed by stable key, dataset revision and selection-manifest hash;
- float32 embeddings, keyed by stable key, model ID, immutable model revision, pooling implementation hash and maximum token length.

A cache entry is reused only when every immutable key matches. Corrupt code or embedding payloads are treated as misses.

Supported modes:

- `read-write`: reuse valid entries and write misses; this is the default;
- `refresh`: ignore existing entries, recompute and replace them;
- `off`: do not open or write a SQLite database.

## Normal cached run

CPU:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-a `
  --cache-db .writer/option-b/cache/option-b.sqlite3 `
  --cache-mode read-write `
  --batch-size 16 `
  --device cpu
```

CUDA, when available:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-a `
  --cache-db .writer/option-b/cache/option-b.sqlite3 `
  --cache-mode read-write `
  --batch-size 32 `
  --device cuda
```

On the first run, the command reconstructs the selected source code from the exact frozen CodeSearchNet revision, verifies every stable key, stores the verified code, and generates missing embeddings.

Later output directories can reuse the verified code and embeddings without rescanning CodeSearchNet or rerunning CodeBERT inference.

Progress is printed to stderr. The final JSON report is printed to stdout.

## Restart behavior

Each completed output batch is also stored under:

```text
runs/option-b/embeddings-a/chunks/<split>/
```

Restarting with the same output directory first reuses completed chunk files. A new output directory can reuse individual embeddings from SQLite.

Do not change model revision, selected manifests, batch ordering, maximum token length or pooling implementation between canonical restarts.

## Outputs

```text
runs/option-b/embeddings-a/
  option-b-embeddings-train-v1.npy
  option-b-embeddings-validation-v1.npy
  option-b-embeddings-test-v1.npy
  option-b-canonical-embeddings-v1.json
  chunks/
```

The report records shape, dtype, array hash, file hash, frozen model revision, pooling implementation hash, selected-manifest hashes, cache mode, cache hit/miss counts and runtime versions.

The SQLite database is operational cache state, not a scientific artifact. The `.npy` matrices and JSON report remain the canonical outputs.

## Independent reproduction

Do not prove reproducibility by reading the same cached vectors twice. Use either a fresh database or `refresh` mode.

Recommended separate database:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-b `
  --cache-db .writer/option-b/cache/reproduction.sqlite3 `
  --cache-mode read-write `
  --batch-size 16 `
  --device cpu
```

Alternatively, force recomputation while replacing the shared cache:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-b `
  --cache-db .writer/option-b/cache/option-b.sqlite3 `
  --cache-mode refresh `
  --batch-size 16 `
  --device cpu
```

Compare the three `array_sha256` values. The `.npy` file hashes should also match when the NumPy version and writer implementation are identical.

## Scientific boundary

After successful independent reproduction:

```text
Canonical embeddings: COMPLETE
Embedding determinism: CONFIRMED
Primitive probes: NOT YET FIT
Hard-negative manifest: NOT YET GENERATED
Scientific result: NOT OBSERVED
```

The next permitted stage is primitive-probe fitting only.

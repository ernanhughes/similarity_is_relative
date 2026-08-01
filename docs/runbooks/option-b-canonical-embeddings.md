# Option B canonical embedding extraction

## Scope

This stage extracts frozen CodeBERT embeddings for the already committed canonical train, validation and test row manifests.

It does not fit primitive probes, build hard negatives, evaluate retrieval accuracy or make a scientific claim.

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

Because the row manifests contain identities rather than source text, the command reconstructs the selected rows from the exact frozen CodeSearchNet revision and verifies every stable key before embedding.

## Run

CPU:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-a `
  --batch-size 16 `
  --device cpu
```

CUDA, when available:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-a `
  --batch-size 32 `
  --device cuda
```

Progress is printed to stderr. The final JSON report is printed to stdout.

## Restart behavior

Each completed batch is stored under:

```text
runs/option-b/embeddings-a/chunks/<split>/
```

Restarting with the same output directory reuses completed chunk files and resumes at the first missing batch. Do not change model revision, selected manifests, batch ordering or pooling implementation between restarts.

## Outputs

```text
runs/option-b/embeddings-a/
  option-b-embeddings-train-v1.npy
  option-b-embeddings-validation-v1.npy
  option-b-embeddings-test-v1.npy
  option-b-canonical-embeddings-v1.json
  chunks/
```

The report records shape, dtype, array hash, file hash, frozen model revision, pooling rule, selected-manifest hashes and runtime versions.

## Reproduction

Run a second extraction in a different directory:

```powershell
relate-option-b-embed `
  --output-dir runs/option-b/embeddings-b `
  --batch-size 16 `
  --device cpu
```

Compare the three `array_sha256` values. The `.npy` file hashes should also match when the NumPy version and writer implementation are identical.

## Scientific boundary

After successful reproduction:

```text
Canonical embeddings: COMPLETE
Embedding determinism: CONFIRMED
Primitive probes: NOT YET FIT
Hard-negative manifest: NOT YET GENERATED
Scientific result: NOT OBSERVED
```

The next permitted stage is primitive-probe fitting only.

# Option B Real-Code Execution Runbook

This runbook implements the frozen contract in
[`docs/experiments/08-option-b-real-code-premise-test.md`](../experiments/08-option-b-real-code-premise-test.md).

## Status

The implementation may be developed and tested before the model revision is frozen.
Canonical embedding extraction and scientific evaluation remain blocked until a documentation-only commit records the resolved CodeBERT and tokenizer revisions.

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,option-b]"
ruff check .
pytest
relate-option-b --print-contract
```

## Expected local layout

Large evidence-bearing arrays remain local and are identified by committed hashes.

```text
data/option-b/raw/
  train/*.jsonl
  validation/*.jsonl
  test/*.jsonl

runs/option-b/
  manifests/
  primitives/
  embeddings/
  predictions/
  results/
  environment/
```

Do not commit CodeSearchNet source archives, raw functions, embedding matrices or prediction arrays.
Commit their manifests, production contracts and SHA-256 identities.

## Stage 1 — freeze external identities

Before canonical extraction, commit:

- CodeSearchNet source/version and archive hashes;
- resolved `microsoft/codebert-base` model revision;
- tokenizer revision and file hashes;
- Python, PyTorch, Transformers, Tokenizers and platform versions;
- pooling implementation hash;
- ten-sample embedding fixture input and output hashes.

This must be a documentation-only commit. It may not include scientific metrics.

## Stage 2 — prepare the dataset

The preparation command will:

1. read the published train, validation and test partitions;
2. parse exactly one top-level Python function per row;
3. extract the three frozen AST primitives;
4. tokenize without truncation to enforce the `32..256` eligibility range;
5. remove all normalized-AST duplicates crossing split boundaries;
6. sort by the frozen stable SHA-256 key;
7. apply the `20,000 / 4,000 / 4,000` limits;
8. write filtered manifests and primitive arrays.

Required identities:

- raw source hashes;
- retained-row manifest hash;
- duplicate-removal report hash;
- primitive-array hash;
- split and repository-count hashes.

## Stage 3 — extract frozen embeddings

Use attention-mask-weighted mean pooling of the final hidden state.

Canonical constraints:

```text
model: microsoft/codebert-base
revision: committed resolved revision
maximum sequence length: 256
embedding dtype: float32
model updates: forbidden
```

The extractor must checkpoint by split and batch so interruption does not change row order.

## Stage 4 — train primitive probes

For each primitive independently:

```text
alpha in {0.01, 0.1, 1.0, 10.0, 100.0}
selection metric: validation MAE
selection tie-break: larger alpha
```

Training-only robust scaling is applied before fitting.
No compound labels are used.

## Stage 5 — freeze the hard-negative manifest

Build the manifest from true scaled primitive values only.
Commit its SHA-256 before computing method performance on test queries.

The manifest contains:

```text
query index
closer candidate index
farther candidate index
query repository
oracle distances
rank separation
length decile
sparse-query flag
```

## Stage 6 — evaluate once

Methods:

- raw cosine;
- raw Euclidean;
- token-length distance;
- predicted-primitive Chebyshev executor;
- true-primitive Chebyshev oracle.

Primary decision:

```text
raw_best = max(raw cosine hard-negative triplet accuracy,
               raw Euclidean hard-negative triplet accuracy)

gap = predicted executor hard-negative triplet accuracy - raw_best
```

```text
gap >= 0.10  -> REAL_PREMISE_SUPPORTED
gap < 0.10   -> REAL_PREMISE_FAILED
```

No secondary metric may override the result.

## Stage 7 — verify independently

The independent recomputation must read frozen:

- embeddings;
- true primitive values;
- predicted primitive values;
- split manifests;
- hard-negative manifest.

It must not call the experiment runner or its metric helpers.

## Publication boundary

A pass permits only a separately frozen Option C refusal contract.
A failure closes RELATE and is published as the real-domain negative result.

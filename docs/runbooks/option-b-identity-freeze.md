# Option B External Identity Freeze

This runbook captures the immutable external inputs and ten-sample embedding fixture required before the canonical Option B run.

## Preconditions

```powershell
python -m pip install -e ".[dev,option-b]"
ruff check .
pytest
relate-option-b --print-contract
```

## Generate the identity manifest

```powershell
relate-option-b-freeze
```

Optional explicit cache location:

```powershell
relate-option-b-freeze --cache-dir D:\hf-cache
```

Default output:

```text
runs/option-b/identity/option-b-external-identity-v1.json
```

## What the command records

- immutable `microsoft/codebert-base` Hub revision;
- immutable `code-search-net/code_search_net` Hub revision;
- Python subset declaration;
- tokenizer and model-configuration file hashes available in the frozen snapshot;
- SHA-256 of the registered pooling implementation;
- Python, platform, NumPy, PyTorch, Transformers, Tokenizers, Datasets and Hugging Face Hub versions;
- ten fixed source-code fixture inputs;
- fixture token counts;
- per-row embedding hashes;
- full float32 embedding-matrix hash.

## Review checklist

Before committing the manifest, verify:

1. `status` is `IDENTITY_CAPTURE_COMPLETE`;
2. model and dataset revisions are full immutable commit hashes;
3. fixture count is exactly `10`;
4. embedding dtype is `float32`;
5. embedding shape is `[10, hidden_size]`;
6. every fixture row has a code hash, token count and embedding hash;
7. the environment section contains non-null versions for all Option B packages;
8. the pooling implementation hash matches the checked-out implementation;
9. rerunning in the same environment produces the same fixture matrix hash.

## Commit the checkpoint

Copy the reviewed manifest to:

```text
artifacts/canonical/option-b/option-b-external-identity-v1.json
```

Commit it without canonical dataset rows, embeddings or performance metrics.

Suggested commit message:

```text
Freeze Option B external model and dataset identities
```

## Scientific boundary

This checkpoint does not test the premise and must not change `CLAIMS.md`.

After it is committed, canonical dataset preparation may begin under the already frozen Option B contract.

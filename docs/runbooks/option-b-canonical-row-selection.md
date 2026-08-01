# Option B canonical row selection

This stage selects the exact CodeSearchNet Python rows that may enter the canonical Option B embedding run.

It does **not** generate embeddings, fit probes, build hard-negative triplets or compute any scientific metric.

## Prerequisite

The reviewed identity artifact must exist at:

```text
artifacts/canonical/option-b/option-b-external-identity-v1.json
```

The selection command refuses to run without it. The file must identify:

- `microsoft/codebert-base` at the frozen immutable revision;
- `code-search-net/code_search_net` at the frozen immutable revision;
- subset `python`;
- the confirmed ten-row fixture matrix hash;
- the pooling implementation hash.

## Install

```powershell
python -m pip install -e ".[dev,option-b]"
```

## Run

```powershell
relate-option-b-select
```

Default output directory:

```text
runs/option-b/selection/
```

The command writes:

```text
option-b-selected-train-v1.jsonl
option-b-selected-validation-v1.jsonl
option-b-selected-test-v1.jsonl
option-b-primitives-train-v1.jsonl
option-b-primitives-validation-v1.jsonl
option-b-primitives-test-v1.jsonl
option-b-canonical-row-selection-v1.json
```

## Frozen processing order

1. Load the exact dataset revision from the canonical identity file.
2. Load the exact tokenizer revision from the same file.
3. Preserve the dataset's published `train`, `validation` and `test` partitions.
4. Require valid Python AST parsing.
5. Require exactly one top-level function or async function.
6. Require tokenizer length between 32 and 256 inclusive.
7. Compute the three frozen AST primitives.
8. Remove every normalized AST appearing in more than one split.
9. Sort each remaining split by the frozen stable-key SHA-256.
10. Select at most 20,000 train, 4,000 validation and 4,000 test rows.
11. Write selected-row manifests and primitive tables with SHA-256 hashes.

No code text or embedding vector is committed by this command. The selected-row manifest identifies each function through repository, path, function identifier and content hashes.

## Determinism check

Run the command twice into separate directories:

```powershell
relate-option-b-select --output-dir runs/option-b/selection-a
relate-option-b-select --output-dir runs/option-b/selection-b
```

Compare the hashes in both reports. Every `selected_manifest.sha256` and `primitive_table.sha256` must match.

## Review checklist

Before canonical embedding extraction:

- confirm model and dataset revisions match the identity artifact;
- inspect source, eligibility, exclusion and selected-row counts;
- inspect cross-split duplicate removals;
- confirm all six artifact hashes reproduce on a second run;
- confirm `scientific_result_observed` is `false`;
- copy the reviewed report and six manifests into `artifacts/canonical/option-b/selection/`;
- commit them before generating full embeddings.

## Scientific boundary

This stage cannot support or reject the Option B premise. It freezes the population on which the already-registered comparison will later run.

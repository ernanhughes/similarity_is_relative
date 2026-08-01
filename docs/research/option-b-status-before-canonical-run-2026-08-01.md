# Option B Status Before the Canonical Run

## Why this note exists

Option B is now far enough along that implementation progress could easily be mistaken for scientific progress.

That distinction matters.

The experiment contract is frozen. The pipeline exists. The command-line contract prints correctly. The AST primitive extractors, deduplication rules, scaling, ridge probes, hard-negative construction and metric helpers have been implemented.

But the scientific test has **not run**.

No canonical CodeSearchNet rows have been selected. No canonical CodeBERT embedding matrix exists. No primitive model has been fitted to the canonical representation. No hard-negative score has been observed. The project therefore has no Option B result yet.

## What has been completed

### Research decision

After E01 was independently audited and closed, the project rejected the broad synthetic roadmap.

The next question became the load-bearing real-domain premise:

> Does a frozen representation that we did not train materially underexpose an objectively measurable compound relation under its default geometry?

The experiment is deliberately binary. If the predicted-primitive executor beats the strongest raw geometry by less than `0.10` hard-negative triplet accuracy, RELATE closes. A pass authorises only the separately contracted refusal test.

### Frozen design

The frozen Option B design uses:

- real Python functions from the CodeSearchNet Python partition;
- `microsoft/codebert-base` without fine-tuning;
- cyclomatic complexity;
- maximum control nesting depth;
- distinct normalized call-site count;
- one Chebyshev conjunction query;
- raw cosine and raw Euclidean as principal baselines;
- repository-separated evaluation;
- one hard-negative triplet decision.

### Implemented pipeline

The repository now contains code for:

- CodeSearchNet-style JSONL ingestion;
- exact AST primitive extraction;
- normalized-AST cross-split deduplication;
- deterministic stable-key sampling;
- frozen CodeBERT mean pooling;
- training-only robust scaling;
- validation-selected primitive ridge probes;
- Chebyshev oracle and predicted distances;
- raw cosine and Euclidean distances;
- deterministic hard-negative manifests;
- evidence hashing and environment capture.

These are capabilities, not findings.

## Why identity capture comes next

A model name is not an immutable model.

A dataset name is not an immutable dataset.

A package range is not an execution environment.

Before the canonical run, the project must record the exact external state that generated the representation. Otherwise a later replay could silently resolve a different model commit, tokenizer, dataset revision or dependency stack.

The identity checkpoint must therefore contain:

- resolved CodeBERT model commit;
- resolved CodeSearchNet dataset commit;
- tokenizer-file hashes;
- pooling implementation hash;
- Python and dependency versions;
- ten fixed input snippets;
- token counts for those snippets;
- per-row embedding hashes;
- complete fixture-matrix hash.

## New identity-capture command

After installing the Option B dependencies, run:

```powershell
python -m pip install -e ".[dev,option-b]"
relate-option-b-freeze
```

Default output:

```text
runs/option-b/identity/option-b-external-identity-v1.json
```

The command resolves immutable Hub revisions, loads the frozen model and tokenizer, embeds ten fixed source snippets using the registered pooling function, and writes the identity manifest.

This command does not select the canonical dataset and does not evaluate the experiment.

## Commit boundary

The generated manifest must be reviewed and committed in a separate checkpoint commit before canonical dataset preparation begins.

That commit freezes the external world seen by Option B.

After the manifest is committed:

1. download the frozen CodeSearchNet revision;
2. prepare and hash the eligible rows;
3. remove cross-split normalized-AST duplicates;
4. select the frozen sample by stable-key order;
5. generate and hash CodeBERT embeddings;
6. commit the hard-negative manifest before method scoring;
7. run the primary decision once;
8. independently recompute the metrics from frozen artifacts.

## Current classification

```text
E01 composition line: CLOSED
Option B contract: FROZEN
Option B implementation: COMPLETE ENOUGH FOR IDENTITY CAPTURE
External identity checkpoint: NOT YET GENERATED
Canonical dataset: NOT YET SELECTED
Canonical embeddings: NOT YET GENERATED
Scientific result: NOT OBSERVED
```

The next evidence-bearing artifact is the identity manifest, not a performance result.

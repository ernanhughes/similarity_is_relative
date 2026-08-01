# Option B canonical row-selection checkpoint

Date: 2026-08-01

## Status

```text
Option B contract: FROZEN
Option B pipeline: IMPLEMENTED
External identity checkpoint: COMPLETE
Identity fixture determinism: CONFIRMED
Canonical row selection: COMPLETE
Row-selection determinism: CONFIRMED
Canonical embeddings: NOT YET GENERATED
Primitive probes: NOT YET FIT
Hard-negative manifest: NOT YET GENERATED
Scientific result: NOT OBSERVED
```

This checkpoint records completion of deterministic canonical CodeSearchNet row selection for the frozen Option B premise test. It does not report a scientific result and does not change the registered experiment contract.

## Frozen external identities

```text
Model: microsoft/codebert-base
Model revision: 3b0952feddeffad0063f274080e3c23d75e7eb39
Dataset: code-search-net/code_search_net
Dataset revision: bd0cf261e357a3eb5c8fba490d23ec1a1cd59555
Dataset subset: python
Fixture matrix SHA-256: 300b75891b2a498f17e774d27baf3ce432082a55cd1fc2401b003c8b5f4e5f46
Pooling implementation SHA-256: 9ac3a71225bcae6bbaf7e4c01788f6a85914b22f0edb054202f00707f3b1cbf5
```

The ten-row CodeBERT identity fixture was executed twice in the same frozen environment. The complete matrix hash and all ten row-level embedding hashes reproduced exactly.

## Frozen selection contract

The canonical selector preserved the published CodeSearchNet train, validation and test splits and applied the registered rules:

- exactly one top-level Python function;
- frozen AST primitive extraction;
- CodeBERT token count between 32 and 256 inclusive;
- removal of normalized ASTs appearing in more than one split;
- stable SHA-256 ordering;
- selection limits of 20,000 train, 4,000 validation and 4,000 test rows.

The three objective primitives remain:

1. cyclomatic complexity;
2. maximum control nesting depth;
3. distinct call-site count.

## Selection results

| Split | Source rows | AST-ineligible | AST recursion-limit | Token length | Eligible | Selected |
|---|---:|---:|---:|---:|---:|---:|
| Train | 412,178 | 4,011 | 1 | 228,507 | 179,659 | 20,000 |
| Validation | 23,107 | 290 | 0 | 12,908 | 9,909 | 4,000 |
| Test | 22,176 | 228 | 0 | 12,370 | 9,578 | 4,000 |

One valid but pathologically deep training AST exceeded Python's recursive visitor limit. The row was deterministically isolated, excluded as `ast_recursion_limit`, and counted. The remaining selection continued unchanged.

## Cross-split deduplication

```text
cross_split_ast_count: 0
removed train: 0
removed validation: 0
removed test: 0
```

No eligible normalized AST occurred in more than one published split.

## Canonical artifact hashes

The selector was run independently into `selection-a` and `selection-b`. All six scientific artifacts matched byte-for-byte.

| Artifact | Rows | SHA-256 |
|---|---:|---|
| `option-b-selected-train-v1.jsonl` | 20,000 | `73f2cf89d96e1b80af50306a46e65d6f090c8b54e1baa91416e8147d31220c30` |
| `option-b-primitives-train-v1.jsonl` | 20,000 | `89a1b745942faf176b0650234115cfc2de67c5cfb5f736efbe7f6444719d9f36` |
| `option-b-selected-validation-v1.jsonl` | 4,000 | `3dab1c99f1443340336bbedceac60995267163abe9b5b4283bdd5d023b6eb2f9` |
| `option-b-primitives-validation-v1.jsonl` | 4,000 | `8b265eb7892cdcc725870697b6dd3bb34fc6acd36e50941f282f98201903fdc7` |
| `option-b-selected-test-v1.jsonl` | 4,000 | `e3eb77c45deb74d8e96c8582e097aa241e19e0ac89ac8b99e42f4a29ffd618e7` |
| `option-b-primitives-test-v1.jsonl` | 4,000 | `df98c6279498a1eb29d96816a33c80f061796c6a06b477ef52f0318118debb58` |

The first-run selection report recorded payload SHA-256:

```text
a70f71d5f9e6cdbb7aa2f11c904fa264f4388ed66aaf1c611563451c95c93078
```

Report-file hashes are not the determinism criterion because output directory paths differ between the two runs. The six selected-row and primitive-table artifacts are the registered comparison.

## What this checkpoint establishes

This checkpoint establishes that:

- the external model, tokenizer, dataset and pooling identities are frozen;
- the eligible CodeSearchNet population can be processed without an unhandled pathological-AST failure;
- canonical row selection is deterministic under the registered procedure;
- the exact selected rows and primitive labels are now fixed before embedding extraction.

It does not establish that CodeBERT encodes the three primitives, that a primitive executor outperforms raw similarity, or that the Option B premise is supported.

## Claims not yet allowed

The following claims remain prohibited:

- CodeBERT embeddings are compositionally structured for this query;
- the three primitives are recoverable with useful accuracy;
- relation-specific execution beats raw cosine or Euclidean similarity;
- the continuation gap reaches or exceeds 0.10;
- the real-code premise is supported.

No probe, hard-negative or primary-metric result exists at this checkpoint.

## Next permitted stage

The next bounded stage is **canonical CodeBERT embedding extraction only**.

That stage should:

- consume the committed selected-row manifests rather than reselect rows;
- use the frozen CodeBERT revision and pooling implementation;
- extract train, validation and test embeddings once;
- provide live progress and restart-safe per-split outputs;
- write shape, dtype and content hashes;
- verify row order against the canonical selected manifests;
- stop before fitting primitive probes or evaluating any scientific metric.

Changes to the model, language, query, primitive definitions, row limits, threshold or registered baselines remain prohibited.

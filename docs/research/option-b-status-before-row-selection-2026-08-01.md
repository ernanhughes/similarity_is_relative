# Option B status before canonical row selection

## Where the programme stands

The synthetic E01 composition line is closed. The current programme is the bounded Option B real-representation premise test.

The question remains:

> Does frozen CodeBERT geometry materially underexpose a compound structural relation that simple independently trained primitive readouts expose?

The scientific threshold remains frozen:

```text
predicted-primitive hard-negative triplet accuracy
minus strongest raw CodeBERT geometry
must be at least 0.10
```

Nothing completed so far answers that question.

## Completed

```text
E01 audit and closure: COMPLETE
Option B domain and threshold contract: FROZEN
Option B AST and evaluation pipeline: IMPLEMENTED
CodeBERT and CodeSearchNet revisions: CAPTURED
Ten-row embedding fixture: REPRODUCED IDENTICALLY
Identity fixture matrix hash:
300b75891b2a498f17e774d27baf3ce432082a55cd1fc2401b003c8b5f4e5f46
```

The frozen external identities are:

```text
CodeBERT revision:
3b0952feddeffad0063f274080e3c23d75e7eb39

CodeSearchNet revision:
bd0cf261e357a3eb5c8fba490d23ec1a1cd59555
```

## Current stage

The next irreversible step is to freeze the exact real functions entering the experiment.

The row-selection stage will:

1. load the frozen CodeSearchNet Python revision;
2. preserve its published repository-separated splits;
3. apply the registered AST and token-length eligibility rules;
4. remove every normalized AST duplicated across splits;
5. select rows by deterministic SHA order;
6. write selected-row manifests and objective primitive tables;
7. repeat the procedure and verify all output hashes.

This stage observes dataset composition and filtering counts, but no model-comparison metric.

## Why the row manifest comes before embeddings

Embedding extraction is expensive and produces the evidence used by the final test. The candidate population must therefore be immutable before any complete embedding matrix exists.

Freezing rows first prevents later choices such as:

- removing inconvenient functions after seeing retrieval failures;
- changing the token window after observing model behaviour;
- replacing repositories with easier examples;
- resolving duplicates differently after inspecting metrics;
- silently altering the number or composition of test queries.

## Status vocabulary after this PR

```text
Option B contract: FROZEN
Option B pipeline: IMPLEMENTED
External identity checkpoint: COMPLETE LOCALLY
Canonical row-selection command: IMPLEMENTED
Canonical selected rows: NOT YET GENERATED
Canonical embeddings: NOT YET GENERATED
Primitive probes: NOT YET FIT
Hard-negative manifest: NOT YET GENERATED
Scientific result: NOT OBSERVED
```

## Next transition

After this PR merges:

1. commit the reviewed external identity artifact if it is not already canonical;
2. run `relate-option-b-select` twice;
3. verify the six row/primitive artifact hashes match;
4. inspect filtering and duplicate-removal counts;
5. commit the canonical selection report and manifests;
6. only then begin full CodeBERT embedding extraction.

No Option C work is authorised unless the final Option B gap reaches the frozen `0.10` threshold.

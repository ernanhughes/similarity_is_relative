# Option B predicted executor contract

Date: 2026-08-01

## Status

```text
Canonical selection v2: COMPLETE
Predicted executor contract: COMPLETE
Canonical embeddings v2: NOT GENERATED
Canonical primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE EMBEDDING EXTRACTION
```

## Frozen semantics

The predicted executor compares predicted primitive vectors on both sides:

```text
predicted test-query primitives versus predicted train-candidate primitives
```

The following mixed geometry is prohibited:

```text
predicted test-query primitives versus true train-candidate primitives
```

True primitives may be used only for train-only scaler and ridge fitting, validation-only alpha selection, and the later separately frozen oracle/hard-negative construction.

## Candidate prediction protocol

Train candidates receive deterministic balanced five-fold out-of-fold predictions. Fold membership is derived from stable-key hashes and is independent of input order. Each candidate is predicted only by a model that did not fit that row's primitive labels.

For each primitive:

1. fit the robust scaler on training primitives only;
2. fit each candidate ridge alpha on all training embeddings and evaluate validation MAE;
3. choose the lowest validation MAE, breaking exact ties in favour of the larger alpha;
4. generate train-candidate predictions out of fold with the selected alpha;
5. refit the selected alpha on all training rows;
6. use the refit model for validation-row and test-query predictions.

Test primitive labels are absent from the fitting API. Predictions remain float64 and are not rounded to the integer lattice.

## Required identities

The contract records hashes for:

- ordered stable-key sequences for train, validation and test;
- deterministic fold assignment;
- train-candidate, validation-row and test-query prediction arrays;
- train-only scaler median and scale;
- selected alpha per primitive;
- final coefficients and intercepts;
- every out-of-fold coefficient and intercept;
- the complete prediction bundle.

The executor accepts role-tagged, hash-verified prediction objects only. Query predictions must have the test-query role, candidate predictions must have the train-candidate role, and both must belong to the same fitted bundle.

## Scientific boundary

This stage freezes and tests semantics only. It does not generate canonical embeddings, fit canonical probes, generate canonical predictions, build hard negatives, calculate retrieval accuracy, calculate the registered gap, or observe the scientific result.

## Next permitted stage

The next bounded stage is **PR 5 — embedding identity v2**. Canonical embedding extraction remains blocked until embedding identity and chunk/cache recovery hardening are complete.

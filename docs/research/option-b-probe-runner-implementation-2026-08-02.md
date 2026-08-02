# Option B primitive probe runner implementation

Date: 2026-08-02

## Status

```text
Canonical selection v2: COMPLETE
Primitive tables v2: COMPLETE
Predicted executor contract: COMPLETE
Embedding identity amendment: COMPLETE AND MERGED
Independent embedding reproduction: COMPLETE AND MERGED
Probe runner implementation: COMPLETE IN THIS PR
Canonical primitive probe fit: NOT RUN
Predicted primitive arrays: NOT GENERATED
Hard-negative manifest: NOT GENERATED
Scientific metric: NOT OBSERVED
Scientific result: NOT OBSERVED
Gate: BLOCK BEFORE CANONICAL PROBE FIT
```

## Scope

This stage implements and reviews the one-time primitive probe fitting runner. It does not
execute the canonical fit or publish fitted coefficients or predictions.

The later canonical-fit checkpoint must run the reviewed command once, promote the
resulting artifacts byte-for-byte, and remain separate from hard-negative generation and
scientific evaluation.

## Accepted inputs

The runner verifies:

- the committed independent embedding reproduction checkpoint;
- the committed fixed-batch CUDA amendment checkpoint;
- the canonical selection-v2 report;
- selected-manifest hashes, row counts, uniqueness and exact stable-key order;
- primitive-table hashes from the selection checkpoint;
- one independently reproduced embedding-run report;
- the local train, validation and test embedding matrices against their logical-array,
  file and extraction-fingerprint identities.

The default embedding replica is Run A under:

```text
runs/option-b/gpu-fixed-batch-10/embeddings-a
```

Run B is equivalent because the merged reproduction checkpoint established exact logical
and serialized equality for all three splits.

## Label boundary

Only the train and validation primitive tables are parsed into numeric labels.

```text
train labels      -> robust scaler fitting, ridge fitting and OOF prediction
validation labels -> alpha selection only
test labels       -> never parsed and absent from the fitting API
```

The test primitive-table file remains part of the canonical selection checkpoint and its
file hash is verified, but its label values are not loaded into the probe runner.

## Frozen fitting protocol

The runner invokes the already reviewed `option-b-predicted-executor-v1` contract:

- three independent ridge probes;
- robust scaling fitted on train primitives only;
- alphas `0.01, 0.1, 1.0, 10.0, 100.0`;
- validation MAE selects alpha;
- exact ties select the larger alpha;
- deterministic balanced five-fold assignment from stable-key hashes;
- train candidates receive out-of-fold predictions;
- validation and test receive predictions from a final train-only refit;
- no prediction rounding;
- float64 prediction arrays;
- scaler, fold, coefficient, intercept, row-order, prediction and bundle hashes.

## Prospective outputs

After this implementation PR merges, the canonical-fit stage may produce:

```text
option-b-predicted-train-candidates-v1.npy
option-b-predicted-validation-rows-v1.npy
option-b-predicted-test-queries-v1.npy
option-b-primitive-probe-bundle-v1.json
```

The JSON report records all verified inputs, runtime versions, thread-related environment
variables, the frozen contract report, output shapes, dtypes, logical-array hashes and
file hashes.

## Scientific boundary

This PR does not:

- fit canonical probes;
- inspect test primitive labels;
- generate a hard-negative manifest;
- compute raw cosine or Euclidean accuracy;
- compute predicted-executor accuracy;
- compute the registered gap;
- observe or classify the scientific result.

The frozen decision remains:

```text
gap = predicted_executor_accuracy - max(raw_cosine_accuracy, raw_euclidean_accuracy)

gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

## Validation

Focused tests cover:

- train/validation-only label loading;
- absence of test-label arguments from the runner API;
- rejection of embedding payload tampering;
- rejection of a changed CUDA batch size;
- atomic hash-addressed float64 prediction publication;
- proof that no test labels are passed into the predicted-executor helper.

## Next permitted stage

After this implementation PR is reviewed and merged:

1. run the canonical probe fit once in a fresh output directory;
2. inspect only integrity metadata, not scientific evaluation results;
3. promote the three prediction arrays and fit report byte-for-byte;
4. open a dedicated probe-artifact checkpoint PR;
5. do not generate hard negatives until that checkpoint is merged.

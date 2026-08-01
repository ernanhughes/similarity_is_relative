# E00.4 Multi-Seed Confirmation Attempt v1

## Status

- Verification: `PASS`
- Scientific gate: `FAIL`
- Verified seeds: `23, 41, 59, 83, 101`
- Verified model selections: `5`
- Verified decisions: `7`
- Required decisions matched: `6 of 7`
- Claim promotion: `BLOCKED`

This is a scientifically failed but independently reproduced confirmation gate. It is not an implementation or verifier failure.

## Aggregate decisions

| Decision | Status |
|---|---|
| Axis-aligned rank-one recovery | `SUPPORTED` |
| Rotated rank-one recovery | `SUPPORTED` |
| Absent relation | `UNSUPPORTED_AT_THRESHOLD` |
| Linear XOR | `UNSUPPORTED_AT_THRESHOLD` |
| Nonlinear XOR | `INSUFFICIENT_EVIDENCE` |
| Diagonal basis dependence | `SUPPORTED` |
| Correlated-nuisance shift | `UNSTABLE_UNDER_SHIFT` |

## Main replicated results

The learned rank-one direction was stable across all five fresh synthetic seeds:

- axis-aligned mean triplet accuracy: `0.9385`, seed-level 95% interval `0.9350–0.9420`;
- rotated mean triplet accuracy: `0.9390`, seed-level 95% interval `0.9351–0.9425`.

Rotation changed the basis but did not materially change rank-one recovery:

- mean rank-one rotation retention: `1.0005`;
- seed-level 95% interval: `0.9931–1.0089`.

Diagonal coordinate weighting did not retain comparable performance:

- mean diagonal rotation retention: `0.5968`;
- seed-level 95% interval: `0.5879–0.6057`.

The controls behaved as required:

- absent relation mean triplet accuracy: `0.5008`;
- linear XOR mean triplet accuracy: `0.4999`;
- correlated-nuisance mean validation-to-test gap: `0.3525`, interval `0.3455–0.3594`.

## Why the gate failed

The preregistered nonlinear XOR family did not recover the relation consistently across seeds.

Per-seed nonlinear average precision was approximately:

```text
0.5011
0.7788
0.7928
0.9195
0.7806
```

Aggregate nonlinear XOR evidence:

- mean average precision: `0.7546`;
- seed-level 95% interval: `0.6154–0.8640`;
- minimum seed result: `0.5011`;
- nonlinear-minus-linear lower seed-level interval: `0.1169`, below the frozen `0.15` requirement.

The correct aggregate decision is therefore `INSUFFICIENT_EVIDENCE`.

## Frozen evidence identities

```text
Aggregate result:
8dd526eaa45a28f56c99cb1045138685b89982109dbf61fb9788a6a65937e86d

Decision tree:
25b52842a4d5fbfefa1145c8f406328dc70744659852b7aa0535cf06788f4c90
```

## Publication boundary

The experiment supports bounded synthetic conclusions about multi-seed rank-one recovery, rotation retention, basis dependence, absent controls and shortcut instability.

It does not permit promotion of the complete E00 claim because the nonlinear control failed its preregistered confirmation threshold.

The E00.4 contract, thresholds, results and decisions must not be edited retroactively.

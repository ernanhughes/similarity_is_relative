# E00.3 — Nulls, Uncertainty, and Certification

## Purpose

Convert the verified E00.2 point estimates into explicit seed-17 decisions using deterministic permutation nulls, query-level bootstrap confidence intervals, a nonlinear XOR diagnostic, and frozen support thresholds.

This stage consumes the existing E00 source arrays and operator matrix. It does not regenerate either artifact.

## Inputs

- `runs/e00/canonical-seed-17/manifest.json`
- `runs/e00/canonical-seed-17/arrays/*.npz`
- `runs/e00/operator-matrix-seed-17/operator-matrix.json`

Both upstream SHA-256 identities are recorded in the output.

## Frozen uncertainty contract

- 100 deterministic label permutations per learned linear method and regime;
- 1,000 query-level bootstrap resamples;
- 95% percentile intervals;
- permutation evaluation on 200 test queries and 1,024 training candidates;
- all random operations use certification seed `1703`.

## Frozen decisions

| Decision | Required status |
|---|---|
| axis-linear rank-one operator | `SUPPORTED` |
| rotated-linear rank-one operator | `SUPPORTED` |
| absent relation under rank one | `UNSUPPORTED_AT_THRESHOLD` |
| XOR under linear rank one | `UNSUPPORTED_AT_THRESHOLD` |
| XOR under nonlinear MLP | `SUPPORTED_NONLINEAR_ONLY` |
| diagonal basis dependence | `SUPPORTED` |
| correlated nuisance under shift | `UNSTABLE_UNDER_SHIFT` |

Support for the continuous rank-one cases requires:

1. the 95% bootstrap lower bound on triplet accuracy to be at least `0.75`; and
2. the observed estimate to exceed the 99th percentile of its label-permutation null.

The nonlinear XOR diagnostic requires a 95% bootstrap lower bound on average precision of at least `0.80`.

Diagonal basis dependence requires the lower confidence bound for axis-aligned minus rotated diagonal triplet accuracy to be at least `0.50`.

Shortcut instability requires the lower confidence bound for validation-minus-test triplet accuracy to be at least `0.10`.

## Outputs

```text
runs/e00/certification-seed-17/
├── certification.json
├── certification-result.json
└── verification.json
```

## Commands

```powershell
.\scripts\30-run-e00-certification.ps1
.\scripts\31-verify-e00-certification.ps1
```

## Publication boundary

Even a passing E00.3 gate does not promote a scientific claim. It establishes a complete decision for the frozen seed-17 experiment only. Multi-seed confirmatory replication remains mandatory before `claim_promotion_allowed` may become true.

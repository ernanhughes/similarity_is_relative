# E00.4 — Preregistered Multi-Seed Confirmation

## Status

Frozen before the canonical run.

E00.3 remains an immutable verified gate failure. This stage does not alter its thresholds, decisions, hashes, or interpretation.

## Confirmatory seeds

Exactly: `23, 41, 59, 83, 101`. Seed 17 is historical only and is excluded from aggregation and model selection.

## Questions

1. Does supervised rank-one recovery replicate across fresh seeds?
2. Does diagonal coordinate weighting lose substantially more performance under rotation than rank-one projection?
3. Can a preregistered nonlinear family recover XOR while the linear family remains at chance?
4. Are absent relations rejected and shortcut relations marked unstable?

## Frozen operator families

- raw Euclidean and cosine;
- ridge predicted-value distance;
- diagonal ridge metric;
- rank-one ridge projection;
- XOR candidates selected on validation only:
  - degree-2 interaction-only polynomial logistic regression with `C ∈ {0.1, 1, 10}`;
  - MLP hidden layers `(16,)`, `(32,)`, `(32,16)` with `alpha ∈ {0.0001, 0.001, 0.01}`.

Exact ties are resolved lexically by model identifier. Test labels are not available to model selection.

## Nulls and intervals

- 100 deterministic label permutations per required seed/method;
- 1,000 deterministic query-level bootstrap resamples;
- 1,000 deterministic seed-level bootstrap resamples;
- 95% intervals;
- the seed, not the query, is the confirmatory unit.

## Required aggregate decisions

- `axis_linear.rank1_multiseed = SUPPORTED`
- `rotated_linear.rank1_multiseed = SUPPORTED`
- `absent.rank1_multiseed = UNSUPPORTED_AT_THRESHOLD`
- `xor.linear_multiseed = UNSUPPORTED_AT_THRESHOLD`
- `xor.nonlinear_multiseed = SUPPORTED_NONLINEAR_ONLY`
- `diagonal.basis_dependence_multiseed = SUPPORTED`
- `correlated_nuisance.shift_multiseed = UNSTABLE_UNDER_SHIFT`

The overall gate passes only if all seven match.

## Frozen thresholds

### Rank-one linear support

For axis and rotated regimes: at least 4/5 seeds have triplet accuracy ≥ 0.85; at least 4/5 exceed seed-specific null q99; seed-level lower 95% bound ≥ 0.80; no seed below 0.75.

### Basis dependence

Define rotation retention as rotated / axis triplet accuracy. Require at least 4/5 diagonal retentions ≤ 0.75, upper seed-level 95% bound ≤ 0.80, at least 4/5 rank-one retentions ≥ 0.95, and lower seed-level 95% bound ≥ 0.90.

### Absent and linear XOR

No more than 1/5 may exceed null q99; aggregate mean triplet accuracy must remain below 0.55.

### Nonlinear XOR

At least 4/5 test average precision values ≥ 0.85; none below 0.75; lower seed-level 95% bound ≥ 0.80; nonlinear-minus-linear AP ≥ 0.20 in at least 4/5 seeds; aggregate lower bound for that difference ≥ 0.15.

### Correlated nuisance

At least 4/5 validation-minus-test triplet gaps ≥ 0.15 and the aggregate lower 95% bound ≥ 0.10.

## Publication boundary

`claim_promotion_allowed` may become true only after independent verification, a passing seven-decision gate, complete hashes, and an exact synthetic-only claim in `CLAIMS.md`. No transfer, composition, or real-embedding claim is permitted.

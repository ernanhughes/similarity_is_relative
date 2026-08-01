# E00 Operator Matrix Checkpoint v1

## Status

- Experiment: `e00-operator-matrix`
- Verification: **PASS**
- Verified regimes: **6**
- Verified method sets: **40**
- Claim promotion: **blocked**
- Source manifest: `8558e1847918b08eb0db9ce512c4bcfb4e94e4a1f7dc4a222cdd2b99cd2c6220`
- Operator matrix: `c25202e5842b79073ae27ab2edb5068a12846a57bcaa47cfc8d3be30436ce235`

## Selected point estimates

| Regime | Raw cosine | Raw Euclidean | Diagonal ridge metric | Rank-one ridge projection |
|---|---:|---:|---:|---:|
| Axis linear | 0.0779 | 0.0944 | 0.9766 | 0.9766 |
| Rotated linear | 0.0813 | 0.1053 | 0.1771 | 0.9768 |

Values are mean Spearman correlations between oracle target distance and method distance over the frozen test queries.

The absent relation remained close to chance across all methods. Its largest reported Spearman value was `0.0081`, while triplet accuracy remained between `0.5000` and `0.5060`.

The implemented linear methods also remained near chance on nonlinear XOR: average precision ranged from `0.5033` to `0.5067`, and triplet accuracy ranged from `0.4999` to `0.5028`.

## Provisional interpretation

The deterministic point estimates support four observations for the next confirmatory stage:

1. raw cosine and Euclidean geometry do not strongly expose the known synthetic linear relation;
2. diagonal weighting performs strongly when the relation is axis-aligned but degrades sharply after orthogonal rotation;
3. a learned rank-one direction retains strong performance after rotation;
4. the current linear methods do not invent performance for the absent relation or solve nonlinear XOR.

These observations are not yet promoted findings. Permutation nulls, paired bootstrap confidence intervals, confirmatory seeds and certification decisions remain required.

## Reproduction

```powershell
.\scripts\20-run-e00-operator-matrix.ps1
.\scripts\21-verify-e00-operator-matrix.ps1
```

## Revision condition

This checkpoint must be revised if independent recomputation no longer reproduces the operator matrix hash, or if the confirmatory stage shows that the apparent axis/rotation contrast is not stable across nulls, resamples and seeds.

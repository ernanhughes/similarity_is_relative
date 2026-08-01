# E00 Baseline Checkpoint v1

- **Checkpoint:** `e00-baseline-checkpoint-v1`
- **Status:** `BASELINE_VERIFIED`
- **Scientific status:** `E00_INCOMPLETE`
- **Manifest SHA-256:** `8558e1847918b08eb0db9ce512c4bcfb4e94e4a1f7dc4a222cdd2b99cd2c6220`
- **Verification SHA-256:** `d9178ba52e0854d1fa41d52db4e2959fbc4aa3c97d7c7850608dc5b7d8d2d4d4`
- **Claim promotion allowed:** `false`
- **Recorded at:** `2026-08-01T09:44:05.671391+00:00`

## Baseline summary

| Regime | Target | Spearman | Triplet accuracy | Recall@10 |
|---|---|---:|---:|---:|
| `absent` | continuous | 0.0033 | 0.5042 | 0.0034 |
| `axis_linear` | continuous | 0.9766 | 0.9334 | 0.0601 |
| `correlated_nuisance` | continuous | 0.2944 | 0.6309 | 0.0029 |
| `nonlinear_xor` | binary | 0.0066 | 0.5028 | 0.0034 |
| `rotated_linear` | continuous | 0.9768 | 0.9387 | 0.0739 |
| `weak_linear` | continuous | 0.7417 | 0.7861 | 0.0172 |

## Decision

The deterministic generator, artifact identities, ridge baseline and target-specific
metric verifier passed. This is a **baseline checkpoint**, not a completed E00
scientific result. The next required work is the registered operator suite,
permutation nulls, bootstrap intervals and certification decision.

## Reproduce

```powershell
.\scripts\10-run-e00.ps1
.\scripts\11-verify-e00.ps1
.\scripts\12-finalize-e00.ps1
```

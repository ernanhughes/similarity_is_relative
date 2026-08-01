# E00 Evidence Audit and Erratum

Date: 2026-08-01

## Purpose

This audit records two methodological corrections discovered after the frozen E00.4 multi-seed checkpoint. It does not modify any historical result artifact, hash, threshold, seed, model selection, decision, or gate outcome.

The frozen E00.4 outcome remains:

```text
Replay verification: PASS
Scientific gate: FAIL
Required decisions matched: 6 of 7
Claim promotion: blocked
```

Evidence identities remain:

```text
Aggregate result:
8dd526eaa45a28f56c99cb1045138685b89982109dbf61fb9788a6a65937e86d

Decision tree:
25b52842a4d5fbfefa1145c8f406328dc70744659852b7aa0535cf06788f4c90
```

## Erratum 1: mixed metrics in one nonlinear diagnostic

The E00.4 implementation labelled a derived quantity as nonlinear-minus-linear average precision. The calculation instead subtracted linear triplet accuracy from nonlinear average precision.

Those metrics are not commensurable and must not be subtracted. The reported lower confidence bound of approximately `0.1169` is therefore invalid as an average-precision advantage interval and must not be used as evidence.

This error does not reverse the historical nonlinear decision. The nonlinear XOR result independently failed other preregistered conditions:

- minimum seed test AP was approximately `0.5011`, below `0.75`;
- only one of five seeds reached test AP of at least `0.85`;
- mean test AP was approximately `0.7546`;
- the seed-level lower confidence bound was approximately `0.6154`, below `0.80`.

The historical decisions therefore remain:

```text
xor.nonlinear_multiseed = INSUFFICIENT_EVIDENCE
scientific gate = FAIL
```

Future comparisons between linear and nonlinear XOR methods must use the same metric on both sides, normally average precision.

## Erratum 2: verifier classification

The E00.4 verifier imported and called the experiment runner, regenerated the result in a temporary directory, and compared the complete result trees.

That establishes deterministic replay, stable model selection, hash-addressed reproducibility, and absence of accidental dependence on the original run directory.

It does not constitute an independent mathematical implementation because shared metric or decision bugs are reproduced by the same code path. The correct term for E00.4 is therefore:

> deterministic replay verifier

This audit distinguishes:

- **artifact validation** — required files, fields, and hashes are present;
- **deterministic replay** — the same implementation reproduces the same result;
- **independent recomputation** — separate substantive code recomputes metrics and decisions;
- **adversarial audit** — alternative calculations search for conceptual or methodological defects.

Future stages must not describe replay verification as independent recomputation.

## Claim-boundary correction

Ridge predicted-value distance and distance along the normalised ridge coefficient define the same ranking geometry in the scalar linear setting. The intercept cancels and normalisation applies only a positive global scale.

E00 therefore does not establish an algorithmic advantage of rank-one projection over ridge predicted-value retrieval. It establishes a representation and geometry result:

> In the registered synthetic setting, a known linear relation weakly exposed by raw cosine and Euclidean distance was strongly recoverable through a supervised scalar direction, and that recoverability survived an information-preserving rotation.

## Correct current status

The complete composite E00 certification claim remains blocked. Narrower registered outcomes should nevertheless be recorded accurately:

| Component | Evidence status |
|---|---|
| Linear recovery in native and rotated bases | `REPLICATED_SYNTHETIC` |
| Rank-one rotation retention | `REPLICATED_SYNTHETIC` |
| Diagonal basis dependence | `REPLICATED_SYNTHETIC` |
| Absent relation | `UNSUPPORTED_AT_THRESHOLD` |
| Linear XOR recovery | `UNSUPPORTED_AT_THRESHOLD` |
| Shortcut robustness | `UNSTABLE_UNDER_SHIFT` |
| Reliable nonlinear XOR recovery | `INSUFFICIENT_EVIDENCE` |
| Complete E00 certification claim | `BLOCKED` |

## Publication consequence

No frozen artifact is rewritten. The blog and repository status are corrected prospectively, and this audit remains linked from the affected result records and claims ledger.

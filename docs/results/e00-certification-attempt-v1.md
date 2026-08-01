# E00.3 Seed-17 Certification Attempt v1

## Outcome

- Independent verification: **PASS**
- Certification gate: **FAIL**
- Verified decisions: **7**
- Scientific claim promotion: **blocked**

This is a valid failed gate, not an execution failure. The runner and independent verifier agreed on the complete decision tree.

## Decision record

| Decision | Recorded status |
|---|---|
| Axis-aligned rank-one recovery | `SUPPORTED` |
| Rotated rank-one recovery | `SUPPORTED` |
| Absent relation | `UNSUPPORTED_AT_THRESHOLD` |
| Linear XOR recovery | `UNSUPPORTED_AT_THRESHOLD` |
| Nonlinear XOR recovery | `INSUFFICIENT_EVIDENCE` |
| Diagonal basis dependence | `INSUFFICIENT_EVIDENCE` |
| Correlated-nuisance shift | `UNSTABLE_UNDER_SHIFT` |

## Why the gate failed

The diagonal basis-dependence estimate was approximately `0.3747`, below the predeclared effect-size floor of `0.50`.

The nonlinear XOR diagnostic reached average precision of approximately `0.8112`, but its 95% bootstrap lower bound was approximately `0.7924`, below the predeclared support floor of `0.80`.

The thresholds are preserved unchanged. Any revised protocol must receive a new experiment or checkpoint identifier.

## Evidence identities

- Source manifest: `8558e1847918b08eb0db9ce512c4bcfb4e94e4a1f7dc4a222cdd2b99cd2c6220`
- Operator matrix: `c25202e5842b79073ae27ab2edb5068a12846a57bcaa47cfc8d3be30436ce235`
- Certification: `f095fada6527d1214c26c1086d95c751df5ebc4f267c7bd1a2c70a7ec5279b16`
- Decision tree: `32e084b8a7bde09d80e19c9b0df00b8f55df1cdde5db329ab74141e8a331c832`

## Next step

Design a separately preregistered remediation and confirmatory protocol. Do not overwrite, reinterpret or lower the thresholds of this attempt.

# RELATE Claim Ledger

This ledger separates established prior art, implemented tests, replicated results, verified findings and rejected hypotheses.

## Status vocabulary

- **Prior art:** established by earlier work; not a RELATE contribution.
- **Proposed:** falsifiable claim recorded before implementation.
- **Implemented:** executable test exists; canonical result not yet verified.
- **Replicated:** an established result was reproduced under a committed contract.
- **Verified:** a canonical run passed the committed verifier.
- **Refined:** evidence supports a narrower claim.
- **Rejected:** evidence contradicted the claim.
- **Unsupported:** recoverability was not certified at the declared operating threshold.

## Claims

| ID | Claim | Status | Experiment | Required baseline | Falsification or revision condition |
|---|---|---|---|---|---|
| PA-001 | Context-specific masks and metrics over shared embeddings are established prior art. | Prior art | E02 | Conditional Similarity Networks and standard metric learning | Never present this as a RELATE invention. |
| H-001 | A low-rank operator can recover a randomly rotated linear relation that raw cosine and a raw-basis diagonal operator fail to expose. | Proposed | E00 | Exact raw cosine, ridge predicted-distance, diagonal metric | Low-rank performance fails to exceed the strongest simple baseline under the frozen synthetic contract. |
| H-002 | A raw-coordinate diagonal operator is basis dependent. | Proposed | E00 | Native-basis and randomly rotated runs | Diagonal performance is unchanged across rotations within the frozen tolerance. |
| H-003 | Linear operators fail honestly when the target relation is nonlinear or absent. | Proposed | E00 | Nonlinear probe and permutation null | Linear methods materially exceed the null on absent signal, or the verifier certifies unsupported signal as supported. |
| H-004 | Certification can distinguish supported, unsupported-at-threshold and insufficient-evidence regimes. | Proposed | E00/E06 | Fixed confidence threshold and permutation null | Certification cannot separate known present and absent synthetic signals under the preregistered thresholds. |
| H-005 | Primitive relation operators can later serve unseen relational compositions with bounded regret. | Proposed | E05 | Exact score fusion, constraints, Pareto retrieval, joint oracle | Simple baselines match or beat RELATE composition. |
| H-006 | Findings from protein embeddings transfer to sentence embeddings. | Proposed | E07 | Exact raw cosine and text-specific probes | Protein success does not reproduce on the frozen sentence benchmark. |

## Publication rule

A publication sentence beginning with “we found” must map to a **Verified**, **Replicated**, **Refined**, or explicitly qualified **Unsupported** row. Proposed and Implemented rows remain questions or procedures.

# RELATE Claim Ledger

This ledger separates established prior art, implemented tests, point estimates, replicated results, verified findings, unsupported hypotheses and blocked composite claims.

## Status vocabulary

- **Prior art:** established by earlier work; not a RELATE contribution.
- **Proposed:** falsifiable claim recorded before implementation.
- **Implemented:** executable test exists; canonical result not yet verified.
- **Replay-verified point estimate:** one registered run passed its frozen point-estimate rule and deterministic replay, but has not been confirmed across fresh dataset seeds.
- **Replicated synthetic:** a registered synthetic result reproduced across fresh dataset seeds.
- **Refined:** evidence supports a narrower claim than originally proposed.
- **Unsupported at threshold:** the declared operator family was not certified at the frozen threshold.
- **Insufficient evidence:** the result did not cross the frozen support or rejection rule.
- **Unstable under shift:** development performance did not survive the registered distribution shift.
- **Blocked:** a composite publication claim cannot be promoted because one or more required decisions failed.

## Claims

| ID | Claim | Status | Experiment | Required baseline | Falsification or revision condition |
|---|---|---|---|---|---|
| PA-001 | Context-specific masks and metrics over shared embeddings are established prior art. | Prior art | E03 | Conditional Similarity Networks and standard metric learning | Never present this as a RELATE invention. |
| E00-LIN-001 | In the registered synthetic setting, a known linear relation weakly exposed by raw cosine and Euclidean distance is strongly recoverable through a supervised scalar direction. | Replicated synthetic | E00.2/E00.4 | Raw cosine, raw Euclidean, ridge predicted-value distance | Fresh registered seeds fail the rank-one recovery thresholds or raw geometry closes the declared gap. |
| E00-ROT-001 | Recovery through the supervised scalar direction survives a common information-preserving orthogonal rotation. | Replicated synthetic | E00.4 | Native and rotated rank-one retrieval | Rotation retention fails the frozen multi-seed thresholds. |
| E00-BASIS-001 | A raw-coordinate diagonal metric is basis dependent under the registered rotation test. | Replicated synthetic | E00.4 | Native and rotated diagonal retrieval | Diagonal retention no longer shows the preregistered degradation across fresh seeds. |
| E00-ABS-001 | The registered rank-one family does not certify the absent synthetic relation. | Unsupported at threshold | E00.3/E00.4 | Permutation null and absent generator | The absent relation crosses the registered support rule on confirmation. |
| E00-XOR-LIN-001 | The registered linear family does not recover the nonlinear XOR relation. | Unsupported at threshold | E00.3/E00.4 | Linear rank-one and permutation null | Linear recovery crosses the registered nonlinear support threshold. |
| E00-XOR-NL-001 | The registered nonlinear family reliably recovers XOR across fresh synthetic seeds. | Insufficient evidence | E00.4 | Validation-selected polynomial and MLP families | A new preregistered nonlinear diagnosis and confirmation stage satisfies its frozen multi-seed rules. |
| E00-SHIFT-001 | The registered shortcut-dependent relation is unstable when its development-time correlation breaks at test time. | Unstable under shift | E00.3/E00.4 | Validation-to-test gap | The gap no longer crosses the registered instability rule on fresh seeds. |
| E00-COMP-001 | The complete E00 family-aware certification claim passes all required positive, negative and shift controls. | Blocked | E00.4 | Seven-decision all-or-nothing gate | Every required decision passes in a new preregistered confirmation stage. |
| E01-COMP-PE-001 | Independently predicted primitive coordinates approximated four preregistered weighted product-space relations in the seed-307 synthetic run and exceeded the controls included in the frozen E01.1 contract. | Replay-verified point estimate | E01.1 | Raw cosine, raw Euclidean, one declared scalar collapse, one cyclic wrong alignment, true-target product-space oracle | Fresh-seed confirmation fails, a stronger scalar or wrong-alignment baseline closes the gap, or unsupported-component tests show confident composition from unsupported primitives. This row is not evidence of algorithmic novelty. |
| H-005 | Primitive relation operators can serve unseen relational compositions with bounded regret and support-aware refusal beyond standard score fusion. | Proposed | E01.2/E01.3/E06 | Strong scalar projections, weighted product-space score fusion, constraints, Pareto retrieval, direct compound comparator, unsupported-component controls | Standard score fusion or directly trained baselines match or beat the proposed RELATE mechanism, or unsupported primitives are not correctly refused. |
| H-006 | Findings from protein embeddings transfer to sentence embeddings. | Proposed | E08 | Exact raw cosine and text-specific probes | Protein success does not reproduce on the frozen sentence benchmark. |

## Interpretation notes

### Ridge equivalence

In the scalar linear E00 setting, ridge predicted-value distance and distance along the normalised ridge coefficient are ranking-equivalent. The intercept cancels and coefficient normalisation applies a positive global scale. E00-LIN-001 is therefore a representation and geometry result, not evidence that rank-one projection outperforms ridge prediction.

### E00.4 erratum

One E00.4 secondary diagnostic subtracted linear triplet accuracy from nonlinear average precision while labelling the quantity as an AP difference. That derived interval is invalid and must not be used. The nonlinear decision and gate failure remain unchanged because multiple other preregistered conditions failed independently. See [`docs/audits/e00-evidence-audit-2026-08-01.md`](docs/audits/e00-evidence-audit-2026-08-01.md).

### E01.1 classification

E01.1 is a successful synthetic composition positive control and harness validation. Its method is standard weighted product-space score fusion over independently predicted properties. It is a real non-collapsing composition operation, but it is not evidence of a novel RELATE composition algorithm. Its frozen `composition_regret` field is interpreted as oracle triplet disagreement, not regret against a directly trained compound model.

### Verification classification

E00.4 and E01.1 have deterministic replay verification. Their verifiers called the corresponding experiment runners and compared regenerated output trees; they did not independently reimplement the substantive mathematics.

## Publication rule

A publication sentence beginning with “we found” must map to a **Replicated synthetic**, **Refined**, or explicitly qualified **Unsupported at threshold**, **Insufficient evidence**, or **Unstable under shift** row. A replay-verified point estimate must be described as a point estimate or positive control, not as a promoted finding. Proposed, Implemented and Blocked rows remain questions, procedures or failed composite gates.

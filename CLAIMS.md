# RELATE Claim Ledger

This ledger separates established prior art, implemented tests, point estimates, replicated results, independently audited interpretations, unsupported hypotheses and blocked composite claims.

## Status vocabulary

- **Prior art:** established by earlier work; not a RELATE contribution.
- **Proposed:** falsifiable claim recorded before implementation.
- **Implemented:** executable test exists; canonical result not yet verified.
- **Replay-verified point estimate:** one registered run passed its frozen rule and deterministic replay.
- **Replicated synthetic:** a registered synthetic measurement reproduced across fresh dataset seeds.
- **Refined:** later evidence supports a narrower interpretation than the original status implied.
- **Closed:** the line has been evaluated and will not be advanced under its former thesis.
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
| E01-COMP-PE-001 | In seed 307, predicted primitive coordinates approximated four weighted product-space queries and exceeded the controls in the frozen E01.1 contract. | Refined | E01.1 / independent recomputation | Raw cosine, raw Euclidean, scalar collapse, all five non-identity permutations, latent oracle | The measurement remains valid, but only `a3_c` retains E01.1's original `0.10` margin when all five permutations are considered. This row is a historical positive-control record, not general composition evidence. |
| E01-COMP-MS-001 | Across five fresh seeds, predicted primitive coordinates reproduced four weighted product-space measurements and exceeded the scalar and permutation controls under the E01.2a substage rule. | Refined | E01.2a / independent recomputation | Scalar projections, all permutations, latent oracle, top-k retrieval | The measurement replicated, but the executor was saturated at the latent oracle and the substage rule differed from E01.1. This is standard score fusion in a non-discriminating generator. |
| E01-AUDIT-001 | E01.1 fails its original `0.10` control-margin rule for three of four compounds when the strongest of all five non-identity permutations is used. | Independently audited | E01 independent recomputation | Exhaustive permutation sweep and original frozen rule | A separate independent implementation does not reproduce margins near `0.0853`, `0.1464`, `0.0788`, and `0.0374`. |
| E01-CEIL-001 | The E01.2a predicted-primitive executor operates at effectively the same triplet-accuracy ceiling as the true noiseless latent executor. | Independently audited | E01 independent recomputation | Latent oracle and ceiling fraction | Fresh non-saturated generator regimes produce a material and stable gap from the attainable ceiling. |
| E01-PERM-001 | In the exchangeable E01 generator, the strongest wrong-permutation margin is primarily determined by weight separation and is zero for symmetric weights. | Independently audited | E01 independent recomputation | Frozen weight-separation sweep | A non-exchangeable semantic-identity experiment shows the same diagnostic has semantic validity. |
| E01-LINE-001 | The E01 weighted-product-space line supports a general or novel relational-composition claim. | Closed | E01.0–E01.2a | Direct compound models, non-saturated primitives, semantic identity, support boundaries | This former thesis is closed. Any future support-aware query-runtime claim begins under a new experiment contract and does not inherit E01 success. |
| H-005 | A support-aware relational query runtime can execute declared compound queries over imperfect primitive evidence, retain a useful zero-shot reuse advantage, propagate uncertainty and refuse unsupported requests. | Proposed | E02–E07 | Direct compound comparators, conditional metric learning, independent thresholding, conformal/selective prediction | Direct baselines match the runtime at equal supervision and coverage, the runtime cannot identify unsupported queries, or the effect fails in a limited real-domain pilot. |
| H-006 | Findings from one real frozen-representation domain transfer to sentence embeddings. | Proposed | E08 | Exact raw cosine and text-specific probes | Real-domain success does not reproduce on the frozen sentence benchmark. |

## Interpretation notes

### Ridge equivalence

In the scalar linear E00 setting, ridge predicted-value distance and distance along the normalised ridge coefficient are ranking-equivalent. The intercept cancels and coefficient normalisation applies a positive global scale. E00-LIN-001 is therefore a representation and geometry result, not evidence that rank-one projection outperforms ridge prediction.

### E00.4 erratum

One E00.4 secondary diagnostic subtracted linear triplet accuracy from nonlinear average precision while labelling the quantity as an AP difference. That interval is invalid and must not be used. The nonlinear decision and gate failure remain unchanged. See [`docs/audits/e00-evidence-audit-2026-08-01.md`](docs/audits/e00-evidence-audit-2026-08-01.md).

### E01 closure

E01.1 and E01.2a remain numerically reproducible historical positive controls. Independent recomputation established three interpretation-changing facts:

1. only one of four E01.1 compounds retains the original `0.10` rule under exhaustive wrong-alignment controls;
2. E01.2a operates at effectively the true-latent attainable ceiling;
3. the exchangeable-primitives permutation margin is a weight-separation diagnostic, not a semantic-identity test.

The E01.2a label `scientific gate: PASS` referred only to its in-code positive-control substage rule. The complete E01.2 support-aware gate was not attempted.

See:

- [`docs/results/e01-independent-recomputation-checkpoint-v1.md`](docs/results/e01-independent-recomputation-checkpoint-v1.md)
- [`docs/blog/closing-the-e01-composition-line.md`](docs/blog/closing-the-e01-composition-line.md)
- [`docs/audits/e01-external-review-audit-2026-08-01.md`](docs/audits/e01-external-review-audit-2026-08-01.md)

### Verification classification

E00.4, E01.1 and E01.2a have deterministic replay verification. The E01 closure additionally has an independent recomputation implementation that does not call the experiment runners or their metric and decision helpers.

## Publication rule

A publication sentence beginning with “we found” must map to a **Replicated synthetic**, **Refined**, **Independently audited**, or explicitly qualified negative row. Replay-only point estimates must be described as point estimates or positive controls. Closed rows must not be revived without a new experiment identifier, a new frozen contract and an explicit statement that no prior success is inherited.

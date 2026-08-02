# RELATE Claim Ledger

This ledger separates established prior art, implemented tests, point estimates, replicated results, independently verified real-domain findings, independently audited interpretations, unsupported hypotheses and blocked composite claims.

## Status vocabulary

- **Prior art:** established by earlier work; not a RELATE contribution.
- **Proposed:** falsifiable claim recorded before implementation.
- **Proposed, authorised:** the preceding gate passed, but the confirmatory experiment has not yet produced a result.
- **Implemented:** executable test exists; canonical result not yet verified.
- **Replay-verified point estimate:** one registered run passed its frozen rule and deterministic replay.
- **Replicated synthetic:** a registered synthetic measurement reproduced across fresh dataset seeds.
- **Independently verified real-domain:** a registered real-domain result passed its frozen rule and a separate substantive implementation exactly recomputed the primary evidence and decision.
- **Independently audited:** a separate substantive implementation reproduced an interpretation-changing audit result.
- **Refined:** later evidence supports a narrower interpretation than the original status implied.
- **Closed:** the line has been evaluated and will not be advanced under its former thesis.
- **Unsupported at threshold:** the declared operator family was not certified at the frozen threshold.
- **Insufficient evidence:** the result did not cross the frozen support or rejection rule.
- **Unstable under shift:** development performance did not survive the registered distribution shift.
- **Blocked:** a composite publication claim cannot be promoted because one or more required decisions failed.

Exploratory C0 measurements are not claim statuses. They may select a hypothesis for C1, but they cannot promote or revise a scientific claim without fresh confirmatory evidence.

## Claims

| ID | Claim | Status | Experiment | Required baseline | Falsification or revision condition |
|---|---|---|---|---|---|
| PA-001 | Context-specific masks and metrics over shared embeddings are established prior art. | Prior art | Historical / future baseline work | Conditional Similarity Networks and standard metric learning | Never present this as a RELATE invention. |
| PA-CODE-001 | Pretrained code models, frozen probing, AST metrics and repository-separated code benchmarks are established prior art. | Prior art | Option B | CodeBERT, CodeSearchNet and code-model probing literature | Never present the representation, probes, AST extractors or split design as RELATE inventions. |
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
| H-005 | The cancelled broad E02–E07 synthetic roadmap can establish a support-aware relational query runtime through a large factorisation and supervision matrix. | Closed | Post-E01 decision | Real-premise test and bounded refusal test | This roadmap is cancelled. It may not be revived without a new explicit project decision. |
| B-PREM-001 | In repository-separated real Python code, independently predicted AST primitives expose the frozen three-way structural relation materially better than the strongest default CodeBERT geometry. | Independently verified real-domain | Option B | Raw CodeBERT cosine, raw CodeBERT Euclidean, token-length diagnostic, true-primitive oracle | A separate substantive recomputation fails to reproduce the exact `4,000 × 5` query-score matrix or the registered `0.199537109375` gap, or a new preregistered external replication materially contradicts the bounded claim. |
| C-REFUSE-001 | Propagated compound support can improve selective risk at matched coverage beyond independent per-primitive conformal abstention and a directly trained compound model with its own conformal wrapper. | Proposed, authorised | Option C1, conditional on C0 | Independent primitive conformal abstention, direct compound conformal model, uncalibrated confidence diagnostic and oracle-support headroom | C0 records `C1_NOT_JUSTIFIED`, `C0_DATA_FIREWALL_FAILED` or `C0_BUDGET_EXHAUSTED`, or C1 later fails its frozen material-margin decision. C0 exploratory measurements cannot support this row. |

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

### Option B result and boundary

Option B was a real-premise kill test, not a novelty experiment. It froze one CodeSearchNet language, one CodeBERT representation, three objective AST primitives, one Chebyshev conjunction and one primary `0.10` continuation threshold.

The registered primary result was:

```text
raw cosine accuracy:       0.532458984375
raw Euclidean accuracy:    0.533314453125
predicted executor:        0.732851562500
raw best:                  0.533314453125
gap:                       0.199537109375
threshold:                 0.100000000000
outcome:                   REAL_PREMISE_SUPPORTED
```

All 4,000 test queries contributed 128 frozen hard-negative pairs. A standalone implementation that did not import the evaluator reverified every input, independently recomputed the complete `4,000 × 5` primary query-score matrix, required exact equality and reproduced the final decision.

Secondary evidence was directionally consistent but did not determine the decision. The predicted executor's Spearman correlation with oracle distance was approximately `0.723`, versus approximately `0.112` for raw cosine and `0.110` for raw Euclidean. Its recall@10 improved to approximately `0.0091`, but remained low in absolute terms. The claim is therefore about material underexposure by default geometry, not solved nearest-neighbour retrieval.

Option B does not establish novelty, a general composition algorithm, semantic binding, uncertainty propagation or calibrated refusal. It authorises the bounded Option C0/C1 sequence only.

See:

- [`docs/experiments/08-option-b-real-code-premise-test.md`](docs/experiments/08-option-b-real-code-premise-test.md)
- [`docs/results/option-b-real-code-premise-checkpoint-v1.md`](docs/results/option-b-real-code-premise-checkpoint-v1.md)
- [`docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md`](docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)
- [`artifacts/canonical/option-b/method-evaluation-v1/`](artifacts/canonical/option-b/method-evaluation-v1/)

### Option C0 discovery boundary

Option C0 freezes how the project may explore the refusal mechanism; it does not freeze or validate the final mechanism itself.

C0 uses five repository-separated roles:

```text
C0 fit
C0 iteration
C0 selection
C1 calibration reserve
C1 test reserve
```

C1 calibration and test rows are not selected during C0. A future C1 contract must freeze the selection procedure, and the final identities are derived only after that contract merges.

C0 requires:

- an append-only candidate registry;
- an append-only discovery ledger;
- independent primitive conformal abstention;
- a direct compound conformal model;
- propagated-support candidates;
- attainable-headroom diagnostics;
- complete retention of failed and superseded candidates;
- one explicit C0 exit outcome.

The permitted C0 outcomes are:

```text
C1_CONTRACT_JUSTIFIED
C1_NOT_JUSTIFIED
C0_DATA_FIREWALL_FAILED
C0_BUDGET_EXHAUSTED
```

Only `C1_CONTRACT_JUSTIFIED` permits a later documentation-only C1 contract. It does not promote C-REFUSE-001.

See:

- [`docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`](docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md)
- [`docs/research/option-c0-discovery-preservation-decision-2026-08-02.md`](docs/research/option-c0-discovery-preservation-decision-2026-08-02.md)

### Discovery-preservation rule

An unexpected C0 observation may influence the future C1 contract when it is recorded before C1 freezes. It cannot be described as confirmed, inspect C1 evidence, rescue a failed C1 decision or inherit support from B-PREM-001.

An unexpected observation first discovered on C1 test data requires a new experiment identifier and fresh data before it can become a promoted claim.

### Option C1 boundary

Option C1 remains blocked until C0 publishes `C1_CONTRACT_JUSTIFIED`.

The future C1 contract must freeze:

- the selected propagation mechanism;
- the exact query or bounded query set;
- train and fitting roles;
- the final calibration method;
- independent primitive and direct compound baselines;
- coverage and selective-risk definitions;
- matched-coverage comparison procedure;
- material margin;
- refusal, tie and empty-support handling;
- post-contract reserve selection;
- independent recomputation requirements;
- the claim-scoped novelty-line decision.

No Option B threshold, outcome, model, language, canonical row or manifest may be changed to assist C0 or C1.

### Verification classification

E00.4, E01.1 and E01.2a have deterministic replay verification. The E01 closure additionally has an independent recomputation implementation that does not call the experiment runners or their metric and decision helpers.

Option B has independent real-domain primary recomputation over frozen embeddings, primitive values, predicted vectors and hard-negative manifests. The independent implementation did not import the experiment evaluator and exactly matched every primary query score and the final decision.

C0 outputs are exploratory even when deterministically replayed. Verification of C0 artifacts establishes provenance and integrity, not C-REFUSE-001.

## Publication rule

A publication sentence beginning with “we found” must map to a **Replicated synthetic**, **Refined**, **Independently audited**, **Independently verified real-domain**, or explicitly qualified negative row. Replay-only point estimates must be described as point estimates or positive controls.

C0 measurements must be described as exploratory observations, development diagnostics or mechanism-selection evidence. They may not be phrased as “we found” support for C-REFUSE-001.

Closed rows must not be revived without a new experiment identifier, a new frozen contract and an explicit statement that no prior success is inherited.

# Option C0 Advanced Review Synthesis

Date: 2026-08-02

Status: **INDEPENDENT REVIEW SYNTHESIS — NOT A SCIENTIFIC DECISION**

## Reviewed material

This synthesis combines two advanced external reviews with direct inspection of the merged implementation and canonical v1 artifact.

The reviews are treated as hypothesis and defect reports, not as evidence merely because they were produced by advanced models.

## Overall assessment of the latest review

The latest review is technically useful and materially stronger than the initial weak reviews. Its best new contributions are:

1. identifying that `StandardScaler` is fitted before repository-grouped Ridge folds;
2. distinguishing full-embedding direct prediction from information-matched use of the three predicted primitive margins;
3. identifying that current role separation does not establish code-, AST-, fork-, mirror-, template-, or repository-family separation;
4. demanding class-specific selective metrics, repository-unit uncertainty, and complete execution provenance;
5. proposing an exact compiled query-boundary baseline and a direct classifier on the same three predicted margins.

These points are incorporated into C0-D.

## Where the latest review is incomplete

### It understates confirmed diagnostic defects

The review says that no critical result-destroying implementation error is proven. That is too weak.

Direct code inspection confirms:

- the interval ranking score is folded and non-monotone;
- the direct-conformal ranked curves use a prediction vector that is not an ordinary prediction outside singleton sets.

These defects invalidate the affected matched-coverage curves. They do not erase every v1 observation, but they prevent the published comparison layer from supporting selection or C1.

### It treats the boundary mass as minor

The review classifies strict `> 0` thresholds on discrete medians as minor. In the v1 iteration, 2,380 of 4,110 rows are exactly tied on at least one primitive threshold. The labels remain defined by the frozen rule, but the magnitude makes this a major interpretation and task-design issue rather than a minor detail.

### It does not fully address execution provenance

The review correctly describes a fragmented adapter chain, but the more precise defect is that the candidate registry's evaluated events identify the registered implementation commit rather than the complete source composition that executed the run. C0-D requires an executable-source manifest and an explicit registry/provenance erratum.

### Some proposed diagnostics do not require fresh data

Accepted-class composition, constant-class references, exact query-boundary distance, corrected risk–coverage curves, information-matched three-margin baselines, repository weighting, and duplicate-role audits are legitimate post-result diagnostics or integrity corrections on the already published C0 roles.

They cannot create confirmation, but they do not inherently require C0 selection or C1 data.

## Findings confirmed by direct inspection

### Confirmed implementation defects

1. `StandardScaler` is fitted on all model-fit embeddings before grouped fold selection.
2. The interval ranking score is folded and non-monotone.
3. Direct-conformal ranked curves reuse prediction-set membership as a class prediction outside singleton sets.
4. The `absent` diagnostic regime is unreachable under the current branch order and margin lattice.
5. The current publication lacks a complete executing-source manifest.
6. Accepted-class composition is absent from the result.
7. The so-called oracle acceptance set is a query-independent true-margin tie diagnostic, not a selective-coverage ceiling.

### Confirmed descriptive facts

1. The conjunction iteration prevalence is approximately 6.52%, or 268 positive rows among 4,110.
2. `candidate_joint_box_alpha_0.01` has 268 full-coverage errors and therefore predicts False on every conjunction row.
3. Its 61 accepted zero-error conjunction rows are therefore all accepted negative answers.
4. The empirical residual-mass beta `0.01` result accepts 1,756 rows with zero errors, but the artifact does not reveal their true/predicted class composition.
5. The direct ordinary-confidence curve and empirical residual-mass curve are the principal surviving globally ranked curves in v1.
6. All three primitive Ridge models selected alpha `100`, the top of the frozen grid.

## Risks requiring measurement rather than assumption

1. exact source duplication across Option C roles;
2. normalized-AST duplication across roles;
3. fork, mirror, generated-template, or repository-family overlap;
4. residual covariance and heteroscedasticity;
5. repository-cluster uncertainty;
6. whether the top-of-grid alpha choice materially changes under fold-local preprocessing;
7. whether empirical residual mass adds anything beyond exact boundary geometry;
8. whether complete residual-vector dependence matters relative to shuffled controls;
9. whether the conjunction accepted set includes meaningful positive answers.

## Correct interpretation of the direct baseline

The full-embedding direct classifier is mandatory as a practical baseline, but it does not isolate the uncertainty-propagation question because it receives 768 embedding dimensions while the candidates receive three predicted primitive margins.

C0-D therefore requires both:

```text
direct_compound_full_embedding
direct_compound_predicted_primitives
```

The second is the decisive information-matched baseline for determining whether explicit propagation adds value beyond direct use of the same primitive summary.

## Correct interpretation of the current candidates

### Joint max-residual box

This is a global constant-width, axis-aligned interval mechanism. It is structurally close to independent primitive interval abstention and cannot express row-conditional uncertainty.

It is not literally identical to the independent baseline because its radius vector is calibrated through a joint max-residual quantile rather than separate coordinate quantiles. The two methods nevertheless occupy the same broad mechanism class.

### Empirical residual mass

This applies one global empirical set of complete joint residual vectors to every row. It preserves observed residual dependence but does not condition uncertainty on the row, repository, predicted value, or embedding neighbourhood.

It is more than an axis-aligned boundary distance, but it remains a globally smoothed confidence function of the predicted primitive vector. Its distinctive value is not demonstrated.

## Governing decision

The latest review supports remediation, not C1 and not immediate termination.

```text
C0 selection: blocked
C1: blocked
v1 artifact: preserved
v1 comparison layer: partially invalidated
next phase: C0-D integrity audit and corrected replay
```

The detailed PR sequence and kill conditions are frozen in:

```text
docs/audits/option-c0-d-remediation-plan-2026-08-02.md
```

## What would count as successful remediation

Successful remediation does not mean producing a positive Option C result. It means producing a trustworthy answer.

C0-D succeeds if it:

1. resolves the duplicate/family firewall question;
2. creates one auditable execution identity;
3. corrects model-selection preprocessing and diagnostic scores;
4. publishes class-conditional and repository-aware metrics;
5. adds constant, boundary-distance, and information-matched controls;
6. replays the same six candidates without changing the scientific question;
7. independently recomputes the corrected summaries;
8. reaches a bounded decision even if that decision is `C1_NOT_JUSTIFIED`.

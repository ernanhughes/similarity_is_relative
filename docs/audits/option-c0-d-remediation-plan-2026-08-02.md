# Option C0-D Diagnostic Remediation and Corrected Replay Plan

Date: 2026-08-02

Status: **FROZEN FOR IMPLEMENTATION REVIEW**

## Purpose

Option C0-D is an integrity-remediation cycle for the already published Option C0 iteration. It is not a new scientific option, a new candidate round, or an opportunity to rescue a preferred result.

The original v1 result remains immutable at:

```text
artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json
SHA-256: ca81076fd21ecf97fc33dcd2a1690a2cd29443cb9cf5c26eba49c00095a1df99
```

C0-D exists because independent review identified confirmed defects in the diagnostic comparison layer and additional integrity risks that must be measured before C0 selection or C1 can be considered.

## Current scientific status

```text
C0 v1 artifact:                    PRESERVED, DESCRIPTIVE ONLY
C0 diagnostic comparison:         INVALIDATED PENDING REMEDIATION
C0 candidate registry closure:    NOT JUSTIFIED
C0 selection access:              BLOCKED
C1 contract:                      NOT JUSTIFIED
C1 reserve access:                BLOCKED
C-REFUSE-001:                     PROPOSED ONLY
scientific result observed:       false
```

The v1 artifact is not deleted or overwritten. Corrected outputs must be published under a new versioned path and must explicitly reference the v1 identity.

## Confirmed defects

### D-001 — interval risk–coverage score is folded and non-monotone

`interval_query_decision` currently assigns:

```python
scores = np.min(np.minimum(np.abs(low), np.abs(high)), axis=1)
```

For a symmetric one-dimensional interval with radius `r`, this becomes `||p| - r|`. A maximally ambiguous point at `p = 0` and a resolved point at `p = 2r` receive the same score. Therefore the ranked risk–coverage curves for:

- `candidate_joint_box_*`; and
- `independent_primitive_*`

are not valid matched-coverage comparisons.

The correction must be query-specific. It must rank by the minimum expansion or movement required to change the resolved compound answer, not by a folded coordinate-endpoint distance.

### D-002 — direct-conformal ranked curves use undefined predictions outside singleton sets

`direct_compound_conformal_decision` records `included[:, 1]` as the prediction. That is meaningful only when the conformal prediction set is a singleton. It is not an ordinary class prediction for ambiguous or empty sets.

The selective conformal results on singleton accepted rows remain descriptive. The ranked curves over all rows are invalid and must be recomputed from the fixed estimator argmax probabilities, with prediction-set membership reported separately.

### D-003 — model-selection preprocessing leaks validation repositories

`fit_primitive_models` fits `StandardScaler` once on the complete model-fit partition before repository-grouped cross-validation. Each validation fold therefore influences the preprocessing used to select Ridge alpha.

The scaler must be fitted inside each training fold during alpha selection. A final scaler may then be fitted on all model-fit rows after alpha is selected.

### D-004 — evaluation execution provenance is incomplete

The published execution used the original runner together with identity, diagnostic, recovery, cache, and canonical-batch adapters. The candidate registry's `commit_sha` identifies the registered candidate implementation rather than the complete executing source composition.

The corrected publication must contain a full execution manifest with file hashes, repository commit, command, arguments, environment identity, cache fingerprint, and source/embedding identities.

### D-005 — diagnostic regime taxonomy is degenerate

The current `weak` threshold captures every exact primitive-boundary tie before the `absent` branch is evaluated. On the discrete margin lattice, `absent` is unreachable.

The corrected result must use lattice-aware strata, for example:

1. tied on at least one primitive;
2. resolved by exactly one lattice step;
3. resolved by two or more lattice steps;
4. large prediction error or shifted regime.

### D-006 — accepted-class composition is missing

The conjunction has 268 positives among 4,110 iteration rows. Some low-error subsets may therefore be dominated by accepted negative answers.

Every selective result must report:

- true positives;
- true negatives;
- false positives;
- false negatives;
- accepted rows by true class;
- accepted rows by predicted class;
- positive and negative class coverage;
- positive and negative selective error;
- balanced selective risk;
- excess risk relative to constant-class policies.

### D-007 — the current oracle name and interpretation are misleading

`oracle_support` uses true primitive margins and therefore makes correct query predictions, but its acceptance rule is query-independent: accept only when no primitive is exactly tied at its threshold.

It must be renamed and documented as a **true-margin boundary diagnostic**, not an attainable selective-coverage ceiling.

## Required integrity audits

The following are not yet proven defects. They must be measured before the corrected replay is interpreted.

### A-001 — cross-role exact source duplication

Compute intersections of `code_sha256` across:

- C0 fit;
- C0 iteration;
- C0 selection;
- C1 reserve;
- excluded Option B repositories where relevant.

### A-002 — cross-role normalized-AST duplication

Compute the same role intersections for `normalized_ast_sha256`. The existing `remove_cross_split_duplicates` procedure removes normalized ASTs shared across original CodeSearchNet splits; it does not establish absence of same-split duplicates assigned to different Option C roles.

### A-003 — forks, mirrors, templates, and repository families

Create a bounded repository-family audit using available repository metadata and exact/near-duplicate evidence. If material cross-role connected components are found, the allocation must be invalidated and regenerated at family-component level before further result use.

### A-004 — repository clustering

Add repository-weighted metrics and repository-unit bootstrap intervals. Row-level conformal summaries must not be presented as repository-level guarantees.

### A-005 — alpha-grid boundary

All three primitive models selected alpha `100`, the largest frozen value. The corrected v2 result must retain the frozen alpha grid for comparability, while separately reporting fit-only diagnostics on an extended grid. The extended grid must not silently replace the registered grid in the corrected replay.

### A-006 — residual structure

Report residual covariance, heteroscedasticity by predicted-value and primitive-value strata, and repository-level residual variation. This determines whether global residual propagation is an adequate uncertainty substrate.

## Information-matched and trivial baselines

The corrected replay must include the following diagnostics. These are controls, not post-hoc promoted candidates.

1. constant False;
2. constant True;
3. accept only predicted False;
4. accept only predicted True;
5. exact compiled query-boundary distance using the three predicted margins;
6. direct query classifier using exactly the three predicted margins;
7. minimum/maximum primitive margin and confidence summaries;
8. residual magnitude and primitive-disagreement scores;
9. direct full-embedding classifier with fixed argmax confidence;
10. favourable-repository and low-complexity diagnostics, clearly labelled non-general controls.

The full-embedding direct model remains a mandatory practical baseline. The three-margin direct model is the information-matched mechanistic baseline.

## Corrected comparison rules

Methods must be compared using:

- risk at matched compound coverage;
- coverage at matched risk;
- class-balanced selective risk;
- class-specific coverage and error;
- repository-weighted risk;
- repository-unit bootstrap intervals;
- AURC or an equivalently predeclared full-curve summary;
- accepted-row counts alongside percentages.

Independent and joint intervals must not be compared at the same nominal alpha as if those alpha values imply the same joint primitive coverage. Report observed joint coverage and compare at matched observed coverage.

## C0-D pull-request sequence

### PR D0 — status and remediation contract

Scope:

- preserve v1 evidence;
- mark affected comparisons invalid;
- freeze this remediation plan;
- update README and review documentation;
- keep C0 selection and C1 blocked.

No scientific code or metric changes.

### PR D1 — firewall and execution audit

Scope:

- exact code- and AST-hash cross-role audit;
- bounded fork/mirror/template-family report;
- execution-source manifest infrastructure;
- one canonical clean replay command;
- tests for role separation and manifest completeness.

Decision gate:

```text
material role contamination found:
    publish C0_DATA_FIREWALL_FAILED or an explicit allocation-invalidated outcome
    do not perform the corrected replay on the old allocation

no material contamination found:
    retain allocation and continue to D2
```

### PR D2 — mechanical diagnostic and modelling corrections

Scope:

- fit preprocessing inside grouped folds;
- correct query-specific ranking scores;
- separate direct argmax prediction from conformal-set membership;
- add class contingency and repository-aware diagnostics;
- replace degenerate regimes;
- rename oracle boundary diagnostic;
- add constant and information-matched baselines;
- add primitive and residual diagnostics;
- remove diagnostic monkeypatching where practical and make one public execution path;
- comprehensive regression tests.

No new support-mechanism family may be introduced in D2.

### PR D3 — corrected C0 iteration replay v2

Scope:

- same visible C0 fit and iteration roles, unless D1 invalidates the allocation;
- same six registered v1 candidates;
- same frozen primitives, thresholds, queries, alpha grid, beta grid, and model family;
- corrected diagnostics and model-selection preprocessing;
- versioned v2 result, publication checkpoint, registry erratum, and execution manifest;
- cached embeddings may be reused only after exact fingerprint verification.

This is an integrity correction on already observed exploratory data. It cannot create confirmatory evidence.

### PR D4 — interpretation and decision

Scope:

- independent recomputation of corrected summaries;
- append classified discovery-ledger entries;
- state which v1 observations survive, change, or are invalidated;
- publish one bounded decision about the existing mechanism line.

Possible outcomes include:

```text
C1_NOT_JUSTIFIED
SECOND_C0_MECHANISM_ROUND_JUSTIFIED
C0_DATA_FIREWALL_FAILED
C0_REMEDIATION_INCOMPLETE
```

`C1_CONTRACT_JUSTIFIED` is not an assumed outcome and would require a corrected, non-trivial, scientifically meaningful advantage that survives the declared controls.

### PR D5 — new mechanism round, only if D4 justifies it

Any new mechanism must be registered before evaluation and must address a named failure of the v1 candidates. Priority families are:

- row-conditional primitive uncertainty;
- local or Mondrian residual distributions;
- discrete ordinal/count primitive distributions;
- query-specific compound risk control;
- dependence-preservation ablations.

No new mechanism is implemented in D0–D3.

## Kill conditions

Close the current propagated-support novelty line if the corrected replay shows that:

1. exact boundary distance, constant-class selection, or direct three-margin confidence matches or dominates the candidates;
2. any apparent conjunction advantage disappears under class-specific and repository-weighted analysis;
3. complete joint residual vectors do not outperform shuffled or independent residual controls in a later registered round;
4. row-conditional uncertainty fails to create a stable non-dominated region in a later registered round; or
5. any remaining gain exists only for easy negative conjunction examples.

A stopping decision does not alter the independently supported Option B premise result.

## Prohibited actions during C0-D

- access C0 selection;
- access or select C1 rows;
- overwrite or delete v1 artifacts;
- treat corrected replay as confirmation;
- change query thresholds, primitives, candidate definitions, or operating grids inside the v2 integrity replay;
- introduce new candidates before the corrected v2 result is independently reviewed;
- promote `C-REFUSE-001`.

## Next allowed action

```text
IMPLEMENT_PR_D1_FIREWALL_AND_EXECUTION_AUDIT
```

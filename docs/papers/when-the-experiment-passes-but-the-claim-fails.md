# When the Experiment Passes but the Claim Fails

## Evidence-First Evaluation of Relational Structure in Frozen Embeddings

**Working paper — version 0.1**  
**Date:** 2026-08-04  
**Status:** Technical-report draft; not yet a literature-complete or peer-reviewed manuscript

## Abstract

Research on learned representations often begins with a compelling intuition: an embedding may contain useful structure that its default cosine or Euclidean geometry does not expose. The difficult methodological problem is determining when an experiment supports that intuition, when it supports only a narrower implementation claim, and when apparently positive evidence is produced by a non-discriminating synthetic design.

This paper presents the RELATE research sequence as a case study in evidence-first experimental governance. The sequence includes: synthetic harness and boundary testing in E00; a reproducible weighted-product-space result in E01 whose broader composition interpretation failed under independent audit; closure of the original composition claim without altering the frozen evidence; and Option B, a preregistered real-code kill test using frozen CodeBERT representations and objective AST-derived relations. Option B independently reproduced a `0.199537109375` hard-negative accuracy gap over the strongest raw geometry, supporting a narrow real-domain premise while leaving general composition, support propagation and calibrated refusal unresolved.

The methodological contribution is a process for preventing successful experiments from silently becoming claims broader than their evidence. The process combines a claim ledger, frozen contracts, prospective decision rules, canonical artifact identities, exhaustive control review, explicit verification classes, independent recomputation, immutable historical records and architecture that separates execution, authorization, publication and retrospective closure. The central lesson is that reproducibility is necessary but not sufficient: an experiment may reproduce exactly while its scientific interpretation still requires rejection or revision.

## 1. Introduction

A common representation-research pattern is straightforward:

1. select an embedding;
2. define a target relation;
3. train an operator or probe;
4. show improvement over cosine similarity;
5. interpret the improvement as evidence that the embedding contains a useful latent geometry.

Every step can be technically correct while the final interpretation remains too broad.

The target may be embedded directly in a synthetic generator. The learned method may be equivalent to a standard predictor. The evaluation regime may be saturated. A control may test weight separation rather than semantic identity. A high global ranking score may coexist with weak nearest-neighbour retrieval. A deterministic replay may reproduce the implementation without independently validating the substantive mathematics. A successful score may show that an executor can always return a ranking, not that the requested relation is evidentially supported.

RELATE began from the hypothesis that frozen representations may contain useful relational signals that their default similarity geometry underexposes. The intended programme was broader than replacing cosine with another fixed metric. It aimed to recover relation-specific evidence, execute declared queries over that evidence and eventually refuse queries whose required relations were weak, absent or shifted.

The early experiments did not advance cleanly toward that full thesis. Instead, they produced a sequence of increasingly informative corrections:

- E00 validated several parts of the experimental harness while failing its complete scientific gate.
- E01 produced strong and reproducible weighted-product-space results, but independent recomputation showed that the generator was saturated, most original margins failed exhaustive controls and the permutation diagnostic did not establish semantic identity.
- The original E01 composition claim was closed while its numerical evidence was preserved.
- Option B moved to a real frozen representation and asked one narrow kill-test question.
- Option B passed that bounded test and was independently recomputed, but it did not inherit or restore the broader E01 claim.

This paper asks:

> How can evidence-first experimental governance prevent synthetic representation research from producing claims broader than its experiments support?

The answer developed here is not that governance guarantees scientific truth. It does not. Rather, governance makes the chain from question to evidence to interpretation inspectable, creates explicit places where a claim can fail, and permits later evidence to narrow or close an interpretation without rewriting the original record.

## 2. Research setting

### 2.1 The motivating representation question

For an artifact `x`, let a frozen encoder produce a representation `z(x)`. Raw cosine similarity supplies one global ordering over pairs of representations. RELATE investigates whether other externally defined relations can be recovered from the same frozen representation and queried more effectively than through that default geometry.

The broad operational model is:

```text
artifact
  -> frozen representation
  -> independently testable primitive relations
  -> declared query-specific executor
  -> support and uncertainty checks
  -> ranking, qualification or refusal
```

This model contains several distinct scientific claims that must not be conflated:

1. **Recoverability:** a primitive property or relation can be predicted from the frozen representation.
2. **Execution:** predicted primitive outputs can be used to answer a declared compound query.
3. **Composition:** reusable primitive relations support more than one query without retraining a new compound model each time.
4. **Semantic binding:** the executor uses the requested relation identities rather than interchangeable or accidentally aligned coordinates.
5. **Support:** the required primitive evidence is strong enough for the query.
6. **Refusal:** unsupported queries are rejected or qualified rather than assigned an unearned confident ranking.
7. **Application utility:** the resulting retrieval or decision improves a real task against strong alternatives.

A result at one level does not automatically establish the next.

### 2.2 Why synthetic success is dangerous

Synthetic experiments are essential because they permit exact control over signal presence, noise, transformations and oracle structure. They are also unusually easy to overinterpret.

When the generator writes target variables directly into a representation before an orthogonal rotation, a linear probe may recover those variables with high accuracy. Combining the predicted values with a hand-specified weighted distance may then reproduce the oracle ranking. Such a result can be a useful positive control. It does not by itself establish a novel relational operator, meaningful semantic composition or support-aware query execution.

The methodological danger appears when an implementation-level success is described using the language of the intended long-term thesis.

## 3. Evidence-first experimental governance

RELATE evolved a set of mechanisms intended to constrain that drift.

### 3.1 Claim ledger

Every scientific statement is assigned a claim identifier and a status such as:

- proposed;
- implemented;
- replay-verified point estimate;
- replicated synthetic;
- independently verified real-domain;
- independently audited;
- refined;
- unsupported at threshold;
- insufficient evidence;
- unstable under shift;
- blocked;
- closed.

The claim ledger separates a numerical result from the interpretation permitted by that result. A result can remain reproducible while its claim status is narrowed or closed.

### 3.2 Frozen contracts

Before confirmatory execution, a contract fixes the substantive question, representation, data identities, model family, baselines, metrics, thresholds, decision rule and permitted outcomes.

The contract prevents the experiment from changing its definition after observing the result. It does not make a weak design strong. Later audit may still show that a frozen control was insufficient or that a generator was non-discriminating. The contract preserves what was actually tested so that later interpretation can be revised honestly.

### 3.3 Prospective kill tests

A kill test is designed to terminate or narrow a research line rather than merely produce another positive score.

The decision rule is fixed before execution. Secondary metrics cannot rescue a failed primary rule. A failed result closes the exact scoped claim unless a new experiment identifier, fresh contract and explicit non-inheritance decision are created.

### 3.4 Artifact and identity commitments

Evidence-bearing inputs and outputs are committed through stable identities and SHA-256 hashes. These may include:

- source manifests;
- selected-row manifests;
- frozen embeddings;
- primitive tables;
- predictions;
- hard-negative streams;
- query-score arrays;
- compact result records;
- decision trees;
- independent verification records;
- source-code identities.

This permits later work to distinguish a reinterpretation of existing evidence from regeneration or silent replacement of that evidence.

### 3.5 Verification classes

RELATE distinguishes several verification strengths.

**Deterministic replay** reruns the registered implementation and reproduces its outputs. It is valuable for detecting nondeterminism, missing dependencies and artifact drift, but it may reproduce the same conceptual or mathematical error.

**Independent recomputation** uses a separate substantive implementation that does not import the decisive evaluator. It recomputes the primary quantities and final decision from committed inputs.

**Independent audit** may ask an interpretation-changing question that the original frozen experiment did not ask, such as evaluating all non-identity permutations or measuring the attainable oracle ceiling.

A replayed success is not labelled as independent recomputation.

### 3.6 Immutable evidence and revisable interpretation

Frozen artifacts are not rewritten when later evidence changes their meaning.

Instead, the repository adds:

- an audit record;
- a refined or closed claim status;
- a human-readable checkpoint;
- an explicit statement of what remains numerically valid;
- a statement of what can no longer be claimed.

This avoids two common failures: erasing inconvenient positive results, and continuing to cite them using an interpretation that later evidence has invalidated.

### 3.7 Execution and publication architecture

The repository eventually separated:

- workflow execution;
- human authorization;
- noncanonical staging;
- evidence review;
- canonical publication;
- retrospective terminal-state review;
- closure disposition.

Exact-byte publication and immutable destination rules prevent a reviewed candidate from being replaced during publication. Read-only closure verifies the historical authorization chain, claim, trace, receipt or failure records, and canonical destination bytes. The architecture does not decide whether a scientific claim is true; it preserves the identity and reviewability of the evidence on which that decision rests.

## 4. Case study I: E00 as harness and boundary testing

E00 tested whether simple supervised directions could expose registered synthetic relations under several controlled regimes.

The multi-seed confirmation attempt was deterministically replayed across five fresh seeds. Six of seven required decisions matched, but the complete scientific gate failed.

### 4.1 Supported bounded results

The learned rank-one direction recovered the registered linear relation in both axis-aligned and commonly rotated representations:

| Measurement | Result |
|---|---:|
| Axis-aligned mean triplet accuracy | `0.9385` |
| Rotated mean triplet accuracy | `0.9390` |
| Mean rank-one rotation retention | `1.0005` |
| Mean diagonal rotation retention | `0.5968` |

The experiment also produced appropriate boundary behaviour:

| Control | Result |
|---|---:|
| Absent relation mean triplet accuracy | `0.5008` |
| Linear XOR mean triplet accuracy | `0.4999` |
| Correlated-nuisance validation-to-test gap | `0.3525` |

These results supported bounded conclusions about linear recoverability, rotation retention, raw-coordinate diagonal basis dependence, absent-signal rejection and shortcut instability.

### 4.2 Failed complete gate

The preregistered nonlinear XOR family did not recover the relation consistently across seeds. Nonlinear average precision ranged from approximately `0.5011` to `0.9195`, and the frozen multi-seed conditions failed. The correct decision was `INSUFFICIENT_EVIDENCE`.

A later audit also identified an invalid secondary diagnostic that mixed nonlinear average precision with linear triplet accuracy. The diagnostic was withdrawn without modifying the frozen artifact or changing the already-failed scientific gate.

### 4.3 Methodological interpretation

E00 demonstrates why a scientific gate must be separable from its successful subresults. The experiment produced several real positive findings, yet the complete composite claim remained blocked because one required boundary failed.

The lesson was not that E00 had no value. It was that successful components could not be aggregated rhetorically into a complete capability the gate had not certified.

## 5. Case study II: E01 passes numerically but fails interpretively

E01 asked whether independently predicted primitive coordinates could support several weighted product-space queries more effectively than scalar collapses and included alignment controls.

The registered results were strong and reproducible. Triplet accuracies were approximately `0.92–0.93`, and multi-seed execution retained positive margins over the included controls.

At first glance, this appeared to support relational composition.

Independent recomputation changed that interpretation.

### 5.1 Exhaustive controls changed the original decision

E01.1 required the composed method to exceed every included control by at least `0.10`. The frozen experiment included one cyclic wrong alignment. Independent recomputation evaluated all five non-identity permutations.

| Compound | Margin over strongest permutation | Original `0.10` rule |
|---|---:|---|
| `a2_b` | `0.0853` | fail |
| `a3_c` | `0.1464` | pass |
| `b2_c` | `0.0788` | fail |
| `a_b2_c3` | `0.0374` | fail |

Only one of four compounds retained the original threshold under the exhaustive control set.

The frozen E01.1 artifact was not modified. The later audit established that its original four-of-four success depended on a weaker control set.

### 5.2 The generator was saturated

The predicted-primitive executor was effectively indistinguishable from applying the same query to the true noiseless latent primitives. Median ceiling fractions across the registered compounds were approximately `1.00005–1.00037`.

This meant the generator provided almost no attainable headroom. Narrow variation across seeds reflected repeated draws from an easy, saturated generator rather than a difficult mechanism surviving substantially different conditions.

### 5.3 The semantic control tested weight separation

The registered primitives were exchangeable independent Gaussian variables with similar recoverability. Permuting their identities primarily reassigned unequal query weights.

The margin over the strongest permutation changed predictably with weight separation:

| Weights | Margin |
|---|---:|
| `(1,1,1)` | `0.00000` |
| `(1,1.1,1.2)` | `0.00183` |
| `(1,1.5,2)` | `0.02091` |
| `(1,2,3)` | `0.03737` |
| `(1,4,16)` | `0.06739` |

The permutation result was therefore a weight-separation diagnostic, not evidence that semantic primitive identities had been learned or preserved.

### 5.4 High ranking accuracy did not equal solved retrieval

Headline triplet accuracy remained around `0.92–0.93`, but mean recall@10 ranged from approximately `0.1614` to `0.3542`, depending on the query. The latent oracle produced essentially the same retrieval profile.

This showed that the gap was partly a property of the ranking target and evaluation geometry. It also reinforced the need to preserve metric continuity: publication language about retrieval must include local retrieval metrics, not only global pairwise ordering.

### 5.5 Closing the claim without deleting the result

The E01 records remain:

- numerically reproducible;
- useful positive controls;
- evidence that preserving predicted coordinates avoids the registered scalar collapses.

They do not establish:

- general relational composition;
- semantic relation-name identity;
- a novel RELATE algorithm;
- support propagation;
- calibrated refusal;
- transfer to real frozen representations.

The weighted-product-space composition line was therefore closed.

This is the central example behind the paper title. The experiment passed important implementation and positive-control checks. The broader claim failed because later evidence showed that the experiment did not discriminate the intended scientific thesis from simpler explanations.

## 6. Case study III: Option B as a real-domain kill test

After closing E01, RELATE did not automatically construct a larger synthetic rescue programme. It moved to one bounded real-representation premise test.

### 6.1 Registered question

Option B asked:

> Does a frozen code representation that we did not train materially underexpose an objectively measurable compound structural relation under its default geometry?

The experiment used:

- the Python partition of CodeSearchNet;
- repository-separated splits;
- frozen `microsoft/codebert-base` embeddings;
- `20,000` training functions;
- `4,000` validation functions;
- `4,000` test queries;
- cyclomatic complexity;
- maximum control nesting depth;
- distinct call-site count;
- one Chebyshev-style joint structural relation;
- `512,000` preregistered hard-negative pairs.

The predicted executor had no compound supervision. It used independently predicted primitive vectors on both query and candidate sides, with out-of-fold predictions for training candidates.

### 6.2 Frozen decision rule

The primary rule was:

```text
raw_best = max(raw_cosine_hard_triplet_accuracy,
               raw_euclidean_hard_triplet_accuracy)

gap = predicted_executor_hard_triplet_accuracy - raw_best

gap >= 0.10 -> REAL_PREMISE_SUPPORTED
gap < 0.10  -> REAL_PREMISE_FAILED
```

There was no inconclusive band and no secondary-metric rescue.

### 6.3 Primary result

| Method | Hard-negative triplet accuracy |
|---|---:|
| Raw CodeBERT cosine | `0.532458984375` |
| Raw CodeBERT Euclidean | `0.533314453125` |
| Token-length diagnostic | `0.498683593750` |
| True-primitive oracle | `1.000000000000` |
| Predicted primitive executor | `0.732851562500` |

The strongest raw method was Euclidean distance. The registered gap was:

```text
0.732851562500 - 0.533314453125 = 0.199537109375
```

The result passed the frozen `0.10` continuation threshold.

### 6.4 Retrieval context and bounded interpretation

The predicted executor's Spearman correlation with oracle distance was approximately `0.723079`, compared with approximately `0.111985` for raw cosine and `0.110453` for raw Euclidean.

However, recall@10 improved only from approximately `0.003` to `0.009075`, remaining low in absolute terms. Option B therefore does not support a claim that nearest-neighbour retrieval was solved.

The bounded promoted claim is:

> In repository-separated real Python code, independently predicted AST primitive coordinates exposed a frozen three-way structural relation materially better than raw CodeBERT cosine or Euclidean geometry on the preregistered hard-negative test.

This supports the premise that a real frozen representation can contain useful relational information that its default geometry materially underexposes.

It does not establish general composition, semantic binding, support propagation, calibrated refusal, superiority to a directly trained compound model or production utility.

### 6.5 Independent primary recomputation

The independent verifier did not import the method-evaluation runner. It separately reverified the canonical manifests, primitive tables, embeddings, predicted primitive arrays and hard-negative stream. It recomputed the complete `4,000 × 5` primary query-score matrix and required exact equality.

Every primary query score, aggregate estimate, registered gap and final decision matched.

The independent recomputation is important for two reasons:

1. it provides stronger evidence than replay that the recorded Option B result follows from the committed inputs;
2. it does not broaden the scientific claim beyond the registered question.

Verification strength and claim breadth remain separate dimensions.

## 7. The methodological result

The RELATE sequence supports a general methodological conclusion:

> Scientific governance should be designed not only to reproduce successful experiments, but also to make it possible for later evidence to reject the interpretation of a reproducible success.

Several specific principles follow.

### 7.1 A passing implementation is not a passing thesis

E01 showed that code correctness, deterministic replay, high accuracy and positive registered margins can coexist with a failed broader interpretation. The decisive questions were whether the controls represented the intended alternatives, whether the generator had headroom and whether the method did more than standard property prediction followed by score fusion.

### 7.2 Controls must test the claim's semantics

A control that appears to test semantic alignment may instead measure a simpler quantity such as weight separation. Controls require their own validity argument. Their labels are not sufficient.

### 7.3 Ceiling measurement should precede celebration

When a learned executor reaches the latent oracle, additional seed replication may mostly measure generator stability. Attainable-headroom analysis distinguishes a robust difficult result from repeated saturation.

### 7.4 Metrics must match publication language

Pairwise ranking accuracy cannot, by itself, justify broad claims about nearest-neighbour retrieval. Retrieval claims require local retrieval metrics, and selective claims require risk-coverage metrics.

### 7.5 Negative and narrowed results are cumulative evidence

Closing E01 did not erase E00 or E01. It clarified what each experiment established and redirected the programme toward a real-domain premise test. Option B then succeeded without inheriting the unsupported composition claim.

### 7.6 Independent recomputation validates evidence, not rhetoric

Exact recomputation can strongly validate a numerical result. It cannot make an overbroad interpretation correct. Verification must be paired with claim-scoped decision rules.

### 7.7 Architecture can preserve epistemic boundaries

Separating execution, authorization, publication, evidence review and closure reduces the risk that later code silently regenerates, replaces or reclassifies canonical evidence. Architecture is not a substitute for experimental design, but it can enforce the identity and immutability conditions on which trustworthy reinterpretation depends.

## 8. Governance pattern

The resulting evidence-first pattern can be summarized as follows.

### Before execution

1. Record a proposed claim and its falsification or revision condition.
2. Define the external target independently of the representation.
3. Freeze the representation, data roles, baselines, metrics and decision rule.
4. Measure attainable ceiling and ensure the regime can discriminate the thesis.
5. State the exact publication language permitted by each outcome.

### During execution

1. Preserve source, configuration and environment identities.
2. Write append-only traces and immutable evidence records.
3. Retain failed and superseded candidates.
4. Prevent access to protected confirmation evidence.
5. Keep secondary analyses from changing the primary decision.

### After execution

1. Publish a compact result and human-readable checkpoint.
2. Recompute the primary result independently when the claim warrants it.
3. Audit control validity, ceiling saturation and metric continuity.
4. Update the claim ledger without rewriting frozen evidence.
5. Close, refine or promote only the exact scoped claim.

## 9. Limitations

This paper is a case study from one research repository, not evidence that the RELATE governance process is optimal or universally applicable.

Several limitations remain.

### 9.1 No controlled comparison of governance systems

The work does not compare teams using different experimental-governance methods. It therefore cannot quantify how much the process reduces false claims across research groups.

### 9.2 Researcher and auditor are not institutionally independent

Independent recomputation refers to substantive implementation independence within the project. It is not equivalent to replication by an external laboratory with independent incentives and infrastructure.

### 9.3 Literature review is incomplete

This draft is not yet situated comprehensively within preregistration, reproducible research, selective prediction, concept bottlenecks, metric learning, model auditing or machine-learning artifact-evaluation literature.

### 9.4 The real-domain result is narrow

Option B covers one programming language, one frozen encoder, three AST-derived primitives and one compound relation. It does not establish transfer to other models, relations, languages or domains.

### 9.5 The intended support-aware contribution remains unconfirmed

RELATE has not yet shown that primitive support can be propagated through a compound query more effectively than independent conformal abstention or a directly trained compound model with its own conformal wrapper.

## 10. Future work

The immediate scientific route is the bounded Option C0/C1 support-and-refusal programme.

C0 may explore support representations and propagation candidates using development-only roles. It must compare against independent primitive conformal abstention, a directly trained compound model, confidence diagnostics and oracle headroom. It must distinguish supported, weak, absent, out-of-family and shifted relations.

C0 can only justify a later contract; it cannot promote the refusal claim.

If and only if C0 produces `C1_CONTRACT_JUSTIFIED`, C1 will freeze one mechanism and test selective risk at matched coverage in a one-shot confirmation. A failure will close the current propagated-refusal route while preserving Option B. A pass will permit one bounded real-domain refusal pilot.

Separate future application studies may test conceptual duplicate retrieval in code and author-grounded conceptual retrieval in writing. Those studies require new claim identifiers, external labels, strong direct baselines and independent evaluation. They do not inherit success from Option B beyond its exact structural premise.

## 11. Conclusion

RELATE's most defensible methodological result did not emerge from an uninterrupted sequence of successful experiments. It emerged from preserving the distinction between a successful calculation and a justified scientific claim.

E00 produced valuable bounded evidence while failing its complete gate. E01 reproduced strongly while independent audit invalidated its general composition interpretation. The project closed that claim without erasing the result. Option B then tested a narrower premise in real frozen code representations and passed with exact independent recomputation.

The sequence demonstrates why reproducibility must be coupled to discriminating experimental design, valid controls, ceiling analysis, metric continuity, immutable evidence and explicit claim governance.

An experiment can pass while its claim fails. A research process becomes stronger—not weaker—when it is designed to record that outcome precisely.

## Evidence map

### Governing claim and decision records

- [`CLAIMS.md`](../../CLAIMS.md)
- [`docs/research/post-e01-publication-and-kill-test-decision-2026-08-01.md`](../research/post-e01-publication-and-kill-test-decision-2026-08-01.md)
- [`docs/research/relate-research-program.md`](../research/relate-research-program.md)
- [`docs/research/next-scientific-program.md`](../research/next-scientific-program.md)

### E00

- [`docs/results/e00-multiseed-confirmation-attempt-v1.md`](../results/e00-multiseed-confirmation-attempt-v1.md)
- [`docs/audits/e00-evidence-audit-2026-08-01.md`](../audits/e00-evidence-audit-2026-08-01.md)

### E01

- [`docs/results/e01-independent-recomputation-checkpoint-v1.md`](../results/e01-independent-recomputation-checkpoint-v1.md)
- [`docs/blog/closing-the-e01-composition-line.md`](../blog/closing-the-e01-composition-line.md)
- [`docs/audits/e01-external-review-audit-2026-08-01.md`](../audits/e01-external-review-audit-2026-08-01.md)

### Option B

- [`docs/experiments/08-option-b-real-code-premise-test.md`](../experiments/08-option-b-real-code-premise-test.md)
- [`docs/results/option-b-real-code-premise-checkpoint-v1.md`](../results/option-b-real-code-premise-checkpoint-v1.md)
- [`docs/blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md`](../blog/option-b-the-embedding-knew-more-than-its-geometry-showed.md)
- [`artifacts/canonical/option-b/method-evaluation-v1/`](../../artifacts/canonical/option-b/method-evaluation-v1/)

### Architecture and evidence preservation

- [`docs/architecture/current-system-map.md`](../architecture/current-system-map.md)
- [`docs/architecture/migration-status.md`](../architecture/migration-status.md)
- [`docs/architecture/capability-continuity.md`](../architecture/capability-continuity.md)
- [`docs/architecture/decisions/007-publication-closure-is-read-only-and-nonscientific.md`](../architecture/decisions/007-publication-closure-is-read-only-and-nonscientific.md)

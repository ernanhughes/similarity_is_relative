# Option C0 Found a Selective Signal—Not Yet a Distinctive Mechanism

Option B gave RELATE a reason to continue.

On repository-separated Python code, a frozen CodeBERT representation contained enough recoverable information to predict three objective AST properties. When those predictions were used as coordinates for a frozen structural query, they exposed that relation far better than raw cosine or Euclidean distance.

That result answered one question:

> Is there useful relational structure inside a real frozen representation that its default geometry underexposes?

For the registered Option B setting, yes.

Option C asks the harder question:

> Can the system tell when its predicted relational coordinates are supported strongly enough to answer a compound query—and refuse when they are not?

The first bounded mechanism-discovery iteration, C0, has now completed. The answer is more interesting than either a clean success or a clean failure.

There is a real selective signal. It is strongest for a conjunction. But the mechanisms we registered have not yet shown that they are more useful than simpler ways of ranking confidence or directly predicting the compound label.

That distinction is the result.

## What C0 was allowed to do

C0 was not a confirmation experiment. It was a firewalled development stage.

The eligible Python repositories were assigned by whole repository to four roles:

| Role | Repositories | Rows |
|---|---:|---:|
| C0 fit | 2,117 | 8,007 |
| C0 iteration | 1,058 | 4,110 |
| C0 selection | 545 | 2,070 |
| C1 reserve | 1,604 | 6,357 |

C0 fit could train and calibrate the registered mechanisms. C0 iteration could expose their exploratory behaviour. C0 selection remained inaccessible. C1 remained inaccessible, and its final rows were not even selected.

This matters because mechanism discovery is adaptive. We wanted enough freedom to discover how support behaves without turning the final reserve into a debugging surface.

## What was predicted

The frozen representation was still `microsoft/codebert-base`.

The three predicted AST-derived primitives were:

- cyclomatic complexity;
- maximum control nesting depth;
- distinct call-site count.

C0 converted each primitive to a signed margin around a median fitted only on the C0-fit data. It then asked three Boolean questions:

1. Are **all three** primitives above their thresholds?
2. Is **any one** primitive above its threshold?
3. Are **two of the three** primitives above their thresholds?

The point was not that these are the ultimate code queries. They create three different compound decision boundaries over the same predicted primitives.

## The two candidate mechanisms

The first candidate family built a calibrated joint box around the predicted primitive margins. It answered only when the entire box implied the same Boolean result.

The second kept complete joint calibration residuals. It perturbed each predicted primitive vector by those observed residual vectors, counted how often the compound query evaluated true or false, and answered only when one side had sufficiently high empirical mass.

Both families were registered across five strictness levels.

We also required four kinds of comparison:

- independent conformal intervals for each primitive;
- a directly trained compound classifier with conformal abstention;
- ordinary uncalibrated confidence ranking;
- an oracle-support diagnostic.

That last set of comparisons prevents a common experimental mistake: discovering that abstention helps, then attributing the entire benefit to a complicated mechanism without checking whether confidence alone selects the same easy cases.

## The conjunction result was striking

For the query requiring all three primitives to be above threshold, the empirical residual mechanism produced:

```text
beta 0.01:
coverage 42.73%
accepted rows 1,756
errors 0

beta 0.025:
coverage 51.22%
accepted rows 2,105
errors 2
selective risk 0.095%
```

The joint-box mechanism also found zero-error subsets, although at lower coverage. At alpha 0.05 it accepted roughly 21.8% of the iteration rows with no observed errors.

That is not noise in the casual sense. The frozen representation, primitive readouts and support calculations together can isolate a substantial subset on which the conjunction answer is extremely reliable.

But that is only half of the interpretation.

At roughly 50% coverage, ordinary confidence ranking also made two errors, for a selective risk of about 0.097%. The independent primitive baseline was similarly competitive.

So the conjunction result demonstrates a selective structure. It does not yet demonstrate that the registered joint-support mechanisms own that structure.

## The other queries resisted the broad story

For the `any` query, the best selected candidate operating points had noticeably higher selective risk:

```text
empirical residual mass, beta 0.01:
coverage approximately 28.3%
risk approximately 1.89%

joint box, alpha 0.05:
coverage approximately 21.0%
risk approximately 1.39%

 direct compound conformal, alpha 0.01:
coverage approximately 38.3%
risk approximately 1.14%
```

For `two-of-three`, the direct and confidence baselines were stronger at the selected points:

```text
empirical residual mass, beta 0.01:
coverage approximately 22.9%
risk approximately 1.06%

joint box, alpha 0.10:
coverage approximately 24.1%
risk approximately 1.31%

direct compound conformal, alpha 0.01:
coverage approximately 60.3%
risk approximately 0.807%

uncalibrated confidence near 50% coverage:
risk approximately 0.195%
```

That pattern is important. A general support-composition mechanism should not be declared from one attractive conjunction cell while the disjunction and thresholded-majority results tell a less favourable story.

## The uncertainty intervals themselves were not obviously broken

The joint primitive intervals tracked nominal aggregate coverage closely:

| Nominal | Observed |
|---:|---:|
| 99.0% | 98.91% |
| 97.5% | 97.40% |
| 95.0% | 94.72% |
| 90.0% | 89.76% |
| 80.0% | 80.73% |

That rules out one easy explanation: the candidate did not fail simply because the primitive intervals were grossly miscalibrated in aggregate.

The harder issue is the translation from primitive uncertainty to useful compound decisions. A well-calibrated primitive box can still be conservative, poorly matched to a query boundary, or less informative than a direct confidence score.

## Why `all`, `any` and `two-of-three` may differ

We do not yet have a confirmed explanation.

Several hypotheses are plausible:

- The conjunction's positive class is rare, and many negative examples may sit far from at least one boundary.
- A disjunction can change truth when any one uncertain primitive crosses its boundary, creating more ways for support to become ambiguous.
- Two-of-three has multiple interacting boundary faces and may reward a direct compound model.
- Primitive prediction errors may be correlated in ways that help one Boolean operator and hurt another.
- Confidence ranking may simply identify the same far-from-boundary cases without needing explicit residual propagation.

These are discovery hypotheses. C0 was designed to reveal such questions, not to confirm their answers.

## One more warning from model fitting

All three primitive Ridge models chose alpha 100, the largest value in the registered grid.

That may mean heavy regularisation is genuinely appropriate. It may also mean the optimum lies beyond the grid. Because the result was observed after the plan froze, extending the grid now would create a new hypothesis and require a new experimental cycle. It cannot silently modify this checkpoint.

## What C0 has and has not given us

C0 has given us good news about the existence of selective signal:

- predicted primitives are usable;
- aggregate primitive intervals are coherent;
- some compound queries admit sizeable low-error accepted subsets;
- the behaviour is structured rather than uniform.

It has given us adverse evidence about the broad mechanism claim:

- the result is strongly query-dependent;
- confidence ranking is difficult to beat;
- direct compound prediction can be stronger;
- no registered candidate is yet clearly distinctive.

The cleanest current summary is:

> Predicted primitive support can isolate useful low-risk subsets for some compound structural queries, especially the conjunction, but the registered candidate mechanisms have not yet shown an advantage over the strongest simpler baselines.

That is an exploratory summary, not a promoted scientific finding.

## C1 has not spoken

C1 has not been selected, inspected or run.

Nothing in this result is a C1 result. The C1 reserve remains sealed.

The next decision is whether C0 justifies a separately frozen C1 contract. A broad C1 claiming general superiority across Boolean queries would be difficult to defend from this evidence. A narrower conjunction-focused replication might be meaningful—but only if it is not merely a post-hoc rescue and only if its relationship to the confidence baseline is made explicit.

Possible review outcomes remain:

```text
C1_CONTRACT_JUSTIFIED
C1_NOT_JUSTIFIED
C0_DATA_FIREWALL_FAILED
C0_BUDGET_EXHAUSTED
```

No outcome has been chosen.

## Why the discovery ledger is still empty

The result was packaged with six registered candidates and six evaluated events, but zero discovery-ledger entries.

That is intentional.

The project has committed the numbers before committing an interpretation. Independent reviewers can now challenge the apparent conjunction signal, the baseline comparison, the query asymmetry and the proposed next step before any narrative becomes part of the canonical discovery record.

## Where to inspect the evidence

Start with:

- [Option C0 result checkpoint](../results/option-c0-discovery-iteration-checkpoint-v1.md)
- [Independent review guide](../reviews/option-c0-iteration-independent-review-guide.md)
- [Canonical full result](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json)
- [Candidate registry](../../artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl)
- [Publication checkpoint](../../artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json)
- [Claim ledger](../../CLAIMS.md)

The evidence branch is `agent/option-c0-iteration-results-v1`, at commit `07cf6fc`.

## The decision in front of us

The question is no longer whether anything happened. Something did.

The question is whether that something is:

1. a distinctive support-composition mechanism worthy of confirmation;
2. a useful but ordinary selective-prediction effect;
3. a conjunction-specific phenomenon;
4. or exploratory evidence insufficient to spend the C1 reserve.

C0 was built to let us ask that question honestly. The next stage is review, not momentum.

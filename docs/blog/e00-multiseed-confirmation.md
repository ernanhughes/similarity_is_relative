# Six Results Replicated. One Did Not.

The next stage moved beyond the original seed-17 experiment and generated five fresh synthetic datasets using seeds `23`, `41`, `59`, `83` and `101`.

Seed 17 was excluded from model selection, aggregation and certification. Each fresh seed received its own rotation, train-validation-test split, generated arrays, permutation nulls, bootstrap intervals and validation-only nonlinear model selection.

The independent verifier then regenerated the complete five-seed experiment and reproduced all five model selections, all seven decisions and the entire aggregate result tree without error.

The verification status was:

```text
Verification: PASS
Verified seeds: 5
Verified model selections: 5
Verified decisions: 7
```

The scientific gate still failed.

This time, however, six of the seven required decisions passed.

## The linear relation replicated across every seed

The learned rank-one direction remained strong in both the axis-aligned and rotated representations.

Across the five fresh seeds, axis-aligned triplet accuracy had a mean of approximately `0.9385`, with a seed-level 95% confidence interval from `0.9350` to `0.9420`.

After an information-preserving orthogonal rotation, mean triplet accuracy was approximately `0.9390`, with an interval from `0.9351` to `0.9425`.

The two results were almost indistinguishable.

Mean rank-one rotation retention was `1.0005`, with a seed-level interval from `0.9931` to `1.0089`.

In this registered synthetic setting, the recoverable relation therefore behaved like a direction that survived a change of basis rather than a property tied to one coordinate system.

## Diagonal weighting did not survive the same rotation

The diagonal operator behaved differently.

Its mean rotated-to-axis performance retention was approximately `0.5968`, with a seed-level interval from `0.5879` to `0.6057`.

The rank-one operator retained essentially all of its performance. The diagonal operator retained only about sixty per cent.

This multi-seed result crossed the newly preregistered basis-retention gate.

The result does not prove that diagonal metrics are generally useless. It shows something narrower and more important:

> A coordinate-weighted metric can appear highly effective when the relation happens to align with the native basis, yet lose much of that performance after an information-preserving rotation.

The relation was not the coordinate.

## The controls replicated too

The absent relation remained at chance across all five seeds.

Its mean rank-one triplet accuracy was approximately `0.5008`.

The linear operator also remained at chance on XOR, with a mean triplet accuracy of approximately `0.4999`.

The correlated-nuisance regime again exposed shortcut dependence. Its mean validation-to-test triplet-accuracy drop was approximately `0.3525`, with a seed-level interval from `0.3455` to `0.3594`.

These are not secondary details. They show that the machinery did not simply label every learned operator as supported. It rejected an absent relation, respected the boundary of the linear family and detected instability when a development-time shortcut broke at test time.

## The nonlinear control did not replicate

The only failed decision was the nonlinear XOR confirmation.

The preregistered process evaluated a fixed grid of polynomial-logistic and multilayer-perceptron models using training data for fitting and validation data for selection. The selected model was then refitted on train plus validation and evaluated once on test.

The five test average-precision results were approximately:

```text
0.5011
0.7788
0.7928
0.9195
0.7806
```

One seed collapsed almost completely to chance. The others ranged from moderate to strong recovery.

The aggregate mean was approximately `0.7546`, but the seed-level 95% confidence interval ran from `0.6154` to `0.8640`. The minimum seed result was `0.5011`.

The nonlinear-minus-linear advantage was positive on average, but its lower seed-level confidence bound was approximately `0.1169`, below the preregistered requirement of `0.15`.

The correct decision was therefore:

> `INSUFFICIENT_EVIDENCE`

This failure is more informative than a single successful XOR demonstration would have been.

A nonlinear model could recover the relation on some seeds, sometimes very strongly, but the registered family and selection procedure did not produce reliable out-of-seed recovery.

That means the next question is not simply whether nonlinear structure exists. We generated the XOR relation, so we know that it does.

The question is why the selected nonlinear operator is unstable across equivalent synthetic draws.

## The all-or-nothing gate did its job

The complete decision record was:

| Decision | Outcome |
|---|---|
| Axis-aligned rank-one recovery | `SUPPORTED` |
| Rotated rank-one recovery | `SUPPORTED` |
| Absent relation | `UNSUPPORTED_AT_THRESHOLD` |
| Linear XOR | `UNSUPPORTED_AT_THRESHOLD` |
| Nonlinear XOR | `INSUFFICIENT_EVIDENCE` |
| Diagonal basis dependence | `SUPPORTED` |
| Correlated-nuisance shift | `UNSTABLE_UNDER_SHIFT` |

Six of seven decisions matched the preregistered gate.

The gate nevertheless remained false:

```text
Verification: PASS
Scientific gate: FAIL
Required decisions matched: 6 of 7
Claim promotion: blocked
```

We did not lower the nonlinear threshold, remove the failed seed, average only the successful runs or replace the selected model after seeing test performance.

The experiment was designed so that one failed required control blocks the full claim.

That is exactly what happened.

## What we can now say

The full E00 claim remains unpromoted, but the multi-seed experiment supports several bounded statements within the registered synthetic setting.

Across five independently generated representations, a supervised rank-one direction consistently recovered a known linear relation in both the original and rotated bases.

Diagonal coordinate weighting did not retain comparable performance after rotation.

The absent relation and linear XOR control remained at chance.

The shortcut-dependent relation was consistently identified as unstable under distribution shift.

What did not replicate was reliable nonlinear XOR recovery under the preregistered model family and validation-selection protocol.

The evidence identities for this frozen attempt are:

```text
Aggregate result:
8dd526eaa45a28f56c99cb1045138685b89982109dbf61fb9788a6a65937e86d

Decision tree:
25b52842a4d5fbfefa1145c8f406328dc70744659852b7aa0535cf06788f4c90
```

The result is therefore not “the hypothesis passed” or “the hypothesis failed.”

It is more precise:

> The linear, rotational, absent-signal and shortcut-instability parts replicated strongly across fresh seeds. The registered nonlinear recovery procedure did not.

That boundary is now the next experiment.

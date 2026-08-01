# Similarity Is Relative

## Testing Whether One Frozen Representation Can Answer Different Questions

Most embedding systems make one relationship look universal.

A model turns an object into a vector. A query becomes another vector. The system compares them—usually with cosine similarity—and returns whichever vectors are closest.

That process is useful because it compresses a difficult question into a fast calculation:

> Which representation points in roughly the same direction?

But it also hides a stronger assumption:

> There is one correct notion of similarity for every question we might ask of this representation.

That assumption is often false.

Two sentences can discuss the same subject while disagreeing. Two protein sequences can share a structural fold while having low sequence identity. Two objects can be close under one relation and far apart under another.

This research asks whether a frozen representation can support more than its default neighbourhood—and whether we can establish that without inventing semantic meaning in arbitrary embedding coordinates.

The executable work lives in the companion repository. Every future sentence beginning with “we found” must map to a committed experiment, a compact result record, an independent verifier and the cryptographic identities of the local evidence.

## We began by trying to make the experiment fail

Before using protein or sentence embeddings, we constructed generated representations in which we know exactly what information exists.

The first experiment contains six regimes:

- an axis-aligned linear signal;
- the same kind of signal after random orthogonal rotation;
- a weak linear signal beneath high-variance nuisance dimensions;
- a nonlinear XOR relation;
- a completely absent relation;
- a shortcut correlated during development and deliberately broken during testing.

These are not intended to resemble biology or language. They establish the boundary of the machinery.

A method that cannot recover a known linear signal is not ready for scientific data. A method that claims to recover an absent signal is worse. A method that succeeds only while a shortcut remains correlated must not be certified as understanding the requested relation.

The experiment uses 4,096 vectors with 64 dimensions, a deterministic seed, frozen 60/20/20 train-validation-test assignments and one hashed orthogonal rotation. The large local arrays are not committed to GitHub. Their identities, configuration, metrics and verification records are.

The initial baseline is intentionally ordinary: train a ridge regressor on the frozen training vectors, predict the target value, and retrieve candidates by absolute distance between predicted values. This is the simplest serious control for any later claim that a learned similarity operator contributes something beyond a linear probe.

## The first local checkpoint

The first complete local run generated all six regimes, stored hashes for every input array, target array, split and rotation, and passed an independent verifier with no errors.

The verifier did not merely check that the files existed. It reloaded the hashed arrays, reconstructed the splits, retrained the ridge model and recomputed the reported metrics.

The baseline behaved in the direction the synthetic contract predicted:

| Regime | Spearman distance correlation | Triplet accuracy | Reading |
|---|---:|---:|---|
| Axis-aligned linear | 0.9766 | 0.9334 | strong linear recoverability |
| Rotated linear | 0.9768 | 0.9387 | rotation preserved a recoverable linear direction |
| Weak linear | 0.7417 | 0.7861 | partial recoverability beneath nuisance variance |
| Nonlinear XOR | 0.0066 | 0.5028 | linear probe at chance |
| Absent relation | 0.0033 | 0.5042 | no fabricated linear signal |
| Correlated nuisance | 0.2944 | 0.6309 | broad ordering partly survived, local retrieval collapsed under shift |

This is not yet a RELATE result. It is a baseline audit.

It establishes that the harness can distinguish a strong linear signal, a weaker one, a nonlinear relation inaccessible to the chosen model family, an absent relation and a shortcut that fails when the distribution changes.

It also exposed a problem in our own evaluation.

## The metrics had to survive the experiment too

Exact top-ten neighbour overlap was much lower than the global ordering metrics even for the strong linear regimes. That is possible when a continuous target contains many nearly tied candidates: a small prediction error can move the exact tenth neighbour far down the identity ranking while still returning candidates with almost the same target value.

We therefore expanded the evaluation beyond exact overlap to include larger retrieval cutoffs, triplet accuracy, true-neighbour rank and graded near-miss measures.

That audit exposed two metrics we should not trust without qualification.

First, dividing retrieved distance by oracle distance becomes meaningless when the oracle distance is zero or extremely small. In the binary XOR regime it produced enormous numerical ratios even though the underlying error was ordinary. We replaced that as the primary comparison with additive neighbour regret and now record the ratio as undefined when its denominator is too small.

Second, scalar NDCG appeared deceptively high for XOR because half of the candidate pool can be tied as equally relevant. We now evaluate binary relations using class precision, class recall and average precision instead of pretending that continuous and binary retrieval share one metric geometry.

The revised contract therefore separates target types:

- continuous relations use rank correlation, exact recall, additive neighbour regret, tolerance coverage and graded ranking;
- binary relations use precision, recall and average precision;
- both retain triplet accuracy and true-neighbour rank as diagnostic measures.

This refinement matters because the repository is not designed to protect the hypothesis from failure. It is designed to make failure legible—including failure in the experiment itself.

## What this checkpoint does and does not establish

The checkpoint supports a narrow statement:

> The deterministic synthetic generator, artifact identities, ridge baseline and independent metric verification ran successfully, and their behaviour matched the known linear, nonlinear, absent-signal and shortcut boundaries of the generated data.

It does not show that:

- diagonal weighting survives rotation;
- low-rank similarity operators add value beyond ridge prediction;
- RELATE can compose independently learned relations;
- the system can yet certify or abstain reliably;
- any result transfers to protein or sentence embeddings.

Those remain registered tests.

## Next

The next stage completes the E00 operator matrix:

1. exact raw cosine and Euclidean retrieval;
2. diagonal Mahalanobis distance;
3. rank-1, rank-4 and rank-16 operators;
4. a nonlinear probe for the XOR boundary;
5. label-permutation and random-operator nulls;
6. paired bootstrap confidence intervals;
7. the first supported, unsupported or insufficient-evidence decision.

Only then can the synthetic experiment promote a scientific claim rather than an implementation checkpoint.

## Publication status

- Research hypothesis: recorded
- Synthetic contract: frozen and refined
- Generator, ridge baseline and independent verifier: locally verified
- Target-specific metric contract: implemented; canonical rerun required
- Complete E00 operator suite: pending
- Claims of RELATE recoverability, composition or abstention: not yet permitted

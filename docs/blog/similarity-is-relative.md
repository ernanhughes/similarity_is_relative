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

This was not yet a RELATE result. It was a baseline audit.

It established that the harness can distinguish a strong linear signal, a weaker one, a nonlinear relation inaccessible to the chosen model family, an absent relation and a shortcut that fails when the distribution changes.

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

## The operator matrix

The next checkpoint stopped asking only whether a ridge probe could predict the hidden scalar. It compared several actual retrieval geometries over the same frozen vectors:

- raw cosine distance;
- raw Euclidean distance;
- ridge predicted-value distance;
- a diagonal ridge-weighted metric;
- a rank-one projection along the learned ridge direction;
- conventional supervised PLS projections at ranks four and sixteen.

The runner did not regenerate the data. It consumed the frozen arrays from the first checkpoint, reconstructed the exact original splits, checked all source hashes and then performed exhaustive retrieval. An independent verifier reran all 40 method/regime combinations and reproduced the complete metric tree.

The verified operator matrix has SHA-256 identity:

`c25202e5842b79073ae27ab2edb5068a12846a57bcaa47cfc8d3be30436ce235`

## A relation can be present without appearing in the default geometry

The clearest contrast appears in the two strong linear regimes.

| Method | Axis-aligned Spearman | Rotated Spearman |
|---|---:|---:|
| Raw cosine | 0.0779 | 0.0813 |
| Raw Euclidean | 0.0944 | 0.1053 |
| Diagonal ridge metric | 0.9766 | 0.1771 |
| Rank-one ridge projection | 0.9766 | 0.9768 |
| PLS rank 4 | 0.4257 | 0.4367 |
| PLS rank 16 | 0.1924 | 0.2075 |

The raw vector geometry barely exposed the relation even though the relation was known to exist.

A supervised rank-one direction recovered it almost perfectly in both bases.

That is the first important provisional conclusion from the programme:

> Information can be strongly recoverable from a frozen representation while remaining largely invisible to its default cosine or Euclidean neighbourhood.

The wording matters. This does not mean that every embedding contains every relation. It means that, in this controlled synthetic case, absence from the default neighbourhood was not evidence of absence from the representation.

## Coordinates were not the relation

The diagonal metric created the more revealing contrast.

It reached a Spearman correlation of `0.9766` when the signal happened to align with a native coordinate. After an orthogonal rotation—one that preserved all information—it fell to `0.1771`.

The rank-one projection remained at `0.9768` after the same rotation.

The point estimates therefore support a second provisional conclusion:

> The useful relation behaved like a direction or subspace, not like a stable semantic coordinate.

This is exactly why assigning human meaning to raw embedding dimensions is dangerous. A coordinate can look decisive in one basis and cease to be decisive after a mathematically equivalent rotation.

A method that treats embedding dimensions as inherently meaningful can succeed for accidental reasons.

## The controls did not light up

The absent relation remained near chance across the complete method set. The largest reported Spearman value was only `0.0081`, and triplet accuracy stayed between approximately `0.5000` and `0.5060`.

The implemented linear methods also remained near chance on XOR. Average precision stayed between approximately `0.5033` and `0.5067`, while triplet accuracy stayed between `0.4999` and `0.5028`.

These controls matter because a method that appears powerful on every regime is not discovering relational structure. It is probably exploiting the evaluation.

At this checkpoint, the machinery distinguishes known linear recoverability from absent and nonlinear boundaries rather than manufacturing universal success.

## More dimensions were not automatically better

The PLS baselines produced another useful warning.

Rank four outperformed rank sixteen on both strong linear regimes. Adding components made the projected Euclidean geometry worse rather than better.

This is not mysterious. A supervised projection can contain directions that help some fitting objective while degrading the distance geometry used for retrieval.

The result cautions against treating operator rank as a simple capacity dial:

> A larger relational space is not necessarily a better relational space.

That observation will matter later when we compare primitive operators and attempt composition. Additional degrees of freedom must earn their place through held-out relational performance, not through model size alone.

## Where this leaves the hypothesis

E00.2 is complete as a verified deterministic point-estimate stage.

It supports the following provisional observations:

1. raw cosine and Euclidean distance can fail to expose a known relation present in a frozen representation;
2. a diagonal metric can succeed because of accidental basis alignment;
3. a learned direction can retain recoverability after an information-preserving rotation;
4. the current linear methods remain near chance on absent and nonlinear controls;
5. increasing low-rank operator dimensionality does not automatically improve relational retrieval.

It still does not permit a formal “we found” claim under the repository’s publication rule.

The current run uses one deterministic seed and point estimates. It has not yet established:

- performance relative to label-permutation and matched random-operator nulls;
- paired bootstrap confidence intervals;
- stability across confirmatory seeds;
- a successful nonlinear control for XOR;
- calibrated supported, unsupported or unstable decisions;
- any transfer beyond synthetic vectors.

## Next: nulls, uncertainty and certification

The next stage is E00.3.

It will ask whether the visible contrasts survive deliberate attempts to explain them away. That means adding permutation nulls, matched random operators, paired bootstrap intervals, confirmatory seeds and a nonlinear XOR diagnostic.

Only after those tests can the project decide whether to promote its first scientific claim:

> A relation can be recoverable from a frozen representation even when default similarity fails to expose it, and the recoverable object is a direction or subspace rather than a semantically stable raw coordinate.

Until then, that sentence remains a candidate conclusion rather than a published finding.

## Publication status

- Research hypothesis: recorded
- Synthetic generator and baseline checkpoint: verified
- Target-specific metric contract: verified
- E00.2 operator matrix: verified across 6 regimes and 40 method sets
- E00.3 nulls, uncertainty and certification: pending
- Promoted claims of RELATE recoverability, composition or abstention: not yet permitted

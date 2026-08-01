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

## The first experiment

Before using protein or sentence embeddings, we begin with generated representations in which we know exactly what information exists.

The synthetic harness includes:

- an axis-aligned linear signal;
- the same signal after random orthogonal rotation;
- a weak signal hidden beneath high-variance nuisance dimensions;
- a nonlinear XOR relation;
- a completely absent relation;
- a nuisance correlated during development and decoupled during testing.

The first question is deliberately modest:

> Can ordinary exact search, a simple probe, a diagonal metric or a low-rank operator recover each relation—and do they fail where mathematics says they should?

No empirical result is claimed yet. The experiment contract is frozen before the complete operator suite is implemented.

## Publication status

- Research hypothesis: recorded
- Synthetic contract: frozen
- Initial generator and ridge baseline: implemented
- Canonical verified result: pending
- Claims of recoverability, composition or abstention: not yet permitted

# Research Decisions

## D-001 — Similarity is relation-dependent

The project tests relation-specific retrieval over frozen representations. It does not assume that one default cosine geometry is scientifically sufficient.

## D-002 — Raw embedding dimensions are not semantic features

Coordinate-level weighting may be tested as a baseline, but raw coordinates and adjacency in a reshaped heatmap must not be assigned inherent semantic meaning.

## D-003 — Exact brute force is the research default

Canonical experiments use exhaustive scoring over the frozen candidate pool. Approximate-nearest-neighbour infrastructure is excluded until scale makes it necessary.

## D-004 — Projected cosine and Mahalanobis distance are distinct

Experiments must name the scoring rule explicitly. The canonical distance metric is

```text
sqrt((q - x)^T M (q - x))
```

with `M = A^T A` for positive-semidefinite low-rank operators.

## D-005 — QM9 is a falsification harness

QM9 will test scalar collapse, rank-one sufficiency, size confounding and basis dependence. It is not currently the headline scientific benchmark.

## D-006 — Protein domains are the proposed scientific benchmark

Protein-domain embeddings provide externally testable but competing relations including sequence, fold, superfamily and function. Success there will not by itself establish transfer to language.

## D-007 — Composition is the primary novelty candidate

Simple weighted score fusion is not treated as novel. The main question is whether primitive operators can serve held-out conjunction, exclusion and multi-objective contexts with bounded regret relative to a directly trained oracle.

## D-008 — Abstention requires evidence

The system may report `supported`, `unsupported_at_threshold`, or `insufficient_evidence`. It must not claim that information is absolutely absent from an embedding.

## D-009 — Visualisation follows verification

A visual demo may display retrieved neighbours, declared bases, operator spectra, confidence and failures. It may not manufacture semantic regions from arbitrary coordinate layout.

## D-010 — Local evidence must remain publicly identifiable

Large local artifacts may remain uncommitted, but their source identities, configuration, hashes, verification status and compact results must be committed before publication claims are promoted.

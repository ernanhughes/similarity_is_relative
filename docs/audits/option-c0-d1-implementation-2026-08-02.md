# Option C0-D1 Implementation

Date: 2026-08-02

Status: implementation prepared for review.

## Purpose

D1 adds a resumable visible-role integrity audit for the published Option C0 v1
artifact. It measures exact source duplicates, exact normalized-AST duplicates,
bounded near-duplicate candidates, repository-family name heuristics, and
execution-source composition manifests.

## Firewall

The implementation reconstructs only `c0_fit` and `c0_iteration` row content via
the existing guarded visible-role path. `c0_selection` and `c1_reserve` row
content remain inaccessible and all result firewall booleans remain false.

Repository-family diagnostics use published allocation repository names only.
Those groups are labelled heuristic candidates, not proof of relatedness.

## SQLite Recovery

The cache lives at `.writer/option-c0/cache/option-c0-d1-integrity-v1.sqlite3`.
It is context-bound and stores only derived visible-row identities and
fingerprints. It validates visible row counts before reuse and resumes completed
near-duplicate scans only when the cached phase metadata matches the active
context parameters.

The context includes the D1 source identity, discovery runner, mechanism
harness, Option B reconstruction helpers, Python version, canonical input
identities, normalization constants, SimHash constants, banding constants, and
all near-duplicate limits.

Visible-row and near-pair phases have ordered SHA-256 commitments. Same-count
row corruption and stale near-pair distances are rejected.

Skipped oversized buckets or truncated candidate-pair output mark the
near-duplicate scan incomplete.

Candidate-pair generation is SQLite-backed and bounded by
`near_max_candidate_pairs`; hitting that bound marks candidate generation and
the near scan incomplete.

Candidate generation now checkpoints each completed bucket and resumes after the
last durable bucket checkpoint. Pair comparison uses keyset pagination with a
bounded batch size and resumes after the last committed candidate key. The
canonical comparison path does not materialize the complete candidate table in
Python memory.

Completed-scan reuse is separate from partial recovery: reusable near-scan
metadata is accepted only after candidate-pair and near-pair commitments are
recomputed and verified.

## Provenance

The runner records Git-object byte hashes for the C0 v1 runtime source
composition at `13466976195abeed56367a449ebd5a6678e3ef7e`, the publication
artifacts at `07cf6fc5ea9c261b10df272215a8afb404612e76`, and the D1 execution
composition at the running `HEAD`. Missing paths are recorded explicitly and
mark the manifest incomplete.

The manifest distinguishes the registered candidate implementation commit, the
published v1 result commit, and the D1 execution commit.

It also compares runtime source files between the runtime source commit and the
publication commit. Byte identity is recorded as provenance only; it does not
make those evidence roles interchangeable.

## Scientific Exclusions

D1 does not modify candidates, primitives, queries, thresholds, alpha or beta
grids. It does not fit models, evaluate mechanisms, access C0 selection rows,
access C1 reserve rows, append scientific interpretations, or decide whether C1
is justified.

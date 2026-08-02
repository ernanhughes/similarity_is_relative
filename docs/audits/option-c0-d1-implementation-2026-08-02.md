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

Skipped oversized buckets or truncated candidate-pair output mark the
near-duplicate scan incomplete.

## Provenance

The runner records Git-object byte hashes for the C0 v1 execution composition at
`07cf6fc5ea9c261b10df272215a8afb404612e76` and for the D1 execution
composition at the running `HEAD`. Missing paths are recorded explicitly and
mark the manifest incomplete.

The manifest distinguishes the registered candidate implementation commit, the
published v1 result commit, and the D1 execution commit.

## Scientific Exclusions

D1 does not modify candidates, primitives, queries, thresholds, alpha or beta
grids. It does not fit models, evaluate mechanisms, access C0 selection rows,
access C1 reserve rows, append scientific interpretations, or decide whether C1
is justified.

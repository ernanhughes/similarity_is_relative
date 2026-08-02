# Option C0 Discovery-Iteration Handoff

## Required starting state

```text
Option B: COMPLETE — REAL_PREMISE_SUPPORTED
C0 protocol: FROZEN
C0 canonical repository allocation: MERGED AND VERIFIED
C0 mechanism harness: MERGED
C0 initial candidate plan: MERGED WITH REGULAR MERGE COMMIT
C0 candidate registrations: 6
C0 iteration result: UNOBSERVED
C0 selection: UNSEEN
C1 reserve: UNDIVIDED
C1 rows: UNSELECTED
```

Read before execution:

1. `docs/experiments/09-option-c0-discovery-and-confirmation-protocol.md`
2. `docs/research/option-c0-initial-candidate-plan-2026-08-02.md`
3. `artifacts/canonical/option-c0/candidate-plan-v1/option-c0-initial-candidate-plan-v1.json`
4. `artifacts/canonical/option-c0/candidate-plan-v1/option-c0-candidate-registry-v1.jsonl`
5. `src/relate/experiments/option_c0_discovery_runner.py`
6. `scripts/run-option-c0-discovery-iteration-v1.ps1`

## Merge requirement

The candidate-plan PR must be merged using a regular merge commit.

Do not squash it. The six registered candidates point to:

```text
d36436209d95eca555215a83856f042d241a90f4
```

The execution script requires that implementation commit to be an ancestor of `main`.

## One-time execution

From a clean checkout after the candidate-plan PR merges:

```powershell
cd C:\Projects\similarity_is_relative

git switch main
git pull --ff-only origin main

powershell -ExecutionPolicy Bypass `
    -File scripts/run-option-c0-discovery-iteration-v1.ps1
```

The script creates:

```text
agent/option-c0-iteration-results-v1
```

and refuses if either the local or remote branch already exists.

## Execution stages

The script will:

1. verify the mechanism-harness and registered implementation ancestry;
2. verify the exact candidate-plan and registry SHA-256 identities;
3. require a clean worktree and unused output directories;
4. install the reviewed package;
5. run Ruff, focused discovery tests, the full suite and whitespace checks;
6. validate all six registration events without loading hidden roles;
7. reconstruct only `c0_fit` and `c0_iteration` rows;
8. embed visible rows using the frozen CodeBERT identity;
9. split `c0_fit` repositories deterministically into model-fit and development-calibration partitions;
10. fit primitive readouts and fair direct-compound baselines;
11. evaluate the two candidate families and four required baselines on `C0_ITERATION`;
12. publish exploratory diagnostics;
13. append one `EVALUATED` event for each registered candidate;
14. leave the discovery ledger empty pending human interpretation;
15. commit and push the result checkpoint to the result branch.

## Expected result state

```text
C0_ITERATION_RESULTS_PUBLISHED_PENDING_REVIEW
scientific_result_observed = false
mechanism_result_observed = true
c0_selection_accessed = false
c1_rows_selected = false
candidate_registrations = 6
candidate_evaluations = 6
discovery_ledger_entries = 0
```

`mechanism_result_observed = true` means exploratory C0 development evidence now exists. It does not create an Option C scientific finding.

## After execution

Do not access `c0_selection` immediately.

First review:

- candidate and baseline risk–coverage curves;
- label prevalence for all three query forms;
- degenerate coverage or empty-error regions;
- direct-compound strength;
- oracle headroom;
- repository dispersion;
- supported, weak, absent and shifted strata;
- failures suggesting implementation or data-integrity problems;
- runtime and memory feasibility.

Then append genuine discovery-ledger observations in a separate review PR. Do not fabricate observations automatically from metric values.

## Candidate revision rule

A candidate may be revised after C0 iteration review, but:

- the evaluated `v1` event remains immutable;
- the revision receives a new version;
- its implementation and specification are committed first;
- a new `REGISTERED` event is appended before evaluation;
- the reason for revision is recorded in the discovery ledger;
- the five-working-day C0 budget still applies.

## C0 selection remains blocked

C0 selection may be opened only after:

1. all planned iteration candidates and strong baselines have been evaluated;
2. candidate revisions are complete;
3. every material observation is recorded;
4. the candidate registry is explicitly closed;
5. a separate selection-opening checkpoint is reviewed and merged.

## Prohibited actions

Do not:

- rerun an existing discovery output directory;
- mutate an evaluated candidate version;
- remove a failed candidate;
- access `c0_selection` before registry closure;
- access or split the C1 reserve;
- define C1 success criteria from iteration results;
- present C0 iteration evidence as confirmatory;
- use Option B test performance to tune Option C.

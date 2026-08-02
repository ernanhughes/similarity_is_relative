# Option C0 Discovery-Preservation Decision

Date: 2026-08-02

## Decision

Option C will not begin with a single frozen refusal mechanism.

The authorised fifteen-working-day Option C budget is divided into:

```text
C0  bounded mechanism discovery — maximum 5 working days
C1  separately frozen confirmation — remaining budget, total <= 15 days
```

C0 is exploratory and cannot promote a scientific claim. C1 is confirmatory and cannot begin until a later prospective contract freezes the selected mechanism, data roles, calibration procedure, baselines, selective-risk comparison, material margin and kill rule.

## Why the sequence changed

The post-E01 decision originally described Option C as one propagated-refusal test. That description identified the scientific comparison but did not resolve the mechanism.

Unlike Option B, Option C currently contains both a discovery problem and a confirmation problem:

- the support representation is not settled;
- propagation semantics are not settled;
- the non-degenerate coverage region is not known;
- the strongest direct and primitive baselines have not yet been implemented in this operating regime;
- absent, weak and shifted primitive behaviour has not been characterised;
- the project does not yet know whether meaningful attainable headroom exists.

Freezing one candidate immediately would create a false choice between flexibility and scientific discipline. The better design is to freeze the exploration boundary now and freeze the selected scientific test only after development evidence exists.

## What C0 freezes

C0 freezes:

- a maximum five-working-day discovery budget;
- five data roles with repository separation;
- deferred selection of C1 calibration and test rows;
- an append-only candidate registry;
- an append-only discovery ledger;
- required strong baselines;
- complete reporting of rejected candidates;
- explicit C0 exit outcomes;
- claim-scoped stop rules;
- the prohibition on promoting exploratory observations;
- the requirement for a separate C1 contract.

C0 does not freeze:

- a favourite propagation mechanism;
- a final query set;
- a final nonconformity score;
- a final coverage band;
- a C1 material margin;
- C1 calibration or test rows;
- a scientific Option C outcome.

## Discovery and confirmation boundary

The project will use this distinction:

```text
C0 asks: what mechanism is coherent and worth testing?
C1 asks: does the selected mechanism beat the frozen alternatives?
```

C0 may revise mechanisms using only C0-visible data. Every candidate and revision must remain in the record.

C1 may not revise its mechanism after the contract merges. Final calibration and test identities are derived only after that merge from a previously committed reserve pool.

## Unexpected findings

Unexpected observations are not treated as noise merely because they were not the original target.

They must be recorded as:

- exploratory observations;
- unexpected findings;
- mechanism diagnostics;
- integrity findings; or
- new hypotheses requiring fresh data.

They may influence the C1 contract only when discovered before C1 freezes and only through explicit documentation.

They may not rescue a failed C1 decision or become confirmed claims from the same evidence on which they were discovered.

## Stop-rule interpretation

The original Option C kill condition is retained but clarified.

If C0 cannot justify a meaningful C1 test, or if C1 later fails its frozen gate, the current RELATE propagated-refusal novelty line closes.

That outcome does not invalidate:

- the independently verified Option B premise;
- the Option B canonical evidence;
- the evidence-first methodological output;
- properly labelled exploratory observations;
- unrelated future work under a new decision and fresh evidence.

No automatic rescue stage follows C0 or C1 failure.

## Data-firewall decision

The final C1 calibration and test rows will not be selected during C0.

C0 must first create and commit:

- a reproducible eligible reserve pool;
- whole-repository exclusions for Option B and visible C0 data;
- aggregate counts and cryptographic commitments;
- a deterministic future selection algorithm.

The final C1 row identities are generated only after the C1 contract merges, using that merge commit as part of the frozen selection seed.

This does not make public data literally secret. It prevents the project from choosing the holdout after seeing candidate behaviour and makes any premature materialisation an auditable protocol violation.

## Budget rule

```text
maximum C0 budget: 5 working days
maximum Option C total: 15 working days
```

Unused C0 time may remain available to C1. The total cannot expand without a new decision record.

## Current status

```text
Option B: COMPLETE — REAL_PREMISE_SUPPORTED
Option C: AUTHORISED
C0 protocol: PROSPECTIVELY FROZEN BY PR WHEN MERGED
C0 implementation: NOT STARTED
C1 contract: NOT WRITTEN
C1 evidence: UNSELECTED AND UNOBSERVED
Option C claim: UNTESTED
```

## Next action

Implement only the C0 data allocation, candidate-registry and discovery-ledger infrastructure.

Mechanism discovery remains blocked until the data firewall is independently reviewed. C1 remains blocked until C0 publishes one explicit exit outcome.
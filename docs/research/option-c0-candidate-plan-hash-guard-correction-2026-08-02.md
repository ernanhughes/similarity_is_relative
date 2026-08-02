# Option C0 Candidate-Plan Identity Erratum

Date: 2026-08-02

## Status

```text
C0_CANDIDATE_PLAN_IDENTITY_ERRATUM_REVIEWED_PENDING_MERGE
scientific_result_observed = false
mechanism_result_observed = false
c0_selection_accessed = false
c1_rows_selected = false
result_branch_created = false
```

## What happened

The one-time C0 iteration script stopped during pre-execution identity checks. The first guard compared the candidate plan's exact file-byte hash with a different published digest. After separating file and canonical JSON hashing, the regression test established that the published digest was not the canonical identity of the final committed JSON either.

The two reproducible identities of the committed candidate plan are:

```text
candidate-plan exact file SHA-256:
5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d

candidate-plan canonical JSON SHA-256:
7de70669553f180ea0507c68b28dc790e896019d664055fbaa0a535b550c10c6

candidate-registry exact file SHA-256:
a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282
```

The stale digest is:

```text
f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94
```

It appears as `artifact_hashes.candidate_plan` in the six immutable pre-execution `REGISTERED` events, but it is not the final plan's exact file hash or canonical parsed-JSON hash.

## Execution boundary was preserved

Both failures occurred before:

- creation of `agent/option-c0-iteration-results-v1`;
- candidate evaluation;
- observation of a C0 mechanism result;
- access to `c0_selection`;
- access to or division of the C1 reserve.

PR #49 was merged correctly with regular merge commit:

```text
59cb6232ec9813742216536397ebe1bdeaf1f05c
```

The registered implementation commit remains in `main` ancestry:

```text
d36436209d95eca555215a83856f042d241a90f4
```

## Correction approach

The original registry events remain immutable. They are not silently rewritten.

A pre-execution erratum is published at:

```text
artifacts/canonical/option-c0/candidate-plan-v1/
option-c0-candidate-plan-identity-erratum-v1.json
```

The erratum records:

- the stale published digest;
- both reproducible final plan identities;
- the exact registry identity;
- the six affected registrations;
- the fact that the issue was observed before execution;
- the unchanged candidate definitions and evidence boundary.

The one-time execution script now refuses unless it verifies:

1. exact candidate-plan file bytes;
2. canonical parsed candidate-plan JSON;
3. exact candidate-registry bytes;
4. exact erratum bytes;
5. all six registry events contain the stale digest documented by the erratum;
6. the erratum binds that stale digest to the corrected identities.

The exploratory result publication will carry the erratum identity alongside the plan and registry identities.

## Scientific boundary

This erratum changes no:

- primitive;
- query form;
- threshold or scale procedure;
- candidate mechanism;
- propagation rule;
- baseline;
- data role;
- repository assignment;
- implementation commit.

It does not create an Option C result or rescue any observed mechanism outcome, because no mechanism outcome exists yet.

## Next action

Validate this correction PR, squash merge it, update local `main`, and rerun the one-time C0 iteration script.

# Option C0 Candidate-Plan Hash Guard Correction

Date: 2026-08-02

## Status

```text
C0_CANDIDATE_PLAN_HASH_GUARD_CORRECTED_PENDING_MERGE
scientific_result_observed = false
mechanism_result_observed = false
c0_selection_accessed = false
c1_rows_selected = false
result_branch_created = false
```

## What happened

The one-time C0 iteration script stopped during its pre-execution identity checks with:

```text
Candidate-plan hash mismatch:
5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d
```

The failure occurred before the result branch was created and before any C0 iteration evidence was observed.

PR #49 was merged with a regular merge commit. The registered implementation commit remains in `main` ancestry. The failure was not caused by the merge method.

## Root cause

The checkpoint carries two legitimate identities for the candidate plan:

1. the SHA-256 of the exact pretty-printed JSON file bytes;
2. the SHA-256 of the parsed JSON serialized canonically with sorted keys and compact separators.

The script used `Get-FileHash`, which computes the first identity, but compared it with the second identity.

The frozen identities are:

```text
candidate-plan file SHA-256:
5af359e4a9d3b7eede8ca8d9e8a36bcac524164375f819c5676541503e5e3e0d

candidate-plan canonical JSON SHA-256:
f8254d5fed4ab168f48e0c519a03c5e322ac2ae0ad52fc97cdbf43d1dac66e94

candidate-registry file SHA-256:
a34bf7696c0586c2683de817515fa5f849be7cab5ccf07a6a844474c94017282
```

Both candidate-plan identities refer to the same reviewed JSON value. They are expected to differ because the file representation contains indentation and newlines while the canonical representation does not.

## Correction

The execution script now verifies all three identities explicitly:

- exact candidate-plan file bytes;
- canonical parsed candidate-plan JSON;
- exact candidate-registry file bytes.

A repository test freezes the distinction and prevents the byte identity from being confused with the semantic canonical identity again.

## Scientific boundary

This correction changes no candidate, query, primitive, threshold, propagation rule, baseline, data role or evidence identity.

It does not:

- evaluate a candidate;
- access `c0_iteration` results;
- access `c0_selection`;
- access or divide the C1 reserve;
- select C1 rows;
- create an Option C scientific finding.

## Next action

Merge the guard correction, update local `main`, rerun the complete test suite, and then rerun the one-time C0 iteration script.

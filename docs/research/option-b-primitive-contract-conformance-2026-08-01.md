# Option B primitive contract conformance

Date: 2026-08-01

## Status

```text
Option B contract: FROZEN
Primitive semantics clarification: PROSPECTIVE AND COMPLETE
Primitive extractor repair: IMPLEMENTED FOR REVIEW
Primitive tables v1: INVALIDATED; UNCHANGED IN THIS STAGE
Selected manifests v1: REQUIRE REVERIFICATION; UNCHANGED IN THIS STAGE
Canonical embeddings: NOT GENERATED
Primitive probes: NOT FIT
Hard-negative manifest: NOT GENERATED
Scientific metric: NOT OBSERVED
Gate: BLOCK BEFORE EMBEDDING EXTRACTION
```

This record resolves the primitive-extraction ambiguities identified by the
pre-embedding audit before any canonical v2 selection or embedding extraction.
It does not change the model, language, compound query, candidate pool,
baselines, continuation threshold, decision rule, or allowed scientific
outcomes.

## Prospective primitive clarification

### P1 — cyclomatic complexity

The existing registered increments remain in force. The following rules remove
implementation ambiguity:

- every comprehension generator contributes one cyclomatic increment because it
  introduces one loop decision;
- every comprehension filter contributes one additional cyclomatic increment;
- a comprehension with two generators and two filters therefore contributes
  four increments;
- every `elif` contributes the same one increment as an `If` node;
- `Try`, `With`, and `AsyncWith` do not independently add a P1 increment;
- every `ExceptHandler` continues to add one increment;
- conditional expressions, chained boolean operations, and `match` retain their
  already pinned treatment.

### P2 — maximum control nesting depth

The function body begins at depth zero. The registered control constructs are:

```text
If
For / AsyncFor
While
Try
With / AsyncWith
Match
List / set / dict comprehensions and generator expressions
```

The clarified depth rules are:

- each registered control construct adds one nesting level while its controlled
  body is traversed;
- each comprehension generator adds one level, and multiple generators are
  nested in source order;
- comprehension filters add P1 complexity but do not add a P2 nesting level;
- an `elif` remains at the same nesting depth as the `if` that begins its chain;
- an `if` written inside an `else` suite is a genuinely nested control and adds
  another level;
- nested functions, async functions, classes, and lambdas remain excluded from
  the enclosing function's primitive values.

The `elif` distinction is pinned from the parsed source location: an `If` that
is the sole `orelse` node and has the same column offset as its parent is an
`elif`; an indented `If` inside an `else` suite is nested.

## CodeSearchNet provenance mapping

Canonical selection uses the fields exposed by the pinned
`code-search-net/code_search_net` dataset loader:

```text
repository_name          -> repository
func_path_in_repository  -> path
func_name                -> function_id
whole_func_string        -> raw function code
```

The original JSON field names (`repo`, `path`, `original_string`) remain accepted
for deterministic local reconstruction. A row missing repository, path, or
function identifier is excluded as `missing_provenance`; an empty path is not
permitted to enter the stable-key calculation.

## Recursion behavior

Canonical primitive extraction pins Python's recursion limit to:

```text
1000
```

A `RecursionError` raised while parsing or visiting one row is recorded as
`ast_recursion_limit`, and that row alone is excluded. The existing observable
chunked selector remains a deterministic outer fallback for an uncaught
recursion failure.

The limit is exposed as `AST_RECURSION_LIMIT` and pinned by regression tests.
The v2 selection report produced in PR 3 must record the value explicitly.

## Artifact boundary

This stage deliberately does not regenerate or edit any committed v1 canonical
artifact. In particular, it does not modify:

- `option-b-selected-*-v1.jsonl`;
- `option-b-primitives-*-v1.jsonl`;
- `option-b-canonical-row-selection-v1.json`;
- external identity v1;
- any embedding, probe, manifest, metric, or decision artifact.

Primitive tables v1 remain invalidated by the audit. Selected manifests v1
remain unverified after the provenance repair.

## Next permitted stage

The next bounded stage is:

```text
PR 3 — canonical selection and primitive checkpoint v2
```

That stage must run selection A and B in separate fresh directories, compare
selected membership and ordering with v1, publish versioned v2 primitive tables
and a v2 selection report, and stop before embedding extraction.

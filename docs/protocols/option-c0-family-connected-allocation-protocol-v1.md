# Option C0 Family-Connected Allocation Protocol v1

Status: frozen for implementation review.

Protocol identity:
`82cb26a2ccd82c156e02062b263972f670403f5a1a062833253c49230e649991`

## Scope

This protocol defines a typed repository-family graph for future Option C0
family analysis. It freezes the evidence model, component construction, cache
contract, and decision rules. It does not execute the canonical family graph,
change allocations, refit models, replay C0, access hidden row contents, or
begin D2.

## Evidence Model

The family model is:

```text
repository nodes
typed evidence edges
frozen component rules
```

Same owner is a proxy observation, not proof of family membership. SimHash-near
function evidence is a heuristic review signal, not proof of family membership.

Hard connecting edge types:

- `DECLARED_GITHUB_FORK`
- `VERIFIED_REPOSITORY_SUCCESSION`
- `EXACT_CROSS_REPOSITORY_SOURCE_IDENTITY`
- `VERIFIED_SHARED_PACKAGE_LINEAGE`

Conditional connecting edge types:

- `EXACT_AST_WITH_CORROBORATING_PROVENANCE`
- `SAME_MODULE_LINEAGE_WITH_CORROBORATION`
- `EXPLICIT_COPY_OR_EXTRACTION_HISTORY`

Nonconnecting review evidence:

- `SAME_OWNER_PROXY`
- `SIMILAR_REPOSITORY_NAME`
- `SUFFIX_STRIPPED_NAME_MATCH`
- `SIMHASH_NEAR_FUNCTION`
- `COMMON_FRAMEWORK_OR_BOILERPLATE`
- `SHARED_LANGUAGE_OR_TOPIC`

Nonconnecting edges are retained for review and never participate in union-find
component formation.

## Component Rule

Repository identities are normalized to lowercase `owner/repository` strings.
Malformed or duplicate allocation entries are refused. Connecting edges are
sorted deterministically, and only those edges are used for union-find
components. Transitivity applies only to connecting edges.

Component IDs are SHA-256 hashes over the sorted member repositories and the
protocol identity.

## Public Metadata

Public repository metadata must be snapshotted and hashed. Unavailable, deleted,
renamed, archived, and rate-limited repositories must be recorded explicitly.
Live mutable API responses must not be silent dependencies.

## Decision Rule

Allowed future family-graph outcomes are:

- `FAMILY_GRAPH_COMPLETE_NO_CROSS_ROLE_COMPONENTS`
- `FAMILY_GRAPH_COMPLETE_CROSS_ROLE_COMPONENTS_OBSERVED`
- `FAMILY_GRAPH_INCOMPLETE_METADATA`
- `FAMILY_GRAPH_INCOMPLETE_REVIEW_REQUIRED`

The protocol distinguishes:

- family crossing observed
- allocation independence violated
- material contamination established
- reallocation required

These are not synonyms. Cross-role components do not automatically establish
material contamination, and material contamination does not automatically emit a
reallocation requirement without explicit human review under this protocol.

## Firewall

Permitted inputs are published repository names, published role assignments,
published aggregate row counts, D1 visible-row hashes and bounded metadata, and
public repository metadata.

Prohibited inputs and actions:

- C0 selection row-content access
- C1 reserve row-content access
- hidden row-content access
- canonical family graph execution in this PR
- allocation changes
- model refits
- C0 replay
- D2 execution


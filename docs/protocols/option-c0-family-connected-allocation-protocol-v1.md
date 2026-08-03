# Option C0 Family-Connected Allocation Protocol v1

Status: frozen for implementation review.

Protocol identity:
`a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08`

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

Each hard edge has its own explicit typed evidence schema. A generic
`required_evidence_complete = true` field is not accepted as family evidence.
Rules with manual review produce unresolved evidence candidates first. A
separate `ManualReviewDisposition` can approve or reject a candidate only when
its candidate ID, protocol SHA-256, evidence commitment, reviewer identity,
review timestamp, bounded reason, and derived disposition ID match exactly. A
resolved reviewed edge is valid only when independently checked against its
candidate and final disposition record.

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

Every edge rule has conjunctive evidence-source requirements. If a rule requires
both `d1_visible_cache` and `public_metadata_snapshot`, both immutable source
identities must be present in the canonical source bundle.

Rule payload evidence identities are cross-bound to source bundle entries. Fork,
succession, and lineage records must match the public metadata snapshot identity
in the bundle. D1-visible evidence must carry a stable visible evidence
commitment tied to the `d1_visible_cache` source identity.

Source bundle identities must resolve to validated immutable source records.
Automatic fork and exact-source edges cannot validate from hash strings alone;
their source records must support the endpoint-bound claim. Reviewed edges also
require those source records in addition to a valid manual disposition.

Exact-AST evidence identifies the specific reviewed visible pair through left
and right stable keys, the normalized AST hash, visible roles, function
identities, path suffixes, and the D1-visible evidence identity.

## Component Rule

Repository identities are normalized to lowercase `owner/repository` strings.
Malformed or duplicate allocation entries are refused. Connecting edges are
sorted deterministically, and only those edges are used for union-find
components. Duplicate edge IDs are rejected before counting, commitment,
publication, or component construction. Transitivity applies only to connecting
edges.

Initial allocation cache population must come from the canonical allocation
manifest and must match the frozen repository count, role repository counts,
role row counts, and ordered allocation-table commitment.

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

The materiality-input contract includes affected repositories and rows by role
pair, largest component, affected C0 fit and iteration fractions, hard and
conditional crossing counts, and feasibility of a family-disjoint allocation.
No automatic materiality threshold is frozen in v1.

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

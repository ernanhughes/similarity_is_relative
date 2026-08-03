"""Clean family-domain capability package.

Stage 2A extraction from relate.experiments.option_c0_family_connected_protocol.

Modules
-------
models       Pure immutable dataclasses.
rules        Frozen edge-rule taxonomy and rule-derived constants.
repositories Repository identity, normalization and allocation-domain operations.
sources      Source-evidence construction and validation.
edges        Edge, candidate and review construction and validation.
store        SQLite persistence: FamilyGraphCache, FamilyGraphCacheIdentity,
             make_cache_identity, component-membership and phase-commitment
             APIs (Stage 2B; Stage 2D).
graph        Pure connected-component construction: UnionFind, component_id,
             build_components (Stage 2D).
commitments  Graph-specific SHA-256 commitments: component_commitment,
             edge_commitment (Stage 2D). Distinct from the Stage 2C
             relate.workflows commitment chain, which binds workflow
             execution steps and results, not scientific graph records.
outcome      Bounded graph completeness and the frozen family-outcome
             decision: graph_completeness, family_graph_outcome (Stage 2D).

Dependency direction
--------------------
relate.family
    -> relate.evidence  (neutral helpers)
    internally: edges -> sources -> repositories -> models
                rules -> models
                store -> edges, repositories, sources, models
                graph -> edges, repositories, models
                commitments -> graph, edges, repositories, models
                outcome -> edges, rules, sources, models

The historical protocol module imports from relate.family; relate.family never
imports from relate.experiments.
"""

from __future__ import annotations

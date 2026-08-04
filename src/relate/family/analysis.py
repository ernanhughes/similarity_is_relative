"""Bounded cross-role component analysis.

Completes a pre-existing implementation gap recorded in Stage 2D
(docs/architecture/capability-continuity.md): ``family_graph_outcome``
consumes ``cross_role_connecting_components`` and
``hard_or_exact_fit_iteration_crossing_observed``, but no capability ever
computed them. The frozen protocol already defines the rule these values
answer (``protocol_contract()["decision_rules"]["family_crossing_observed"]``
== "true when a connecting component spans roles"). This module implements
that already-frozen rule; it does not introduce a new one.

Interpretation note on "hard_or_exact_fit_iteration_crossing_observed"
-----------------------------------------------------------------------
This exact field name was consumed but never computed anywhere in the
repository, so its precise derivation is an interpretation of the frozen
taxonomy, not a verbatim copy of prior code. It is derived here as:

- "hard_or_exact": an edge type in ``relate.family.rules.HARD_CONNECTING_EDGE_TYPES``,
  or ``EXACT_AST_WITH_CORROBORATING_PROVENANCE`` — the one
  conditional-connecting rule whose name and connecting policy assert an
  *exact* match (as opposed to the other two conditional-connecting rules,
  which are lineage/copy-history judgements). This is the natural reading of
  "hard or exact" against the taxonomy's own vocabulary.
- "fit_iteration crossing": a connecting edge whose two endpoints sit in
  different roles, and those two roles are exactly ``{"c0_fit", "c0_iteration"}``
  — the first two entries of ``relate.family.repositories.ROLE_ORDER``, and
  the only two roles the frozen scientific record currently uses (C0
  selection and C1 reserve remain blocked and unaccessed).

This interpretation is recorded in docs/architecture/migration-status.md and
docs/architecture/capability-continuity.md as a documented decision, not a
silent guess, per the extraction brief's instruction not to guess from a
name alone.

Inputs are bounded to repository identities, published role assignments,
published aggregate row counts, validated component membership, and
validated edge types/connectivity. This module never reads SQLite directly,
never reads function-row contents, and never concludes contamination,
materiality, or reallocation.

No database access, CLI parsing, file publication, or workflow
orchestration. This module must not import from relate.experiments,
relate.workflows, or relate.cli.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_text
from relate.family.graph import component_id
from relate.family.models import AllocationEntry, EvidenceEdge
from relate.family.repositories import ROLE_ORDER, normalize_repository
from relate.family.rules import HARD_CONNECTING_EDGE_TYPES

ROLE_CROSSING_ANALYSIS_SCHEMA_ID: Final = "relate-family-role-crossing-analysis-v1"
BOUNDED_FAMILY_OUTCOME_SCHEMA_ID: Final = "relate-family-bounded-outcome-v1"

HARD_OR_EXACT_CONNECTING_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    HARD_CONNECTING_EDGE_TYPES
) | {"EXACT_AST_WITH_CORROBORATING_PROVENANCE"}

_FIT_ITERATION_ROLE_PAIR: Final[frozenset[str]] = frozenset({"c0_fit", "c0_iteration"})


@dataclass(frozen=True)
class RoleCrossingComponent:
    """One connected component whose repositories span more than one role."""

    component_id: str
    repositories: tuple[str, ...]
    roles: tuple[str, ...]
    role_pairs: tuple[tuple[str, str], ...]
    repository_count: int

    def as_record(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "repositories": list(self.repositories),
            "roles": list(self.roles),
            "role_pairs": [list(pair) for pair in self.role_pairs],
            "repository_count": self.repository_count,
        }


@dataclass(frozen=True)
class RolePairImpact:
    """Repositories and aggregate published row counts affected by one role pair."""

    role_pair: tuple[str, str]
    repositories: tuple[str, ...]
    aggregate_row_count: int

    def as_record(self) -> dict[str, Any]:
        return {
            "role_pair": list(self.role_pair),
            "repositories": list(self.repositories),
            "aggregate_row_count": self.aggregate_row_count,
        }


@dataclass(frozen=True)
class RoleCrossingAnalysis:
    """Bounded facts about connecting components that span allocation roles.

    Never concludes material contamination, reallocation, or D2
    authorization — see module docstring.
    """

    cross_role_connecting_components: int
    crossing_component_ids: tuple[str, ...]
    crossing_components: tuple[RoleCrossingComponent, ...]
    role_pair_impacts: tuple[RolePairImpact, ...]
    largest_crossing_component_repository_count: int
    hard_or_exact_fit_iteration_crossing_observed: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "cross_role_connecting_components": self.cross_role_connecting_components,
            "crossing_component_ids": list(self.crossing_component_ids),
            "crossing_components": [c.as_record() for c in self.crossing_components],
            "role_pair_impacts": [r.as_record() for r in self.role_pair_impacts],
            "largest_crossing_component_repository_count": (
                self.largest_crossing_component_repository_count
            ),
            "hard_or_exact_fit_iteration_crossing_observed": (
                self.hard_or_exact_fit_iteration_crossing_observed
            ),
        }


def _role_sort_key(role: str) -> int:
    return ROLE_ORDER.index(role)


def analyse_role_crossings(
    allocation_entries: Sequence[AllocationEntry],
    components: Sequence[Mapping[str, Any]],
    resolved_edges: Sequence[EvidenceEdge],
    *,
    protocol_sha256: str,
) -> RoleCrossingAnalysis:
    """Compute bounded cross-role crossing facts from already-validated inputs.

    ``allocation_entries`` supplies published role assignments and aggregate
    row counts; ``components`` must be the shape produced by
    ``relate.family.graph.build_components``; ``resolved_edges`` supplies
    validated connectivity. Every repository in ``components`` must be known
    to ``allocation_entries``, every repository must appear in exactly one
    component, and every connecting edge's endpoints must fall inside a
    single computed component.
    """
    role_by_repository: dict[str, str] = {}
    row_count_by_repository: dict[str, int] = {}
    for entry in allocation_entries:
        repo = normalize_repository(entry.repository)
        if repo in role_by_repository:
            raise ValueError(f"duplicate allocation entry: {repo}")
        if entry.role not in ROLE_ORDER:
            raise ValueError(f"invalid allocation role: {entry.role}")
        role_by_repository[repo] = entry.role
        row_count_by_repository[repo] = entry.row_count

    seen_in_components: set[str] = set()
    seen_component_ids: set[str] = set()
    normalized_components: list[tuple[str, tuple[str, ...]]] = []
    for component in components:
        component_id_value = str(component.get("component_id", ""))
        if not component_id_value.strip():
            raise ValueError("component_id must be a nonempty string")
        if component_id_value in seen_component_ids:
            raise ValueError(f"duplicate component ID: {component_id_value}")
        seen_component_ids.add(component_id_value)
        raw_repositories = list(component.get("repositories") or [])
        if not raw_repositories:
            raise ValueError(f"component has no repositories: {component_id_value!r}")
        normalized_repositories: list[str] = []
        for repository in raw_repositories:
            repo = normalize_repository(str(repository))
            if repo not in role_by_repository:
                raise ValueError(f"component references unknown repository: {repo}")
            if repo in seen_in_components:
                raise ValueError(f"repository appears in multiple components: {repo}")
            seen_in_components.add(repo)
            normalized_repositories.append(repo)
        if int(component.get("repository_count", -1)) != len(normalized_repositories):
            raise ValueError(f"component repository_count is malformed: {component_id_value!r}")
        repositories = tuple(sorted(normalized_repositories))
        if component_id_value != component_id(repositories, protocol_sha256):
            raise ValueError(f"component_id is stale or tampered: {component_id_value!r}")
        normalized_components.append((component_id_value, repositories))

    missing_from_components = set(role_by_repository) - seen_in_components
    if missing_from_components:
        raise ValueError(
            f"repositories missing from computed components: {sorted(missing_from_components)}"
        )

    component_by_repository = {
        repo: component_id_value
        for component_id_value, repositories in normalized_components
        for repo in repositories
    }

    hard_or_exact_fit_iteration_crossing_observed = False
    for edge in resolved_edges:
        if not edge.connecting:
            continue
        left = normalize_repository(edge.left_repository)
        right = normalize_repository(edge.right_repository)
        if left not in component_by_repository or right not in component_by_repository:
            raise ValueError(f"connecting edge endpoint not in any component: {edge.edge_id}")
        if component_by_repository[left] != component_by_repository[right]:
            raise ValueError(
                f"connecting edge endpoints are not in the same component: {edge.edge_id}"
            )
        left_role = role_by_repository[left]
        right_role = role_by_repository[right]
        if (
            left_role != right_role
            and {left_role, right_role} == _FIT_ITERATION_ROLE_PAIR
            and edge.edge_type in HARD_OR_EXACT_CONNECTING_EDGE_TYPES
        ):
            hard_or_exact_fit_iteration_crossing_observed = True

    crossing_components: list[RoleCrossingComponent] = []
    role_pair_repositories: dict[tuple[str, str], set[str]] = {}
    for component_id_value, repositories in sorted(normalized_components):
        roles_in_component = sorted(
            {role_by_repository[repo] for repo in repositories}, key=_role_sort_key
        )
        if len(roles_in_component) <= 1:
            continue
        role_pairs: list[tuple[str, str]] = []
        for i in range(len(roles_in_component)):
            for j in range(i + 1, len(roles_in_component)):
                pair = (roles_in_component[i], roles_in_component[j])
                role_pairs.append(pair)
                role_pair_repositories.setdefault(pair, set()).update(
                    repo for repo in repositories if role_by_repository[repo] in pair
                )
        crossing_components.append(
            RoleCrossingComponent(
                component_id=component_id_value,
                repositories=repositories,
                roles=tuple(roles_in_component),
                role_pairs=tuple(role_pairs),
                repository_count=len(repositories),
            )
        )

    role_pair_impacts = tuple(
        RolePairImpact(
            role_pair=pair,
            repositories=tuple(sorted(role_pair_repositories[pair])),
            aggregate_row_count=sum(
                row_count_by_repository[repo] for repo in role_pair_repositories[pair]
            ),
        )
        for pair in sorted(
            role_pair_repositories, key=lambda p: (_role_sort_key(p[0]), _role_sort_key(p[1]))
        )
    )

    largest = max((c.repository_count for c in crossing_components), default=0)

    return RoleCrossingAnalysis(
        cross_role_connecting_components=len(crossing_components),
        crossing_component_ids=tuple(c.component_id for c in crossing_components),
        crossing_components=tuple(crossing_components),
        role_pair_impacts=role_pair_impacts,
        largest_crossing_component_repository_count=largest,
        hard_or_exact_fit_iteration_crossing_observed=hard_or_exact_fit_iteration_crossing_observed,
    )


def role_crossing_analysis_commitment(
    analysis: RoleCrossingAnalysis, *, protocol_sha256: str
) -> str:
    """Versioned scientific commitment for bounded role-crossing facts."""
    return sha256_text(
        canonical_json(
            {
                "schema_id": ROLE_CROSSING_ANALYSIS_SCHEMA_ID,
                "family_protocol_sha256": protocol_sha256,
                "analysis": analysis.as_record(),
            }
        )
    )


def bounded_family_outcome_commitment(outcome: Mapping[str, Any], *, protocol_sha256: str) -> str:
    """Versioned scientific commitment for the frozen bounded family outcome."""
    return sha256_text(
        canonical_json(
            {
                "schema_id": BOUNDED_FAMILY_OUTCOME_SCHEMA_ID,
                "family_protocol_sha256": protocol_sha256,
                "outcome": dict(outcome),
            }
        )
    )

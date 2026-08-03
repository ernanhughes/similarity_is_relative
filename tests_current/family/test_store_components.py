"""Component-membership persistence tests for relate.family.store.

Covers insertion, deterministic retrieval, identical/conflicting replay,
unknown-repository rejection, no partial state after a rejected write, and
persistence across close/reopen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from relate.family.store import CACHE_SCHEMA_ID, FamilyGraphCache, make_cache_identity


def _identity(**overrides: str) -> object:
    base = dict(
        family_protocol_sha256="a" * 64,
        allocation_manifest_sha256="b" * 64,
        allocation_context_sha256="c" * 64,
        d1_audit_result_sha256="d" * 64,
        d1_1_classification_sha256="e" * 64,
        cache_schema_version=CACHE_SCHEMA_ID,
        family_runner_source_identity="f" * 64,
    )
    base.update(overrides)
    return make_cache_identity(**base)


def _seed_repositories(cache: FamilyGraphCache, repositories: tuple[str, ...]) -> None:
    cache.connection.executemany(
        "INSERT OR IGNORE INTO allocation_repositories(repository, role, row_count) "
        "VALUES (?, 'c0_fit', 1)",
        [(repo,) for repo in repositories],
    )
    cache.connection.commit()


COMPONENTS = [
    {"component_id": "comp-1", "repositories": ["owner/a", "owner/b"], "repository_count": 2},
    {"component_id": "comp-2", "repositories": ["owner/c"], "repository_count": 1},
]


class TestComponentMembershipInsertion:
    def test_insertion_and_deterministic_retrieval(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a", "owner/b", "owner/c"))
            cache.put_component_memberships(COMPONENTS)
            first = cache.get_component_memberships()
            second = cache.get_component_memberships()
        assert first == second
        assert {c["component_id"] for c in first} == {"comp-1", "comp-2"}
        by_id = {c["component_id"]: c for c in first}
        assert by_id["comp-1"]["repositories"] == ("owner/a", "owner/b")
        assert by_id["comp-2"]["repository_count"] == 1

    def test_identical_replay_is_accepted(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a", "owner/b", "owner/c"))
            cache.put_component_memberships(COMPONENTS)
            cache.put_component_memberships(COMPONENTS)  # must not raise

    def test_conflicting_replay_is_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a", "owner/b", "owner/c"))
            cache.put_component_memberships(COMPONENTS)
            different = [
                {"component_id": "comp-1", "repositories": ["owner/a"], "repository_count": 1},
                {
                    "component_id": "comp-3",
                    "repositories": ["owner/b", "owner/c"],
                    "repository_count": 2,
                },
            ]
            with pytest.raises(ValueError, match="differ from the existing stored graph"):
                cache.put_component_memberships(different)
            # No partial mutation occurred: the original graph is intact.
            assert cache.get_component_memberships() == cache.get_component_memberships()
            by_id = {c["component_id"]: c for c in cache.get_component_memberships()}
            assert set(by_id) == {"comp-1", "comp-2"}

    def test_unknown_repository_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a", "owner/b"))
            with pytest.raises(ValueError, match="unknown repositories"):
                cache.put_component_memberships(COMPONENTS)  # references owner/c, not seeded

    def test_no_partial_state_after_failed_write(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a", "owner/b"))
            with pytest.raises(ValueError, match="unknown repositories"):
                cache.put_component_memberships(COMPONENTS)
            assert cache.get_component_memberships() == ()

    def test_empty_component_identifier_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a",))
            with pytest.raises(ValueError, match="component_id must be a nonempty string"):
                cache.put_component_memberships(
                    [{"component_id": "", "repositories": ["owner/a"], "repository_count": 1}]
                )

    def test_component_with_no_repositories_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            with pytest.raises(ValueError, match="no repositories"):
                cache.put_component_memberships(
                    [{"component_id": "comp-x", "repositories": [], "repository_count": 0}]
                )

    def test_repository_in_multiple_components_rejected(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            _seed_repositories(cache, ("owner/a",))
            with pytest.raises(ValueError, match="multiple components"):
                cache.put_component_memberships(
                    [
                        {
                            "component_id": "comp-1",
                            "repositories": ["owner/a"],
                            "repository_count": 1,
                        },
                        {
                            "component_id": "comp-2",
                            "repositories": ["owner/a"],
                            "repository_count": 1,
                        },
                    ]
                )


class TestComponentMembershipResume:
    def test_persists_across_close_and_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "family.sqlite3"
        identity = _identity()
        with FamilyGraphCache(db, identity=identity) as cache:
            _seed_repositories(cache, ("owner/a", "owner/b", "owner/c"))
            cache.put_component_memberships(COMPONENTS)
        with FamilyGraphCache(db, identity=identity) as cache:
            stored = cache.get_component_memberships()
        assert {c["component_id"] for c in stored} == {"comp-1", "comp-2"}

    def test_empty_store_returns_empty_tuple(self, tmp_path: Path) -> None:
        with FamilyGraphCache(tmp_path / "family.sqlite3", identity=_identity()) as cache:
            assert cache.get_component_memberships() == ()

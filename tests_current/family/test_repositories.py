"""Tests for relate.family.repositories."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from relate.family.repositories import (
    ALLOCATION_REPOSITORY_COMMITMENT_SHA256,
    ALLOCATION_REPOSITORY_COUNT,
    ALLOCATION_ROLE_REPOSITORY_COUNTS,
    ALLOCATION_ROLE_ROW_COUNTS,
    ROLE_ORDER,
    AllocationEntry,
    allocation_repository_commitment,
    load_allocation_manifest,
    normalize_repository,
    repository_owner,
    validate_canonical_allocation_entries,
)


class TestNormalizeRepository:
    def test_lowercase(self) -> None:
        assert normalize_repository("Owner/Repo") == "owner/repo"

    def test_strip_whitespace(self) -> None:
        assert normalize_repository("  owner/repo  ") == "owner/repo"

    def test_valid_chars(self) -> None:
        assert normalize_repository("org-name/my.repo_1") == "org-name/my.repo_1"

    def test_no_slash_rejected(self) -> None:
        with pytest.raises(ValueError, match="malformed"):
            normalize_repository("owneronly")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            normalize_repository("")

    def test_non_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            normalize_repository(123)  # type: ignore[arg-type]

    def test_uppercase_letters_in_name_normalized(self) -> None:
        assert normalize_repository("MyOrg/MyRepo") == "myorg/myrepo"

    def test_double_slash_rejected(self) -> None:
        with pytest.raises(ValueError, match="malformed"):
            normalize_repository("owner//repo")

    def test_leading_dash_rejected(self) -> None:
        with pytest.raises(ValueError, match="malformed"):
            normalize_repository("-owner/repo")

    def test_deterministic(self) -> None:
        assert normalize_repository("Owner/Repo") == normalize_repository("owner/repo")


class TestRepositoryOwner:
    def test_extracts_owner(self) -> None:
        assert repository_owner("owner/repo") == "owner"

    def test_normalizes_before_extracting(self) -> None:
        assert repository_owner("MyOrg/Repo") == "myorg"

    def test_rejects_malformed(self) -> None:
        with pytest.raises(ValueError):
            repository_owner("notvalid")


class TestAllocationRepositoryCommitment:
    def _entries(self) -> list[AllocationEntry]:
        return [
            AllocationEntry(repository="owner/a", role="c0_fit", row_count=10),
            AllocationEntry(repository="owner/b", role="c0_iteration", row_count=5),
        ]

    def test_returns_sha256(self) -> None:
        sha = allocation_repository_commitment(self._entries())
        assert len(sha) == 64
        assert sha.isalnum()

    def test_deterministic(self) -> None:
        assert allocation_repository_commitment(
            self._entries()
        ) == allocation_repository_commitment(self._entries())

    def test_order_independent(self) -> None:
        entries = self._entries()
        reversed_entries = list(reversed(entries))
        assert allocation_repository_commitment(entries) == allocation_repository_commitment(
            reversed_entries
        )

    def test_duplicate_repository_rejected(self) -> None:
        entries = [
            AllocationEntry(repository="owner/a", role="c0_fit", row_count=10),
            AllocationEntry(repository="owner/a", role="c0_iteration", row_count=5),
        ]
        with pytest.raises(ValueError, match="duplicate"):
            allocation_repository_commitment(entries)

    def test_invalid_role_rejected(self) -> None:
        entries = [
            AllocationEntry(repository="owner/a", role="bad_role", row_count=10),
        ]
        with pytest.raises(ValueError, match="invalid allocation role"):
            allocation_repository_commitment(entries)

    def test_invalid_row_count_rejected(self) -> None:
        entries = [
            AllocationEntry(repository="owner/a", role="c0_fit", row_count=True),  # type: ignore[arg-type]
        ]
        with pytest.raises(ValueError, match="row count"):
            allocation_repository_commitment(entries)

    def test_canonical_commitment_value(self) -> None:
        # The canonical commitment is a recorded invariant.
        assert ALLOCATION_REPOSITORY_COMMITMENT_SHA256 == (
            "cede73f5321d5a667a26b27a66131b8a324b89423353dd77be45f40c16ffc103"
        )


class TestLoadAllocationManifest:
    def test_parses_jsonl(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            json.dumps({"repository": "owner/a", "role": "c0_fit", "row_count": 10})
            + "\n"
            + json.dumps({"repository": "Owner/B", "role": "c0_iteration", "row_count": 5})
            + "\n",
            encoding="utf-8",
        )
        entries = load_allocation_manifest(manifest)
        assert len(entries) == 2
        assert entries[0].repository == "owner/a"
        assert entries[1].repository == "owner/b"

    def test_sorted_by_repository(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            json.dumps({"repository": "owner/z", "role": "c0_fit", "row_count": 1})
            + "\n"
            + json.dumps({"repository": "owner/a", "role": "c0_fit", "row_count": 1})
            + "\n",
            encoding="utf-8",
        )
        entries = load_allocation_manifest(manifest)
        assert entries[0].repository == "owner/a"
        assert entries[1].repository == "owner/z"

    def test_duplicate_repository_rejected(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            json.dumps({"repository": "owner/a", "role": "c0_fit", "row_count": 1})
            + "\n"
            + json.dumps({"repository": "owner/a", "role": "c0_iteration", "row_count": 2})
            + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="duplicate"):
            load_allocation_manifest(manifest)

    def test_invalid_role_rejected(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            json.dumps({"repository": "owner/a", "role": "bad", "row_count": 1}) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="invalid role"):
            load_allocation_manifest(manifest)

    def test_invalid_row_count_rejected(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            json.dumps({"repository": "owner/a", "role": "c0_fit", "row_count": -1}) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="row_count"):
            load_allocation_manifest(manifest)

    def test_sha256_mismatch_rejected(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            json.dumps({"repository": "owner/a", "role": "c0_fit", "row_count": 1}) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="SHA-256"):
            load_allocation_manifest(manifest, expected_sha256="0" * 64)

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        manifest = tmp_path / "alloc.jsonl"
        manifest.write_text(
            "\n"
            + json.dumps({"repository": "owner/a", "role": "c0_fit", "row_count": 1})
            + "\n"
            + "\n",
            encoding="utf-8",
        )
        entries = load_allocation_manifest(manifest)
        assert len(entries) == 1


class TestValidateCanonicalAllocationEntries:
    def test_rejects_wrong_count(self) -> None:
        entries = [AllocationEntry(repository="owner/a", role="c0_fit", row_count=1)]
        with pytest.raises(ValueError, match="repository count"):
            validate_canonical_allocation_entries(entries)

    def test_role_order_preserved(self) -> None:
        assert ROLE_ORDER == ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")

    def test_canonical_counts_recorded(self) -> None:
        assert ALLOCATION_REPOSITORY_COUNT == 5324
        assert ALLOCATION_ROLE_REPOSITORY_COUNTS == {
            "c0_fit": 2117,
            "c0_iteration": 1058,
            "c0_selection": 545,
            "c1_reserve": 1604,
        }
        assert ALLOCATION_ROLE_ROW_COUNTS == {
            "c0_fit": 8007,
            "c0_iteration": 4110,
            "c0_selection": 2070,
            "c1_reserve": 6357,
        }

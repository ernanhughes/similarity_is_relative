"""Compatibility tests: clean relate.family package vs. historical facade.

Verifies that symbols re-exported from the historical module are the same
objects as those in the clean package, and that identity computations agree.

No canonical data files are read.  Protocol contract comparison uses the
canonical artifact path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---- Historical facade imports ----
import relate.experiments.option_c0_family_connected_protocol as historical

# ---- Clean package imports ----
import relate.family.edges as clean_edges
import relate.family.models as clean_models
import relate.family.repositories as clean_repos
import relate.family.rules as clean_rules
import relate.family.sources as clean_sources

TIMESTAMP = "2026-08-02T00:00:00+00:00"
SOURCE_ID = "a" * 64
FAKE_SHA = "b" * 64
LEFT = "owner/alpha"
RIGHT = "owner/beta"

CANONICAL_ARTIFACT = Path(
    "artifacts/canonical/option-c0/review-v1/family-protocol-v1/"
    "option-c0-family-connected-allocation-contract-v1.json"
)
CANONICAL_PROTOCOL_SHA = "a36b37728c0630a0de5f2c75628cf0409796f8902cd547277f3ad087c7876c08"


# ---------------------------------------------------------------------------
# Object identity checks — re-exports must be the same Python objects
# ---------------------------------------------------------------------------


class TestObjectIdentity:
    def test_evidence_edge_is_same_object(self) -> None:
        assert historical.EvidenceEdge is clean_models.EvidenceEdge

    def test_evidence_candidate_is_same_object(self) -> None:
        assert historical.EvidenceCandidate is clean_models.EvidenceCandidate

    def test_manual_review_disposition_is_same_object(self) -> None:
        assert historical.ManualReviewDisposition is clean_models.ManualReviewDisposition

    def test_allocation_entry_is_same_object(self) -> None:
        assert historical.AllocationEntry is clean_models.AllocationEntry

    def test_source_evidence_record_is_same_object(self) -> None:
        assert historical.SourceEvidenceRecord is clean_models.SourceEvidenceRecord

    def test_edge_rule_is_same_object(self) -> None:
        assert historical.EdgeRule is clean_models.EdgeRule

    def test_edge_rules_is_same_dict(self) -> None:
        assert historical.EDGE_RULES is clean_rules.EDGE_RULES

    def test_all_edge_types_is_same_tuple(self) -> None:
        assert historical.ALL_EDGE_TYPES is clean_rules.ALL_EDGE_TYPES

    def test_connecting_edge_types_is_same_tuple(self) -> None:
        assert historical.CONNECTING_EDGE_TYPES is clean_rules.CONNECTING_EDGE_TYPES

    def test_hard_connecting_edge_types_is_same_tuple(self) -> None:
        assert historical.HARD_CONNECTING_EDGE_TYPES is clean_rules.HARD_CONNECTING_EDGE_TYPES

    def test_conditional_connecting_edge_types_is_same_tuple(self) -> None:
        assert (
            historical.CONDITIONAL_CONNECTING_EDGE_TYPES
            is clean_rules.CONDITIONAL_CONNECTING_EDGE_TYPES
        )

    def test_nonconnecting_edge_types_is_same_tuple(self) -> None:
        assert historical.NONCONNECTING_EDGE_TYPES is clean_rules.NONCONNECTING_EDGE_TYPES


# ---------------------------------------------------------------------------
# Data equality checks
# ---------------------------------------------------------------------------


class TestEdgeRulesEquality:
    def test_same_edge_rules_data(self) -> None:
        assert historical.EDGE_RULES == clean_rules.EDGE_RULES

    def test_same_insertion_order(self) -> None:
        assert list(historical.EDGE_RULES) == list(clean_rules.EDGE_RULES)

    def test_same_taxonomy_tuples(self) -> None:
        assert historical.ALL_EDGE_TYPES == clean_rules.ALL_EDGE_TYPES
        assert historical.CONNECTING_EDGE_TYPES == clean_rules.CONNECTING_EDGE_TYPES
        assert historical.HARD_CONNECTING_EDGE_TYPES == clean_rules.HARD_CONNECTING_EDGE_TYPES
        assert (
            historical.CONDITIONAL_CONNECTING_EDGE_TYPES
            == clean_rules.CONDITIONAL_CONNECTING_EDGE_TYPES
        )
        assert historical.NONCONNECTING_EDGE_TYPES == clean_rules.NONCONNECTING_EDGE_TYPES


# ---------------------------------------------------------------------------
# Rule contract equality
# ---------------------------------------------------------------------------


class TestRuleContractEquality:
    def test_same_contract(self) -> None:
        assert historical.edge_rules_contract() == clean_rules.edge_rules_contract()

    def test_same_contract_type(self) -> None:
        assert type(historical.edge_rules_contract()) is type(clean_rules.edge_rules_contract())


# ---------------------------------------------------------------------------
# Repository normalization equality
# ---------------------------------------------------------------------------


class TestRepositoryNormalizationEquality:
    def test_same_normalize(self) -> None:
        for name in ["Owner/Repo", "MYORG/MYREPO", "  foo/bar  "]:
            assert historical.normalize_repository(name) == clean_repos.normalize_repository(name)

    def test_same_owner_extraction(self) -> None:
        assert historical.repository_owner("Owner/Repo") == clean_repos.repository_owner(
            "Owner/Repo"
        )


# ---------------------------------------------------------------------------
# Allocation commitment equality
# ---------------------------------------------------------------------------


class TestAllocationCommitmentEquality:
    def _entries(self):
        return [
            clean_models.AllocationEntry(repository="owner/a", role="c0_fit", row_count=10),
            clean_models.AllocationEntry(repository="owner/b", role="c0_iteration", row_count=5),
        ]

    def test_same_commitment(self) -> None:
        assert historical.allocation_repository_commitment(
            self._entries()
        ) == clean_repos.allocation_repository_commitment(self._entries())

    def test_same_canonical_sha256(self) -> None:
        assert (
            historical.ALLOCATION_REPOSITORY_COMMITMENT_SHA256
            == clean_repos.ALLOCATION_REPOSITORY_COMMITMENT_SHA256
        )


# ---------------------------------------------------------------------------
# Source record equality
# ---------------------------------------------------------------------------


class TestSourceRecordEquality:
    def _make_record(self, module):
        return module.make_source_record(
            "fixture",
            payload={"k": "v"},
            provenance={"generated_at": TIMESTAMP},
        )

    def test_same_source_record(self) -> None:
        hist = historical.SourceEvidenceRecord(
            source_type="fixture",
            source_identity=clean_sources.make_source_record(
                "fixture", payload={"k": "v"}, provenance={"generated_at": TIMESTAMP}
            ).source_identity,
            payload={"k": "v"},
            provenance={"generated_at": TIMESTAMP},
            status="COMPLETE",
            record_sha256=clean_sources.make_source_record(
                "fixture", payload={"k": "v"}, provenance={"generated_at": TIMESTAMP}
            ).record_sha256,
        )
        clean = clean_sources.make_source_record(
            "fixture", payload={"k": "v"}, provenance={"generated_at": TIMESTAMP}
        )
        assert hist == clean

    def test_make_source_record_gives_same_result(self) -> None:
        clean = clean_sources.make_source_record(
            "fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP}
        )
        # historical module re-exports make_source_record from clean_sources
        hist = historical.make_source_record(
            "fixture", payload={"k": "v"}, provenance={"t": TIMESTAMP}
        )
        assert hist == clean
        assert hist.source_identity == clean.source_identity
        assert hist.record_sha256 == clean.record_sha256


# ---------------------------------------------------------------------------
# Evidence candidate equality
# ---------------------------------------------------------------------------


class TestEvidenceCandidateEquality:
    def _fork_candidate(self, module_make, module_src):
        snap = clean_sources.make_source_record(
            "public_metadata_snapshot",
            payload={
                "fork": True,
                "child_full_name": LEFT,
                "parent_or_source_full_name": RIGHT,
                "left_repository_id": "1",
                "right_repository_id": "2",
            },
            provenance={},
        )
        evidence_sources = {
            "github_rest": snap.source_identity,
            "public_metadata_snapshot": snap.source_identity,
        }
        payload = {
            "left_repository_id": "1",
            "right_repository_id": "2",
            "child_full_name": LEFT,
            "parent_or_source_full_name": RIGHT,
            "fork": True,
            "metadata_snapshot_identity": snap.source_identity,
            "snapshot_status": "COMPLETE",
        }
        return module_make(
            LEFT,
            RIGHT,
            "DECLARED_GITHUB_FORK",
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )

    def test_same_candidate_id(self) -> None:
        clean = self._fork_candidate(clean_edges.make_evidence_candidate, clean_sources)
        hist = self._fork_candidate(historical.make_evidence_candidate, clean_sources)
        assert clean.candidate_id == hist.candidate_id
        assert clean.evidence_commitment == hist.evidence_commitment

    def test_same_candidate_type(self) -> None:
        clean = self._fork_candidate(clean_edges.make_evidence_candidate, clean_sources)
        hist = self._fork_candidate(historical.make_evidence_candidate, clean_sources)
        assert type(clean) is type(hist)
        assert type(clean) is clean_models.EvidenceCandidate


# ---------------------------------------------------------------------------
# Manual review disposition equality
# ---------------------------------------------------------------------------


class TestManualReviewDispositionEquality:
    def _make_disp(self, module_make):
        return module_make(
            edge_candidate_id="c" * 64,
            protocol_sha256=FAKE_SHA,
            evidence_commitment="e" * 64,
            disposition="APPROVED",
            reviewer_identity=SOURCE_ID,
            review_timestamp=TIMESTAMP,
            bounded_reason="test review",
        )

    def test_same_disposition_id(self) -> None:
        clean = self._make_disp(clean_edges.make_manual_review_disposition)
        hist = self._make_disp(historical.make_manual_review_disposition)
        assert clean.disposition_id == hist.disposition_id

    def test_same_type(self) -> None:
        clean = self._make_disp(clean_edges.make_manual_review_disposition)
        hist = self._make_disp(historical.make_manual_review_disposition)
        assert type(clean) is type(hist)
        assert type(clean) is clean_models.ManualReviewDisposition


# ---------------------------------------------------------------------------
# Resolved edge equality
# ---------------------------------------------------------------------------


class TestResolvedEdgeEquality:
    def _fork_candidate(self):
        snap = clean_sources.make_source_record(
            "public_metadata_snapshot",
            payload={
                "fork": True,
                "child_full_name": LEFT,
                "parent_or_source_full_name": RIGHT,
                "left_repository_id": "1",
                "right_repository_id": "2",
            },
            provenance={},
        )
        evidence_sources = {
            "github_rest": snap.source_identity,
            "public_metadata_snapshot": snap.source_identity,
        }
        payload = {
            "left_repository_id": "1",
            "right_repository_id": "2",
            "child_full_name": LEFT,
            "parent_or_source_full_name": RIGHT,
            "fork": True,
            "metadata_snapshot_identity": snap.source_identity,
            "snapshot_status": "COMPLETE",
        }
        return clean_edges.make_evidence_candidate(
            LEFT,
            RIGHT,
            "DECLARED_GITHUB_FORK",
            evidence_sources=evidence_sources,
            evidence_payload=payload,
        )

    def test_same_resolved_edge_from_clean(self) -> None:
        cand = self._fork_candidate()
        clean_edge = clean_edges.resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_SHA)
        hist_edge = historical.resolve_evidence_candidate(cand, None, protocol_sha256=FAKE_SHA)
        assert clean_edge.edge_id == hist_edge.edge_id
        assert clean_edge.connecting == hist_edge.connecting
        assert type(clean_edge) is type(hist_edge)
        assert type(clean_edge) is clean_models.EvidenceEdge


# ---------------------------------------------------------------------------
# Protocol contract and SHA
# ---------------------------------------------------------------------------


class TestProtocolContractEquality:
    def test_protocol_sha_matches_canonical(self) -> None:
        contract = historical.protocol_contract()
        assert contract["protocol_sha256"] == CANONICAL_PROTOCOL_SHA

    def test_canonical_artifact_sha_matches(self) -> None:
        if not CANONICAL_ARTIFACT.exists():
            pytest.skip("canonical artifact not accessible from test working directory")
        with CANONICAL_ARTIFACT.open(encoding="utf-8") as fh:
            artifact = json.load(fh)
        assert artifact["protocol_sha256"] == CANONICAL_PROTOCOL_SHA

    def test_protocol_contract_is_deterministic(self) -> None:
        c1 = historical.protocol_contract()
        c2 = historical.protocol_contract()
        assert c1 == c2

    def test_protocol_version_matches(self) -> None:
        assert historical.PROTOCOL_VERSION == clean_edges.PROTOCOL_VERSION


# ---------------------------------------------------------------------------
# No forbidden imports in clean package
# ---------------------------------------------------------------------------


class TestDependencyDirection:
    def test_family_models_does_not_import_experiments(self) -> None:
        import relate.family.models as m

        _assert_no_experiments_import(m)

    def test_family_rules_does_not_import_experiments(self) -> None:
        import relate.family.rules as r

        _assert_no_experiments_import(r)

    def test_family_repositories_does_not_import_experiments(self) -> None:
        import relate.family.repositories as r

        _assert_no_experiments_import(r)

    def test_family_sources_does_not_import_experiments(self) -> None:
        import relate.family.sources as s

        _assert_no_experiments_import(s)

    def test_family_edges_does_not_import_experiments(self) -> None:
        import relate.family.edges as e

        _assert_no_experiments_import(e)


def _assert_no_experiments_import(module) -> None:
    """Check that no member of module.__dict__ is from relate.experiments."""
    for name, obj in vars(module).items():
        mod = getattr(obj, "__module__", None) or ""
        if "relate.experiments" in mod:
            raise AssertionError(f"{module.__name__}.{name} is from {mod} (forbidden)")

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from relate.evidence.hashing import sha256_file
from relate.family.publication import (
    ALLOWED_PUBLICATION_DISPOSITIONS,
    AUTHORIZE_BOUNDED_REVIEW_PUBLICATION,
    WITHHOLD_BOUNDED_REVIEW_PUBLICATION,
    FamilyPublicationDisposition,
    derive_publication_disposition_id,
    make_family_publication_disposition,
    make_publication_bundle,
    publish_family_review_bundle,
)
from relate.family.review import build_family_review_packet, family_review_packet_commitment


def _packet(completed_family_workflow):
    plan, result = completed_family_workflow
    return build_family_review_packet(plan=plan, result=result)


def _disposition(packet, disposition=AUTHORIZE_BOUNDED_REVIEW_PUBLICATION):
    return make_family_publication_disposition(
        packet=packet,
        disposition=disposition,
        reviewer_identity="reviewer:stage-2f",
        review_timestamp="2026-08-03T12:00:00+00:00",
        bounded_reason="bounded review publication decision",
    )


def test_valid_authorization_and_withholding(completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    assert _disposition(packet).disposition == AUTHORIZE_BOUNDED_REVIEW_PUBLICATION
    assert _disposition(packet, WITHHOLD_BOUNDED_REVIEW_PUBLICATION).disposition == (
        WITHHOLD_BOUNDED_REVIEW_PUBLICATION
    )
    assert "REALLOCATION_REQUIRED" not in ALLOWED_PUBLICATION_DISPOSITIONS
    assert "D2_AUTHORIZED" not in ALLOWED_PUBLICATION_DISPOSITIONS


def test_invalid_disposition_inputs_rejected(completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    with pytest.raises(ValueError, match="invalid"):
        _disposition(packet, "REALLOCATION_REQUIRED")
    with pytest.raises(ValueError, match="timezone-aware"):
        make_family_publication_disposition(
            packet=packet,
            disposition=AUTHORIZE_BOUNDED_REVIEW_PUBLICATION,
            reviewer_identity="reviewer:stage-2f",
            review_timestamp="2026-08-03T12:00:00",
            bounded_reason="reason",
        )
    with pytest.raises(ValueError, match="nonempty"):
        make_family_publication_disposition(
            packet=packet,
            disposition=AUTHORIZE_BOUNDED_REVIEW_PUBLICATION,
            reviewer_identity="",
            review_timestamp="2026-08-03T12:00:00+00:00",
            bounded_reason="reason",
        )


def test_tampered_disposition_id_rejected(completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    disposition = _disposition(packet)
    record = disposition.as_record()
    record.pop("schema_id")
    with pytest.raises(ValueError, match="stale"):
        FamilyPublicationDisposition(**{**record, "disposition_id": "0" * 64})


def test_authorized_noncanonical_publication_succeeds(
    tmp_path: Path, completed_family_workflow
) -> None:
    packet = _packet(completed_family_workflow)
    disposition = _disposition(packet)
    destination = tmp_path / "review" / "family-review-publication.json"
    receipt = publish_family_review_bundle(
        packet=packet,
        disposition=disposition,
        destination=destination,
        repo_root=Path.cwd(),
    )
    assert destination.exists()
    assert receipt.published_file_sha256 == sha256_file(destination)
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert data["bundle_commitment"] == receipt.bundle_commitment
    assert data["review_packet_commitment"] == family_review_packet_commitment(packet)
    assert receipt.disposition_id == disposition.disposition_id
    assert not list(destination.parent.glob("*.tmp-*"))


def test_withheld_publication_refused(tmp_path: Path, completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    disposition = _disposition(packet, WITHHOLD_BOUNDED_REVIEW_PUBLICATION)
    with pytest.raises(ValueError, match="not authorized"):
        publish_family_review_bundle(
            packet=packet,
            disposition=disposition,
            destination=tmp_path / "withheld.json",
            repo_root=Path.cwd(),
        )


def test_existing_destination_refused(tmp_path: Path, completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    disposition = _disposition(packet)
    destination = tmp_path / "exists.json"
    destination.write_text("old", encoding="utf-8")
    with pytest.raises(FileExistsError):
        publish_family_review_bundle(
            packet=packet,
            disposition=disposition,
            destination=destination,
            repo_root=Path.cwd(),
        )


def test_canonical_destination_refused(tmp_path: Path, completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    disposition = _disposition(packet)
    canonical = Path.cwd() / "artifacts" / "canonical" / ".." / "canonical" / "x.json"
    with pytest.raises(ValueError, match="canonical path"):
        publish_family_review_bundle(
            packet=packet,
            disposition=disposition,
            destination=canonical,
            repo_root=Path.cwd(),
        )


def test_stale_disposition_refused(completed_family_workflow) -> None:
    packet = _packet(completed_family_workflow)
    disposition = _disposition(packet)
    wrong_packet_commitment = "0" * 64
    stale_id = derive_publication_disposition_id(
        family_protocol_sha256=disposition.family_protocol_sha256,
        review_packet_commitment=wrong_packet_commitment,
        publication_scope=disposition.publication_scope,
        disposition=disposition.disposition,
        reviewer_identity=disposition.reviewer_identity,
        review_timestamp=disposition.review_timestamp,
        bounded_reason=disposition.bounded_reason,
    )
    stale = replace(
        disposition,
        review_packet_commitment=wrong_packet_commitment,
        disposition_id=stale_id,
    )
    with pytest.raises(ValueError, match="another packet"):
        make_publication_bundle(packet, stale)

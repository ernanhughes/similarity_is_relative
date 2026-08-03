"""Immutable noncanonical publication boundary for family review packets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from relate.evidence.atomic_io import atomic_write_json
from relate.evidence.canonical_json import canonical_json_compact_unicode as canonical_json
from relate.evidence.hashing import sha256_file, sha256_text
from relate.evidence.immutable import refuse_overwrite
from relate.family.review import (
    FAMILY_REVIEW_PACKET_SCHEMA_ID,
    FamilyReviewPacket,
    family_review_packet_commitment,
    reject_canonical_path,
)
from relate.family.sources import parse_timestamp, validate_source_identity
from relate.family.workflow.models import validate_sha256_identity

FAMILY_PUBLICATION_DISPOSITION_SCHEMA_ID: Final = "relate-family-publication-disposition-v1"
FAMILY_PUBLICATION_BUNDLE_SCHEMA_ID: Final = "relate-family-publication-bundle-v1"
AUTHORIZE_BOUNDED_REVIEW_PUBLICATION: Final = "AUTHORIZE_BOUNDED_REVIEW_PUBLICATION"
WITHHOLD_BOUNDED_REVIEW_PUBLICATION: Final = "WITHHOLD_BOUNDED_REVIEW_PUBLICATION"
PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY: Final = "BOUNDED_FAMILY_RESULT_ONLY"
ALLOWED_PUBLICATION_DISPOSITIONS: Final = (
    AUTHORIZE_BOUNDED_REVIEW_PUBLICATION,
    WITHHOLD_BOUNDED_REVIEW_PUBLICATION,
)
_MAX_REASON_LENGTH: Final = 500


def _reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("bounded reason must be nonempty")
    stripped = value.strip()
    if len(stripped) > _MAX_REASON_LENGTH:
        raise ValueError("bounded reason exceeds length limit")
    return stripped


@dataclass(frozen=True)
class FamilyPublicationDisposition:
    family_protocol_sha256: str
    review_packet_commitment: str
    publication_scope: str
    disposition: str
    reviewer_identity: str
    review_timestamp: str
    bounded_reason: str
    disposition_id: str

    def __post_init__(self) -> None:
        validate_sha256_identity(self.family_protocol_sha256, label="family_protocol_sha256")
        validate_sha256_identity(self.review_packet_commitment, label="review_packet_commitment")
        if self.publication_scope != PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY:
            raise ValueError("publication disposition scope is not permitted")
        if self.disposition not in ALLOWED_PUBLICATION_DISPOSITIONS:
            raise ValueError("invalid family publication disposition")
        reviewer = validate_source_identity(self.reviewer_identity)
        timestamp = parse_timestamp(self.review_timestamp)
        reason = _reason(self.bounded_reason)
        expected = derive_publication_disposition_id(
            family_protocol_sha256=self.family_protocol_sha256,
            review_packet_commitment=self.review_packet_commitment,
            publication_scope=self.publication_scope,
            disposition=self.disposition,
            reviewer_identity=reviewer,
            review_timestamp=timestamp,
            bounded_reason=reason,
        )
        if self.disposition_id != expected:
            raise ValueError("family publication disposition ID is stale")
        object.__setattr__(self, "reviewer_identity", reviewer)
        object.__setattr__(self, "review_timestamp", timestamp)
        object.__setattr__(self, "bounded_reason", reason)

    def as_record(self) -> dict[str, Any]:
        return {
            "schema_id": FAMILY_PUBLICATION_DISPOSITION_SCHEMA_ID,
            "family_protocol_sha256": self.family_protocol_sha256,
            "review_packet_commitment": self.review_packet_commitment,
            "publication_scope": self.publication_scope,
            "disposition": self.disposition,
            "reviewer_identity": self.reviewer_identity,
            "review_timestamp": self.review_timestamp,
            "bounded_reason": self.bounded_reason,
            "disposition_id": self.disposition_id,
        }


def derive_publication_disposition_id(
    *,
    family_protocol_sha256: str,
    review_packet_commitment: str,
    publication_scope: str,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> str:
    payload = {
        "schema_id": FAMILY_PUBLICATION_DISPOSITION_SCHEMA_ID,
        "family_protocol_sha256": family_protocol_sha256,
        "review_packet_commitment": review_packet_commitment,
        "publication_scope": publication_scope,
        "disposition": disposition,
        "reviewer_identity": reviewer_identity,
        "review_timestamp": review_timestamp,
        "bounded_reason": bounded_reason,
    }
    return sha256_text(canonical_json(payload))


def make_family_publication_disposition(
    *,
    packet: FamilyReviewPacket,
    disposition: str,
    reviewer_identity: str,
    review_timestamp: str,
    bounded_reason: str,
) -> FamilyPublicationDisposition:
    packet_record = packet.as_record()
    protocol_sha = str(packet_record["family_protocol_sha256"])
    packet_commitment = family_review_packet_commitment(packet)
    reviewer = validate_source_identity(reviewer_identity)
    timestamp = parse_timestamp(review_timestamp)
    reason = _reason(bounded_reason)
    disposition_id = derive_publication_disposition_id(
        family_protocol_sha256=protocol_sha,
        review_packet_commitment=packet_commitment,
        publication_scope=PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY,
        disposition=disposition,
        reviewer_identity=reviewer,
        review_timestamp=timestamp,
        bounded_reason=reason,
    )
    return FamilyPublicationDisposition(
        family_protocol_sha256=protocol_sha,
        review_packet_commitment=packet_commitment,
        publication_scope=PUBLICATION_SCOPE_BOUNDED_FAMILY_RESULT_ONLY,
        disposition=disposition,
        reviewer_identity=reviewer,
        review_timestamp=timestamp,
        bounded_reason=reason,
        disposition_id=disposition_id,
    )


def publication_disposition_commitment(disposition: FamilyPublicationDisposition) -> str:
    return sha256_text(canonical_json(disposition.as_record()))


def family_publication_disposition_from_record(
    record: dict[str, Any],
) -> FamilyPublicationDisposition:
    if record.get("schema_id") != FAMILY_PUBLICATION_DISPOSITION_SCHEMA_ID:
        raise ValueError("unsupported family publication disposition schema")
    payload = dict(record)
    payload.pop("schema_id")
    return FamilyPublicationDisposition(**payload)


@dataclass(frozen=True)
class FamilyPublicationBundle:
    packet: FamilyReviewPacket
    packet_commitment: str
    disposition: FamilyPublicationDisposition
    disposition_commitment: str
    bundle_commitment: str

    def as_record(self) -> dict[str, Any]:
        return {
            "schema_id": FAMILY_PUBLICATION_BUNDLE_SCHEMA_ID,
            "review_packet": self.packet.as_record(),
            "review_packet_commitment": self.packet_commitment,
            "publication_disposition": self.disposition.as_record(),
            "publication_disposition_commitment": self.disposition_commitment,
            "bundle_commitment": self.bundle_commitment,
        }


def make_publication_bundle(
    packet: FamilyReviewPacket,
    disposition: FamilyPublicationDisposition,
) -> FamilyPublicationBundle:
    if packet.as_record().get("schema_id") != FAMILY_REVIEW_PACKET_SCHEMA_ID:
        raise ValueError("invalid family review packet schema")
    packet_commitment = family_review_packet_commitment(packet)
    if disposition.review_packet_commitment != packet_commitment:
        raise ValueError("publication disposition reviews another packet")
    if disposition.family_protocol_sha256 != packet.as_record()["family_protocol_sha256"]:
        raise ValueError("publication disposition protocol mismatch")
    disposition_commitment = publication_disposition_commitment(disposition)
    payload = {
        "schema_id": FAMILY_PUBLICATION_BUNDLE_SCHEMA_ID,
        "review_packet": packet.as_record(),
        "review_packet_commitment": packet_commitment,
        "publication_disposition": disposition.as_record(),
        "publication_disposition_commitment": disposition_commitment,
    }
    bundle_commitment = sha256_text(canonical_json(payload))
    return FamilyPublicationBundle(
        packet=packet,
        packet_commitment=packet_commitment,
        disposition=disposition,
        disposition_commitment=disposition_commitment,
        bundle_commitment=bundle_commitment,
    )


@dataclass(frozen=True)
class FamilyPublicationReceipt:
    bundle_commitment: str
    published_file_sha256: str
    review_packet_commitment: str
    disposition_id: str

    def as_record(self) -> dict[str, str]:
        return {
            "bundle_commitment": self.bundle_commitment,
            "published_file_sha256": self.published_file_sha256,
            "review_packet_commitment": self.review_packet_commitment,
            "disposition_id": self.disposition_id,
        }


def publish_family_review_bundle(
    *,
    packet: FamilyReviewPacket,
    disposition: FamilyPublicationDisposition,
    destination: Path,
    repo_root: Path,
) -> FamilyPublicationReceipt:
    """Atomically publish an authorized noncanonical family review bundle."""
    reject_canonical_path(destination, repo_root=repo_root, label="publication destination")
    reject_canonical_path(destination.parent, repo_root=repo_root, label="publication parent")
    refuse_overwrite(destination, label="family review publication")
    if disposition.disposition != AUTHORIZE_BOUNDED_REVIEW_PUBLICATION:
        raise ValueError("family review publication was not authorized")
    bundle = make_publication_bundle(packet, disposition)
    atomic_write_json(destination, bundle.as_record())
    return FamilyPublicationReceipt(
        bundle_commitment=bundle.bundle_commitment,
        published_file_sha256=sha256_file(destination),
        review_packet_commitment=bundle.packet_commitment,
        disposition_id=disposition.disposition_id,
    )

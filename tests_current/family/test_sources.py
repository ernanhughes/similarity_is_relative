"""Tests for relate.family.sources."""

from __future__ import annotations

import pytest

from relate.family.sources import (
    ALLOWED_EVIDENCE_SOURCES,
    FORBIDDEN_PAYLOAD_PATTERNS,
    HASH_PATTERN,
    MAX_EVIDENCE_STRING_LENGTH,
    METADATA_STATUSES,
    PUBLIC_METADATA_FIELDS,
    make_source_record,
    parse_timestamp,
    payload_hash,
    public_metadata_snapshot,
    source_record_from_record,
    validate_payload_firewall,
    validate_source_identity,
    validate_source_record,
)

TIMESTAMP = "2026-08-02T00:00:00+00:00"
SOURCE_ID = "a" * 64


class TestParseTimestamp:
    def test_parses_valid_iso(self) -> None:
        result = parse_timestamp("2026-08-02T00:00:00+00:00")
        assert result == "2026-08-02T00:00:00+00:00"

    def test_parses_z_suffix(self) -> None:
        result = parse_timestamp("2026-08-02T00:00:00Z")
        assert "+00:00" in result

    def test_rejects_naive(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            parse_timestamp("2026-08-02T00:00:00")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            parse_timestamp("")

    def test_rejects_non_string(self) -> None:
        with pytest.raises(ValueError):
            parse_timestamp(None)  # type: ignore[arg-type]


class TestValidateSourceIdentity:
    def test_accepts_sha256(self) -> None:
        assert validate_source_identity("a" * 64) == "a" * 64

    def test_accepts_locator(self) -> None:
        locator = "https://api.github.com/repos/owner/repo"
        assert validate_source_identity(locator) == locator

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="nonempty"):
            validate_source_identity("")

    def test_rejects_plain_string(self) -> None:
        with pytest.raises(ValueError, match="SHA-256 or frozen locator"):
            validate_source_identity("not-a-hash-or-locator")

    def test_rejects_too_long(self) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            validate_source_identity("x" * (MAX_EVIDENCE_STRING_LENGTH + 1))

    def test_hash_pattern_is_64_hex_chars(self) -> None:
        assert HASH_PATTERN.fullmatch("a" * 64)
        assert not HASH_PATTERN.fullmatch("a" * 63)
        assert not HASH_PATTERN.fullmatch("g" * 64)


class TestValidatePayloadFirewall:
    def test_allows_clean_payload(self) -> None:
        validate_payload_firewall({"key": "value", "nested": {"k": "v"}})

    def test_rejects_forbidden_key(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            validate_payload_firewall({"source_body": "x"})

    def test_rejects_nested_forbidden_key(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            validate_payload_firewall({"outer": {"raw_source": "x"}})

    def test_rejects_long_string(self) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            validate_payload_firewall({"k": "x" * (MAX_EVIDENCE_STRING_LENGTH + 1)})

    def test_allows_list_values(self) -> None:
        validate_payload_firewall({"items": [1, 2, 3]})

    def test_rejects_forbidden_in_list(self) -> None:
        with pytest.raises(ValueError):
            validate_payload_firewall({"items": [{"source_body": "x"}]})

    def test_forbidden_patterns_complete(self) -> None:
        for pattern in FORBIDDEN_PAYLOAD_PATTERNS:
            with pytest.raises(ValueError, match="forbidden"):
                validate_payload_firewall({pattern: "x"})


class TestPayloadHash:
    def test_returns_sha256(self) -> None:
        result = payload_hash({"k": "v"})
        assert len(result) == 64
        assert result.isalnum()

    def test_deterministic(self) -> None:
        assert payload_hash({"k": "v"}) == payload_hash({"k": "v"})

    def test_sensitive_to_key(self) -> None:
        assert payload_hash({"a": "v"}) != payload_hash({"b": "v"})

    def test_rejects_forbidden_payload(self) -> None:
        with pytest.raises(ValueError):
            payload_hash({"source_body": "x"})


class TestMakeSourceRecord:
    def _make(self, **kwargs) -> object:
        defaults = dict(
            source_type="fixture",
            payload={"key": "value"},
            provenance={"generated_at": TIMESTAMP},
            status="COMPLETE",
        )
        defaults.update(kwargs)
        return make_source_record(defaults["source_type"], payload=defaults["payload"],
                                  provenance=defaults["provenance"], status=defaults["status"])

    def test_creates_record(self) -> None:
        record = self._make()
        assert record.source_type == "fixture"
        assert record.status == "COMPLETE"
        assert len(record.source_identity) == 64
        assert len(record.record_sha256) == 64

    def test_deterministic_identity(self) -> None:
        r1 = self._make()
        r2 = self._make()
        assert r1.source_identity == r2.source_identity
        assert r1.record_sha256 == r2.record_sha256

    def test_payload_change_changes_identity(self) -> None:
        r1 = self._make(payload={"key": "v1"})
        r2 = self._make(payload={"key": "v2"})
        assert r1.source_identity != r2.source_identity

    def test_invalid_source_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid source record type"):
            make_source_record("unknown_type", payload={}, provenance={})

    def test_forbidden_payload_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_source_record("fixture", payload={"source_body": "x"}, provenance={})

    def test_incomplete_status_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid source record status"):
            make_source_record("fixture", payload={}, provenance={}, status="INVALID")

    def test_as_record_round_trip(self) -> None:
        original = self._make()
        record_dict = original.as_record()
        restored = source_record_from_record(record_dict)
        assert original == restored

    def test_all_allowed_source_types(self) -> None:
        for source_type in ALLOWED_EVIDENCE_SOURCES:
            record = make_source_record(source_type, payload={}, provenance={})
            assert record.source_type == source_type


class TestValidateSourceRecord:
    def test_valid_record_passes(self) -> None:
        record = make_source_record("fixture", payload={"k": "v"}, provenance={"ts": TIMESTAMP})
        validate_source_record(record)

    def test_tampered_source_identity_rejected(self) -> None:
        record = make_source_record("fixture", payload={"k": "v"}, provenance={})
        from dataclasses import replace
        tampered = replace(record, source_identity="0" * 64)
        with pytest.raises(ValueError, match="tampered"):
            validate_source_record(tampered)

    def test_tampered_record_sha256_rejected(self) -> None:
        record = make_source_record("fixture", payload={"k": "v"}, provenance={})
        from dataclasses import replace
        tampered = replace(record, record_sha256="0" * 64)
        with pytest.raises(ValueError, match="tampered"):
            validate_source_record(tampered)


class TestPublicMetadataSnapshot:
    def _snapshot(self, **kwargs):
        defaults = dict(
            repository="owner/repo",
            status="COMPLETE",
            retrieval_timestamp=TIMESTAMP,
            evidence_source_identity=SOURCE_ID,
            payload={"fork": False},
        )
        defaults.update(kwargs)
        return public_metadata_snapshot(**defaults)

    def test_creates_snapshot(self) -> None:
        snap = self._snapshot()
        assert "snapshot_sha256" in snap
        assert "payload" in snap
        assert snap["repository"] == "owner/repo"

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValueError, match="status is not frozen"):
            self._snapshot(status="INVALID")

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValueError, match="unexpected public metadata fields"):
            self._snapshot(payload={"fork": False, "secret": "x"})

    def test_public_metadata_fields_allowlist(self) -> None:
        for field in PUBLIC_METADATA_FIELDS:
            snap = self._snapshot(payload={field: "value"})
            assert field in snap["payload"]

    def test_normalizes_repository(self) -> None:
        snap = self._snapshot(repository="Owner/Repo")
        assert snap["repository"] == "owner/repo"

    def test_deterministic_snapshot_sha(self) -> None:
        s1 = self._snapshot()
        s2 = self._snapshot()
        assert s1["snapshot_sha256"] == s2["snapshot_sha256"]

    def test_metadata_statuses_complete(self) -> None:
        for status in METADATA_STATUSES:
            snap = self._snapshot(status=status)
            assert snap["status"] == status

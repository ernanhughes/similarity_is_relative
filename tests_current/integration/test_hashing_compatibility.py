"""Hashing compatibility tests.

Verifies that the evidence helper functions produce byte-identical output to
the historical inline implementations they replaced.

Each migrated helper is tested against an independently reconstructed expected
value (using ``hashlib.sha256`` directly, not importing the deleted code).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from relate.evidence.hashing import sha256_bytes, sha256_file, sha256_text

# ---------------------------------------------------------------------------
# Helper: independently compute expected digests
# ---------------------------------------------------------------------------


def _expected_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _expected_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _expected_file_read_bytes(path: Path) -> str:
    """Historical read_bytes() approach (option_b_identity / _v2 style)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_file_streaming(path: Path) -> str:
    """Historical streaming approach (option_b_probe_runner style)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# sha256_bytes
# ---------------------------------------------------------------------------


class TestSha256BytesCompatibility:
    def test_empty_bytes(self) -> None:
        assert sha256_bytes(b"") == _expected_bytes(b"")

    def test_ascii_bytes(self) -> None:
        payload = b"hello world"
        assert sha256_bytes(payload) == _expected_bytes(payload)

    def test_binary_bytes(self) -> None:
        payload = bytes(range(256))
        assert sha256_bytes(payload) == _expected_bytes(payload)

    def test_output_is_64_char_lowercase_hex(self) -> None:
        result = sha256_bytes(b"test")
        assert len(result) == 64
        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# sha256_text
# ---------------------------------------------------------------------------


class TestSha256TextCompatibility:
    def test_empty_string(self) -> None:
        assert sha256_text("") == _expected_text("")

    def test_ascii_text(self) -> None:
        assert sha256_text("hello") == _expected_text("hello")

    def test_unicode_text(self) -> None:
        text = "caf\u00e9 \u4e2d\u6587"
        assert sha256_text(text) == _expected_text(text)

    def test_utf8_encoding_used(self) -> None:
        # Explicitly verify the encoding matches utf-8 encode.
        text = "naïve"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert sha256_text(text) == expected


# ---------------------------------------------------------------------------
# sha256_file
# ---------------------------------------------------------------------------


class TestSha256FileCompatibility:
    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.bin"
        p.write_bytes(b"")
        assert sha256_file(p) == _expected_bytes(b"")

    def test_small_binary_file(self, tmp_path: Path) -> None:
        payload = b"small file content"
        p = tmp_path / "small.bin"
        p.write_bytes(payload)
        assert sha256_file(p) == _expected_bytes(payload)

    def test_matches_read_bytes_approach(self, tmp_path: Path) -> None:
        """streaming sha256_file must match the historical read_bytes() approach."""
        payload = b"test content for compatibility"
        p = tmp_path / "file.bin"
        p.write_bytes(payload)
        assert sha256_file(p) == _expected_file_read_bytes(p)

    def test_matches_streaming_approach(self, tmp_path: Path) -> None:
        """streaming sha256_file must match the historical streaming approach."""
        payload = bytes(range(256)) * 100
        p = tmp_path / "medium.bin"
        p.write_bytes(payload)
        assert sha256_file(p) == _expected_file_streaming(p)

    def test_multi_chunk_file(self, tmp_path: Path) -> None:
        """File larger than 1 MiB must produce same result as non-chunked."""
        payload = bytes(range(256)) * (5 * 1024)  # ~1.25 MiB
        p = tmp_path / "large.bin"
        p.write_bytes(payload)
        expected = _expected_bytes(payload)
        assert sha256_file(p) == expected

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises((FileNotFoundError, OSError)):
            sha256_file(tmp_path / "does_not_exist.bin")

    def test_output_is_64_char_lowercase_hex(self, tmp_path: Path) -> None:
        p = tmp_path / "hex.bin"
        p.write_bytes(b"check format")
        result = sha256_file(p)
        assert len(result) == 64
        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# Cross-function consistency
# ---------------------------------------------------------------------------


class TestHashingCrossConsistency:
    def test_sha256_bytes_and_sha256_text_agree_on_utf8(self) -> None:
        text = "hello"
        assert sha256_text(text) == sha256_bytes(text.encode("utf-8"))

    def test_sha256_bytes_and_sha256_file_agree(self, tmp_path: Path) -> None:
        payload = b"cross-check payload"
        p = tmp_path / "cross.bin"
        p.write_bytes(payload)
        assert sha256_file(p) == sha256_bytes(payload)

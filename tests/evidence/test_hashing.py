"""Tests for relate.evidence.hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from relate.evidence.hashing import sha256_bytes, sha256_file, sha256_text


class TestSha256Bytes:
    def test_empty(self) -> None:
        expected = hashlib.sha256(b"").hexdigest()
        assert sha256_bytes(b"") == expected

    def test_known_value(self) -> None:
        payload = b"hello world"
        expected = hashlib.sha256(payload).hexdigest()
        assert sha256_bytes(payload) == expected

    def test_returns_lowercase_hex(self) -> None:
        result = sha256_bytes(b"test")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_inputs_differ(self) -> None:
        assert sha256_bytes(b"a") != sha256_bytes(b"b")


class TestSha256Text:
    def test_ascii_matches_utf8_bytes(self) -> None:
        text = "hello"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert sha256_text(text) == expected

    def test_unicode_encoded_as_utf8(self) -> None:
        text = "café"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert sha256_text(text) == expected

    def test_returns_lowercase_hex(self) -> None:
        result = sha256_text("anything")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_consistent_with_sha256_bytes(self) -> None:
        text = "deterministic"
        assert sha256_text(text) == sha256_bytes(text.encode("utf-8"))


class TestSha256File:
    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert sha256_file(f) == expected

    def test_known_content(self, tmp_path: Path) -> None:
        content = b"the quick brown fox"
        f = tmp_path / "content.bin"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert sha256_file(f) == expected

    def test_streaming_matches_single_read(self, tmp_path: Path) -> None:
        # Fill a file larger than a single 1 MiB chunk.
        content = b"x" * (2 * 1024 * 1024 + 37)
        f = tmp_path / "large.bin"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert sha256_file(f) == expected

    def test_returns_lowercase_hex(self, tmp_path: Path) -> None:
        f = tmp_path / "any.bin"
        f.write_bytes(b"data")
        result = sha256_file(f)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_files_differ(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        assert sha256_file(f1) != sha256_file(f2)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            sha256_file(tmp_path / "missing.bin")

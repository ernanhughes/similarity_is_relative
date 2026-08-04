"""Tests for relate.evidence.canonical_json."""

from __future__ import annotations

import json

import pytest

from relate.evidence.canonical_json import (
    canonical_json_compact_ascii,
    canonical_json_compact_unicode,
)


class TestCanonicalJsonCompactUnicode:
    def test_simple_dict(self) -> None:
        result = canonical_json_compact_unicode({"b": 1, "a": 2})
        assert result == '{"a":2,"b":1}'

    def test_sort_keys(self) -> None:
        result = canonical_json_compact_unicode({"z": "last", "a": "first"})
        assert result == '{"a":"first","z":"last"}'

    def test_no_spaces(self) -> None:
        result = canonical_json_compact_unicode({"key": "value"})
        assert " " not in result

    def test_unicode_unescaped(self) -> None:
        result = canonical_json_compact_unicode({"k": "café"})
        # ensure_ascii=False: non-ASCII characters pass through unescaped
        assert "café" in result
        assert "\\u" not in result

    def test_nested(self) -> None:
        result = canonical_json_compact_unicode({"b": {"d": 4, "c": 3}, "a": 1})
        assert result == '{"a":1,"b":{"c":3,"d":4}}'

    def test_list(self) -> None:
        result = canonical_json_compact_unicode([3, 1, 2])
        assert result == "[3,1,2]"

    def test_empty_dict(self) -> None:
        assert canonical_json_compact_unicode({}) == "{}"

    def test_null_value(self) -> None:
        result = canonical_json_compact_unicode({"k": None})
        assert result == '{"k":null}'

    def test_round_trips(self) -> None:
        data = {"z": [1, 2], "a": {"nested": True}}
        serialized = canonical_json_compact_unicode(data)
        assert json.loads(serialized) == data

    def test_exact_bytes_for_ascii_value(self) -> None:
        # For pure-ASCII content the two variants must agree byte-for-byte.
        data = {"key": "value", "num": 42}
        assert canonical_json_compact_unicode(data) == canonical_json_compact_ascii(data)


class TestCanonicalJsonCompactAscii:
    def test_simple_dict(self) -> None:
        result = canonical_json_compact_ascii({"b": 1, "a": 2})
        assert result == '{"a":2,"b":1}'

    def test_sort_keys(self) -> None:
        result = canonical_json_compact_ascii({"z": "last", "a": "first"})
        assert result == '{"a":"first","z":"last"}'

    def test_no_spaces(self) -> None:
        result = canonical_json_compact_ascii({"key": "value"})
        assert " " not in result

    def test_unicode_escaped(self) -> None:
        result = canonical_json_compact_ascii({"k": "café"})
        # ensure_ascii=True: non-ASCII characters are \uXXXX-escaped
        assert "café" not in result
        assert "\\u" in result

    def test_nested(self) -> None:
        result = canonical_json_compact_ascii({"b": {"d": 4, "c": 3}, "a": 1})
        assert result == '{"a":1,"b":{"c":3,"d":4}}'

    def test_empty_dict(self) -> None:
        assert canonical_json_compact_ascii({}) == "{}"

    def test_round_trips(self) -> None:
        data = {"z": [1, 2], "a": {"nested": True}}
        serialized = canonical_json_compact_ascii(data)
        assert json.loads(serialized) == data


class TestVariantsDiffer:
    def test_unicode_content_produces_different_bytes(self) -> None:
        """The two variants must differ for non-ASCII content."""
        data = {"name": "naïve"}
        unicode_result = canonical_json_compact_unicode(data)
        ascii_result = canonical_json_compact_ascii(data)
        assert unicode_result != ascii_result

    def test_unicode_variant_contains_literal_char(self) -> None:
        data = {"name": "naïve"}
        assert "naïve" in canonical_json_compact_unicode(data)

    def test_ascii_variant_contains_escape(self) -> None:
        data = {"name": "naïve"}
        assert "\\u" in canonical_json_compact_ascii(data)

    @pytest.mark.parametrize("char", ["é", "ü", "中", "🔬"])
    def test_non_ascii_chars_differ(self, char: str) -> None:
        data = {"v": char}
        assert canonical_json_compact_unicode(data) != canonical_json_compact_ascii(data)

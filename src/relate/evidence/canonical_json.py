"""Deterministic canonical JSON serialization.

Two named variants are provided because historical callers require different
byte-level behaviour. Do not silently unify them.

canonical_json_compact_unicode
    sort_keys=True, separators=(",", ":"), ensure_ascii=False
    Unicode characters pass through unescaped.
    Used by: option_c0_family_connected_protocol, option_c0_d1_overlap_classification.

canonical_json_compact_ascii
    sort_keys=True, separators=(",", ":"), ensure_ascii=True
    Non-ASCII characters are \\uXXXX-escaped.
    Used by: option_c0_d1_integrity_audit, option_c0_discovery_runner,
             option_c0_data_firewall, option_c0_data_firewall_independent,
             option_c0_embedding_cache.

These two variants produce different bytes for any value containing non-ASCII
characters. Do not replace one with the other.

This module must not open databases, write files, or reference scientific models.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def canonical_json_compact_unicode(data: Mapping[str, Any] | Any) -> str:
    """Return compact deterministic JSON with Unicode characters unescaped.

    sort_keys=True, separators=(",", ":"), ensure_ascii=False.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json_compact_ascii(data: Any) -> str:
    """Return compact deterministic JSON with non-ASCII characters \\uXXXX-escaped.

    sort_keys=True, separators=(",", ":"), ensure_ascii=True.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

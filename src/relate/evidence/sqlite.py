"""Neutral SQLite durability and identity helpers.

Provides standalone helpers for:

enforce_wal_pragmas(conn)
    Set PRAGMA journal_mode=WAL, synchronous=FULL, foreign_keys=ON.

verify_wal_pragmas(conn)
    Read and verify the three pragmas. Raises ValueError if any is not set
    to the required value. Returns a dict of the observed values.

bind_cache_identity(conn, table, expected, has_data_fn)
    Bind a deterministic identity mapping into *table* (which must have
    key/value TEXT columns). Refuses to open a cache that already contains
    data rows but no identity, and refuses mismatched identity keys or values.

These helpers do not contain scientific schema definitions, family graph tables
or D1 result payloads. Domain-specific schema belongs in capability stores.

This module must not import from relate.experiments.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from typing import Any


def enforce_wal_pragmas(conn: sqlite3.Connection) -> None:
    """Set WAL journal mode, FULL synchronous, and foreign-key enforcement."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")


def verify_wal_pragmas(conn: sqlite3.Connection) -> dict[str, Any]:
    """Verify WAL pragmas are active. Raises ValueError if any are not set correctly.

    Returns a dict with keys: journal_mode, synchronous, foreign_keys, synchronous_full.
    """
    journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
    synchronous = int(conn.execute("PRAGMA synchronous").fetchone()[0])
    foreign_keys = int(conn.execute("PRAGMA foreign_keys").fetchone()[0])
    result: dict[str, Any] = {
        "journal_mode": journal_mode,
        "synchronous": synchronous,
        "foreign_keys": foreign_keys,
        "synchronous_full": synchronous == 2,
    }
    if journal_mode != "wal" or synchronous != 2 or foreign_keys != 1:
        raise ValueError("SQLite WAL pragmas are not enforced")
    return result


def bind_cache_identity(
    conn: sqlite3.Connection,
    table: str,
    expected: Mapping[str, str],
    has_data_fn: Callable[[], bool],
) -> None:
    """Bind *expected* key-value identity rows into *table*.

    If the table already contains identity rows:
      - the key set must match *expected* exactly;
      - every value must match.
    If the table is empty but *has_data_fn()* returns True, the cache contains
    data without identity and is rejected.
    If the table is empty and *has_data_fn()* returns False, identity rows are
    inserted.

    *table* must have TEXT columns (key, value) with key as PRIMARY KEY.
    """
    rows = {
        str(key): str(value)
        for key, value in conn.execute(f"SELECT key, value FROM {table}")  # noqa: S608
    }
    if rows:
        if set(rows) != set(expected):
            raise ValueError(f"cache identity key set mismatch in {table!r}")
        for key, value in expected.items():
            if rows[key] != str(value):
                raise ValueError(f"cache identity mismatch in {table!r}: {key}")
    elif has_data_fn():
        raise ValueError(f"cache contains data rows without identity in {table!r}")
    conn.executemany(
        f"""
        INSERT INTO {table}(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,  # noqa: S608
        sorted(expected.items()),
    )
    conn.commit()

"""Recovery-safe local embedding cache for pre-publication Option C0 execution."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np

from relate.evidence.hashing import sha256_bytes
from relate.evidence.sqlite import enforce_wal_pragmas

CACHE_SCHEMA: Final = "option-c0-embedding-cache-v1"
DEFAULT_CACHE_PATH: Final = Path(".writer/option-c0/cache/option-c0-embeddings-v1.sqlite3")


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return sha256_bytes(payload)


@dataclass(frozen=True)
class EmbeddingFingerprint:
    """Complete identity of one reusable C0 embedding execution."""

    payload: dict[str, Any]
    sha256: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> EmbeddingFingerprint:
        value = dict(payload)
        if value.get("schema") != "option-c0-embedding-fingerprint-v1":
            raise ValueError("unexpected Option C0 embedding fingerprint schema")
        return cls(value, canonical_json_sha256(value))


class OptionC0EmbeddingCache:
    """SQLite cache keyed by source row and complete embedding fingerprint."""

    def __init__(self, path: Path = DEFAULT_CACHE_PATH) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        enforce_wal_pragmas(self.connection)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS fingerprints (
                fingerprint_sha256 TEXT PRIMARY KEY,
                schema_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                stable_key TEXT NOT NULL,
                code_sha256 TEXT NOT NULL,
                fingerprint_sha256 TEXT NOT NULL,
                dtype TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                vector BLOB NOT NULL,
                vector_sha256 TEXT NOT NULL,
                PRIMARY KEY (stable_key, code_sha256, fingerprint_sha256),
                FOREIGN KEY (fingerprint_sha256)
                    REFERENCES fingerprints(fingerprint_sha256)
            );
            """
        )
        self.connection.commit()

    def register_fingerprint(self, fingerprint: EmbeddingFingerprint) -> None:
        payload_json = json.dumps(
            fingerprint.payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        self.connection.execute(
            """
            INSERT INTO fingerprints (
                fingerprint_sha256, schema_id, payload_json
            ) VALUES (?, ?, ?)
            ON CONFLICT(fingerprint_sha256) DO NOTHING
            """,
            (fingerprint.sha256, CACHE_SCHEMA, payload_json),
        )
        row = self.connection.execute(
            """
            SELECT schema_id, payload_json
            FROM fingerprints
            WHERE fingerprint_sha256 = ?
            """,
            (fingerprint.sha256,),
        ).fetchone()
        if row != (CACHE_SCHEMA, payload_json):
            raise ValueError("embedding cache fingerprint collision or corruption")
        self.connection.commit()

    def get(
        self,
        *,
        stable_key: str,
        code_sha256: str,
        fingerprint_sha256: str,
    ) -> np.ndarray | None:
        row = self.connection.execute(
            """
            SELECT dtype, dimensions, vector, vector_sha256
            FROM embeddings
            WHERE stable_key = ?
              AND code_sha256 = ?
              AND fingerprint_sha256 = ?
            """,
            (stable_key, code_sha256, fingerprint_sha256),
        ).fetchone()
        if row is None:
            return None
        dtype, dimensions, vector, expected_sha256 = row
        if dtype != "float32" or int(dimensions) <= 0:
            return None
        payload = bytes(vector)
        if sha256_bytes(payload) != expected_sha256:
            return None
        value = np.frombuffer(payload, dtype=np.float32).copy()
        if value.shape != (int(dimensions),) or not np.isfinite(value).all():
            return None
        return value

    def put(
        self,
        *,
        stable_key: str,
        code_sha256: str,
        fingerprint_sha256: str,
        vector: np.ndarray,
    ) -> None:
        if not stable_key or len(code_sha256) != 64 or len(fingerprint_sha256) != 64:
            raise ValueError("invalid Option C0 embedding cache identity")
        value = np.ascontiguousarray(vector, dtype=np.float32)
        if value.ndim != 1 or not value.size or not np.isfinite(value).all():
            raise ValueError("cached Option C0 embedding must be a finite vector")
        payload = value.tobytes()
        self.connection.execute(
            """
            INSERT INTO embeddings (
                stable_key, code_sha256, fingerprint_sha256,
                dtype, dimensions, vector, vector_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stable_key, code_sha256, fingerprint_sha256)
            DO UPDATE SET
                dtype = excluded.dtype,
                dimensions = excluded.dimensions,
                vector = excluded.vector,
                vector_sha256 = excluded.vector_sha256
            """,
            (
                stable_key,
                code_sha256,
                fingerprint_sha256,
                "float32",
                int(value.shape[0]),
                payload,
                sha256_bytes(payload),
            ),
        )

    def commit(self) -> None:
        self.connection.commit()

    def count(self, fingerprint_sha256: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM embeddings WHERE fingerprint_sha256 = ?",
            (fingerprint_sha256,),
        ).fetchone()
        assert row is not None
        return int(row[0])

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def __enter__(self) -> OptionC0EmbeddingCache:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

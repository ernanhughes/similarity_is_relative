"""Local SQLite cache for Option B source code and frozen embeddings."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

CACHE_MODES = ("off", "read-write", "refresh")


class OptionBCache:
    """Versioned local cache keyed by immutable scientific identities."""

    def __init__(self, path: Path, mode: str = "read-write") -> None:
        if mode not in CACHE_MODES:
            raise ValueError(f"unsupported cache mode: {mode}")
        self.path = path
        self.mode = mode
        self.connection: sqlite3.Connection | None = None
        if mode != "off":
            path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(path)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self._create_schema()

    def _create_schema(self) -> None:
        assert self.connection is not None
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS selected_code (
                stable_key TEXT PRIMARY KEY,
                split TEXT NOT NULL,
                code_sha256 TEXT NOT NULL,
                code TEXT NOT NULL,
                dataset_revision TEXT NOT NULL,
                selection_manifest_sha256 TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                stable_key TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                pooling_sha256 TEXT NOT NULL,
                max_length INTEGER NOT NULL,
                dtype TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                embedding_sha256 TEXT NOT NULL,
                PRIMARY KEY (
                    stable_key,
                    model_id,
                    model_revision,
                    pooling_sha256,
                    max_length
                )
            );
            """
        )
        self.connection.commit()

    @property
    def reads_enabled(self) -> bool:
        return self.connection is not None and self.mode == "read-write"

    @property
    def writes_enabled(self) -> bool:
        return self.connection is not None and self.mode in {"read-write", "refresh"}

    def get_code(
        self,
        *,
        stable_key: str,
        code_sha256: str,
        dataset_revision: str,
        selection_manifest_sha256: str,
    ) -> str | None:
        if not self.reads_enabled:
            return None
        assert self.connection is not None
        row = self.connection.execute(
            """
            SELECT code, code_sha256
            FROM selected_code
            WHERE stable_key = ?
              AND dataset_revision = ?
              AND selection_manifest_sha256 = ?
            """,
            (stable_key, dataset_revision, selection_manifest_sha256),
        ).fetchone()
        if row is None:
            return None
        code, stored_sha = row
        actual_sha = hashlib.sha256(code.encode()).hexdigest()
        if stored_sha != code_sha256 or actual_sha != code_sha256:
            return None
        return str(code)

    def put_code(
        self,
        *,
        stable_key: str,
        split: str,
        code_sha256: str,
        code: str,
        dataset_revision: str,
        selection_manifest_sha256: str,
    ) -> None:
        if not self.writes_enabled:
            return
        if hashlib.sha256(code.encode()).hexdigest() != code_sha256:
            raise ValueError("code cache payload does not match code_sha256")
        assert self.connection is not None
        self.connection.execute(
            """
            INSERT INTO selected_code (
                stable_key, split, code_sha256, code,
                dataset_revision, selection_manifest_sha256
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(stable_key) DO UPDATE SET
                split = excluded.split,
                code_sha256 = excluded.code_sha256,
                code = excluded.code,
                dataset_revision = excluded.dataset_revision,
                selection_manifest_sha256 = excluded.selection_manifest_sha256
            """,
            (
                stable_key,
                split,
                code_sha256,
                code,
                dataset_revision,
                selection_manifest_sha256,
            ),
        )

    def get_embedding(
        self,
        *,
        stable_key: str,
        model_id: str,
        model_revision: str,
        pooling_sha256: str,
        max_length: int,
    ) -> np.ndarray | None:
        if not self.reads_enabled:
            return None
        assert self.connection is not None
        row = self.connection.execute(
            """
            SELECT dtype, dimensions, embedding, embedding_sha256
            FROM embeddings
            WHERE stable_key = ?
              AND model_id = ?
              AND model_revision = ?
              AND pooling_sha256 = ?
              AND max_length = ?
            """,
            (stable_key, model_id, model_revision, pooling_sha256, max_length),
        ).fetchone()
        if row is None:
            return None
        dtype, dimensions, payload, expected_sha = row
        if dtype != "float32":
            return None
        raw = bytes(payload)
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            return None
        vector = np.frombuffer(raw, dtype=np.float32).copy()
        if vector.shape != (int(dimensions),):
            return None
        return vector

    def put_embedding(
        self,
        *,
        stable_key: str,
        model_id: str,
        model_revision: str,
        pooling_sha256: str,
        max_length: int,
        vector: np.ndarray,
    ) -> None:
        if not self.writes_enabled:
            return
        value = np.ascontiguousarray(vector, dtype=np.float32)
        if value.ndim != 1:
            raise ValueError("cached embedding must be one-dimensional")
        payload = value.tobytes()
        assert self.connection is not None
        self.connection.execute(
            """
            INSERT INTO embeddings (
                stable_key, model_id, model_revision, pooling_sha256,
                max_length, dtype, dimensions, embedding, embedding_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(
                stable_key, model_id, model_revision, pooling_sha256, max_length
            ) DO UPDATE SET
                dtype = excluded.dtype,
                dimensions = excluded.dimensions,
                embedding = excluded.embedding,
                embedding_sha256 = excluded.embedding_sha256
            """,
            (
                stable_key,
                model_id,
                model_revision,
                pooling_sha256,
                max_length,
                "float32",
                int(value.shape[0]),
                payload,
                hashlib.sha256(payload).hexdigest(),
            ),
        )

    def commit(self) -> None:
        if self.connection is not None:
            self.connection.commit()

    def close(self) -> None:
        if self.connection is not None:
            self.connection.commit()
            self.connection.close()
            self.connection = None

    def __enter__(self) -> OptionBCache:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

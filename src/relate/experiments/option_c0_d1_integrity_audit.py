"""Option C0-D1 visible-role integrity and execution-composition audit.

The audit reconstructs only the already-visible C0 fit and iteration rows. Hidden
C0-selection and C1 row contents remain inaccessible. Repository names from the
published allocation manifest may be used for bounded family-name diagnostics.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import io
import json
import keyword
import os
import platform
import re
import sqlite3
import subprocess
import sys
import time
import tokenize
import uuid
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TextIO

from relate.experiments import option_c0_discovery_runner as discovery_runner

AUDIT_SCHEMA: Final = "option-c0-d1-integrity-audit-v1"
CACHE_SCHEMA: Final = "option-c0-d1-integrity-cache-v1"
CONTEXT_SCHEMA: Final = "option-c0-d1-integrity-context-v1"
DEFAULT_CACHE_PATH: Final = Path(
    ".writer/option-c0/cache/option-c0-d1-integrity-v1.sqlite3"
)
REGISTERED_CANDIDATE_IMPLEMENTATION_COMMIT: Final = (
    "d36436209d95eca555215a83856f042d241a90f4"
)
V1_RUNTIME_SOURCE_COMMIT: Final = "13466976195abeed56367a449ebd5a6678e3ef7e"
V1_RESULT_PUBLICATION_COMMIT: Final = "07cf6fc5ea9c261b10df272215a8afb404612e76"
CANONICAL_SOURCE_IDENTITY_SHA256: Final = (
    "cefedf4e9a4f1a355a1873f2b6ccc3dd6c2babad1093b4c095f6da36c0222c8d"
)
CANONICAL_ALLOCATION_MANIFEST_SHA256: Final = (
    "41e48447171ac2f0553b795f2b3e50dfc5ac389b68fb30607b7d1c496bdb5bfc"
)
CANONICAL_ALLOCATION_CONTEXT_SHA256: Final = (
    "a3ae0b5dcbef0ae8e5056900ba44eeb53b4fd53a20f7cea8d842f67197ab02ed"
)
VISIBLE_ROLES: Final = ("c0_fit", "c0_iteration")
ALLOCATION_ROLES: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
DATASET_SPLITS: Final = ("train", "validation", "test")
CANONICAL_ROLE_COUNTS: Final = {
    "c0_fit": {"repositories": 2117, "rows": 8007},
    "c0_iteration": {"repositories": 1058, "rows": 4110},
    "c0_selection": {"repositories": 545, "rows": 2070},
    "c1_reserve": {"repositories": 1604, "rows": 6357},
}
SIMHASH_BITS: Final = 64
SIMHASH_SHINGLE_SIZE: Final = 5
SIMHASH_BANDS: Final = 4
MAX_EXHAUSTIVE_SIMHASH_RADIUS: Final = 3
CANDIDATE_COMPARISON_BATCH_SIZE: Final = 10_000
INJECT_AFTER_CANDIDATE_BUCKETS: int | None = None
INJECT_AFTER_COMPARISON_BATCHES: int | None = None
INJECT_DURING_COMPARISON_BATCH_TRANSACTION: bool = False
FAMILY_SUFFIXES: Final = frozenset(
    {
        "backup",
        "clone",
        "copy",
        "fork",
        "legacy",
        "mirror",
        "new",
        "old",
        "orig",
        "original",
    }
)
V1_EXECUTION_PATHS: Final = (
    "pyproject.toml",
    "scripts/run-option-c0-discovery-iteration-v1.ps1",
    "src/relate/experiments/option_c0_discovery_runner.py",
    "src/relate/experiments/option_c0_discovery_entrypoint.py",
    "src/relate/experiments/option_c0_diagnostic_entrypoint.py",
    "src/relate/experiments/option_c0_selective_baselines.py",
    "src/relate/experiments/option_c0_diagnostics.py",
    "src/relate/experiments/option_c0_mechanism_harness.py",
    "src/relate/experiments/option_c0_data_firewall.py",
    "src/relate/experiments/option_b_embedding.py",
    "src/relate/experiments/option_b_identity.py",
    "src/relate/experiments/option_b_real_code.py",
    "src/relate/experiments/option_b_selection.py",
    "src/relate/experiments/option_b_selection_resilient.py",
    "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-initial-candidate-plan-v1.json",
    "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-candidate-plan-identity-erratum-v1.json",
    "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-candidate-registry-v1.jsonl",
    "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-discovery-execution-identity-erratum-v1.json",
    "artifacts/canonical/option-b/option-b-external-identity-v1.json",
    "artifacts/canonical/option-b/embedding-reproduction-v2/option-b-embedding-identity-v2-gpu-batch10.json",
    "artifacts/canonical/option-c0/data-firewall-v1/option-c0-repository-allocation-v1.jsonl",
    "artifacts/canonical/option-c0/data-firewall-v1/option-c0-data-firewall-publication-v1.json",
)
V1_PUBLICATION_ARTIFACT_PATHS: Final = (
    "artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-v1.json",
    "artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-iteration-publication-v1.json",
    "artifacts/canonical/option-c0/discovery-v1/option-c0-candidate-registry-v1.jsonl",
    "artifacts/canonical/option-c0/discovery-v1/option-c0-discovery-ledger-v1.jsonl",
)
D1_EXECUTION_PATHS: Final = (
    "pyproject.toml",
    "scripts/run-option-c0-d1-integrity-audit.ps1",
    "src/relate/experiments/option_c0_d1_integrity_audit.py",
    "src/relate/experiments/option_b_embedding.py",
    "src/relate/experiments/option_b_identity.py",
    "src/relate/experiments/option_c0_discovery_runner.py",
    "src/relate/experiments/option_b_selection.py",
    "src/relate/experiments/option_b_selection_resilient.py",
    "src/relate/experiments/option_c0_data_firewall.py",
    "src/relate/experiments/option_c0_diagnostics.py",
    "src/relate/experiments/option_c0_selective_baselines.py",
    "src/relate/experiments/option_c0_mechanism_harness.py",
    "src/relate/experiments/option_b_real_code.py",
    "artifacts/canonical/option-c0/review-v1/option-c0-d-remediation-status-v1.json",
    "artifacts/canonical/option-c0/review-v1/option-c0-d1-audit-contract-v1.json",
)
D1_CONTEXT_SOURCE_PATHS: Final = (
    "src/relate/experiments/option_c0_d1_integrity_audit.py",
    "src/relate/experiments/option_b_embedding.py",
    "src/relate/experiments/option_b_identity.py",
    "src/relate/experiments/option_c0_discovery_runner.py",
    "src/relate/experiments/option_b_selection.py",
    "src/relate/experiments/option_c0_mechanism_harness.py",
    "src/relate/experiments/option_b_real_code.py",
    "src/relate/experiments/option_b_selection_resilient.py",
    "src/relate/experiments/option_c0_data_firewall.py",
    "src/relate/experiments/option_c0_diagnostics.py",
    "src/relate/experiments/option_c0_selective_baselines.py",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _row_payload(row: VisibleAuditRow) -> dict[str, Any]:
    return {
        "role": row.role,
        "repository": row.repository,
        "stable_key": row.stable_key,
        "source_split": row.source_split,
        "path": row.path,
        "function_id": row.function_id,
        "code_sha256": row.code_sha256,
        "normalized_ast_sha256": row.normalized_ast_sha256,
        "token_count": row.token_count,
        "simhash_hex": row.simhash_hex,
    }


def visible_rows_metadata(rows: Sequence[VisibleAuditRow]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (row.role, row.stable_key))
    stable_keys = [row.stable_key for row in ordered]
    if len(stable_keys) != len(set(stable_keys)):
        raise ValueError("visible audit stable keys must be globally unique")
    payload = b"".join((_canonical_json(_row_payload(row)) + "\n").encode() for row in ordered)
    return {
        "row_count": len(ordered),
        "role_counts": {role: sum(row.role == role for row in ordered) for role in VISIBLE_ROLES},
        "repository_counts": {
            role: len({row.repository for row in ordered if row.role == role})
            for role in VISIBLE_ROLES
        },
        "ordered_rows_sha256": _sha256_bytes(payload),
    }


def near_pair_commitment(pairs: Sequence[tuple[str, str, int]]) -> str:
    ordered = sorted((left, right, int(distance)) for left, right, distance in pairs)
    payload = b"".join(
        (
            _canonical_json(
                {"left": left, "right": right, "hamming_distance": distance}
            )
            + "\n"
        ).encode()
        for left, right, distance in ordered
    )
    return _sha256_bytes(payload)


def _duration(seconds: float) -> str:
    if seconds < 0 or not float(seconds) < float("inf"):
        return "unknown"
    value = max(int(round(seconds)), 0)
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes:d}m{secs:02d}s"
    return f"{secs:d}s"


def _package_versions(names: Sequence[str]) -> dict[str, str]:
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


class ProgressReporter:
    """Emit phase and row progress with elapsed time, rate, and ETA."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream or sys.stderr

    def message(self, text: str) -> None:
        print(f"[option-c0-d1] {text}", file=self.stream, flush=True)

    def completed(self, text: str, started: float) -> None:
        self.message(f"{text} complete | elapsed={_duration(time.perf_counter() - started)}")

    def rows(
        self,
        label: str,
        completed: int,
        total: int,
        *,
        started: float,
        cache_hits: int = 0,
        cache_misses: int = 0,
    ) -> None:
        elapsed = max(time.perf_counter() - started, 1e-9)
        rate = completed / elapsed
        remaining = max(total - completed, 0)
        eta = remaining / rate if rate > 0 else float("inf")
        percentage = 100.0 * completed / total if total else 100.0
        self.message(
            f"{label}: {completed:,}/{total:,} ({percentage:5.1f}%) "
            f"| cache={cache_hits:,} hit/{cache_misses:,} miss "
            f"| {rate:,.1f}/s | elapsed={_duration(elapsed)} | eta={_duration(eta)}"
        )


@dataclass(frozen=True)
class VisibleAuditRow:
    role: str
    repository: str
    stable_key: str
    source_split: str
    path: str
    function_id: str
    code_sha256: str
    normalized_ast_sha256: str
    token_count: int
    simhash_hex: str

    def __post_init__(self) -> None:
        if self.role not in VISIBLE_ROLES:
            raise ValueError(f"hidden or unknown row role is forbidden: {self.role}")
        if self.source_split not in DATASET_SPLITS:
            raise ValueError(f"unexpected source split: {self.source_split}")
        if self.token_count < 0:
            raise ValueError("visible audit token_count must be non-negative")
        for field in (self.repository, self.stable_key, self.code_sha256):
            if not field:
                raise ValueError("visible audit row identities must be non-empty")
        for digest in (self.code_sha256, self.normalized_ast_sha256):
            if len(digest) != 64 or any(item not in "0123456789abcdef" for item in digest):
                raise ValueError("visible audit row digests must be SHA-256 hexadecimal")
        if (
            len(self.simhash_hex) != 16
            or any(item not in "0123456789abcdef" for item in self.simhash_hex)
        ):
            raise ValueError("visible audit row SimHash must be 64-bit lowercase hexadecimal")


@dataclass(frozen=True)
class AuditContext:
    payload: dict[str, Any]
    sha256: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> AuditContext:
        value = dict(payload)
        if value.get("schema") != CONTEXT_SCHEMA:
            raise ValueError("unexpected Option C0-D1 audit context schema")
        return cls(value, _sha256_bytes(_canonical_json(value).encode()))


class IntegrityAuditCache:
    """SQLite cache for reconstructed visible rows and completed near-pair scans."""

    def __init__(self, path: Path = DEFAULT_CACHE_PATH) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS contexts (
                context_sha256 TEXT PRIMARY KEY,
                schema_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS visible_rows (
                context_sha256 TEXT NOT NULL,
                role TEXT NOT NULL,
                repository TEXT NOT NULL,
                stable_key TEXT NOT NULL,
                source_split TEXT NOT NULL,
                path TEXT NOT NULL,
                function_id TEXT NOT NULL,
                code_sha256 TEXT NOT NULL,
                normalized_ast_sha256 TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                simhash_hex TEXT NOT NULL,
                PRIMARY KEY (context_sha256, stable_key),
                FOREIGN KEY (context_sha256) REFERENCES contexts(context_sha256)
            );

            CREATE INDEX IF NOT EXISTS visible_rows_code
                ON visible_rows(context_sha256, code_sha256);
            CREATE INDEX IF NOT EXISTS visible_rows_ast
                ON visible_rows(context_sha256, normalized_ast_sha256);
            CREATE INDEX IF NOT EXISTS visible_rows_role
                ON visible_rows(context_sha256, role);

            CREATE TABLE IF NOT EXISTS near_pairs (
                context_sha256 TEXT NOT NULL,
                left_key TEXT NOT NULL,
                right_key TEXT NOT NULL,
                hamming_distance INTEGER NOT NULL,
                PRIMARY KEY (context_sha256, left_key, right_key),
                FOREIGN KEY (context_sha256) REFERENCES contexts(context_sha256)
            );

            CREATE TABLE IF NOT EXISTS candidate_pairs (
                context_sha256 TEXT NOT NULL,
                left_key TEXT NOT NULL,
                right_key TEXT NOT NULL,
                PRIMARY KEY (context_sha256, left_key, right_key),
                FOREIGN KEY (context_sha256) REFERENCES contexts(context_sha256)
            );

            CREATE TABLE IF NOT EXISTS phase_checkpoints (
                context_sha256 TEXT NOT NULL,
                phase_name TEXT NOT NULL,
                cursor_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                PRIMARY KEY (context_sha256, phase_name),
                FOREIGN KEY (context_sha256) REFERENCES contexts(context_sha256)
            );

            CREATE TABLE IF NOT EXISTS phases (
                context_sha256 TEXT NOT NULL,
                phase_name TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                PRIMARY KEY (context_sha256, phase_name),
                FOREIGN KEY (context_sha256) REFERENCES contexts(context_sha256)
            );
            """
        )
        self.verify_pragmas()
        self.connection.commit()

    def __enter__(self) -> IntegrityAuditCache:
        return self

    def __exit__(self, *_: object) -> None:
        self.connection.close()

    def register_context(self, context: AuditContext) -> None:
        payload_json = _canonical_json(context.payload)
        self.connection.execute(
            """
            INSERT INTO contexts(context_sha256, schema_id, payload_json)
            VALUES (?, ?, ?)
            ON CONFLICT(context_sha256) DO NOTHING
            """,
            (context.sha256, CACHE_SCHEMA, payload_json),
        )
        row = self.connection.execute(
            """
            SELECT schema_id, payload_json
            FROM contexts
            WHERE context_sha256 = ?
            """,
            (context.sha256,),
        ).fetchone()
        if row != (CACHE_SCHEMA, payload_json):
            raise ValueError("integrity cache context collision or corruption")
        self.connection.commit()

    def verify_pragmas(self) -> dict[str, Any]:
        journal_mode = str(self.connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        synchronous = int(self.connection.execute("PRAGMA synchronous").fetchone()[0])
        foreign_keys = int(self.connection.execute("PRAGMA foreign_keys").fetchone()[0])
        result = {
            "journal_mode": journal_mode,
            "synchronous": synchronous,
            "foreign_keys": foreign_keys,
            "synchronous_full": synchronous == 2,
        }
        if journal_mode != "wal" or synchronous != 2 or foreign_keys != 1:
            raise ValueError("integrity cache SQLite pragmas are not enforced")
        return result

    def visible_row_count(self, context_sha256: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM visible_rows WHERE context_sha256 = ?",
            (context_sha256,),
        ).fetchone()
        return int(row[0])

    def clear_visible_rows(self, context_sha256: str) -> None:
        self.connection.execute(
            "DELETE FROM near_pairs WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.execute(
            "DELETE FROM candidate_pairs WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.execute(
            "DELETE FROM phase_checkpoints WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.execute(
            "DELETE FROM phases WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.execute(
            "DELETE FROM visible_rows WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.commit()

    def put_visible_rows(self, context_sha256: str, rows: Sequence[VisibleAuditRow]) -> None:
        self.connection.executemany(
            """
            INSERT INTO visible_rows(
                context_sha256, role, repository, stable_key, source_split,
                path, function_id, code_sha256, normalized_ast_sha256,
                token_count, simhash_hex
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(context_sha256, stable_key) DO UPDATE SET
                role = excluded.role,
                repository = excluded.repository,
                source_split = excluded.source_split,
                path = excluded.path,
                function_id = excluded.function_id,
                code_sha256 = excluded.code_sha256,
                normalized_ast_sha256 = excluded.normalized_ast_sha256,
                token_count = excluded.token_count,
                simhash_hex = excluded.simhash_hex
            """,
            [
                (
                    context_sha256,
                    row.role,
                    row.repository,
                    row.stable_key,
                    row.source_split,
                    row.path,
                    row.function_id,
                    row.code_sha256,
                    row.normalized_ast_sha256,
                    row.token_count,
                    row.simhash_hex,
                )
                for row in rows
            ],
        )
        self.connection.commit()

    def load_visible_rows(self, context_sha256: str) -> tuple[VisibleAuditRow, ...]:
        values = self.connection.execute(
            """
            SELECT role, repository, stable_key, source_split, path, function_id,
                   code_sha256, normalized_ast_sha256, token_count, simhash_hex
            FROM visible_rows
            WHERE context_sha256 = ?
            ORDER BY role, stable_key
            """,
            (context_sha256,),
        ).fetchall()
        return tuple(VisibleAuditRow(*value) for value in values)

    def phase_complete(self, context_sha256: str, phase_name: str) -> bool:
        return self.phase_metadata(context_sha256, phase_name) is not None

    def phase_metadata(
        self,
        context_sha256: str,
        phase_name: str,
    ) -> dict[str, Any] | None:
        state = self.phase_state(context_sha256, phase_name)
        if state is None:
            return None
        status, value = state
        return value if status == "COMPLETE" else None

    def phase_state(
        self,
        context_sha256: str,
        phase_name: str,
    ) -> tuple[str, dict[str, Any]] | None:
        row = self.connection.execute(
            """
            SELECT status, metadata_json FROM phases
            WHERE context_sha256 = ? AND phase_name = ?
            """,
            (context_sha256, phase_name),
        ).fetchone()
        if row is None:
            return None
        status, metadata_json = row
        value = json.loads(str(metadata_json))
        if not isinstance(value, dict):
            raise ValueError("integrity cache phase metadata is corrupt")
        return str(status), value

    def mark_phase_complete(
        self,
        context_sha256: str,
        phase_name: str,
        metadata: Mapping[str, Any],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO phases(context_sha256, phase_name, status, metadata_json)
            VALUES (?, ?, 'COMPLETE', ?)
            ON CONFLICT(context_sha256, phase_name) DO UPDATE SET
                status = excluded.status,
                metadata_json = excluded.metadata_json
            """,
            (context_sha256, phase_name, _canonical_json(metadata)),
        )
        self.connection.commit()

    def set_phase_status(
        self,
        context_sha256: str,
        phase_name: str,
        status: str,
        metadata: Mapping[str, Any],
    ) -> None:
        if status not in {"IN_PROGRESS", "COMPLETE", "TRUNCATED", "CORRUPT"}:
            raise ValueError(f"unexpected phase status: {status}")
        self.connection.execute(
            """
            INSERT INTO phases(context_sha256, phase_name, status, metadata_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(context_sha256, phase_name) DO UPDATE SET
                status = excluded.status,
                metadata_json = excluded.metadata_json
            """,
            (context_sha256, phase_name, status, _canonical_json(metadata)),
        )
        self.connection.commit()

    def load_phase_checkpoint(
        self,
        context_sha256: str,
        phase_name: str,
    ) -> tuple[str, dict[str, Any]] | None:
        row = self.connection.execute(
            """
            SELECT cursor_text, metadata_json
            FROM phase_checkpoints
            WHERE context_sha256 = ? AND phase_name = ?
            """,
            (context_sha256, phase_name),
        ).fetchone()
        if row is None:
            return None
        cursor, metadata_json = row
        metadata = json.loads(str(metadata_json))
        if not isinstance(metadata, dict):
            raise ValueError("phase checkpoint metadata is corrupt")
        return str(cursor), metadata

    def save_phase_checkpoint(
        self,
        context_sha256: str,
        phase_name: str,
        cursor: str,
        metadata: Mapping[str, Any],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO phase_checkpoints(
                context_sha256, phase_name, cursor_text, metadata_json
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(context_sha256, phase_name) DO UPDATE SET
                cursor_text = excluded.cursor_text,
                metadata_json = excluded.metadata_json
            """,
            (context_sha256, phase_name, cursor, _canonical_json(metadata)),
        )
        self.connection.commit()

    def clear_phase_checkpoint(self, context_sha256: str, phase_name: str) -> None:
        self.connection.execute(
            "DELETE FROM phase_checkpoints WHERE context_sha256 = ? AND phase_name = ?",
            (context_sha256, phase_name),
        )
        self.connection.commit()

    def clear_near_pairs(self, context_sha256: str) -> None:
        self.connection.execute(
            "DELETE FROM near_pairs WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.execute(
            "DELETE FROM candidate_pairs WHERE context_sha256 = ?",
            (context_sha256,),
        )
        self.connection.execute(
            """
            DELETE FROM phase_checkpoints
            WHERE context_sha256 = ? AND phase_name IN (
                'candidate_generation', 'pair_comparison'
            )
            """,
            (context_sha256,),
        )
        self.connection.execute(
            """
            DELETE FROM phases
            WHERE context_sha256 = ? AND phase_name = 'near_duplicate_scan'
            """,
            (context_sha256,),
        )
        self.connection.commit()

    def put_candidate_pairs(
        self,
        context_sha256: str,
        pairs: Sequence[tuple[str, str]],
        *,
        limit: int | None = None,
    ) -> None:
        selected = list(pairs)
        if limit is not None:
            remaining = max(limit - self.count_candidate_pairs(context_sha256), 0)
            selected = selected[:remaining]
        if not selected:
            return
        self.connection.executemany(
            """
            INSERT INTO candidate_pairs(context_sha256, left_key, right_key)
            VALUES (?, ?, ?)
            ON CONFLICT(context_sha256, left_key, right_key) DO NOTHING
            """,
            [(context_sha256, left, right) for left, right in selected],
        )
        self.connection.commit()

    def count_candidate_pairs(self, context_sha256: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM candidate_pairs WHERE context_sha256 = ?",
            (context_sha256,),
        ).fetchone()
        return int(row[0])

    def candidate_pair_exists(self, context_sha256: str, left: str, right: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1 FROM candidate_pairs
            WHERE context_sha256 = ? AND left_key = ? AND right_key = ?
            """,
            (context_sha256, left, right),
        ).fetchone()
        return row is not None

    def candidate_pair_commitment(self, context_sha256: str) -> tuple[int, str]:
        digest = hashlib.sha256()
        count = 0
        cursor_left = ""
        cursor_right = ""
        while True:
            batch = self.fetch_candidate_pair_batch(
                context_sha256,
                after_left=cursor_left,
                after_right=cursor_right,
                limit=10_000,
            )
            if not batch:
                break
            for left, right in batch:
                digest.update((_canonical_json({"left": left, "right": right}) + "\n").encode())
                count += 1
            cursor_left, cursor_right = batch[-1]
        return count, digest.hexdigest()

    def fetch_candidate_pair_batch(
        self,
        context_sha256: str,
        *,
        after_left: str,
        after_right: str,
        limit: int,
    ) -> tuple[tuple[str, str], ...]:
        values = self.connection.execute(
            """
            SELECT left_key, right_key
            FROM candidate_pairs
            WHERE context_sha256 = ?
              AND (left_key > ? OR (left_key = ? AND right_key > ?))
            ORDER BY left_key, right_key
            LIMIT ?
            """,
            (context_sha256, after_left, after_left, after_right, limit),
        ).fetchall()
        return tuple((str(left), str(right)) for left, right in values)

    def put_near_pairs(
        self,
        context_sha256: str,
        pairs: Sequence[tuple[str, str, int]],
    ) -> None:
        self.connection.executemany(
            """
            INSERT INTO near_pairs(
                context_sha256, left_key, right_key, hamming_distance
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(context_sha256, left_key, right_key) DO UPDATE SET
                hamming_distance = excluded.hamming_distance
            """,
            [
                (context_sha256, left_key, right_key, distance)
                for left_key, right_key, distance in pairs
            ],
        )
        self.connection.commit()

    def count_near_pairs(self, context_sha256: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM near_pairs WHERE context_sha256 = ?",
            (context_sha256,),
        ).fetchone()
        return int(row[0])

    def commit_comparison_batch(
        self,
        context_sha256: str,
        *,
        cursor: str,
        near_pairs: Sequence[tuple[str, str, int]],
        metadata: Mapping[str, Any],
    ) -> int:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.executemany(
                """
                INSERT INTO near_pairs(
                    context_sha256, left_key, right_key, hamming_distance
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(context_sha256, left_key, right_key) DO UPDATE SET
                    hamming_distance = excluded.hamming_distance
                """,
                [
                    (context_sha256, left_key, right_key, distance)
                    for left_key, right_key, distance in near_pairs
                ],
            )
            if INJECT_DURING_COMPARISON_BATCH_TRANSACTION:
                raise RuntimeError("injected comparison-batch transaction interruption")
            row = self.connection.execute(
                "SELECT COUNT(*) FROM near_pairs WHERE context_sha256 = ?",
                (context_sha256,),
            ).fetchone()
            near_pair_count = int(row[0])
            checkpoint_metadata = {
                **metadata,
                "near_pairs_found": near_pair_count,
                "near_pair_count": near_pair_count,
            }
            self.connection.execute(
                """
                INSERT INTO phase_checkpoints(
                    context_sha256, phase_name, cursor_text, metadata_json
                ) VALUES (?, 'pair_comparison', ?, ?)
                ON CONFLICT(context_sha256, phase_name) DO UPDATE SET
                    cursor_text = excluded.cursor_text,
                    metadata_json = excluded.metadata_json
                """,
                (context_sha256, cursor, _canonical_json(checkpoint_metadata)),
            )
            self.connection.execute("COMMIT")
            return near_pair_count
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def load_near_pairs(self, context_sha256: str) -> tuple[tuple[str, str, int], ...]:
        values = self.connection.execute(
            """
            SELECT left_key, right_key, hamming_distance
            FROM near_pairs
            WHERE context_sha256 = ?
            ORDER BY hamming_distance, left_key, right_key
            """,
            (context_sha256,),
        ).fetchall()
        return tuple((str(left), str(right), int(distance)) for left, right, distance in values)


def _normalised_code_tokens(code: str) -> tuple[str, ...]:
    values: list[str] = []
    try:
        stream = tokenize.generate_tokens(io.StringIO(code).readline)
        for item in stream:
            if item.type == tokenize.NAME:
                values.append(item.string if keyword.iskeyword(item.string) else "NAME")
            elif item.type == tokenize.NUMBER:
                values.append("NUMBER")
            elif item.type == tokenize.STRING:
                values.append("STRING")
            elif item.type == tokenize.OP:
                values.append(item.string)
    except (IndentationError, tokenize.TokenError):
        values = re.findall(r"[A-Za-z_]+|\d+|[^\w\s]", code)
    return tuple(values)


def token_simhash(code: str, *, shingle_size: int = SIMHASH_SHINGLE_SIZE) -> str:
    """Return a deterministic 64-bit SimHash over normalised token shingles."""

    tokens = _normalised_code_tokens(code)
    if not tokens:
        tokens = ("<empty>",)
    width = max(1, min(shingle_size, len(tokens)))
    shingles = Counter(
        "\0".join(tokens[index : index + width])
        for index in range(len(tokens) - width + 1)
    )
    weights = [0] * SIMHASH_BITS
    for shingle, frequency in shingles.items():
        value = int.from_bytes(hashlib.sha256(shingle.encode()).digest()[:8], "big")
        for bit in range(SIMHASH_BITS):
            weights[bit] += frequency if value & (1 << bit) else -frequency
    fingerprint = sum(1 << bit for bit, weight in enumerate(weights) if weight >= 0)
    return f"{fingerprint:016x}"


def simhash_hamming(left: str, right: str) -> int:
    if len(left) != 16 or len(right) != 16:
        raise ValueError("SimHash values must be 64-bit hexadecimal")
    return (int(left, 16) ^ int(right, 16)).bit_count()


def repository_signatures(repository: str) -> tuple[str, str]:
    """Return exact-normalised and suffix-stripped repository-name signatures."""

    basename = repository.rsplit("/", 1)[-1].lower()
    tokens = re.findall(r"[a-z0-9]+", basename)
    exact = "-".join(tokens)
    family = list(tokens)
    while family and (
        family[-1] in FAMILY_SUFFIXES
        or family[-1].isdigit()
        or re.fullmatch(r"v\d+", family[-1]) is not None
    ):
        family.pop()
    return exact, "-".join(family) or exact


def _load_assignments(path: Path) -> tuple[dict[str, Any], ...]:
    assignments: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        role = str(value.get("role", ""))
        repository = str(value.get("repository", ""))
        if role not in ALLOCATION_ROLES or not repository:
            raise ValueError("allocation manifest contains an invalid role or repository")
        assignments.append(dict(value))
    if not assignments:
        raise ValueError("allocation manifest is empty")
    repositories = [str(item["repository"]) for item in assignments]
    if len(repositories) != len(set(repositories)):
        raise ValueError("allocation manifest repeats a repository")
    return tuple(assignments)


def validate_canonical_inputs(
    *,
    identity_path: Path,
    allocation_path: Path,
    firewall_dir: Path,
    assignments: Sequence[Mapping[str, Any]],
    allow_test_fixture_inputs: bool,
) -> dict[str, Any]:
    source_sha = _sha256_file(identity_path)
    allocation_sha = _sha256_file(allocation_path)
    publication_path = firewall_dir / "option-c0-data-firewall-publication-v1.json"
    allocation_context = ""
    if publication_path.is_file():
        publication = json.loads(publication_path.read_text(encoding="utf-8"))
        allocation_context = str(publication.get("allocation_context_sha256", ""))
    role_counts: dict[str, dict[str, int]] = {}
    owners: dict[str, str] = {}
    for item in assignments:
        role = str(item["role"])
        repository = str(item["repository"])
        if repository in owners:
            raise ValueError(f"allocation repository appears more than once: {repository}")
        owners[repository] = role
        counts = role_counts.setdefault(role, {"repositories": 0, "rows": 0})
        counts["repositories"] += 1
        counts["rows"] += int(item["row_count"])
    missing_roles = sorted(set(ALLOCATION_ROLES) - set(role_counts))
    if missing_roles:
        raise ValueError(f"allocation manifest is missing roles: {missing_roles}")

    failures = []
    if source_sha != CANONICAL_SOURCE_IDENTITY_SHA256:
        failures.append("source identity SHA-256 mismatch")
    if allocation_sha != CANONICAL_ALLOCATION_MANIFEST_SHA256:
        failures.append("allocation manifest SHA-256 mismatch")
    if allocation_context != CANONICAL_ALLOCATION_CONTEXT_SHA256:
        failures.append("allocation context SHA-256 mismatch")
    if role_counts != CANONICAL_ROLE_COUNTS:
        failures.append("allocation role counts mismatch")
    if failures and not allow_test_fixture_inputs:
        raise ValueError("canonical input validation failed: " + "; ".join(failures))
    return {
        "source_identity_sha256": source_sha,
        "allocation_manifest_sha256": allocation_sha,
        "allocation_context_sha256": allocation_context,
        "role_counts": role_counts,
        "canonical_inputs_verified": not failures,
        "test_fixture_override_used": bool(failures and allow_test_fixture_inputs),
        "failures": failures,
    }


def validate_d1_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_id") != "option-c0-d1-audit-contract-v1":
        raise ValueError("unexpected D1 audit contract schema")
    for field in ("scientific_result_observed", "mechanism_result_observed"):
        if value.get(field) is not False:
            raise ValueError(f"D1 contract must keep {field}=false")
    if value.get("hidden_row_content_accessed") is not False:
        raise ValueError("D1 contract must keep hidden_row_content_accessed=false")
    if tuple(value.get("visible_row_roles", ())) != VISIBLE_ROLES:
        raise ValueError("D1 contract visible roles changed")
    commits = value.get("v1_commit_identities", {})
    expected = {
        "registered_candidate_implementation_commit": (
            REGISTERED_CANDIDATE_IMPLEMENTATION_COMMIT
        ),
        "v1_runtime_source_commit": V1_RUNTIME_SOURCE_COMMIT,
        "v1_result_publication_commit": V1_RESULT_PUBLICATION_COMMIT,
    }
    if commits != expected:
        raise ValueError("D1 contract commit identities changed")
    return {
        "path": str(path).replace("\\", "/"),
        "sha256": _sha256_file(path),
        "validated": True,
    }


def _source_manifest_hash(repo_root: Path, ref: str, paths: Sequence[str]) -> str:
    entries = _hash_paths_at_ref(repo_root, ref, paths, ProgressReporter(io.StringIO()))
    return _sha256_bytes(_canonical_json(entries).encode())


def _audit_context(
    identity_path: Path,
    allocation_path: Path,
    *,
    near_hamming: int,
    near_max_bucket: int,
    near_max_candidate_pairs: int,
    near_max_pairs: int,
    repo_root: Path = Path("."),
) -> AuditContext:
    d1_path = Path(__file__)
    runner_path = Path(discovery_runner.__file__ or "")
    payload = {
        "schema": CONTEXT_SCHEMA,
        "source_identity_sha256": _sha256_file(identity_path),
        "allocation_manifest_sha256": _sha256_file(allocation_path),
        "canonical_source_identity_sha256": CANONICAL_SOURCE_IDENTITY_SHA256,
        "canonical_allocation_manifest_sha256": CANONICAL_ALLOCATION_MANIFEST_SHA256,
        "canonical_allocation_context_sha256": CANONICAL_ALLOCATION_CONTEXT_SHA256,
        "d1_implementation_source_sha256": _sha256_file(d1_path),
        "visible_reconstruction_source_sha256": _sha256_file(runner_path),
        "context_source_manifest_sha256": _source_manifest_hash(
            repo_root,
            "HEAD",
            D1_CONTEXT_SOURCE_PATHS,
        ),
        "python_version": platform.python_version(),
        "visible_roles": list(VISIBLE_ROLES),
        "normalisation_algorithm": "python-token-normalisation-v1",
        "normalisation_algorithm_identity": _sha256_bytes(
            "\n".join(
                (
                    "python-token-normalisation-v1",
                    "keywords preserved",
                    "identifiers->NAME",
                    "numbers->NUMBER",
                    "strings->STRING",
                    "operators preserved",
                )
            ).encode()
        ),
        "near_duplicate_algorithm": "normalised-token-shingle-simhash-banding-v1",
        "near_duplicate_algorithm_identity": _sha256_bytes(
            "\n".join(
                (
                    "normalised-token-shingle-simhash-banding-v1",
                    f"simhash_bits={SIMHASH_BITS}",
                    f"simhash_shingle_size={SIMHASH_SHINGLE_SIZE}",
                    f"simhash_bands={SIMHASH_BANDS}",
                )
            ).encode()
        ),
        "simhash_bits": SIMHASH_BITS,
        "simhash_shingle_size": SIMHASH_SHINGLE_SIZE,
        "simhash_bands": SIMHASH_BANDS,
        "cache_schema_version": CACHE_SCHEMA,
        "near_hamming": near_hamming,
        "near_max_bucket": near_max_bucket,
        "near_max_candidate_pairs": near_max_candidate_pairs,
        "near_max_pairs": near_max_pairs,
        "candidate_comparison_batch_size": CANDIDATE_COMPARISON_BATCH_SIZE,
    }
    return AuditContext.from_payload(payload)


def _row_from_visible(item: Any) -> VisibleAuditRow:
    record = item.record
    return VisibleAuditRow(
        role=str(item.role),
        repository=str(record.repository),
        stable_key=str(record.stable_key),
        source_split=str(getattr(record, "split", getattr(record, "source_split", ""))),
        path=str(record.path),
        function_id=str(record.function_id),
        code_sha256=str(record.code_sha256),
        normalized_ast_sha256=str(record.normalized_ast_sha256),
        token_count=int(record.token_count),
        simhash_hex=token_simhash(str(record.code)),
    )


def load_or_reconstruct_visible_rows(
    identity_path: Path,
    firewall_dir: Path,
    assignments: Sequence[Mapping[str, Any]],
    *,
    cache: IntegrityAuditCache,
    context: AuditContext,
    reporter: ProgressReporter,
) -> tuple[tuple[VisibleAuditRow, ...], dict[str, Any]]:
    expected = sum(
        int(item["row_count"])
        for item in assignments
        if str(item["role"]) in VISIBLE_ROLES
    )
    cached = cache.visible_row_count(context.sha256)
    phase_metadata = cache.phase_metadata(context.sha256, "visible_rows")
    if cached == expected and phase_metadata is not None:
        started = time.perf_counter()
        reporter.message(f"visible-row cache: {cached:,} hit/0 miss")
        rows = cache.load_visible_rows(context.sha256)
        actual_metadata = visible_rows_metadata(rows)
        if actual_metadata != phase_metadata:
            reporter.message("discarding visible-row cache with mismatched commitment")
            cache.clear_visible_rows(context.sha256)
        else:
            reporter.completed("visible-row cache load", started)
            return rows, {
                "cache_hits": cached,
                "cache_misses": 0,
                "reconstructed": False,
                "rows": len(rows),
                "phase_commitment": actual_metadata,
            }
    if cached:
        reporter.message(
            f"discarding incomplete visible-row cache: {cached:,}/{expected:,} rows"
        )
        cache.clear_visible_rows(context.sha256)

    started = time.perf_counter()
    reporter.message("reconstructing visible C0 fit and iteration rows")
    visible, reconstruction = discovery_runner.reconstruct_visible_records(
        identity_path,
        firewall_dir,
    )
    reporter.completed("visible-row source reconstruction", started)
    rows = tuple(_row_from_visible(item) for item in visible)
    if len(rows) != expected:
        raise ValueError(
            f"visible audit row count differs from allocation: {len(rows)} != {expected}"
        )
    expected_counts = {
        role: sum(int(item["row_count"]) for item in assignments if item["role"] == role)
        for role in VISIBLE_ROLES
    }
    observed_metadata = visible_rows_metadata(rows)
    if observed_metadata["role_counts"] != expected_counts:
        raise ValueError("visible audit role counts differ from allocation")

    write_started = time.perf_counter()
    batch_size = 500
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        cache.put_visible_rows(context.sha256, batch)
        reporter.rows(
            "cache visible rows",
            min(start + len(batch), len(rows)),
            len(rows),
            started=write_started,
            cache_hits=0,
            cache_misses=len(rows),
        )
    cache.mark_phase_complete(context.sha256, "visible_rows", observed_metadata)
    return rows, {
        "cache_hits": 0,
        "cache_misses": len(rows),
        "reconstructed": True,
        "rows": len(rows),
        "phase_commitment": observed_metadata,
        "source_reconstruction": reconstruction,
    }


def exact_overlap_report(
    rows: Sequence[VisibleAuditRow],
    *,
    field: str,
    sample_limit: int = 20,
) -> dict[str, Any]:
    if field not in {"code_sha256", "normalized_ast_sha256"}:
        raise ValueError("exact overlap field is not supported")
    owners: dict[str, list[VisibleAuditRow]] = defaultdict(list)
    for row in rows:
        owners[str(getattr(row, field))].append(row)
    repeated = [items for items in owners.values() if len(items) > 1]
    cross_role = [items for items in repeated if len({item.role for item in items}) > 1]
    cross_role.sort(key=lambda items: (-len(items), str(getattr(items[0], field))))
    involved_rows = {item.stable_key for items in cross_role for item in items}
    involved_repositories = {item.repository for items in cross_role for item in items}
    samples = []
    for items in cross_role[:sample_limit]:
        samples.append(
            {
                "sha256": str(getattr(items[0], field)),
                "rows": len(items),
                "roles": sorted({item.role for item in items}),
                "repositories": sorted({item.repository for item in items})[:20],
                "stable_keys": sorted(item.stable_key for item in items)[:20],
            }
        )
    return {
        "field": field,
        "unique_hashes": len(owners),
        "repeated_hashes_any_role": len(repeated),
        "cross_role_hashes": len(cross_role),
        "cross_role_rows": len(involved_rows),
        "cross_role_repositories": len(involved_repositories),
        "max_cross_role_multiplicity": max((len(items) for items in cross_role), default=0),
        "samples": samples,
    }


def repository_family_report(
    assignments: Sequence[Mapping[str, Any]],
    *,
    sample_limit: int = 30,
) -> dict[str, Any]:
    exact_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    family_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for item in assignments:
        role = str(item["role"])
        repository = str(item["repository"])
        exact, family = repository_signatures(repository)
        if exact:
            exact_groups[exact].append((role, repository))
        if family:
            family_groups[family].append((role, repository))

    def cross_role(groups: Mapping[str, Sequence[tuple[str, str]]]) -> list[dict[str, Any]]:
        result = []
        for signature, owners in groups.items():
            roles = {role for role, _ in owners}
            repositories = sorted({repository for _, repository in owners})
            if len(roles) < 2 or len(repositories) < 2:
                continue
            result.append(
                {
                    "signature": signature,
                    "roles": sorted(roles),
                    "total_repository_count": len(repositories),
                    "repositories": repositories[:sample_limit],
                    "truncated": len(repositories) > sample_limit,
                }
            )
        return sorted(
            result,
            key=lambda item: (-int(item["total_repository_count"]), item["signature"]),
        )

    exact_cross = cross_role(exact_groups)
    family_cross = cross_role(family_groups)
    return {
        "uses_published_repository_names_only": True,
        "hidden_row_content_accessed": False,
        "heuristic_candidates_are_not_proof_of_relatedness": True,
        "exact_basename_cross_role_groups": len(exact_cross),
        "suffix_stripped_cross_role_groups": len(family_cross),
        "exact_basename_samples": exact_cross[:sample_limit],
        "suffix_stripped_samples": family_cross[:sample_limit],
    }


def _simhash_band_values(value: str) -> tuple[tuple[int, int], ...]:
    number = int(value, 16)
    width = SIMHASH_BITS // SIMHASH_BANDS
    mask = (1 << width) - 1
    return tuple((band, (number >> (band * width)) & mask) for band in range(SIMHASH_BANDS))


def _compute_near_pairs(
    rows: Sequence[VisibleAuditRow],
    *,
    cache: IntegrityAuditCache,
    context_sha256: str,
    max_hamming: int,
    max_bucket: int,
    max_candidate_pairs: int,
    max_pairs: int,
    reporter: ProgressReporter,
) -> tuple[tuple[tuple[str, str, int], ...], dict[str, Any]]:
    by_key = {row.stable_key: row for row in rows}
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        for band in _simhash_band_values(row.simhash_hex):
            buckets[band].append(index - 1)
        if index % 1000 == 0 or index == len(rows):
            reporter.rows("index SimHash bands", index, len(rows), started=started)

    ordered_buckets = sorted(buckets.items())
    checkpoint = cache.load_phase_checkpoint(context_sha256, "candidate_generation")
    candidate_generation_resumed = checkpoint is not None
    resume_bucket = ""
    resume_bucket_position = 0
    oversized_buckets = 0
    candidate_buckets_processed = 0
    if checkpoint is not None:
        resume_bucket, generation_meta = checkpoint
        oversized_buckets = int(generation_meta.get("oversized_buckets_skipped", 0))
        candidate_buckets_processed = int(generation_meta.get("candidate_buckets_processed", 0))
        resume_bucket_position = int(generation_meta.get("last_completed_bucket_position", 0))
        if resume_bucket_position:
            if resume_bucket_position < 1 or resume_bucket_position > len(ordered_buckets):
                raise ValueError("candidate-generation checkpoint bucket position is corrupt")
            expected_bucket = ordered_buckets[resume_bucket_position - 1][0]
            stored_band = int(generation_meta.get("last_completed_band", -1))
            stored_value = int(generation_meta.get("last_completed_band_value", -1))
            if (stored_band, stored_value) != expected_bucket:
                raise ValueError("candidate-generation checkpoint bucket key is corrupt")
    candidate_generation_truncated = False
    candidate_limit_reached = cache.count_candidate_pairs(context_sha256) >= max_candidate_pairs
    candidate_generation_new_pairs = 0
    candidate_generation_cache_hits = cache.count_candidate_pairs(context_sha256)
    scan_started = time.perf_counter()
    cache.set_phase_status(
        context_sha256,
        "candidate_generation",
        "IN_PROGRESS",
        {
            "candidate_buckets_total": len(ordered_buckets),
            "candidate_buckets_processed": candidate_buckets_processed,
        },
    )
    for position, (bucket_key, indices) in enumerate(ordered_buckets, start=1):
        bucket_text = f"{bucket_key[0]}:{bucket_key[1]}"
        if position <= resume_bucket_position:
            continue
        candidate_buckets_processed = position
        if len(indices) > max_bucket:
            oversized_buckets += 1
        else:
            staged: list[tuple[str, str]] = []
            for left_position in range(len(indices)):
                left_index = indices[left_position]
                left = rows[left_index]
                for right_index in indices[left_position + 1 :]:
                    right = rows[right_index]
                    if left.role == right.role or left.repository == right.repository:
                        continue
                    left_key, right_key = sorted((left.stable_key, right.stable_key))
                    if candidate_limit_reached:
                        if not cache.candidate_pair_exists(context_sha256, left_key, right_key):
                            candidate_generation_truncated = True
                            break
                        continue
                    staged.append((left_key, right_key))
                    if len(staged) >= 1000:
                        before = cache.count_candidate_pairs(context_sha256)
                        cache.put_candidate_pairs(
                            context_sha256,
                            staged,
                            limit=max_candidate_pairs,
                        )
                        after = cache.count_candidate_pairs(context_sha256)
                        candidate_generation_new_pairs += after - before
                        staged = []
                        if after >= max_candidate_pairs:
                            candidate_limit_reached = True
                            break
                if candidate_generation_truncated:
                    break
            if staged and not candidate_generation_truncated:
                before = cache.count_candidate_pairs(context_sha256)
                cache.put_candidate_pairs(context_sha256, staged, limit=max_candidate_pairs)
                after = cache.count_candidate_pairs(context_sha256)
                candidate_generation_new_pairs += after - before
                if after >= max_candidate_pairs:
                    candidate_limit_reached = True
        generation_checkpoint = {
            "candidate_buckets_total": len(ordered_buckets),
            "candidate_buckets_processed": candidate_buckets_processed,
            "last_completed_bucket_position": position,
            "last_completed_band": bucket_key[0],
            "last_completed_band_value": bucket_key[1],
            "last_completed_bucket_display": bucket_text,
            "candidate_pair_count": cache.count_candidate_pairs(context_sha256),
            "oversized_buckets_skipped": oversized_buckets,
            "candidate_generation_truncated": candidate_generation_truncated,
            "candidate_limit_reached": candidate_limit_reached,
        }
        cache.save_phase_checkpoint(
            context_sha256,
            "candidate_generation",
            bucket_text,
            generation_checkpoint,
        )
        if INJECT_AFTER_CANDIDATE_BUCKETS is not None and (
            candidate_buckets_processed >= INJECT_AFTER_CANDIDATE_BUCKETS
        ):
            raise RuntimeError("injected candidate-generation interruption")
        if position % 250 == 0 or position == len(ordered_buckets):
            reporter.rows(
                "scan SimHash buckets",
                position,
                len(ordered_buckets),
                started=scan_started,
            )
        if candidate_generation_truncated:
            break

    candidate_pair_count, candidate_pair_sha = cache.candidate_pair_commitment(context_sha256)
    generation_complete = (
        candidate_buckets_processed == len(ordered_buckets) and not candidate_generation_truncated
    )
    generation_status = "COMPLETE" if generation_complete else "TRUNCATED"
    generation_metadata = {
        "candidate_buckets_total": len(ordered_buckets),
        "candidate_buckets_processed": candidate_buckets_processed,
        "oversized_buckets_skipped": oversized_buckets,
        "candidate_pair_count": candidate_pair_count,
        "ordered_candidate_pair_sha256": candidate_pair_sha,
        "candidate_generation_complete": generation_complete,
        "candidate_generation_truncated": candidate_generation_truncated,
        "candidate_limit_reached": candidate_limit_reached,
        "candidate_generation_resumed": candidate_generation_resumed,
        "candidate_generation_resume_bucket": resume_bucket,
        "candidate_generation_cache_hits": candidate_generation_cache_hits,
        "candidate_generation_new_pairs": candidate_generation_new_pairs,
    }
    cache.set_phase_status(
        context_sha256,
        "candidate_generation",
        generation_status,
        generation_metadata,
    )

    # Verify candidate-pair commitment before comparison or comparison resume.
    observed_count, observed_sha = cache.candidate_pair_commitment(context_sha256)
    if observed_count != candidate_pair_count or observed_sha != candidate_pair_sha:
        raise ValueError("candidate-pair commitment mismatch")

    comparison_truncated = False
    compare_started = time.perf_counter()
    comparison_checkpoint = cache.load_phase_checkpoint(context_sha256, "pair_comparison")
    pair_comparison_resumed = comparison_checkpoint is not None
    cursor_left = ""
    cursor_right = ""
    candidate_pairs_compared = 0
    near_pairs_found = 0
    comparison_batches_completed = 0
    if comparison_checkpoint is not None:
        cursor, comparison_meta = comparison_checkpoint
        cursor_left, _, cursor_right = cursor.partition("\0")
        candidate_pairs_compared = int(comparison_meta.get("candidate_pairs_compared_total", 0))
        comparison_batches_completed = int(comparison_meta.get("comparison_batches_completed", 0))
    near_pairs_found = cache.count_near_pairs(context_sha256)
    compared_this_run = 0
    cache.set_phase_status(
        context_sha256,
        "pair_comparison",
        "IN_PROGRESS",
        {
            "candidate_pairs_compared_total": candidate_pairs_compared,
            "candidate_pair_count": candidate_pair_count,
        },
    )
    while True:
        batch = cache.fetch_candidate_pair_batch(
            context_sha256,
            after_left=cursor_left,
            after_right=cursor_right,
            limit=CANDIDATE_COMPARISON_BATCH_SIZE,
        )
        if not batch:
            break
        new_near_pairs: list[tuple[str, str, int]] = []
        for left_key, right_key in batch:
            left = by_key[left_key]
            right = by_key[right_key]
            distance = simhash_hamming(left.simhash_hex, right.simhash_hex)
            if distance <= max_hamming and near_pairs_found + len(new_near_pairs) < max_pairs:
                new_near_pairs.append((left_key, right_key, distance))
            elif distance <= max_hamming:
                comparison_truncated = True
                break
        processed = len(batch) if not comparison_truncated else batch.index((left_key, right_key))
        if comparison_truncated:
            processed = max(processed, 0)
            if processed:
                cursor_left, cursor_right = batch[processed - 1]
        else:
            cursor_left, cursor_right = batch[-1]
        candidate_pairs_compared += processed
        compared_this_run += processed
        comparison_batches_completed += 1
        checkpoint_metadata = {
            "last_compared_left_key": cursor_left,
            "last_compared_right_key": cursor_right,
            "candidate_pairs_compared_total": candidate_pairs_compared,
            "candidate_pairs_compared_this_run": compared_this_run,
            "near_pairs_found": near_pairs_found,
            "comparison_truncated": comparison_truncated,
            "comparison_batches_completed": comparison_batches_completed,
        }
        near_pairs_found = cache.commit_comparison_batch(
            context_sha256,
            cursor=f"{cursor_left}\0{cursor_right}",
            near_pairs=new_near_pairs,
            metadata=checkpoint_metadata,
        )
        reporter.rows(
            f"compare SimHash candidates resume={cursor_left}:{cursor_right}",
            candidate_pairs_compared,
            candidate_pair_count,
            started=compare_started,
        )
        if INJECT_AFTER_COMPARISON_BATCHES is not None and (
            comparison_batches_completed >= INJECT_AFTER_COMPARISON_BATCHES
        ):
            raise RuntimeError("injected pair-comparison interruption")
        if comparison_truncated:
            break
    if candidate_pair_count == 0:
        reporter.rows(
            "compare SimHash candidates resume=:",
            0,
            0,
            started=compare_started,
        )
    pairs = cache.load_near_pairs(context_sha256)
    pair_count, pair_sha = len(pairs), near_pair_commitment(pairs)
    comparison_complete = (
        candidate_pairs_compared == candidate_pair_count and not comparison_truncated
    )
    comparison_status = "COMPLETE" if comparison_complete else "TRUNCATED"
    comparison_metadata = {
        "last_compared_left_key": cursor_left,
        "last_compared_right_key": cursor_right,
        "candidate_pairs_compared_total": candidate_pairs_compared,
        "candidate_pairs_compared_this_run": compared_this_run,
        "near_pairs_found": pair_count,
        "near_pair_count": pair_count,
        "ordered_near_pair_sha256": pair_sha,
        "comparison_truncated": comparison_truncated,
        "near_pair_limit_reached": comparison_truncated,
        "comparison_batches_completed": comparison_batches_completed,
        "pair_comparison_resumed": pair_comparison_resumed,
        "pair_comparison_resume_key": f"{cursor_left}\0{cursor_right}"
        if pair_comparison_resumed
        else "",
    }
    cache.set_phase_status(
        context_sha256,
        "pair_comparison",
        comparison_status,
        comparison_metadata,
    )
    scan_complete = (
        oversized_buckets == 0
        and not candidate_generation_truncated
        and not comparison_truncated
        and max_hamming <= MAX_EXHAUSTIVE_SIMHASH_RADIUS
    )
    metadata = {
        **generation_metadata,
        **comparison_metadata,
        "candidate_buckets_total": len(ordered_buckets),
        "candidate_buckets_processed": candidate_buckets_processed,
        "candidate_pairs_generated": candidate_pair_count,
        "candidate_pairs_compared": candidate_pairs_compared,
        "verified_pair_count": candidate_pairs_compared,
        "near_pairs": pair_count,
        "near_pair_count": pair_count,
        "oversized_buckets_skipped": oversized_buckets,
        "candidate_generation_truncated": candidate_generation_truncated,
        "comparison_truncated": comparison_truncated,
        "pair_truncated": comparison_truncated,
        "output_truncated": comparison_truncated,
        "scan_complete": scan_complete,
        "max_hamming": max_hamming,
        "max_bucket": max_bucket,
        "max_candidate_pairs": max_candidate_pairs,
        "max_pairs": max_pairs,
        "candidate_comparison_batch_size": CANDIDATE_COMPARISON_BATCH_SIZE,
        "ordered_near_pair_sha256": pair_sha,
    }
    phase_status = "COMPLETE" if scan_complete else "TRUNCATED"
    cache.set_phase_status(context_sha256, "near_duplicate_scan", phase_status, metadata)
    return pairs, metadata


def near_duplicate_report(
    rows: Sequence[VisibleAuditRow],
    *,
    cache: IntegrityAuditCache,
    context: AuditContext,
    max_hamming: int,
    max_bucket: int,
    max_candidate_pairs: int,
    max_pairs: int,
    reporter: ProgressReporter,
    sample_limit: int = 30,
) -> dict[str, Any]:
    if not 0 <= max_hamming <= MAX_EXHAUSTIVE_SIMHASH_RADIUS:
        raise ValueError("near_hamming must lie between zero and three for exhaustive banding")
    cached_state = cache.phase_state(context.sha256, "near_duplicate_scan")
    cached_metadata = None
    if cached_state is not None and cached_state[0] in {"COMPLETE", "TRUNCATED"}:
        cached_metadata = cached_state[1]
    expected_cache_fields = {
        "max_hamming": max_hamming,
        "max_bucket": max_bucket,
        "max_candidate_pairs": max_candidate_pairs,
        "max_pairs": max_pairs,
    }
    if cached_metadata is not None and all(
        cached_metadata.get(key) == value for key, value in expected_cache_fields.items()
    ):
        reporter.message("near-duplicate cache: completed scan hit")
        candidate_count, candidate_sha = cache.candidate_pair_commitment(context.sha256)
        if (
            candidate_count != int(cached_metadata.get("candidate_pair_count", -1))
            or candidate_sha != cached_metadata.get("ordered_candidate_pair_sha256")
        ):
            raise ValueError("candidate-pair cache commitment mismatch")
        pairs = cache.load_near_pairs(context.sha256)
        if near_pair_commitment(pairs) != cached_metadata.get("ordered_near_pair_sha256"):
            raise ValueError("near-duplicate cache commitment mismatch")
        elif int(cached_metadata.get("near_pairs", -1)) != len(pairs):
            raise ValueError("near-duplicate cache pair count mismatch")
        else:
            metadata = {
                **cached_metadata,
                "near_pairs": len(pairs),
                "cache_reused": True,
            }
    else:
        if cached_metadata is not None:
            reporter.message("discarding near-duplicate cache with mismatched parameters")
            cache.clear_near_pairs(context.sha256)
        pairs, metadata = _compute_near_pairs(
            rows,
            cache=cache,
            context_sha256=context.sha256,
            max_hamming=max_hamming,
            max_bucket=max_bucket,
            max_candidate_pairs=max_candidate_pairs,
            max_pairs=max_pairs,
            reporter=reporter,
        )
        metadata = {**metadata, "cache_reused": False}

    by_key = {row.stable_key: row for row in rows}
    repository_pairs = set()
    samples = []
    exact_code_pairs = 0
    exact_ast_pairs = 0
    non_exact_code_near_pairs = 0
    non_exact_ast_near_pairs = 0
    for left_key, right_key, distance in pairs:
        if left_key not in by_key or right_key not in by_key:
            raise ValueError("near-pair cache references an unknown visible row")
        left = by_key[left_key]
        right = by_key[right_key]
        if left.role == right.role or left.repository == right.repository:
            raise ValueError("near-pair cache contains a non-cross-role pair")
        actual_distance = simhash_hamming(left.simhash_hex, right.simhash_hex)
        if actual_distance != distance:
            raise ValueError("near-pair cache contains a stale Hamming distance")
        same_code = left.code_sha256 == right.code_sha256
        same_ast = left.normalized_ast_sha256 == right.normalized_ast_sha256
        exact_code_pairs += int(same_code)
        exact_ast_pairs += int(same_ast)
        non_exact_code_near_pairs += int(not same_code)
        non_exact_ast_near_pairs += int(not same_ast)
        repository_pairs.add(tuple(sorted((left.repository, right.repository))))
        if len(samples) < sample_limit:
            samples.append(
                {
                    "hamming_distance": distance,
                    "left": {
                        "role": left.role,
                        "repository": left.repository,
                        "stable_key": left.stable_key,
                        "code_sha256": left.code_sha256,
                        "normalized_ast_sha256": left.normalized_ast_sha256,
                    },
                    "right": {
                        "role": right.role,
                        "repository": right.repository,
                        "stable_key": right.stable_key,
                        "code_sha256": right.code_sha256,
                        "normalized_ast_sha256": right.normalized_ast_sha256,
                    },
                }
            )
    return {
        **metadata,
        "near_duplicate_scan_complete": bool(metadata.get("scan_complete")),
        "cross_role_repository_pairs": len(repository_pairs),
        "all_verified_simhash_near_pairs": len(pairs),
        "exact_code_pairs": exact_code_pairs,
        "exact_ast_pairs": exact_ast_pairs,
        "non_exact_code_near_pairs": non_exact_code_near_pairs,
        "non_exact_ast_near_pairs": non_exact_ast_near_pairs,
        "ordered_near_pair_sha256": near_pair_commitment(pairs),
        "samples": samples,
        "near_pair_samples_retained": len(samples),
        "sample_truncated": len(pairs) > len(samples),
        "interpretation": "candidate near duplicates requiring review, not proven contamination",
        "algorithm_documentation": {
            "method": "normalised Python token shingles, 64-bit SimHash, deterministic banding",
            "pigeonhole_guarantee": (
                "With 64 bits split into four disjoint 16-bit bands, any pair at "
                "Hamming radius three or less must share at least one exact band."
            ),
            "can_detect": (
                "token-level near matches that collide in at least one SimHash band "
                "and pass exact Hamming verification"
            ),
            "can_miss": (
                "semantic clones, renamed structures outside the Hamming radius, "
                "and pairs hidden by skipped oversized buckets"
            ),
            "bounds": (
                "oversized buckets and maximum output pairs are explicit; any skip "
                "or truncation marks the scan incomplete"
            ),
            "maximum_exhaustive_radius": MAX_EXHAUSTIVE_SIMHASH_RADIUS,
            "exhaustive_for_radius": bool(metadata.get("scan_complete")),
        },
    }


def _run_git(repo_root: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )


def _git_text(repo_root: Path, arguments: Sequence[str]) -> str:
    result = _run_git(repo_root, arguments)
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {message}")
    return result.stdout.decode().strip()


def _hash_paths_at_ref(
    repo_root: Path,
    ref: str,
    paths: Sequence[str],
    reporter: ProgressReporter,
    *,
    evidence_role: str = "source",
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    started = time.perf_counter()
    for index, path in enumerate(paths, start=1):
        command = _run_git(repo_root, ["show", f"{ref}:{path}"])
        if command.returncode == 0:
            result[path] = {
                "available": True,
                "bytes": len(command.stdout),
                "byte_count": len(command.stdout),
                "sha256": _sha256_bytes(command.stdout),
                "git_ref": ref,
                "evidence_role": evidence_role,
            }
        else:
            result[path] = {
                "available": False,
                "git_ref": ref,
                "evidence_role": evidence_role,
                "error": command.stderr.decode(errors="replace").strip(),
            }
        reporter.rows(f"hash source at {ref[:12]}", index, len(paths), started=started)
    return result


def execution_source_manifest(
    repo_root: Path,
    *,
    v1_runtime_source_commit: str,
    v1_result_publication_commit: str,
    allow_dirty: bool,
    reporter: ProgressReporter,
) -> dict[str, Any]:
    head = _git_text(repo_root, ["rev-parse", "HEAD"])
    dirty_lines = [
        line for line in _git_text(repo_root, ["status", "--porcelain"]).splitlines() if line
    ]
    if dirty_lines and not allow_dirty:
        raise ValueError("D1 execution requires a clean Git worktree")
    runtime_paths = _hash_paths_at_ref(
        repo_root,
        v1_runtime_source_commit,
        V1_EXECUTION_PATHS,
        reporter,
        evidence_role="v1_runtime_source",
    )
    publication_paths = _hash_paths_at_ref(
        repo_root,
        v1_result_publication_commit,
        V1_PUBLICATION_ARTIFACT_PATHS,
        reporter,
        evidence_role="v1_publication_artifact",
    )
    runtime_at_publication = _hash_paths_at_ref(
        repo_root,
        v1_result_publication_commit,
        V1_EXECUTION_PATHS,
        reporter,
        evidence_role="v1_runtime_source_at_publication_commit",
    )
    byte_comparisons = {}
    for path in V1_EXECUTION_PATHS:
        runtime = runtime_paths[path]
        published = runtime_at_publication[path]
        byte_comparisons[path] = {
            "available_at_both_refs": runtime["available"] and published["available"],
            "byte_identical": (
                runtime.get("sha256") == published.get("sha256")
                if runtime["available"] and published["available"]
                else False
            ),
            "runtime_source_commit": v1_runtime_source_commit,
            "publication_commit": v1_result_publication_commit,
        }
    d1_paths = _hash_paths_at_ref(
        repo_root,
        head,
        D1_EXECUTION_PATHS,
        reporter,
        evidence_role="d1_execution_source",
    )
    return {
        "registered_candidate_implementation_commit": REGISTERED_CANDIDATE_IMPLEMENTATION_COMMIT,
        "v1_runtime_source_commit": v1_runtime_source_commit,
        "v1_result_publication_commit": v1_result_publication_commit,
        "v1_runtime_source_paths": runtime_paths,
        "v1_runtime_source_manifest_complete": all(
            item["available"] for item in runtime_paths.values()
        ),
        "v1_publication_artifacts": publication_paths,
        "v1_publication_artifact_manifest_complete": all(
            item["available"] for item in publication_paths.values()
        ),
        "v1_runtime_source_byte_comparison": {
            "runtime_source_commit": v1_runtime_source_commit,
            "publication_commit": v1_result_publication_commit,
            "all_available": all(
                item["available_at_both_refs"] for item in byte_comparisons.values()
            ),
            "all_byte_identical": all(item["byte_identical"] for item in byte_comparisons.values()),
            "paths": byte_comparisons,
        },
        "d1_execution_ref": head,
        "d1_execution_paths": d1_paths,
        "d1_all_paths_available": all(item["available"] for item in d1_paths.values()),
        "worktree_clean": not dirty_lines,
        "dirty_entries": dirty_lines,
    }


def run_d1_integrity_audit(
    *,
    identity_path: Path,
    firewall_dir: Path,
    allocation_path: Path,
    output_path: Path,
    cache_path: Path = DEFAULT_CACHE_PATH,
    repo_root: Path = Path("."),
    v1_runtime_source_commit: str = V1_RUNTIME_SOURCE_COMMIT,
    v1_result_publication_commit: str = V1_RESULT_PUBLICATION_COMMIT,
    near_hamming: int = 3,
    near_max_bucket: int = 250,
    near_max_candidate_pairs: int = 1_000_000,
    near_max_pairs: int = 50_000,
    allow_dirty: bool = False,
    allow_test_fixture_inputs: bool = False,
    allow_test_fixture_provenance: bool = False,
    argv: Sequence[str] | None = None,
    reporter: ProgressReporter | None = None,
) -> dict[str, Any]:
    """Run the guarded D1 audit without exposing hidden-role row contents."""

    if output_path.exists():
        raise FileExistsError(f"D1 audit output already exists: {output_path}")
    if not 0 <= near_hamming <= MAX_EXHAUSTIVE_SIMHASH_RADIUS:
        raise ValueError("near_hamming must lie between zero and three")
    if near_max_bucket < 1 or near_max_pairs < 1 or near_max_candidate_pairs < 1:
        raise ValueError("near duplicate limits must be positive")
    if (
        (
            v1_runtime_source_commit != V1_RUNTIME_SOURCE_COMMIT
            or v1_result_publication_commit != V1_RESULT_PUBLICATION_COMMIT
        )
        and not allow_test_fixture_provenance
    ):
        raise ValueError("D1 provenance refs must match the frozen contract values")
    active_reporter = reporter or ProgressReporter()
    overall_started = time.perf_counter()
    started_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    repo_root = repo_root.resolve()

    head = _git_text(repo_root, ["rev-parse", "HEAD"])
    branch = _git_text(repo_root, ["branch", "--show-current"])
    dirty_lines = [
        line for line in _git_text(repo_root, ["status", "--porcelain"]).splitlines() if line
    ]
    if dirty_lines and not allow_dirty:
        raise ValueError("D1 execution requires a clean Git worktree")

    active_reporter.message("loading published repository allocation")
    assignments = _load_assignments(allocation_path)
    input_validation = validate_canonical_inputs(
        identity_path=identity_path,
        allocation_path=allocation_path,
        firewall_dir=firewall_dir,
        assignments=assignments,
        allow_test_fixture_inputs=allow_test_fixture_inputs,
    )
    contract = validate_d1_contract(
        repo_root / "artifacts/canonical/option-c0/review-v1/option-c0-d1-audit-contract-v1.json"
    )
    active_reporter.message("hashing complete v1 and D1 execution source composition")
    execution = execution_source_manifest(
        repo_root,
        v1_runtime_source_commit=v1_runtime_source_commit,
        v1_result_publication_commit=v1_result_publication_commit,
        allow_dirty=allow_dirty,
        reporter=active_reporter,
    )
    context = _audit_context(
        identity_path,
        allocation_path,
        near_hamming=near_hamming,
        near_max_bucket=near_max_bucket,
        near_max_candidate_pairs=near_max_candidate_pairs,
        near_max_pairs=near_max_pairs,
        repo_root=repo_root,
    )

    with IntegrityAuditCache(cache_path) as cache:
        cache.register_context(context)
        sqlite_pragmas = cache.verify_pragmas()
        rows, row_cache = load_or_reconstruct_visible_rows(
            identity_path,
            firewall_dir,
            assignments,
            cache=cache,
            context=context,
            reporter=active_reporter,
        )
        active_reporter.message("computing exact source and AST overlap")
        exact_code = exact_overlap_report(rows, field="code_sha256")
        exact_ast = exact_overlap_report(rows, field="normalized_ast_sha256")
        active_reporter.message("computing bounded visible-role near-duplicate candidates")
        near = near_duplicate_report(
            rows,
            cache=cache,
            context=context,
            max_hamming=near_hamming,
            max_bucket=near_max_bucket,
            max_candidate_pairs=near_max_candidate_pairs,
            max_pairs=near_max_pairs,
            reporter=active_reporter,
        )

    active_reporter.message("computing allocation-metadata repository-family candidates")
    family = repository_family_report(assignments)
    exact_overlap_found = bool(
        exact_code["cross_role_hashes"] or exact_ast["cross_role_hashes"]
    )
    near_complete = bool(near["near_duplicate_scan_complete"])
    source_manifest_complete = bool(
        execution["v1_runtime_source_manifest_complete"]
        and execution["v1_publication_artifact_manifest_complete"]
        and execution["d1_all_paths_available"]
    )
    if not input_validation["canonical_inputs_verified"]:
        status = "C0_D1_AUDIT_INPUT_IDENTITY_FAILED"
        next_allowed = "FIX_CANONICAL_INPUT_IDENTITY_BEFORE_D1_AUDIT"
    elif not source_manifest_complete:
        status = "C0_D1_AUDIT_INCOMPLETE_SOURCE_MANIFEST"
        next_allowed = "FIX_SOURCE_MANIFEST_BEFORE_D1_REVIEW"
    elif not near_complete:
        status = "C0_D1_AUDIT_INCOMPLETE_NEAR_SCAN"
        next_allowed = "RERUN_D1_WITH_COMPLETE_NEAR_SCAN_BEFORE_D2"
    else:
        status = "C0_D1_AUDIT_COMPLETE_PENDING_HUMAN_REVIEW"
        next_allowed = (
            "REVIEW_AND_CLASSIFY_EXACT_CROSS_ROLE_OVERLAP"
            if exact_overlap_found
            else "REVIEW_D1_AUDIT_BEFORE_D2_IMPLEMENTATION"
        )
    completed_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    elapsed = time.perf_counter() - overall_started
    environment = {
        "argv": list(argv if argv is not None else sys.argv),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "os": platform.system(),
        "machine": platform.machine(),
        "package_versions": _package_versions(
            ("numpy", "datasets", "transformers", "tokenizers")
        ),
        "git_head": head,
        "git_branch": branch,
        "worktree_status": dirty_lines,
        "cache_path": str(cache_path).replace("\\", "/"),
        "output_path": str(output_path).replace("\\", "/"),
        "start_timestamp": started_at,
        "completion_timestamp": completed_at,
        "elapsed_seconds": elapsed,
    }
    result = {
        "schema_id": AUDIT_SCHEMA,
        "status": status,
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_rows_accessed": False,
        "c1_rows_accessed": False,
        "hidden_row_content_accessed": False,
        "audit_context_sha256": context.sha256,
        "audit_context": context.payload,
        "input_validation": input_validation,
        "d1_contract": contract,
        "execution_environment": environment,
        "cache": {
            "schema": CACHE_SCHEMA,
            "path": str(cache_path).replace("\\", "/"),
            "local_recovery_only": True,
            "sqlite_pragmas": sqlite_pragmas,
            **row_cache,
        },
        "visible_rows": {
            "rows": len(rows),
            "roles": {
                role: sum(row.role == role for row in rows) for role in VISIBLE_ROLES
            },
            "repositories": {
                role: len({row.repository for row in rows if row.role == role})
                for role in VISIBLE_ROLES
            },
        },
        "exact_code_overlap": exact_code,
        "exact_ast_overlap": exact_ast,
        "near_duplicate_candidates": near,
        "repository_family_candidates": family,
        "execution_source_manifest": execution,
        "integrity_gates": {
            "exact_cross_role_overlap_absent": not exact_overlap_found,
            "near_duplicate_scan_complete": near_complete,
            "execution_source_manifest_complete": source_manifest_complete,
            "worktree_clean": execution["worktree_clean"],
            "hidden_rows_remained_inaccessible": True,
        },
        "automatic_material_contamination_decision": "NOT_PERMITTED",
        "next_allowed_action": next_allowed,
        "prohibited_actions": [
            "automatic contamination classification from repository-name heuristics",
            "C0 selection access",
            "C1 reserve row access",
            "candidate promotion",
            "Option C scientific decision",
        ],
        "elapsed_seconds": elapsed,
    }
    _atomic_write_json(output_path, result)
    active_reporter.completed("Option C0-D1 integrity audit", overall_started)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--identity",
        type=Path,
        default=Path("artifacts/canonical/option-b/option-b-external-identity-v1.json"),
    )
    parser.add_argument(
        "--firewall-dir",
        type=Path,
        default=Path("artifacts/canonical/option-c0/data-firewall-v1"),
    )
    parser.add_argument("--allocation-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--v1-runtime-source-commit", default=V1_RUNTIME_SOURCE_COMMIT)
    parser.add_argument(
        "--v1-result-publication-commit",
        default=V1_RESULT_PUBLICATION_COMMIT,
    )
    parser.add_argument("--near-hamming", type=int, default=3)
    parser.add_argument("--near-max-bucket", type=int, default=250)
    parser.add_argument("--near-max-candidate-pairs", type=int, default=1_000_000)
    parser.add_argument("--near-max-pairs", type=int, default=50_000)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--allow-test-fixture-inputs", action="store_true")
    args = parser.parse_args()
    allocation_path = args.allocation_manifest or (
        args.firewall_dir / "option-c0-repository-allocation-v1.jsonl"
    )
    result = run_d1_integrity_audit(
        identity_path=args.identity,
        firewall_dir=args.firewall_dir,
        allocation_path=allocation_path,
        output_path=args.output,
        cache_path=args.cache,
        repo_root=args.repo_root,
        v1_runtime_source_commit=args.v1_runtime_source_commit,
        v1_result_publication_commit=args.v1_result_publication_commit,
        near_hamming=args.near_hamming,
        near_max_bucket=args.near_max_bucket,
        near_max_candidate_pairs=args.near_max_candidate_pairs,
        near_max_pairs=args.near_max_pairs,
        allow_dirty=args.allow_dirty,
        allow_test_fixture_inputs=args.allow_test_fixture_inputs,
        argv=sys.argv,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output).replace("\\", "/"),
                "audit_context_sha256": result["audit_context_sha256"],
                "integrity_gates": result["integrity_gates"],
                "next_allowed_action": result["next_allowed_action"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

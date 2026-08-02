"""Option C0-D1 visible-role integrity and execution-composition audit.

The audit reconstructs only the already-visible C0 fit and iteration rows. Hidden
C0-selection and C1 row contents remain inaccessible. Repository names from the
published allocation manifest may be used for bounded family-name diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import keyword
import os
import re
import sqlite3
import subprocess
import sys
import time
import tokenize
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, TextIO

from relate.experiments import option_c0_discovery_runner as discovery_runner

AUDIT_SCHEMA: Final = "option-c0-d1-integrity-audit-v1"
CACHE_SCHEMA: Final = "option-c0-d1-integrity-cache-v1"
CONTEXT_SCHEMA: Final = "option-c0-d1-integrity-context-v1"
DEFAULT_CACHE_PATH: Final = Path(
    ".writer/option-c0/cache/option-c0-d1-integrity-v1.sqlite3"
)
DEFAULT_EXECUTION_REF: Final = "07cf6fc5ea9c261b10df272215a8afb404612e76"
VISIBLE_ROLES: Final = ("c0_fit", "c0_iteration")
ALLOCATION_ROLES: Final = ("c0_fit", "c0_iteration", "c0_selection", "c1_reserve")
SIMHASH_BITS: Final = 64
SIMHASH_SHINGLE_SIZE: Final = 5
SIMHASH_BANDS: Final = 4
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
    "src/relate/experiments/option_b_real_code.py",
    "src/relate/experiments/option_b_selection.py",
    "src/relate/experiments/option_b_selection_resilient.py",
    "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-initial-candidate-plan-v1.json",
    "artifacts/canonical/option-c0/candidate-plan-v1/option-c0-discovery-execution-identity-erratum-v1.json",
    "artifacts/canonical/option-b/option-b-external-identity-v1.json",
    "artifacts/canonical/option-b/embedding-reproduction-v2/option-b-embedding-identity-v2-gpu-batch10.json",
)
D1_EXECUTION_PATHS: Final = (
    "pyproject.toml",
    "scripts/run-option-c0-d1-integrity-audit.ps1",
    "src/relate/experiments/option_c0_d1_integrity_audit.py",
    "src/relate/experiments/option_c0_discovery_runner.py",
    "src/relate/experiments/option_c0_mechanism_harness.py",
    "src/relate/experiments/option_b_real_code.py",
    "artifacts/canonical/option-c0/review-v1/option-c0-d-remediation-status-v1.json",
    "artifacts/canonical/option-c0/review-v1/option-c0-d1-audit-contract-v1.json",
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


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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
        for field in (self.repository, self.stable_key, self.code_sha256):
            if not field:
                raise ValueError("visible audit row identities must be non-empty")
        for digest in (self.code_sha256, self.normalized_ast_sha256):
            if len(digest) != 64 or any(item not in "0123456789abcdef" for item in digest):
                raise ValueError("visible audit row digests must be SHA-256 hexadecimal")
        if len(self.simhash_hex) != 16:
            raise ValueError("visible audit row SimHash must be 64-bit hexadecimal")


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
        row = self.connection.execute(
            """
            SELECT status FROM phases
            WHERE context_sha256 = ? AND phase_name = ?
            """,
            (context_sha256, phase_name),
        ).fetchone()
        return row == ("COMPLETE",)

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

    def clear_near_pairs(self, context_sha256: str) -> None:
        self.connection.execute(
            "DELETE FROM near_pairs WHERE context_sha256 = ?",
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


def _audit_context(
    identity_path: Path,
    allocation_path: Path,
    *,
    near_hamming: int,
    near_max_bucket: int,
    near_max_pairs: int,
) -> AuditContext:
    runner_path = Path(discovery_runner.__file__ or "")
    payload = {
        "schema": CONTEXT_SCHEMA,
        "source_identity_sha256": _sha256_file(identity_path),
        "allocation_manifest_sha256": _sha256_file(allocation_path),
        "visible_reconstruction_source_sha256": _sha256_file(runner_path),
        "visible_roles": list(VISIBLE_ROLES),
        "simhash_bits": SIMHASH_BITS,
        "simhash_shingle_size": SIMHASH_SHINGLE_SIZE,
        "simhash_bands": SIMHASH_BANDS,
        "near_hamming": near_hamming,
        "near_max_bucket": near_max_bucket,
        "near_max_pairs": near_max_pairs,
    }
    return AuditContext.from_payload(payload)


def _row_from_visible(item: Any) -> VisibleAuditRow:
    record = item.record
    return VisibleAuditRow(
        role=str(item.role),
        repository=str(record.repository),
        stable_key=str(record.stable_key),
        source_split=str(record.split),
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
    if cached == expected:
        started = time.perf_counter()
        reporter.message(f"visible-row cache: {cached:,} hit/0 miss")
        rows = cache.load_visible_rows(context.sha256)
        reporter.completed("visible-row cache load", started)
        return rows, {
            "cache_hits": cached,
            "cache_misses": 0,
            "reconstructed": False,
            "rows": len(rows),
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
    return rows, {
        "cache_hits": 0,
        "cache_misses": len(rows),
        "reconstructed": True,
        "rows": len(rows),
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
            repositories = {repository for _, repository in owners}
            if len(roles) < 2 or len(repositories) < 2:
                continue
            result.append(
                {
                    "signature": signature,
                    "roles": sorted(roles),
                    "repositories": sorted(repositories),
                }
            )
        return sorted(result, key=lambda item: (-len(item["repositories"]), item["signature"]))

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
    max_hamming: int,
    max_bucket: int,
    max_pairs: int,
    reporter: ProgressReporter,
) -> tuple[tuple[tuple[str, str, int], ...], dict[str, Any]]:
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        for band in _simhash_band_values(row.simhash_hex):
            buckets[band].append(index - 1)
        if index % 1000 == 0 or index == len(rows):
            reporter.rows("index SimHash bands", index, len(rows), started=started)

    candidate_pairs: set[tuple[int, int]] = set()
    oversized_buckets = 0
    ordered_buckets = sorted(buckets.items())
    scan_started = time.perf_counter()
    for position, (_, indices) in enumerate(ordered_buckets, start=1):
        if len(indices) > max_bucket:
            oversized_buckets += 1
        else:
            for left_position in range(len(indices)):
                left_index = indices[left_position]
                left = rows[left_index]
                for right_index in indices[left_position + 1 :]:
                    right = rows[right_index]
                    if left.role == right.role or left.repository == right.repository:
                        continue
                    pair = tuple(sorted((left_index, right_index)))
                    candidate_pairs.add(pair)
        if position % 250 == 0 or position == len(ordered_buckets):
            reporter.rows(
                "scan SimHash buckets",
                position,
                len(ordered_buckets),
                started=scan_started,
            )

    results: list[tuple[str, str, int]] = []
    truncated = False
    compare_started = time.perf_counter()
    ordered_candidates = sorted(candidate_pairs)
    for position, (left_index, right_index) in enumerate(ordered_candidates, start=1):
        left = rows[left_index]
        right = rows[right_index]
        distance = simhash_hamming(left.simhash_hex, right.simhash_hex)
        if distance <= max_hamming:
            left_key, right_key = sorted((left.stable_key, right.stable_key))
            results.append((left_key, right_key, distance))
            if len(results) >= max_pairs:
                truncated = position < len(ordered_candidates)
                break
        if position % 10000 == 0 or position == len(ordered_candidates):
            reporter.rows(
                "compare SimHash candidates",
                position,
                len(ordered_candidates),
                started=compare_started,
            )
    results.sort(key=lambda item: (item[2], item[0], item[1]))
    return tuple(results), {
        "candidate_pairs": len(candidate_pairs),
        "near_pairs": len(results),
        "oversized_buckets_skipped": oversized_buckets,
        "truncated": truncated,
        "max_hamming": max_hamming,
        "max_bucket": max_bucket,
        "max_pairs": max_pairs,
    }


def near_duplicate_report(
    rows: Sequence[VisibleAuditRow],
    *,
    cache: IntegrityAuditCache,
    context: AuditContext,
    max_hamming: int,
    max_bucket: int,
    max_pairs: int,
    reporter: ProgressReporter,
    sample_limit: int = 30,
) -> dict[str, Any]:
    if cache.phase_complete(context.sha256, "near_duplicate_scan"):
        reporter.message("near-duplicate cache: completed scan hit")
        pairs = cache.load_near_pairs(context.sha256)
        metadata = {
            "near_pairs": len(pairs),
            "cache_reused": True,
            "truncated": False,
            "max_hamming": max_hamming,
            "max_bucket": max_bucket,
            "max_pairs": max_pairs,
        }
    else:
        cache.clear_near_pairs(context.sha256)
        pairs, metadata = _compute_near_pairs(
            rows,
            max_hamming=max_hamming,
            max_bucket=max_bucket,
            max_pairs=max_pairs,
            reporter=reporter,
        )
        for start in range(0, len(pairs), 1000):
            cache.put_near_pairs(context.sha256, pairs[start : start + 1000])
        cache.mark_phase_complete(context.sha256, "near_duplicate_scan", metadata)
        metadata = {**metadata, "cache_reused": False}

    by_key = {row.stable_key: row for row in rows}
    repository_pairs = set()
    samples = []
    for left_key, right_key, distance in pairs:
        left = by_key[left_key]
        right = by_key[right_key]
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
        "cross_role_repository_pairs": len(repository_pairs),
        "samples": samples,
        "interpretation": "candidate near duplicates requiring review, not proven contamination",
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
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    started = time.perf_counter()
    for index, path in enumerate(paths, start=1):
        command = _run_git(repo_root, ["show", f"{ref}:{path}"])
        if command.returncode == 0:
            result[path] = {
                "available": True,
                "bytes": len(command.stdout),
                "sha256": _sha256_bytes(command.stdout),
            }
        else:
            result[path] = {
                "available": False,
                "error": command.stderr.decode(errors="replace").strip(),
            }
        reporter.rows(f"hash source at {ref[:12]}", index, len(paths), started=started)
    return result


def execution_source_manifest(
    repo_root: Path,
    *,
    v1_execution_ref: str,
    allow_dirty: bool,
    reporter: ProgressReporter,
) -> dict[str, Any]:
    head = _git_text(repo_root, ["rev-parse", "HEAD"])
    dirty_lines = [
        line for line in _git_text(repo_root, ["status", "--porcelain"]).splitlines() if line
    ]
    if dirty_lines and not allow_dirty:
        raise ValueError("D1 execution requires a clean Git worktree")
    v1_paths = _hash_paths_at_ref(repo_root, v1_execution_ref, V1_EXECUTION_PATHS, reporter)
    d1_paths = _hash_paths_at_ref(repo_root, head, D1_EXECUTION_PATHS, reporter)
    return {
        "v1_execution_ref": v1_execution_ref,
        "v1_execution_paths": v1_paths,
        "v1_all_paths_available": all(item["available"] for item in v1_paths.values()),
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
    v1_execution_ref: str = DEFAULT_EXECUTION_REF,
    near_hamming: int = 3,
    near_max_bucket: int = 250,
    near_max_pairs: int = 50_000,
    allow_dirty: bool = False,
    reporter: ProgressReporter | None = None,
) -> dict[str, Any]:
    """Run the guarded D1 audit without exposing hidden-role row contents."""

    if output_path.exists():
        raise FileExistsError(f"D1 audit output already exists: {output_path}")
    if not 0 <= near_hamming <= SIMHASH_BITS:
        raise ValueError("near_hamming must lie between zero and 64")
    if near_max_bucket < 2 or near_max_pairs < 1:
        raise ValueError("near duplicate limits must be positive")
    active_reporter = reporter or ProgressReporter()
    overall_started = time.perf_counter()

    active_reporter.message("loading published repository allocation")
    assignments = _load_assignments(allocation_path)
    context = _audit_context(
        identity_path,
        allocation_path,
        near_hamming=near_hamming,
        near_max_bucket=near_max_bucket,
        near_max_pairs=near_max_pairs,
    )

    with IntegrityAuditCache(cache_path) as cache:
        cache.register_context(context)
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
            max_pairs=near_max_pairs,
            reporter=active_reporter,
        )

    active_reporter.message("computing allocation-metadata repository-family candidates")
    family = repository_family_report(assignments)
    active_reporter.message("hashing complete v1 and D1 execution source composition")
    execution = execution_source_manifest(
        repo_root,
        v1_execution_ref=v1_execution_ref,
        allow_dirty=allow_dirty,
        reporter=active_reporter,
    )

    exact_overlap_found = bool(
        exact_code["cross_role_hashes"] or exact_ast["cross_role_hashes"]
    )
    near_complete = not bool(near["truncated"])
    source_manifest_complete = bool(
        execution["v1_all_paths_available"] and execution["d1_all_paths_available"]
    )
    result = {
        "schema_id": AUDIT_SCHEMA,
        "status": "C0_D1_AUDIT_COMPLETE_PENDING_HUMAN_REVIEW",
        "scientific_result_observed": False,
        "mechanism_result_observed": False,
        "c0_selection_rows_accessed": False,
        "c1_rows_accessed": False,
        "hidden_row_content_accessed": False,
        "audit_context_sha256": context.sha256,
        "audit_context": context.payload,
        "cache": {
            "schema": CACHE_SCHEMA,
            "path": str(cache_path).replace("\\", "/"),
            "local_recovery_only": True,
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
        "next_allowed_action": (
            "REVIEW_AND_CLASSIFY_EXACT_CROSS_ROLE_OVERLAP"
            if exact_overlap_found
            else "REVIEW_D1_AUDIT_BEFORE_D2_IMPLEMENTATION"
        ),
        "prohibited_actions": [
            "automatic contamination classification from repository-name heuristics",
            "C0 selection access",
            "C1 reserve row access",
            "candidate promotion",
            "Option C scientific decision",
        ],
        "elapsed_seconds": time.perf_counter() - overall_started,
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
    parser.add_argument("--v1-execution-ref", default=DEFAULT_EXECUTION_REF)
    parser.add_argument("--near-hamming", type=int, default=3)
    parser.add_argument("--near-max-bucket", type=int, default=250)
    parser.add_argument("--near-max-pairs", type=int, default=50_000)
    parser.add_argument("--allow-dirty", action="store_true")
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
        v1_execution_ref=args.v1_execution_ref,
        near_hamming=args.near_hamming,
        near_max_bucket=args.near_max_bucket,
        near_max_pairs=args.near_max_pairs,
        allow_dirty=args.allow_dirty,
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

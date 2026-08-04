"""Recovery-safe embedding cache and live progress for Option C0 discovery."""

from __future__ import annotations

import hashlib
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Final, TextIO

import numpy as np

from relate.experiments import option_c0_diagnostic_entrypoint as diagnostic_entrypoint
from relate.experiments import option_c0_discovery_entrypoint as identity_entrypoint
from relate.experiments import option_c0_discovery_runner as runner
from relate.experiments.option_b_embedding import (
    MAX_LENGTH,
    OUTPUT_DTYPE,
    canonical_embed_batch,
    load_canonical_backend,
    verify_fixture_preflight,
)
from relate.experiments.option_b_identity import FIXTURE_CODES
from relate.experiments.option_b_real_code import FunctionRecord, array_hash
from relate.experiments.option_c0_embedding_cache import (
    DEFAULT_CACHE_PATH,
    EmbeddingFingerprint,
    OptionC0EmbeddingCache,
)

CACHE_ENVIRONMENT_VARIABLE: Final = "OPTION_C0_EMBEDDING_CACHE"
FINGERPRINT_SCHEMA: Final = "option-c0-embedding-fingerprint-v1"


class _TeeTextIO:
    """Write redirected stderr to both its log and the Windows console."""

    def __init__(self, primary: TextIO, console: TextIO) -> None:
        self.primary = primary
        self.console = console

    def write(self, value: str) -> int:
        written = self.primary.write(value)
        self.primary.flush()
        self.console.write(value)
        self.console.flush()
        return written

    def flush(self) -> None:
        self.primary.flush()
        self.console.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.primary, name)


class ProgressReporter:
    """Human-readable phase and row progress with rate and ETA."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream or sys.stderr

    def message(self, text: str) -> None:
        print(f"[option-c0] {text}", file=self.stream, flush=True)

    def completed(self, text: str, started: float) -> None:
        self.message(f"{text} complete | elapsed={_duration(time.perf_counter() - started)}")

    def rows(
        self,
        partition: str,
        completed: int,
        total: int,
        *,
        started: float,
        cache_hits: int,
        cache_misses: int,
    ) -> None:
        elapsed = max(time.perf_counter() - started, 1e-9)
        rate = completed / elapsed
        remaining = max(total - completed, 0)
        eta = remaining / rate if rate > 0.0 else float("inf")
        percentage = 100.0 * completed / total if total else 100.0
        self.message(
            f"embed {partition}: {completed:,}/{total:,} ({percentage:5.1f}%) "
            f"| cache={cache_hits:,} hit/{cache_misses:,} miss "
            f"| {rate:,.1f} rows/s | elapsed={_duration(elapsed)} "
            f"| eta={_duration(eta)}"
        )


def _duration(seconds: float) -> str:
    if not np.isfinite(seconds):
        return "unknown"
    value = max(int(round(seconds)), 0)
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes:d}m{secs:02d}s"
    return f"{secs:d}s"


def install_live_console_tee() -> tuple[TextIO, TextIO] | None:
    """Keep redirected logs while making progress visible in the active console."""

    if os.name != "nt" or sys.stderr.isatty():
        return None
    original = sys.stderr
    try:
        console = open(  # noqa: SIM115 - kept open for the process lifetime
            "CONOUT$",
            "w",
            encoding=getattr(original, "encoding", None) or "utf-8",
            buffering=1,
        )
    except OSError:
        return None
    sys.stderr = _TeeTextIO(original, console)
    return original, console


def restore_live_console_tee(state: tuple[TextIO, TextIO] | None) -> None:
    if state is None:
        return
    original, console = state
    sys.stderr = original
    console.close()


def embedding_fingerprint(
    *,
    lineage: dict[str, Any],
    embedding_identity: dict[str, Any],
    device: str,
    batch_size: int,
) -> EmbeddingFingerprint:
    """Bind cache reuse to every scientific and execution identity."""

    payload = {
        "schema": FINGERPRINT_SCHEMA,
        "source_identity_sha256": lineage["source_identity_sha256"],
        "embedding_identity_sha256": lineage["embedding_identity_sha256"],
        "model_id": embedding_identity["model"]["repo_id"],
        "model_revision": embedding_identity["model"]["revision"],
        "dataset_revision": embedding_identity["dataset"]["revision"],
        "embedding_implementation_sha256": embedding_identity["embedding_implementation_sha256"],
        "tokenization_config_sha256": embedding_identity["tokenization_config_sha256"],
        "max_length": MAX_LENGTH,
        "output_dtype": OUTPUT_DTYPE,
        "device": device,
        "fixed_batch_size": batch_size,
        "identity_variant": embedding_identity.get("identity_variant", "canonical-cpu"),
    }
    return EmbeddingFingerprint.from_payload(payload)


def embed_partition_with_cache(
    records: Sequence[FunctionRecord],
    *,
    partition: str,
    cache: OptionC0EmbeddingCache,
    fingerprint: EmbeddingFingerprint,
    embed_batch: Callable[[list[str]], np.ndarray],
    batch_size: int,
    reporter: ProgressReporter,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Assemble one ordered matrix, embedding and committing only exact misses."""

    if not records:
        raise ValueError(f"Option C0 partition is empty: {partition}")
    if batch_size <= 0:
        raise ValueError("embedding batch size must be positive")

    started = time.perf_counter()
    vectors: list[np.ndarray | None] = [None] * len(records)
    missing: list[int] = []
    hits = 0
    for index, record in enumerate(records):
        actual_code_sha256 = hashlib.sha256(record.code.encode()).hexdigest()
        if actual_code_sha256 != record.code_sha256:
            raise ValueError(f"source code hash mismatch in {partition} row {index}")
        vector = cache.get(
            stable_key=record.stable_key,
            code_sha256=record.code_sha256,
            fingerprint_sha256=fingerprint.sha256,
        )
        if vector is None:
            missing.append(index)
        else:
            vectors[index] = vector
            hits += 1

    misses = len(missing)
    reporter.message(
        f"cache {partition}: {hits:,} hit/{misses:,} miss "
        f"| total={len(records):,} | fingerprint={fingerprint.sha256[:12]}"
    )

    generated = 0
    padded_rows = 0
    progress_stride = max(batch_size, 250)
    next_progress = progress_stride
    for start in range(0, misses, batch_size):
        indices = missing[start : start + batch_size]
        real_count = len(indices)
        codes = [records[index].code for index in indices]
        if real_count < batch_size:
            padded_rows += batch_size - real_count
            codes.extend([codes[-1]] * (batch_size - real_count))
        matrix = np.asarray(embed_batch(codes), dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != batch_size:
            raise ValueError("embedding backend returned an invalid fixed-batch matrix")
        if not np.isfinite(matrix).all():
            raise ValueError("embedding backend returned non-finite values")

        for offset, record_index in enumerate(indices):
            vector = np.ascontiguousarray(matrix[offset], dtype=np.float32)
            record = records[record_index]
            cache.put(
                stable_key=record.stable_key,
                code_sha256=record.code_sha256,
                fingerprint_sha256=fingerprint.sha256,
                vector=vector,
            )
            vectors[record_index] = vector
        cache.commit()
        generated += real_count

        if generated >= next_progress or generated == misses:
            reporter.rows(
                partition,
                hits + generated,
                len(records),
                started=started,
                cache_hits=hits,
                cache_misses=misses,
            )
            while next_progress <= generated:
                next_progress += progress_stride

    if misses == 0:
        reporter.rows(
            partition,
            len(records),
            len(records),
            started=started,
            cache_hits=hits,
            cache_misses=0,
        )

    if any(vector is None for vector in vectors):
        raise RuntimeError(f"Option C0 cache assembly is incomplete: {partition}")
    assembled = np.stack([vector for vector in vectors if vector is not None]).astype(
        np.float32,
        copy=False,
    )
    if assembled.shape[0] != len(records) or not np.isfinite(assembled).all():
        raise ValueError(f"assembled Option C0 embedding matrix is invalid: {partition}")

    return assembled, {
        "rows": len(records),
        "cache_hits": hits,
        "cache_misses": misses,
        "vectors_generated": generated,
        "padded_rows": padded_rows,
        "dimensions": int(assembled.shape[1]),
        "dtype": str(assembled.dtype),
        "array_sha256": array_hash(assembled),
        "seconds": time.perf_counter() - started,
    }


def cached_embed_prepared_data(
    prepared: runner.PreparedData,
    source_identity_path: Path,
    embedding_identity_path: Path,
    *,
    device: str,
    batch_size: int,
    cache_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Perform fixture-verified embedding with exact local recovery."""

    reporter = ProgressReporter()
    started = time.perf_counter()
    reporter.message("verifying source and embedding identities")
    _, embedding_identity, lineage = identity_entrypoint.verify_identity_pair(
        source_identity_path,
        embedding_identity_path,
        device=device,
        batch_size=batch_size,
    )
    erratum = identity_entrypoint.verify_execution_erratum()
    fingerprint = embedding_fingerprint(
        lineage=lineage,
        embedding_identity=embedding_identity,
        device=device,
        batch_size=batch_size,
    )

    reporter.message(f"loading frozen CodeBERT backend on {device}")
    torch = identity_entrypoint.configure_embedding_device(device)
    tokenizer, model, loaded_torch = load_canonical_backend(
        model_id=embedding_identity["model"]["repo_id"],
        revision=embedding_identity["model"]["revision"],
        device=device,
        cache_dir=cache_dir,
    )
    if loaded_torch is not torch:
        torch = loaded_torch
    reporter.message("running frozen ten-row embedding fixture preflight")
    preflight = verify_fixture_preflight(
        embedding_identity,
        FIXTURE_CODES,
        tokenizer,
        model,
        device=device,
        torch_module=torch,
    )
    reporter.message("embedding fixture preflight verified")

    def embed_batch(batch: list[str]) -> np.ndarray:
        return canonical_embed_batch(
            batch,
            tokenizer,
            model,
            device=device,
            torch_module=torch,
        )

    cache_path = Path(os.environ.get(CACHE_ENVIRONMENT_VARIABLE, DEFAULT_CACHE_PATH))
    matrices: dict[str, np.ndarray] = {}
    partitions: dict[str, Any] = {}
    with OptionC0EmbeddingCache(cache_path) as cache:
        cache.register_fingerprint(fingerprint)
        for name, records in (
            ("fit_model", prepared.fit_model),
            ("fit_calibration", prepared.fit_calibration),
            ("iteration", prepared.iteration),
        ):
            matrices[name], partitions[name] = embed_partition_with_cache(
                records,
                partition=name,
                cache=cache,
                fingerprint=fingerprint,
                embed_batch=embed_batch,
                batch_size=batch_size,
                reporter=reporter,
            )
        cached_rows = cache.count(fingerprint.sha256)

    reporter.completed("visible-row embedding", started)
    return matrices, {
        **lineage,
        "identity_id": embedding_identity["identity_id"],
        "identity_variant": embedding_identity.get("identity_variant", "canonical-cpu"),
        "fixture_preflight": preflight,
        "execution_erratum_checkpoint_id": erratum["checkpoint_id"],
        "execution_erratum_status": erratum["status"],
        "execution_erratum_path": str(identity_entrypoint.EXECUTION_ERRATUM).replace("\\", "/"),
        "execution_erratum_sha256": identity_entrypoint._sha256_file(
            identity_entrypoint.EXECUTION_ERRATUM
        ),
        "final_batch_padding_policy": "repeat last real code to fixed batch; discard padding",
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
        "cache": {
            "schema": "option-c0-embedding-cache-v1",
            "path": str(cache_path).replace("\\", "/"),
            "local_recovery_only": True,
            "canonical_scientific_artifact": False,
            "fingerprint_sha256": fingerprint.sha256,
            "fingerprint": fingerprint.payload,
            "cached_rows_after_run": cached_rows,
            "commit_policy": "commit every completed GPU batch",
            "partitions": partitions,
        },
    }


def install_phase_progress(reporter: ProgressReporter) -> dict[str, Any]:
    """Expose progress for the non-embedding stages without changing their results."""

    originals: dict[str, Any] = {
        "reconstruct_visible_records": runner.reconstruct_visible_records,
        "prepare_visible_data": runner.prepare_visible_data,
        "fit_primitive_models": runner.fit_primitive_models,
        "evaluate_query": runner.evaluate_query,
    }

    def reconstruct_visible_records(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        reporter.message("reconstructing and verifying visible C0 source rows")
        value = originals["reconstruct_visible_records"](*args, **kwargs)
        reporter.completed("visible-row reconstruction", started)
        return value

    def prepare_visible_data(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        reporter.message("partitioning C0 fit rows into model and calibration repositories")
        value = originals["prepare_visible_data"](*args, **kwargs)
        reporter.completed("fit/calibration partition", started)
        return value

    def fit_primitive_models(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        reporter.message("fitting grouped cross-validated primitive Ridge models")
        value = originals["fit_primitive_models"](*args, **kwargs)
        reporter.completed("primitive model fitting", started)
        return value

    def evaluate_query(query: Any, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        reporter.message(f"evaluating query {query.query_id}")
        value = originals["evaluate_query"](query, *args, **kwargs)
        reporter.completed(f"query {query.query_id}", started)
        return value

    runner.reconstruct_visible_records = reconstruct_visible_records
    runner.prepare_visible_data = prepare_visible_data
    runner.fit_primitive_models = fit_primitive_models
    runner.evaluate_query = evaluate_query
    return originals


def restore_phase_progress(originals: dict[str, Any]) -> None:
    for name, value in originals.items():
        setattr(runner, name, value)


def main() -> None:
    tee_state = install_live_console_tee()
    reporter = ProgressReporter()
    original_embed = identity_entrypoint.embed_prepared_data_with_identity_roles
    phase_originals = install_phase_progress(reporter)
    identity_entrypoint.embed_prepared_data_with_identity_roles = cached_embed_prepared_data
    reporter.message(
        "recovery cache enabled at "
        f"{os.environ.get(CACHE_ENVIRONMENT_VARIABLE, str(DEFAULT_CACHE_PATH))}"
    )
    try:
        diagnostic_entrypoint.main()
    finally:
        identity_entrypoint.embed_prepared_data_with_identity_roles = original_embed
        restore_phase_progress(phase_originals)
        restore_live_console_tee(tee_state)


if __name__ == "__main__":
    main()

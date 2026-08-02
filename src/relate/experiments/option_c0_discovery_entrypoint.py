"""Pre-execution identity adapter for the Option C0 discovery runner.

The frozen C0 runner reconstructs source rows from the Option B v1 external
identity, while embedding certification belongs to the later Option B v2
embedding identity. This module keeps those roles separate and delegates all
mechanism evaluation to the reviewed discovery runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Final

import numpy as np

from relate.experiments import option_c0_discovery_runner as runner
from relate.experiments.option_b_embedding import (
    canonical_embed_batch,
    load_canonical_backend,
    verify_fixture_preflight,
)
from relate.experiments.option_b_identity import FIXTURE_CODES
from relate.experiments.option_b_real_code import MODEL_ID
from relate.experiments.option_b_selection import DATASET_ID, load_identity

SOURCE_IDENTITY: Final = Path(
    "artifacts/canonical/option-b/option-b-external-identity-v1.json"
)
CPU_EMBEDDING_IDENTITY: Final = Path(
    "artifacts/canonical/option-b/option-b-embedding-identity-v2.json"
)
CUDA_EMBEDDING_IDENTITY: Final = Path(
    "artifacts/canonical/option-b/embedding-reproduction-v2/"
    "option-b-embedding-identity-v2-gpu-batch10.json"
)
EXECUTION_ERRATUM: Final = Path(
    "artifacts/canonical/option-c0/candidate-plan-v1/"
    "option-c0-discovery-execution-identity-erratum-v1.json"
)


class DiscoveryIdentityError(RuntimeError):
    """Raised when source and embedding identity roles are inconsistent."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiscoveryIdentityError(f"identity artifact must be a JSON object: {path}")
    return value


def select_embedding_identity_path(device: str) -> Path:
    """Select the reviewed Option B embedding identity for the execution device."""

    return CUDA_EMBEDDING_IDENTITY if device.startswith("cuda") else CPU_EMBEDDING_IDENTITY


def verify_identity_pair(
    source_identity_path: Path,
    embedding_identity_path: Path,
    *,
    device: str,
    batch_size: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify v1 source lineage and the device-specific v2 embedding identity."""

    source = load_identity(source_identity_path)
    embedding = _load_json(embedding_identity_path)
    if embedding.get("status") != "EMBEDDING_IDENTITY_V2_COMPLETE":
        raise DiscoveryIdentityError("embedding identity v2 checkpoint is incomplete")
    if embedding.get("identity_id") != "option-b-embedding-identity-v2":
        raise DiscoveryIdentityError("unexpected embedding identity id")

    source_model = source.get("model", {})
    embedding_model = embedding.get("model", {})
    if (
        source_model.get("repo_id") != MODEL_ID
        or embedding_model.get("repo_id") != MODEL_ID
        or source_model.get("revision") != embedding_model.get("revision")
    ):
        raise DiscoveryIdentityError("source and embedding model identities differ")

    source_dataset = source.get("dataset", {})
    embedding_dataset = embedding.get("dataset", {})
    dataset_fields = ("repo_id", "revision", "subset")
    if source_dataset.get("repo_id") != DATASET_ID or any(
        source_dataset.get(field) != embedding_dataset.get(field)
        for field in dataset_fields
    ):
        raise DiscoveryIdentityError("source and embedding dataset identities differ")

    predecessor = embedding.get("predecessor", {})
    if predecessor.get("identity_id") != source.get("identity_id"):
        raise DiscoveryIdentityError("embedding identity predecessor id mismatch")
    source_sha = _sha256_file(source_identity_path)
    if predecessor.get("file_sha256") != source_sha:
        raise DiscoveryIdentityError("embedding identity predecessor hash mismatch")

    if batch_size <= 0:
        raise DiscoveryIdentityError("embedding batch size must be positive")
    if device.startswith("cuda"):
        frozen = embedding.get("protocol_amendment", {}).get("frozen_execution", {})
        if embedding.get("identity_variant") != "gpu-fixed-batch10-amendment-v1":
            raise DiscoveryIdentityError("CUDA requires the reviewed fixed-batch identity")
        if frozen.get("device") != "cuda" or int(frozen.get("batch_size", 0)) != batch_size:
            raise DiscoveryIdentityError("CUDA device or batch size differs from its identity")
    else:
        if embedding.get("environment", {}).get("canonical_device") != "cpu":
            raise DiscoveryIdentityError("CPU execution requires the canonical CPU identity")
        invariant = embedding.get("fixture", {}).get("batch_invariance", {}).get(
            str(batch_size), {}
        )
        if invariant.get("exactly_equal_to_canonical") is not True:
            raise DiscoveryIdentityError("CPU batch size is not certified by identity v2")

    return source, embedding, {
        "source_identity_path": str(source_identity_path).replace("\\", "/"),
        "source_identity_sha256": source_sha,
        "embedding_identity_path": str(embedding_identity_path).replace("\\", "/"),
        "embedding_identity_sha256": _sha256_file(embedding_identity_path),
        "model_revision": str(embedding_model["revision"]),
        "dataset_revision": str(embedding_dataset["revision"]),
        "device": device,
        "batch_size": batch_size,
    }


def verify_execution_erratum(path: Path = EXECUTION_ERRATUM) -> dict[str, Any]:
    """Require the reviewed pre-execution correction before mechanism evaluation."""

    value = _load_json(path)
    if value.get("checkpoint_id") != "option-c0-discovery-execution-identity-erratum-v1":
        raise DiscoveryIdentityError("unexpected C0 execution identity erratum")
    for field in (
        "scientific_result_observed",
        "mechanism_result_observed",
        "c0_selection_accessed",
        "c1_rows_selected",
        "canonical_result_artifact_created",
        "remote_result_branch_created",
    ):
        if value.get(field) is not False:
            raise DiscoveryIdentityError(f"execution erratum must keep {field}=false")
    if value.get("embedding_rows_generated") != 0:
        raise DiscoveryIdentityError("execution erratum must record zero generated embeddings")
    if value.get("observed_before_mechanism_result") is not True:
        raise DiscoveryIdentityError("execution correction was not recorded pre-result")
    return value


def configure_embedding_device(device: str) -> Any:
    """Apply the already reviewed Option B deterministic CUDA execution settings."""

    import torch

    if device.startswith("cuda"):
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    return torch


def fixed_batch_embed(
    codes: Sequence[str],
    embed_batch: Callable[[list[str]], np.ndarray],
    *,
    batch_size: int,
) -> tuple[np.ndarray, int]:
    """Embed every model call at one certified batch shape.

    A final short batch repeats its last real code only to fill the model call;
    padded outputs are discarded and never enter the experiment.
    """

    if not codes:
        raise ValueError("fixed-batch embedding requires at least one code row")
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    chunks: list[np.ndarray] = []
    padded_rows = 0
    for start in range(0, len(codes), batch_size):
        real = list(codes[start : start + batch_size])
        real_count = len(real)
        if real_count < batch_size:
            padded_rows += batch_size - real_count
            real.extend([real[-1]] * (batch_size - real_count))
        matrix = np.asarray(embed_batch(real), dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != batch_size:
            raise ValueError("embedding backend returned an invalid fixed-batch matrix")
        chunks.append(matrix[:real_count])
    result = np.concatenate(chunks, axis=0).astype(np.float32, copy=False)
    if result.shape[0] != len(codes) or not np.isfinite(result).all():
        raise ValueError("fixed-batch embedding output is invalid")
    return result, padded_rows


def embed_prepared_data_with_identity_roles(
    prepared: runner.PreparedData,
    source_identity_path: Path,
    embedding_identity_path: Path,
    *,
    device: str,
    batch_size: int,
    cache_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Embed visible C0 rows under the matching Option B v2 execution identity."""

    _, embedding_identity, lineage = verify_identity_pair(
        source_identity_path,
        embedding_identity_path,
        device=device,
        batch_size=batch_size,
    )
    erratum = verify_execution_erratum()
    torch = configure_embedding_device(device)
    tokenizer, model, loaded_torch = load_canonical_backend(
        model_id=embedding_identity["model"]["repo_id"],
        revision=embedding_identity["model"]["revision"],
        device=device,
        cache_dir=cache_dir,
    )
    if loaded_torch is not torch:
        torch = loaded_torch
    preflight = verify_fixture_preflight(
        embedding_identity,
        FIXTURE_CODES,
        tokenizer,
        model,
        device=device,
        torch_module=torch,
    )

    matrices: dict[str, np.ndarray] = {}
    padding: dict[str, int] = {}
    for name, records in (
        ("fit_model", prepared.fit_model),
        ("fit_calibration", prepared.fit_calibration),
        ("iteration", prepared.iteration),
    ):
        codes, _, _ = runner._record_arrays(records)

        def embed_batch(batch: list[str]) -> np.ndarray:
            return canonical_embed_batch(
                batch,
                tokenizer,
                model,
                device=device,
                torch_module=torch,
            )

        matrices[name], padding[name] = fixed_batch_embed(
            codes,
            embed_batch,
            batch_size=batch_size,
        )

    return matrices, {
        **lineage,
        "identity_id": embedding_identity["identity_id"],
        "identity_variant": embedding_identity.get("identity_variant", "canonical-cpu"),
        "fixture_preflight": preflight,
        "execution_erratum_path": str(EXECUTION_ERRATUM).replace("\\", "/"),
        "execution_erratum_sha256": _sha256_file(EXECUTION_ERRATUM),
        "final_batch_padding_policy": "repeat last real code to fixed batch; discard padding",
        "padded_rows_by_partition": padding,
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
    }


def run_discovery_iteration_with_identity_roles(
    *,
    plan_path: Path,
    registry_path: Path,
    source_identity_path: Path,
    embedding_identity_path: Path,
    canonical_firewall_dir: Path,
    output_dir: Path,
    device: str,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Delegate the frozen mechanism run while correcting only identity plumbing."""

    plan = runner.load_discovery_plan(plan_path)
    original = runner.embed_prepared_data

    def embed_adapter(
        prepared: runner.PreparedData,
        identity_path: Path,
        *,
        device: str,
        batch_size: int,
        cache_dir: Path | None = None,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        if identity_path.resolve() != source_identity_path.resolve():
            raise DiscoveryIdentityError("runner source identity changed unexpectedly")
        return embed_prepared_data_with_identity_roles(
            prepared,
            source_identity_path,
            embedding_identity_path,
            device=device,
            batch_size=batch_size,
            cache_dir=cache_dir,
        )

    if plan.embedding_batch_size <= 0:
        raise DiscoveryIdentityError("candidate plan contains an invalid embedding batch size")
    runner.embed_prepared_data = embed_adapter
    try:
        return runner.run_discovery_iteration(
            plan_path=plan_path,
            registry_path=registry_path,
            identity_path=source_identity_path,
            canonical_firewall_dir=canonical_firewall_dir,
            output_dir=output_dir,
            device=device,
            cache_dir=cache_dir,
        )
    finally:
        runner.embed_prepared_data = original


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--identity", type=Path, default=SOURCE_IDENTITY)
    parser.add_argument("--embedding-identity", type=Path)
    parser.add_argument("--canonical-firewall-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    embedding_identity = args.embedding_identity or select_embedding_identity_path(args.device)
    plan = runner.load_discovery_plan(args.plan)
    verify_identity_pair(
        args.identity,
        embedding_identity,
        device=args.device,
        batch_size=plan.embedding_batch_size,
    )
    verify_execution_erratum()

    if args.validate_only:
        result = runner.validate_discovery_setup(
            args.plan,
            args.registry,
            args.canonical_firewall_dir,
        )
        result["source_identity_sha256"] = _sha256_file(args.identity)
        result["embedding_identity_sha256"] = _sha256_file(embedding_identity)
        result["execution_erratum_sha256"] = _sha256_file(EXECUTION_ERRATUM)
    else:
        if args.output_dir is None:
            parser.error("--output-dir is required unless --validate-only is used")
        result = run_discovery_iteration_with_identity_roles(
            plan_path=args.plan,
            registry_path=args.registry,
            source_identity_path=args.identity,
            embedding_identity_path=embedding_identity,
            canonical_firewall_dir=args.canonical_firewall_dir,
            output_dir=args.output_dir,
            device=args.device,
            cache_dir=args.cache_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

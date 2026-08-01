"""Lightweight Option B embedding-environment preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from relate.experiments.option_b_embedding import (
    load_canonical_backend,
    verify_fixture_preflight,
)
from relate.experiments.option_b_embeddings import DEFAULT_IDENTITY, load_json
from relate.experiments.option_b_identity import FIXTURE_CODES
from relate.experiments.option_b_real_code import MODEL_ID


def run_preflight(identity_path: Path, *, device: str) -> dict[str, Any]:
    identity = load_json(identity_path)
    if identity.get("status") != "EMBEDDING_IDENTITY_V2_COMPLETE":
        raise ValueError("embedding identity v2 checkpoint is incomplete")
    if identity.get("identity_id") != "option-b-embedding-identity-v2":
        raise ValueError("unexpected embedding identity id")

    revision = identity["model"]["revision"]
    tokenizer, model, torch = load_canonical_backend(
        model_id=MODEL_ID,
        revision=revision,
        device=device,
    )
    result = verify_fixture_preflight(
        identity,
        FIXTURE_CODES,
        tokenizer,
        model,
        device=device,
        torch_module=torch,
    )
    cuda_runtime = getattr(getattr(torch, "version", None), "cuda", None)
    gpu_name = None
    if device.startswith("cuda") and torch.cuda.is_available():
        index = int(device.split(":", 1)[1]) if ":" in device else 0
        gpu_name = torch.cuda.get_device_name(index)
    return {
        "status": "EMBEDDING_ENVIRONMENT_PREFLIGHT_VERIFIED",
        "scientific_result_observed": False,
        "identity_id": identity["identity_id"],
        "identity_path": str(identity_path).replace("\\", "/"),
        "model_revision": revision,
        "fixture": result,
        "runtime": {
            "torch": torch.__version__,
            "device": device,
            "cuda_runtime": cuda_runtime,
            "gpu_name": gpu_name,
        },
        "next_allowed_action": "INDEPENDENT_EMBEDDING_RUN_A",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    print(json.dumps(run_preflight(args.identity, device=args.device), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

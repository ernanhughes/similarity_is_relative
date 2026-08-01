"""Freeze a verified E00 local run into compact public checkpoint records."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from relate.verification.e00 import verify

CHECKPOINT_ID = "e00-baseline-checkpoint-v1"
README_START = "<!-- RELATE:E00:CHECKPOINT:START -->"
README_END = "<!-- RELATE:E00:CHECKPOINT:END -->"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _selected_metrics(manifest: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for regime, payload in manifest["regimes"].items():
        metrics = payload["ridge_predicted_distance"]
        item: dict[str, Any] = {
            "target_kind": metrics["target_kind"],
            "spearman": metrics["spearman"],
            "triplet_accuracy": metrics["triplet_accuracy"],
            "recall_at_10": metrics["recall_at"]["10"],
            "neighbor_regret_at_10": metrics["neighbor_regret_at"]["10"],
        }
        if metrics["target_kind"] == "continuous":
            item["within_tolerance_at_10"] = metrics["within_tolerance_at"]["10"]
            item["ndcg_at_10"] = metrics["ndcg_at"]["10"]
        else:
            item["average_precision"] = metrics["average_precision"]
            item["class_precision_at_10"] = metrics["class_precision_at"]["10"]
            item["class_recall_at_10"] = metrics["class_recall_at"]["10"]
        summary[regime] = item
    return summary


def _markdown(checkpoint: dict[str, Any]) -> str:
    rows = []
    for regime, metrics in checkpoint["baseline_summary"].items():
        rows.append(
            f"| `{regime}` | {metrics['target_kind']} | "
            f"{metrics['spearman']:.4f} | {metrics['triplet_accuracy']:.4f} | "
            f"{metrics['recall_at_10']:.4f} |"
        )
    table = "\n".join(rows)
    return f"""# E00 Baseline Checkpoint v1

- **Checkpoint:** `{checkpoint['checkpoint_id']}`
- **Status:** `{checkpoint['status']}`
- **Scientific status:** `{checkpoint['scientific_status']}`
- **Manifest SHA-256:** `{checkpoint['manifest_sha256']}`
- **Verification SHA-256:** `{checkpoint['verification_sha256']}`
- **Claim promotion allowed:** `{str(checkpoint['claim_promotion_allowed']).lower()}`
- **Recorded at:** `{checkpoint['recorded_at_utc']}`

## Baseline summary

| Regime | Target | Spearman | Triplet accuracy | Recall@10 |
|---|---|---:|---:|---:|
{table}

## Decision

The deterministic generator, artifact identities, ridge baseline and target-specific
metric verifier passed. This is a **baseline checkpoint**, not a completed E00
scientific result. The next required work is the registered operator suite,
permutation nulls, bootstrap intervals and certification decision.

## Reproduce

```powershell
.\\scripts\\10-run-e00.ps1
.\\scripts\\11-verify-e00.ps1
.\\scripts\\12-finalize-e00.ps1
```
"""


def _update_readme(path: Path, checkpoint: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8")
    block = f"""{README_START}
## E00 baseline checkpoint

- Checkpoint: **`{checkpoint['checkpoint_id']}`**
- Local artifact verification: **PASS**
- Verified regimes / metric sets: **6 / 6**
- Scientific claim promotion: **blocked**
- Manifest: **`{checkpoint['manifest_sha256']}`**
- Public record: [`docs/results/{CHECKPOINT_ID}.md`](docs/results/{CHECKPOINT_ID}.md)

The ridge checkpoint validates the experiment machinery only. E00 remains incomplete
until the registered operator and null suite is verified.
{README_END}"""
    if README_START in text and README_END in text:
        before, remainder = text.split(README_START, 1)
        _, after = remainder.split(README_END, 1)
        updated = before.rstrip() + "\n\n" + block + after
    else:
        marker = "## Development"
        updated = text.replace(marker, block + "\n\n" + marker)
    path.write_text(updated, encoding="utf-8")


def finalize(
    run_directory: Path,
    repository_root: Path,
    *,
    update_readme: bool = True,
) -> dict[str, Any]:
    report = verify(run_directory)
    if report["status"] != "PASS":
        raise RuntimeError(f"E00 verification failed: {report['errors']}")

    manifest_path = run_directory / "manifest.json"
    result_path = run_directory / "result.json"
    verification_path = run_directory / "verification.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not verification_path.exists():
        verification_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    checkpoint: dict[str, Any] = {
        "checkpoint_id": CHECKPOINT_ID,
        "experiment_id": manifest["experiment_id"],
        "status": "BASELINE_VERIFIED",
        "scientific_status": "E00_INCOMPLETE",
        "decision": "CONTINUE_TO_OPERATOR_SUITE",
        "claim_promotion_allowed": bool(report["claim_promotion_allowed"]),
        "verified_regimes": report["verified_regimes"],
        "verified_metric_sets": report["verified_metric_sets"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_before_publication": _git_value("rev-parse", "HEAD"),
        "git_branch": _git_value("branch", "--show-current"),
        "manifest_sha256": _sha256(manifest_path),
        "result_sha256": _sha256(result_path),
        "verification_sha256": _sha256(verification_path),
        "rotation_sha256": manifest["rotation_sha256"],
        "split_hashes": manifest["split_hashes"],
        "config": manifest["config"],
        "artifact_identities": {
            regime: {
                "x_sha256": payload["x_sha256"],
                "y_sha256": payload["y_sha256"],
            }
            for regime, payload in manifest["regimes"].items()
        },
        "baseline_summary": _selected_metrics(manifest),
        "publication_boundary": (
            "This checkpoint verifies the E00 ridge baseline machinery only. "
            "It does not support a RELATE recoverability, composition, or abstention claim."
        ),
    }

    results_dir = repository_root / "docs" / "results"
    canonical_dir = repository_root / "artifacts" / "canonical" / "e00"
    results_dir.mkdir(parents=True, exist_ok=True)
    canonical_dir.mkdir(parents=True, exist_ok=True)

    public_json = results_dir / f"{CHECKPOINT_ID}.json"
    public_md = results_dir / f"{CHECKPOINT_ID}.md"
    canonical_json = canonical_dir / f"{CHECKPOINT_ID}.json"

    payload = json.dumps(checkpoint, indent=2, sort_keys=True) + "\n"
    public_json.write_text(payload, encoding="utf-8")
    canonical_json.write_text(payload, encoding="utf-8")
    public_md.write_text(_markdown(checkpoint), encoding="utf-8")

    if update_readme:
        _update_readme(repository_root / "README.md", checkpoint)

    return checkpoint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-directory",
        type=Path,
        default=Path("runs/e00/canonical-seed-17"),
    )
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--no-readme-update", action="store_true")
    args = parser.parse_args()
    checkpoint = finalize(
        args.run_directory,
        args.repository_root,
        update_readme=not args.no_readme_update,
    )
    print(json.dumps(checkpoint, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

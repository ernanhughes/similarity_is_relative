"""Run the reviewed Option B primitive-probe fit with no scientific tuning knobs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from relate.experiments.option_b_probe_runner import (
    DEFAULT_EMBEDDING_CHECKPOINT,
    DEFAULT_EMBEDDING_DIR,
    DEFAULT_EMBEDDING_REPORT,
    DEFAULT_GPU_AMENDMENT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SELECTION_DIR,
    run_probe_fit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-checkpoint", type=Path, default=DEFAULT_EMBEDDING_CHECKPOINT)
    parser.add_argument("--gpu-amendment", type=Path, default=DEFAULT_GPU_AMENDMENT)
    parser.add_argument("--selection-dir", type=Path, default=DEFAULT_SELECTION_DIR)
    parser.add_argument("--embedding-report", type=Path, default=DEFAULT_EMBEDDING_REPORT)
    parser.add_argument("--embedding-dir", type=Path, default=DEFAULT_EMBEDDING_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_probe_fit(
        checkpoint_path=args.embedding_checkpoint,
        amendment_path=args.gpu_amendment,
        selection_dir=args.selection_dir,
        embedding_report_path=args.embedding_report,
        embedding_dir=args.embedding_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

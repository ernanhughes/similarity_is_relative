"""Immutable file and artifact write protection.

Provides explicit overwrite-refusal guards so that canonical evidence files
are not silently replaced.

This module must not import from relate.experiments.
"""

from __future__ import annotations

from pathlib import Path


def refuse_overwrite(path: Path, label: str = "") -> None:
    """Raise FileExistsError if *path* already exists.

    *label* is included in the error message to identify the artifact.
    """
    if path.exists():
        suffix = f": {label}" if label else f": {path}"
        raise FileExistsError(f"immutable artifact refuses overwrite{suffix}")

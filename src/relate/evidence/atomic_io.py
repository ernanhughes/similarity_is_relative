"""Atomic file I/O utilities.

Provides:

atomic_write_json(path, value)
    Write *value* as indented JSON to *path* atomically.
    Creates parent directories, writes to a temporary sibling, fsyncs the
    file, replaces the target atomically, then fsyncs the parent directory.
    Cleans up the temporary file on failure.

fsync_directory(path)
    fsync a directory descriptor on POSIX systems (no-op on Windows).

The JSON format produced by atomic_write_json is:
    json.dumps(value, indent=2, sort_keys=True) + "\\n"
    encoded as UTF-8 in binary write mode.

This module must not import from relate.experiments or contain scientific schemas.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def fsync_directory(path: Path) -> None:
    """fsync the directory at *path* on POSIX. No-op on Windows."""
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write *value* as indented JSON to *path* atomically.

    Creates parent directories. Writes to a UUID-named temporary sibling,
    fsyncs the data, replaces the destination atomically, then fsyncs the
    parent directory. Removes the temporary file on any failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)

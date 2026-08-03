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


def atomic_create_bytes_no_replace(destination: Path, content: bytes) -> None:
    """Create *destination* from complete bytes without overwrite or replacement.

    The temporary file is created exclusively in the destination's parent, then
    linked into place with ``os.link``. The link operation fails if the
    destination appears concurrently. This function intentionally does not fall
    back to replace semantics.
    """
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")
    if not destination.parent.exists():
        raise FileNotFoundError(f"destination parent is missing: {destination.parent}")
    temporary = destination.with_name(f".{destination.name}.tmp-{uuid.uuid4().hex}")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            os.close(descriptor)
            raise
        os.link(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)

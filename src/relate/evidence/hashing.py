"""SHA-256 hashing utilities.

Provides three stable entry points:

sha256_bytes(payload)   Hash a bytes object directly.
sha256_text(text)       Encode text to UTF-8 then hash.
sha256_file(path)       Stream-hash a file in 1 MiB chunks.

All functions return a lowercase 64-character hexadecimal string.

sha256_file uses streaming so that large files do not require loading the
entire content into memory at once.

This module must not import from relate.experiments.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 hex digest of *payload*."""
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    """Encode *text* as UTF-8 and return its SHA-256 hex digest."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at *path*, streamed in 1 MiB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

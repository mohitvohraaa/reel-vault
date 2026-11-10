"""Filesystem helpers for uploads and media storage."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str) -> str:
    """Strip path components and dangerous characters from an uploaded filename."""
    name = os.path.basename(name or "upload")
    keep = "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip()
    return keep or "upload"


def remove_quietly(path: str | Path | None) -> None:
    if not path:
        return
    p = Path(path)
    try:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    except OSError:
        pass

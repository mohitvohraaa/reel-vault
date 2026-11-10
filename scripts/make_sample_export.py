#!/usr/bin/env python3
"""Generate a synthetic Instagram DM export (directory + zip) under sample_data/.

Usage:
    python scripts/make_sample_export.py

The output ZIP can be uploaded directly in the ReelVault Import page to exercise
the full pipeline without any real personal data.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tests.sample_builder import write_sample_export  # noqa: E402


def main() -> None:
    out_root = REPO_ROOT / "sample_data" / "instagram_export"
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    write_sample_export(out_root)

    zip_base = REPO_ROOT / "sample_data" / "instagram_export"
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=out_root)
    print(f"Sample export directory: {out_root}")
    print(f"Sample export ZIP:       {archive}")
    print("Upload the ZIP in the ReelVault Import page to try the pipeline end-to-end.")


if __name__ == "__main__":
    main()

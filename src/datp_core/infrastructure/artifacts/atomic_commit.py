"""Inter-process atomic commit wrapper backed by filelock."""

from __future__ import annotations

import os
from pathlib import Path

from filelock import FileLock


def atomic_write_file(target_path: Path, content: bytes) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target_path.with_suffix(target_path.suffix + ".lock")
    tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")

    with FileLock(str(lock_path), timeout=30.0):
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)

    if lock_path.exists():
        try:
            lock_path.unlink()
        except OSError:
            pass

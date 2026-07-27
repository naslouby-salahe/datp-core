from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile


def atomic_write_bytes(target: Path, payload: bytes, *, prefix: str = ".tmp_") -> None:
    with NamedTemporaryFile(mode="wb", dir=target.parent, prefix=prefix, delete=False) as temporary:
        temporary.write(payload)
        temporary.flush()
        os.fsync(temporary.fileno())
        temp_path = Path(temporary.name)
    try:
        os.replace(temp_path, target)
        fsync_directory(target.parent)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def atomic_copy_file(target: Path, source: Path, *, prefix: str = ".tmp_") -> None:
    with (
        source.open("rb") as input_file,
        NamedTemporaryFile(mode="wb", dir=target.parent, prefix=prefix, delete=False) as temporary,
    ):
        shutil.copyfileobj(input_file, temporary, length=1_048_576)
        temporary.flush()
        os.fsync(temporary.fileno())
        temp_path = Path(temporary.name)
    try:
        os.replace(temp_path, target)
        fsync_directory(target.parent)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

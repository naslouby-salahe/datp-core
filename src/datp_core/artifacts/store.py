"""Small direct-file store for experiment outputs.

The store deliberately has no artifact identity, manifests, parent lineage, repository port, or
reuse lookup. Callers supply semantic relative paths; a fresh run cannot replace an existing
file unless it makes the replacement explicit.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

from datp_core.artifacts.errors import (
    ArtifactChecksumMismatchError,
    ArtifactFileExistsError,
    ArtifactFileMissingError,
    InvalidArtifactPathError,
)
from datp_core.core.hashing import Checksum, compute_file_checksum


class ArtifactStore:
    """Atomic direct-file persistence rooted at one output directory."""

    def __init__(self, root: Path) -> None:
        if root.is_symlink():
            raise InvalidArtifactPathError(f"Artifact root may not be a symlink: {root}")
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise InvalidArtifactPathError(f"Artifact root must be a regular directory: {root}")
        self._root = root.resolve()

    def write_bytes_atomic(self, relative_path: str, payload: bytes, *, replace: bool = False) -> Checksum:
        """Atomically write bytes, rejecting an accidental fresh-run overwrite."""
        target = self._target(relative_path, create_parent=True)
        self._reject_existing(target, replace)
        with NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".tmp_artifact_", delete=False) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, target)
            self._fsync_directory(target.parent)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return compute_file_checksum(target)

    def write_file_atomic(self, relative_path: str, source: Path, *, replace: bool = False) -> Checksum:
        """Atomically copy a regular source file into the store."""
        if not source.is_file():
            raise ArtifactFileMissingError(f"Artifact source file is missing: {source}")
        target = self._target(relative_path, create_parent=True)
        self._reject_existing(target, replace)
        with source.open("rb") as input_file, NamedTemporaryFile(
            mode="wb", dir=target.parent, prefix=".tmp_artifact_", delete=False
        ) as temporary:
            shutil.copyfileobj(input_file, temporary, length=1_048_576)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, target)
            self._fsync_directory(target.parent)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return compute_file_checksum(target)

    def read_bytes(self, relative_path: str) -> bytes:
        target = self._target(relative_path, create_parent=False)
        if not target.is_file():
            raise ArtifactFileMissingError(f"Artifact file is missing: {relative_path}")
        return target.read_bytes()

    def exists(self, relative_path: str) -> bool:
        return self._target(relative_path, create_parent=False).is_file()

    def checksum(self, relative_path: str) -> Checksum:
        target = self._target(relative_path, create_parent=False)
        if not target.is_file():
            raise ArtifactFileMissingError(f"Artifact file is missing: {relative_path}")
        return compute_file_checksum(target)

    def validate_file(self, relative_path: str, expected_checksum: Checksum) -> None:
        actual = self.checksum(relative_path)
        if actual != expected_checksum:
            raise ArtifactChecksumMismatchError(
                f"Artifact file checksum mismatch at '{relative_path}': expected {expected_checksum}, found {actual}"
            )

    def _target(self, relative_path: str, *, create_parent: bool) -> Path:
        relative = Path(relative_path)
        if not relative_path or relative.is_absolute() or ".." in relative.parts:
            raise InvalidArtifactPathError(f"Artifact path must be a non-empty relative path: {relative_path!r}")
        parent = self._root
        for part in relative.parts[:-1]:
            candidate = parent / part
            if candidate.is_symlink():
                raise InvalidArtifactPathError(f"Artifact path traverses symlinked directory: {relative_path}")
            if candidate.exists() and not candidate.is_dir():
                raise InvalidArtifactPathError(f"Artifact path has a non-directory parent: {relative_path}")
            if create_parent:
                candidate.mkdir(exist_ok=True)
            parent = candidate
        target = self._root / relative
        if target.is_symlink():
            raise InvalidArtifactPathError(f"Artifact path is a symlink: {relative_path}")
        return target

    @staticmethod
    def _reject_existing(target: Path, replace: bool) -> None:
        if target.exists() and not replace:
            raise ArtifactFileExistsError(f"Artifact file already exists: {target}")
        if target.exists() and not target.is_file():
            raise ArtifactFileExistsError(f"Artifact target is not a file: {target}")

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


__all__ = ["ArtifactStore"]

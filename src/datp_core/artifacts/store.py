"""Small direct-file store for experiment outputs.

The store deliberately has no artifact identity, manifests, parent lineage, repository port, or
reuse lookup. Callers supply semantic relative paths; a fresh run cannot replace an existing
file unless it makes the replacement explicit.
"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from datp_core.artifacts.atomic import atomic_copy_file, atomic_write_bytes, fsync_directory
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
        target = self._target(relative_path, create_parent=True)
        self._reject_existing(target, replace)
        atomic_write_bytes(target, payload, prefix=".tmp_artifact_")
        return compute_file_checksum(target)

    def write_file_atomic(self, relative_path: str, source: Path, *, replace: bool = False) -> Checksum:
        if not source.is_file():
            raise ArtifactFileMissingError(f"Artifact source file is missing: {source}")
        target = self._target(relative_path, create_parent=True)
        self._reject_existing(target, replace)
        atomic_copy_file(target, source, prefix=".tmp_artifact_")
        return compute_file_checksum(target)

    def write_bytes_batch(
        self, payloads: dict[str, bytes], *, replace: bool = False
    ) -> dict[str, Checksum]:
        """Atomically batch-write multiple artifact files.

        Writes every payload to a temporary file, then promotes all
        temporaries to their target paths via os.replace.  If any write
        fails, all temporaries are cleaned up before the error propagates.
        """
        temps: dict[str, Path] = {}
        targets: dict[str, Path] = {}
        try:
            for relative_path, payload in payloads.items():
                target = self._target(relative_path, create_parent=True)
                self._reject_existing(target, replace)
                targets[relative_path] = target
                with NamedTemporaryFile(
                    mode="wb", dir=target.parent, prefix=".tmp_batch_", delete=False
                ) as tmp:
                    temps[relative_path] = Path(tmp.name)
                    tmp.write(payload)
                    tmp.flush()
                    os.fsync(tmp.fileno())
        except BaseException:
            for temp in temps.values():
                temp.unlink(missing_ok=True)
            raise

        try:
            for relative_path in payloads:
                os.replace(temps[relative_path], targets[relative_path])
            fsynced: set[Path] = set()
            for relative_path in payloads:
                parent = targets[relative_path].parent
                if parent not in fsynced:
                    fsynced.add(parent)
                    fsync_directory(parent)
        except BaseException:
            for temp in temps.values():
                temp.unlink(missing_ok=True)
            raise

        return {
            relative_path: compute_file_checksum(targets[relative_path])
            for relative_path in payloads
        }

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


__all__ = ["ArtifactStore"]

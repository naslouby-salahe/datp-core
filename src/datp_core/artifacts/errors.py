"""Artifact-domain exceptions."""

from __future__ import annotations


class ArtifactStoreError(ValueError):
    """Base error raised by the direct-file artifact store."""


class InvalidArtifactPathError(ArtifactStoreError):
    """Raised when a store path is absolute, empty, escapes, or traverses a symlink."""


class ArtifactFileMissingError(ArtifactStoreError):
    """Raised when a requested direct artifact file is absent."""


class ArtifactFileExistsError(ArtifactStoreError):
    """Raised when a fresh execution attempts to replace an existing artifact file."""


class ArtifactChecksumMismatchError(ArtifactStoreError):
    """Raised when a direct artifact file does not match its required checksum."""

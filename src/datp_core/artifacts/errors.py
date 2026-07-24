"""Artifact-domain exceptions."""

from __future__ import annotations


class ManifestDecodeError(ValueError):
    """Raised when manifest bytes are not valid, strict, well-formed manifest JSON."""


class ManifestSchemaIncompatibleError(ValueError):
    """Raised when a manifest's schema_version does not match the current codec version."""

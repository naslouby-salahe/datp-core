"""Catalogue use cases return only resolved, immutable domain records."""

from __future__ import annotations

from pathlib import Path

from ..kernel.errors import ConfigurationError
from .config.bundle import ConfigPaths
from .config.load import load_authored_bundle
from .config.map import map_configuration
from .config.validate import validate_references
from .domain import ResolvedConfiguration


def load_resolved_configuration(root: Path) -> ResolvedConfiguration:
    authored = load_authored_bundle(ConfigPaths.under(root))
    issues = validate_references(authored)
    if issues:
        rendered = "; ".join(f"{issue.code} at {issue.path}" for issue in issues)
        raise ConfigurationError(rendered)
    return map_configuration(authored)

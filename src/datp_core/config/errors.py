"""Configuration-specific exceptions."""

from __future__ import annotations

from pathlib import Path


class ConfigurationError(Exception):
    """Typed error for configuration loading, duplicate key, or schema validation failures."""

    def __init__(self, message: str, source_path: Path | None = None, cause: Exception | None = None) -> None:
        formatted = f"[{source_path}] {message}" if source_path else message
        super().__init__(formatted)
        self.source_path = source_path
        self.cause = cause

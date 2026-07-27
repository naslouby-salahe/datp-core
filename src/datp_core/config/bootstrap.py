"""Environment-provided bootstrap settings, configuration-root resolution, and structured logging
setup for the composition root.

These are bootstrap-time concerns: values that cannot be authored in repository YAML because they
describe how to find and interpret the repository itself.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeBootstrapSettings(BaseSettings):
    """External bootstrap settings that cannot be authored in repository YAML."""

    model_config = SettingsConfigDict(
        env_prefix="DATP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    repository_root: Path = Path(".")
    config_root: Path | None = None
    environment_identity: str = "local_linux"
    execution_profile: str = "scientific"


def resolve_config_root(settings: RuntimeBootstrapSettings) -> Path:
    """Single authority for deriving the configuration root from bootstrap settings.

    A relative or omitted ``config_root`` resolves against ``repository_root`` -- never the
    process working directory. An absolute ``config_root`` is used as authored, even if it
    points outside ``repository_root`` (an explicit override, not an accident of cwd).
    """
    repository_root = settings.repository_root.resolve()
    if settings.config_root is None:
        return (repository_root / "configs").resolve()
    if settings.config_root.is_absolute():
        return settings.config_root.resolve()
    return (repository_root / settings.config_root).resolve()


def configure_structured_logging(mode: str, level: str) -> None:
    """Configure logging from an explicitly resolved runtime profile."""
    levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }
    try:
        log_level = levels[level.upper()]
    except KeyError as exc:
        raise ValueError(f"Unknown resolved logging level: {level}") from exc

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if mode == "json":
        processors.append(structlog.processors.JSONRenderer())
    elif mode == "human":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        raise ValueError(f"Unknown resolved logging mode: {mode}")

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )


__all__ = [
    "RuntimeBootstrapSettings",
    "configure_structured_logging",
    "resolve_config_root",
]

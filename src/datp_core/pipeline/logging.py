"""Contextual structured logging setup using structlog."""

from __future__ import annotations

import logging
import sys

import structlog


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


__all__ = ["configure_structured_logging"]

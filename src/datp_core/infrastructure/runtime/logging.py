"""Contextual structured logging setup using structlog."""

from __future__ import annotations

import logging
import sys

import structlog


def configure_structured_logging(mode: str = "human", level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if mode == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.BoundLogger:
    return structlog.get_logger()

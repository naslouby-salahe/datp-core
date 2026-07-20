"""Stable framework-free errors and validation issues."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    document: str
    path: tuple[str | int, ...]
    message: str
    related_paths: tuple[tuple[str | int, ...], ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionError:
    code: str
    message: str


class ConfigurationError(ValueError):
    """Raised only while parsing invalid authored configuration."""


class RegistryError(ValueError):
    """Raised when a registry violates its immutable identity contract."""

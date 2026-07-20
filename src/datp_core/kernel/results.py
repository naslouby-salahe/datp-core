"""Closed expected-outcome union used at scientific stage boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ExecutionError, ValidationIssue


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionWarning:
    code: str
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class InfeasibilityReason:
    code: str
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DependencyBlock:
    dependency: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Completed[T]:
    value: T
    warnings: tuple[ExecutionWarning, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Infeasible:
    reason: InfeasibilityReason
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationFailed:
    issues: tuple[ValidationIssue, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionFailed:
    error: ExecutionError
    retryable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class BlockedByDependency:
    dependencies: tuple[DependencyBlock, ...]


type StageResult[T] = Completed[T] | Infeasible | ValidationFailed | ExecutionFailed | BlockedByDependency

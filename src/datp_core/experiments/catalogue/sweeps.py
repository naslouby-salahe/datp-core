"""Sweep records — value sweeps, condition sweeps, and related enums."""

from __future__ import annotations

from enum import StrEnum

from attrs import define


class SweepConditionAllocation(StrEnum):
    DIRICHLET = "dirichlet"
    EQUAL_ACROSS_SOURCE_DOMAINS = "equal_across_source_domains"


SweepValue = str | int | float | tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ValueSweepRecord:
    name: str
    values: tuple[SweepValue, ...]


@define(frozen=True, slots=True, kw_only=True)
class SweepConditionRecord:
    name: str
    allocation: SweepConditionAllocation
    dirichlet_alpha: float | None


@define(frozen=True, slots=True, kw_only=True)
class ConditionSweepRecord:
    name: str
    conditions: tuple[SweepConditionRecord, ...]


SweepRecord = ValueSweepRecord | ConditionSweepRecord

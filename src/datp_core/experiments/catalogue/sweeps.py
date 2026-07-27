"""Sweep records — value sweeps, condition sweeps, and related enums."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SweepConditionAllocation(StrEnum):
    DIRICHLET = "dirichlet"
    EQUAL_ACROSS_SOURCE_DOMAINS = "equal_across_source_domains"


SweepValue = str | int | float | tuple[str, ...]


class ValueSweepRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    values: tuple[SweepValue, ...]


class SweepConditionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    allocation: SweepConditionAllocation
    dirichlet_alpha: float | None


class ConditionSweepRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    conditions: tuple[SweepConditionRecord, ...]


SweepRecord = ValueSweepRecord | ConditionSweepRecord

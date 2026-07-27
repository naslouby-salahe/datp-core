"""Evaluation specification and recalibration records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum, StrEnum
from typing import cast

from pydantic import BaseModel, ConfigDict, field_validator

from datp_core.core.identifiers import PopulationId, ThresholdPolicyId


class RunRequirement(Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    EXPLORATORY = "exploratory"
    OPTIONAL = "optional"


class RecalibrationMode(StrEnum):
    FROZEN = "frozen"
    ONE_SHOT = "one_shot"
    NOT_APPLICABLE = "not_applicable"


class EvaluationSpecRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    label: str
    threshold_policy_id: ThresholdPolicyId
    run_requirement: RunRequirement
    overrides: Mapping[str, object] | None = None
    population_id: PopulationId | None
    recalibration_mode: RecalibrationMode | None

    @field_validator("overrides", mode="before")
    @classmethod
    def _convert_overrides(cls, v: object) -> Mapping[str, object] | None:
        return dict(cast("Iterable[tuple[str, object]]", v)) if v is not None else None

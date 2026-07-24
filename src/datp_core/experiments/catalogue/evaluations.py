"""Evaluation specification and recalibration records."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, StrEnum

from attrs import define, field

from datp_core.core.identifiers import PopulationId, ThresholdPolicyId
from datp_core.core.immutability import (
    FrozenJson,
    as_optional_frozen_json_mapping,
)


class RunRequirement(Enum):
    MANDATORY = "mandatory"
    CONDITIONAL = "conditional"
    EXPLORATORY = "exploratory"
    OPTIONAL = "optional"


class RecalibrationMode(StrEnum):
    FROZEN = "frozen"
    ONE_SHOT = "one_shot"
    NOT_APPLICABLE = "not_applicable"


@define(frozen=True, slots=True, kw_only=True)
class EvaluationSpecRecord:
    label: str
    threshold_policy_id: ThresholdPolicyId
    run_requirement: RunRequirement
    overrides: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    population_id: PopulationId | None
    recalibration_mode: RecalibrationMode | None

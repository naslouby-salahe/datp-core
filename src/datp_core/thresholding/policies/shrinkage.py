"""Local-global shrinkage and calibration-fallback threshold policy records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from datp_core.thresholding.policies.enums import ThresholdOwnership, ThresholdPolicyKind


class PermittedWeightRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum: float
    maximum: float

    @classmethod
    def from_config(cls, config: Mapping[str, float]) -> PermittedWeightRange:
        return cls(minimum=float(config.get("minimum", 0.0)), maximum=float(config.get("maximum", 1.0)))


class WeightFormulaConstants(BaseModel):
    model_config = ConfigDict(frozen=True)

    n_half: int

    @classmethod
    def from_config(cls, config: Mapping[str, int]) -> WeightFormulaConstants:
        return cls(n_half=int(config["n_half"]))


class LocalGlobalShrinkageThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ClassVar[ThresholdPolicyKind] = ThresholdPolicyKind.SHRINKAGE
    policy: Literal["local_global_shrinkage_threshold"]
    quantile: float
    quantile_estimator: str
    local_reference: str
    global_reference: str
    interpolation_formula: str
    weight_semantics: str
    weight_scope: str
    permitted_weight_range: PermittedWeightRange
    shrinkage_weight_grid: tuple[float, ...]
    shrinkage_weight: float | None
    shrinkage_weight_resolution: str
    out_of_range_weight_behavior: str
    effective_lambda_reporting: str
    threshold_ownership: ThresholdOwnership


class CalibrationFallbackThresholdPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ClassVar[ThresholdPolicyKind] = ThresholdPolicyKind.CALIBRATION_FALLBACK
    policy: Literal["calibration_size_aware_fallback_threshold"]
    quantile: float
    quantile_estimator: str
    local_reference: str
    global_reference: str
    interpolation_formula: str
    weight_semantics: str
    weight_scope: str
    weight_formula: str
    weight_formula_constants: WeightFormulaConstants
    weight_monotone_in_calibration_count: bool
    clamping: str
    permitted_weight_range: PermittedWeightRange
    zero_calibration_behavior: str
    minimum_calibration_behavior: str
    effective_lambda_reporting: str
    fallback_frequency_reporting: str
    threshold_ownership: ThresholdOwnership

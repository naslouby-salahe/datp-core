"""Shared threshold policy infrastructure: defaults record, quantile estimator record, and benign calibration scores."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import ClientId, PopulationId


def _as_tuple_str(value: object) -> tuple[str, ...]:
    return tuple(cast("Iterable[str]", value))


def _as_tuple_float(value: object) -> tuple[float, ...]:
    return tuple(cast("Iterable[float]", value))


def _as_mapping_str_int(value: object) -> Mapping[str, int]:
    return dict(cast("Iterable[tuple[str, int]]", value))


def _as_mapping_str_float(value: object) -> Mapping[str, float]:
    return dict(cast("Iterable[tuple[str, float]]", value))


def _as_mapping_str_object(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", dict(value))  # type: ignore[reportArgumentType]


def _as_mapping_str_str_or_int(value: object) -> Mapping[str, str | int]:
    return dict(cast("Iterable[tuple[str, str | int]]", value))


def _as_mapping_str_str_or_int_or_float(value: object) -> Mapping[str, str | int | float]:
    return dict(cast("Iterable[tuple[str, str | int | float]]", value))


def _as_mapping_str_float_or_mapping(value: object) -> Mapping[str, float | Mapping[str, float]]:
    return cast("Mapping[str, float | Mapping[str, float]]", dict(value))  # type: ignore[reportArgumentType]


def _as_mapping_str_str_or_float_or_bool(value: object) -> Mapping[str, str | float | bool]:
    return dict(cast("Iterable[tuple[str, str | float | bool]]", value))


def _as_mapping_str_tuple_or_str(value: object) -> Mapping[str, tuple[str, ...] | str]:
    return dict(cast("Iterable[tuple[str, tuple[str, ...] | str]]", value))


class ThresholdPolicyDefaultsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_score_population: str
    eligibility_filter: str
    attack_rows_forbidden_in_calibration: bool
    non_finite_calibration_score: str
    empty_client_calibration: str
    application_scope: str
    required_diagnostic_fields: tuple[str, ...]


class QuantileEstimatorRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: str
    sort_order: str
    index_formula: str
    interpolation: str
    single_element_behavior: str
    empty_input_behavior: str
    non_finite_input_behavior: str
    tie_behavior: str


@dataclass(frozen=True, slots=True, kw_only=True)
class BenignCalibrationScores:
    client_id: ClientId
    values: tuple[float, ...]
    population_id: PopulationId | None = None

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise ValueError("Benign calibration score values cannot be empty")
        for val in self.values:
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError("Calibration score values must be finite numbers")
            if val < 0.0:
                raise ValueError("Calibration anomaly scores must be non-negative")

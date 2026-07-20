"""Domain models for threshold policies, benign calibration scores, and estimated threshold sets."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.domain.values import NonNegativeFloat, PositiveInt, Probability


@dataclass(frozen=True, slots=True, kw_only=True)
class BenignCalibrationScores:

    client_id: ClientId
    values: tuple[float, ...]
    population_id: PopulationId | None = None

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise ValueError("Benign calibration score values cannot be empty")
        for val in self.values:
            if not isinstance(val, (int, float)) or val != val or val in (float("inf"), float("-inf")):
                raise ValueError("Calibration score values must be finite numbers")
            if val < 0.0:
                raise ValueError("Calibration anomaly scores must be non-negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdRecord:

    client_id: ClientId
    threshold: NonNegativeFloat | float
    owner: str
    effective_lambda: float | None = None

    def __post_init__(self) -> None:
        val = float(self.threshold)
        is_finite = isinstance(val, (int, float)) and val == val and val not in (float("inf"), float("-inf"))
        if not is_finite:
            raise ValueError("Produced threshold value must be finite")
        if val < 0.0:
            raise ValueError("Produced threshold value cannot be negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSet:

    policy_id: ThresholdPolicyId
    values: tuple[ThresholdRecord, ...]
    target_quantile: Probability = Probability(0.95)

    def get_client_threshold(self, client_id: ClientId) -> ThresholdRecord:
        for rec in self.values:
            if rec.client_id == client_id:
                return rec
        raise KeyError(f"No threshold record for client: {client_id}")


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleSizeCheck:

    client_id: ClientId
    calibration_count: PositiveInt | int
    minimum_required: PositiveInt | int

    @property
    def is_sufficient(self) -> bool:
        return int(self.calibration_count) >= int(self.minimum_required)

"""Runtime domain types: calibration batches, threshold records, typed diagnostics, exceptions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.enums import ClusterAggregation, ThresholdPolicyKind, ThresholdScope

if TYPE_CHECKING:
    from datp_core.thresholding.policies import (
        ClusterPolicy,
        ConformalPolicy,
        FederatedPolicy,
        QuantilePolicy,
        ShrinkagePolicy,
    )


# ── Exceptions ──────────────────────────────────────────────────────────────


class ThresholdingError(Exception):
    """Base exception for thresholding package."""


class InvalidThresholdPolicyError(ThresholdingError):
    """Policy configuration is invalid or internally inconsistent."""


class EmptyCalibrationError(ThresholdingError):
    """Calibration data is empty — no eligible clients or scores."""


class InsufficientCalibrationError(ThresholdingError):
    """Calibration data does not meet minimum sample-size requirements."""


class NonFiniteCalibrationError(ThresholdingError):
    """Calibration scores contain non-finite values."""


class UnsupportedThresholdPolicyError(ThresholdingError):
    """Policy kind has no implemented estimator."""


class ThresholdConfigurationError(ThresholdingError):
    """Threshold construction request is misconfigured."""


class ThresholdArtifactError(ThresholdingError):
    """Threshold artifact is invalid or missing required data."""


# ── Calibration domain types ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class BenignCalibrationScores:
    """Benign-only calibration scores for one eligible client."""

    client_id: ClientId
    values: tuple[float, ...]
    population_id: PopulationId | None = None

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise EmptyCalibrationError("Benign calibration score values cannot be empty")
        for val in self.values:
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise NonFiniteCalibrationError("Calibration score values must be finite numbers")
            if val < 0.0:
                raise NonFiniteCalibrationError("Calibration anomaly scores must be non-negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSampleRequest:
    """Immutable specification for deterministic calibration subsampling."""

    requested_sample_count: int
    training_seed: int
    selection_seed: int
    replicate: int
    namespace_key: str
    digest_bytes: int

    def __post_init__(self) -> None:
        if self.requested_sample_count < 1:
            raise ValueError("Requested sample count must be positive")
        if self.replicate < 0:
            raise ValueError("Replicate must be non-negative")
        if self.digest_bytes < 1:
            raise ValueError("Digest bytes must be positive")
        if not self.namespace_key:
            raise ValueError("Namespace key must be non-empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSampleResult:
    """Result of deterministic calibration subsampling."""

    sampled_scores: tuple[BenignCalibrationScores, ...]
    sample_count: int
    replicate: int


# ── Family assignments ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class FamilyAssignments:
    """Validated client-to-family mapping."""

    mapping: tuple[tuple[ClientId, str], ...]

    def __post_init__(self) -> None:
        if len(self.mapping) == 0:
            raise ValueError("Family assignments must be non-empty")
        families: set[str] = set()
        for _, family in self.mapping:
            families.add(family)
        if len(families) < 1:
            raise ValueError("At least one distinct family label is required")


# ── Threshold records and sets ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdRecord:
    """One client's constructed threshold with optional metadata."""

    client_id: ClientId
    threshold: float
    policy_kind: ThresholdPolicyKind
    scope: ThresholdScope
    effective_lambda: float | None = None
    cluster_label: int | None = None
    finite_sample_rank: int | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.threshold):
            raise ThresholdingError("Produced threshold value must be finite")
        if self.threshold < 0.0:
            raise ThresholdingError("Produced threshold value cannot be negative")
        if self.finite_sample_rank is not None and self.finite_sample_rank < 1:
            raise ThresholdingError("Conformal finite-sample rank must be positive")
        if self.cluster_label is not None and self.cluster_label < 0:
            raise ThresholdingError("Cluster label must be non-negative")


# ── Diagnostics — typed discriminated union ────────────────────────────────


class ClusterDiagnostics(BaseModel):
    """Complete cluster assignment diagnostics."""

    model_config = ConfigDict(frozen=True)

    cluster_count: int
    cluster_labels: tuple[tuple[str, int], ...]
    aggregation: ClusterAggregation
    fingerprint_features: tuple[str, ...]


class ConformalDiagnostics(BaseModel):
    """Per-client conformal rank diagnostics."""

    model_config = ConfigDict(frozen=True)

    ranks: tuple[tuple[str, int], ...]
    coverage_alpha: float


class ShrinkageDiagnostics(BaseModel):
    """Per-client shrinkage weight diagnostics."""

    model_config = ConfigDict(frozen=True)

    effective_lambdas: tuple[tuple[str, float], ...]


class CalibrationFallbackDiagnostics(BaseModel):
    """Per-client calibration-size-aware lambda diagnostics."""

    model_config = ConfigDict(frozen=True)

    effective_lambdas: tuple[tuple[str, float], ...]
    n_half: int
    calibration_counts: tuple[tuple[str, int], ...]


class FederatedMatchedDiagnostics(BaseModel):
    """Matched-exceedance candidate search diagnostics."""

    model_config = ConfigDict(frozen=True)

    selected_coefficient: float
    candidate_grid_minimum: float
    candidate_grid_maximum: float
    candidate_grid_step: float
    pooled_mean: float
    pooled_standard_deviation: float
    achieved_exceedance: tuple[tuple[float, float], ...]
    tie_set: tuple[float, ...]


class FederatedFixedDiagnostics(BaseModel):
    """Fixed-coefficient federated diagnostics."""

    model_config = ConfigDict(frozen=True)

    coefficient: float
    pooled_mean: float
    pooled_standard_deviation: float


class CalibrationSamplingDiagnostics(BaseModel):
    """Calibration subsampling diagnostics."""

    model_config = ConfigDict(frozen=True)

    requested_count: int
    replicate: int
    client_counts: tuple[tuple[str, int], ...]


ThresholdDiagnostics = (
    ClusterDiagnostics
    | ConformalDiagnostics
    | ShrinkageDiagnostics
    | CalibrationFallbackDiagnostics
    | FederatedMatchedDiagnostics
    | FederatedFixedDiagnostics
    | CalibrationSamplingDiagnostics
)


# ── ThresholdSet ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSet:
    """Complete constructed threshold set with typed diagnostics."""

    policy_id: ThresholdPolicyId
    policy_kind: ThresholdPolicyKind
    scope: ThresholdScope
    values: tuple[ThresholdRecord, ...]
    target_quantile: Probability
    diagnostics: ThresholdDiagnostics | None = None

    def get_client_threshold(self, client_id: ClientId) -> ThresholdRecord:
        for rec in self.values:
            if rec.client_id == client_id:
                return rec
        raise KeyError(f"No threshold record for client: {client_id}")


# ── Construction request ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionRequest:
    """Fully resolved, immutable command for threshold construction."""

    policy_id: ThresholdPolicyId
    policy: QuantilePolicy | ClusterPolicy | ConformalPolicy | ShrinkagePolicy | FederatedPolicy
    calibration: tuple[BenignCalibrationScores, ...]
    population_id: PopulationId
    family_assignments: FamilyAssignments | None = None

"""Strict typed threshold policies — discriminated union, no descriptive fields."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp_core.thresholding.enums import (
    ClusterAggregation,
    FingerprintFeature,
    ThresholdPolicyKind,
)


class FrozenPolicyModel(BaseModel):
    """Shared frozen base for all threshold policy models."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class QuantilePolicy(FrozenPolicyModel):
    """Shared-mean, pooled, weighted, local-quantile, and family-mean policies."""

    kind: Literal[
        ThresholdPolicyKind.SHARED_MEAN,
        ThresholdPolicyKind.SHARED_POOLED,
        ThresholdPolicyKind.SHARED_WEIGHTED,
        ThresholdPolicyKind.LOCAL_QUANTILE,
        ThresholdPolicyKind.FAMILY_MEAN,
    ]
    quantile: float = Field(gt=0.0, lt=1.0)


class ClusterPolicy(FrozenPolicyModel):
    """Cluster threshold policy (B4)."""

    kind: Literal[ThresholdPolicyKind.CLUSTER]
    quantile: float = Field(gt=0.0, lt=1.0)
    cluster_count: int = Field(ge=2)
    aggregation: ClusterAggregation
    fingerprint_features: tuple[FingerprintFeature, ...] = Field(min_length=1)
    fingerprint_quantile: float = Field(gt=0.0, lt=1.0)
    kmeans_random_seed: int
    kmeans_initialization_runs: int = Field(ge=1)
    kmeans_maximum_iterations: int = Field(ge=1)
    kmeans_convergence_tolerance: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_cluster_geometry(self) -> ClusterPolicy:
        if len(set(self.fingerprint_features)) != len(self.fingerprint_features):
            raise ValueError("Fingerprint features must be unique")
        return self


class ConformalPolicy(FrozenPolicyModel):
    """Split-conformal threshold policy (B2-conf)."""

    kind: Literal[ThresholdPolicyKind.CONFORMAL]
    coverage_alpha: float = Field(gt=0.0, lt=1.0)
    minimum_sample_count: int = Field(ge=1)


class FixedShrinkagePolicy(FrozenPolicyModel):
    """Local-global shrinkage with a fixed lambda weight."""

    kind: Literal[ThresholdPolicyKind.SHRINKAGE]
    quantile: float = Field(gt=0.0, lt=1.0)
    shrinkage_weight: float = Field(ge=0.0, le=1.0)


class CalibrationFallbackPolicy(FrozenPolicyModel):
    """Calibration-size-aware fallback — lambda = n_k / (n_k + n_half)."""

    kind: Literal[ThresholdPolicyKind.CALIBRATION_FALLBACK]
    quantile: float = Field(gt=0.0, lt=1.0)
    n_half: int = Field(ge=1)


class FederatedMatchedPolicy(FrozenPolicyModel):
    """Matched-exceedance federated threshold via candidate-grid search."""

    kind: Literal[ThresholdPolicyKind.FEDERATED_MATCHED]
    quantile: float = Field(gt=0.0, lt=1.0)
    candidate_grid_minimum: float
    candidate_grid_maximum: float
    candidate_grid_step: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_grid(self) -> FederatedMatchedPolicy:
        if self.candidate_grid_minimum >= self.candidate_grid_maximum:
            raise ValueError("Candidate grid minimum must be less than maximum")
        span = self.candidate_grid_maximum - self.candidate_grid_minimum
        quotient = span / self.candidate_grid_step
        if not _is_integer_within_tolerance(quotient):
            raise ValueError(
                f"Candidate grid span ({span}) must be exactly divisible by step "
                f"({self.candidate_grid_step}); got quotient {quotient}"
            )
        return self


class FederatedFixedPolicy(FrozenPolicyModel):
    """Fixed-coefficient federated threshold: tau = mu + k * sigma."""

    kind: Literal[ThresholdPolicyKind.FEDERATED_FIXED]
    quantile: float = Field(gt=0.0, lt=1.0)
    fixed_coefficient: float


def _is_integer_within_tolerance(value: float, *, tolerance: float = 1e-9) -> bool:
    return abs(value - round(value)) < tolerance


ThresholdPolicyRecord = Annotated[
    QuantilePolicy
    | ClusterPolicy
    | ConformalPolicy
    | FixedShrinkagePolicy
    | CalibrationFallbackPolicy
    | FederatedMatchedPolicy
    | FederatedFixedPolicy,
    Field(discriminator="kind"),
]

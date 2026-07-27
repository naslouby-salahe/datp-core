"""Strict typed threshold policies — one discriminated union, no descriptive fields."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp_core.thresholding.enums import (
    ClusterAggregation,
    FingerprintFeature,
    ThresholdPolicyKind,
)


class QuantilePolicy(BaseModel):
    """Shared-mean, pooled, weighted, local-quantile, and family-mean policies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[
        ThresholdPolicyKind.SHARED_MEAN,
        ThresholdPolicyKind.SHARED_POOLED,
        ThresholdPolicyKind.SHARED_WEIGHTED,
        ThresholdPolicyKind.LOCAL_QUANTILE,
        ThresholdPolicyKind.FAMILY_MEAN,
    ]
    quantile: float = Field(gt=0.0, lt=1.0)


class ClusterPolicy(BaseModel):
    """Cluster threshold policy (B4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[ThresholdPolicyKind.CLUSTER]
    quantile: float = Field(gt=0.0, lt=1.0)
    cluster_count: int = Field(ge=2)
    aggregation: ClusterAggregation
    fingerprint_features: tuple[FingerprintFeature, ...] = Field(min_length=1)
    kmeans_random_seed: int
    kmeans_initialization_runs: int = Field(ge=1)
    kmeans_maximum_iterations: int = Field(ge=1)
    kmeans_convergence_tolerance: float = Field(gt=0.0)

    @model_validator(mode="after")
    def _validate_cluster_geometry(self) -> ClusterPolicy:
        if len(set(self.fingerprint_features)) != len(self.fingerprint_features):
            raise ValueError("Fingerprint features must be unique")
        return self


class ConformalPolicy(BaseModel):
    """Split-conformal threshold policy (B2-conf)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[ThresholdPolicyKind.CONFORMAL]
    coverage_alpha: float = Field(gt=0.0, lt=1.0)
    minimum_sample_count: int = Field(ge=1)


class ShrinkagePolicy(BaseModel):
    """Local-global shrinkage and calibration-size-aware fallback policies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[
        ThresholdPolicyKind.SHRINKAGE,
        ThresholdPolicyKind.CALIBRATION_FALLBACK,
    ]
    quantile: float = Field(gt=0.0, lt=1.0)
    shrinkage_weight: float | None = None
    n_half: int | None = None

    @model_validator(mode="after")
    def _validate_shrinkage_config(self) -> ShrinkagePolicy:
        if self.kind == ThresholdPolicyKind.SHRINKAGE:
            if self.shrinkage_weight is not None and not 0.0 <= self.shrinkage_weight <= 1.0:
                raise ValueError("Shrinkage weight must be in [0.0, 1.0]")
        if self.kind == ThresholdPolicyKind.CALIBRATION_FALLBACK:
            if self.n_half is None or self.n_half <= 0:
                raise ValueError("Calibration fallback requires a positive n_half")
        return self


class FederatedPolicy(BaseModel):
    """Federated summary-statistic threshold policies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[
        ThresholdPolicyKind.FEDERATED_MATCHED,
        ThresholdPolicyKind.FEDERATED_FIXED,
    ]
    quantile: float = Field(gt=0.0, lt=1.0)
    primary_comparator: bool = False
    candidate_grid_minimum: float | None = None
    candidate_grid_maximum: float | None = None
    candidate_grid_step: float | None = None
    fixed_k: float | None = None

    @model_validator(mode="after")
    def _validate_federated_config(self) -> FederatedPolicy:
        if self.kind == ThresholdPolicyKind.FEDERATED_MATCHED:
            if (
                self.candidate_grid_minimum is None
                or self.candidate_grid_maximum is None
                or self.candidate_grid_step is None
            ):
                raise ValueError("Matched-exceedance policy requires candidate_grid minimum, maximum, and step")
            if self.candidate_grid_step <= 0.0:
                raise ValueError("Candidate grid step must be positive")
            if self.candidate_grid_minimum >= self.candidate_grid_maximum:
                raise ValueError("Candidate grid minimum must be less than maximum")
        return self


ThresholdPolicyRecord = Annotated[
    QuantilePolicy | ClusterPolicy | ConformalPolicy | ShrinkagePolicy | FederatedPolicy,
    Field(discriminator="kind"),
]

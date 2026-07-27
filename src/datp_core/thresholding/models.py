"""Runtime domain types: calibration batches, threshold records, typed diagnostics, exceptions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from datp_core.core.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.thresholding.enums import (
    ClusterAggregation,
    FingerprintFeature,
    ThresholdDiagnosticsKind,
    ThresholdPolicyKind,
    ThresholdScope,
    TieBreakRule,
)

if TYPE_CHECKING:
    from datp_core.thresholding.policies import (
        CalibrationFallbackPolicy,
        ClusterPolicy,
        ConformalPolicy,
        FederatedFixedPolicy,
        FederatedMatchedPolicy,
        FixedShrinkagePolicy,
        QuantilePolicy,
    )


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
    namespace_key: str  # canonical boundary type — config's SeedNamespaceRecord.key
    digest_bytes: int

    def __post_init__(self) -> None:
        if self.requested_sample_count < 1:
            raise ThresholdConfigurationError("Requested sample count must be positive")
        if self.replicate < 0:
            raise ThresholdConfigurationError("Replicate must be non-negative")
        if self.digest_bytes < 1:
            raise ThresholdConfigurationError("Digest bytes must be positive")
        if not self.namespace_key:
            raise ThresholdConfigurationError("Namespace key must be non-empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class FamilyAssignments:
    """Validated client-to-family mapping."""

    mapping: tuple[tuple[ClientId, str], ...]

    def __post_init__(self) -> None:
        if len(self.mapping) == 0:
            raise ThresholdConfigurationError("Family assignments must be non-empty")
        seen_clients: set[ClientId] = set()
        families: set[str] = set()
        for client_id, family in self.mapping:
            if client_id in seen_clients:
                raise ThresholdConfigurationError(f"Duplicate client ID in family assignments: {client_id}")
            seen_clients.add(client_id)
            if not family.strip():
                raise ThresholdConfigurationError(f"Family label for client {client_id} must not be blank")
            families.add(family)
        if len(families) < 1:
            raise ThresholdConfigurationError("At least one distinct family label is required")
        sorted_mapping = tuple(sorted(self.mapping, key=lambda x: x[0].value))
        object.__setattr__(self, "mapping", sorted_mapping)


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

        if self.effective_lambda is not None:
            if not math.isfinite(self.effective_lambda):
                raise InvalidThresholdPolicyError("Effective lambda must be finite")
            if not 0.0 <= self.effective_lambda <= 1.0:
                raise InvalidThresholdPolicyError("Effective lambda must be in [0.0, 1.0]")
            if self.policy_kind not in {
                ThresholdPolicyKind.SHRINKAGE,
                ThresholdPolicyKind.CALIBRATION_FALLBACK,
            }:
                raise InvalidThresholdPolicyError(f"Effective lambda is not allowed for policy kind {self.policy_kind}")

        if self.policy_kind in {
            ThresholdPolicyKind.SHARED_MEAN,
            ThresholdPolicyKind.SHARED_POOLED,
            ThresholdPolicyKind.SHARED_WEIGHTED,
            ThresholdPolicyKind.FEDERATED_MATCHED,
            ThresholdPolicyKind.FEDERATED_FIXED,
        }:
            if self.scope is not ThresholdScope.SHARED:
                raise InvalidThresholdPolicyError(f"Policy {self.policy_kind} requires SHARED scope, got {self.scope}")
            if self.cluster_label is not None:
                raise InvalidThresholdPolicyError(f"Policy {self.policy_kind} must not have a cluster_label")
            if self.finite_sample_rank is not None:
                raise InvalidThresholdPolicyError(f"Policy {self.policy_kind} must not have a finite_sample_rank")
        elif self.policy_kind is ThresholdPolicyKind.LOCAL_QUANTILE:
            if self.scope is not ThresholdScope.CLIENT:
                raise InvalidThresholdPolicyError(f"LOCAL_QUANTILE policy requires CLIENT scope, got {self.scope}")
            if self.cluster_label is not None:
                raise InvalidThresholdPolicyError("LOCAL_QUANTILE must not have a cluster_label")
            if self.finite_sample_rank is not None:
                raise InvalidThresholdPolicyError("LOCAL_QUANTILE must not have a finite_sample_rank")
        elif self.policy_kind is ThresholdPolicyKind.FAMILY_MEAN:
            if self.scope is not ThresholdScope.FAMILY:
                raise InvalidThresholdPolicyError(f"FAMILY_MEAN policy requires FAMILY scope, got {self.scope}")
            if self.cluster_label is not None:
                raise InvalidThresholdPolicyError("FAMILY_MEAN must not have a cluster_label")
            if self.finite_sample_rank is not None:
                raise InvalidThresholdPolicyError("FAMILY_MEAN must not have a finite_sample_rank")
        elif self.policy_kind is ThresholdPolicyKind.CLUSTER:
            if self.scope is not ThresholdScope.CLUSTER:
                raise InvalidThresholdPolicyError(f"CLUSTER policy requires CLUSTER scope, got {self.scope}")
            if self.cluster_label is None:
                raise InvalidThresholdPolicyError("CLUSTER policy requires a cluster_label")
            if self.finite_sample_rank is not None:
                raise InvalidThresholdPolicyError("CLUSTER must not have a finite_sample_rank")
        elif self.policy_kind is ThresholdPolicyKind.CONFORMAL:
            if self.scope is not ThresholdScope.CLIENT:
                raise InvalidThresholdPolicyError(f"CONFORMAL policy requires CLIENT scope, got {self.scope}")
            if self.cluster_label is not None:
                raise InvalidThresholdPolicyError("CONFORMAL must not have a cluster_label")
            if self.finite_sample_rank is None:
                raise InvalidThresholdPolicyError("CONFORMAL policy requires a finite_sample_rank")
        elif self.policy_kind in {
            ThresholdPolicyKind.SHRINKAGE,
            ThresholdPolicyKind.CALIBRATION_FALLBACK,
        }:
            if self.scope is not ThresholdScope.CLIENT:
                raise InvalidThresholdPolicyError(f"{self.policy_kind} policy requires CLIENT scope, got {self.scope}")
            if self.cluster_label is not None:
                raise InvalidThresholdPolicyError(f"{self.policy_kind} must not have a cluster_label")
            if self.finite_sample_rank is not None:
                raise InvalidThresholdPolicyError(f"{self.policy_kind} must not have a finite_sample_rank")
            if self.effective_lambda is None:
                raise InvalidThresholdPolicyError(f"{self.policy_kind} policy requires an effective_lambda")


class FrozenDiagnosticsModel(BaseModel):
    """Frozen base for all threshold diagnostics models — forbids inf/nan values."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class ClusterDiagnostics(FrozenDiagnosticsModel):
    """Complete cluster assignment diagnostics."""

    kind: Literal[ThresholdDiagnosticsKind.CLUSTER]
    cluster_count: int
    eligible_client_count: int
    unique_fingerprint_row_count: int
    cluster_labels: tuple[tuple[str, int], ...]
    aggregation: ClusterAggregation
    fingerprint_features: tuple[FingerprintFeature, ...]
    fingerprint_quantile: float
    kmeans_random_seed: int
    kmeans_initialization_runs: int
    kmeans_maximum_iterations: int
    kmeans_convergence_tolerance: float
    cluster_members: tuple[tuple[int, tuple[str, ...]], ...]
    cluster_thresholds: tuple[tuple[int, float], ...]


class ConformalDiagnostics(FrozenDiagnosticsModel):
    """Per-client conformal rank diagnostics."""

    kind: Literal[ThresholdDiagnosticsKind.CONFORMAL]
    ranks: tuple[tuple[str, int], ...]
    coverage_alpha: float


class ShrinkageDiagnostics(FrozenDiagnosticsModel):
    """Per-client shrinkage weight diagnostics."""

    kind: Literal[ThresholdDiagnosticsKind.SHRINKAGE]
    effective_lambdas: tuple[tuple[str, float], ...]


class CalibrationFallbackDiagnostics(FrozenDiagnosticsModel):
    """Per-client calibration-size-aware lambda diagnostics."""

    kind: Literal[ThresholdDiagnosticsKind.CALIBRATION_FALLBACK]
    effective_lambdas: tuple[tuple[str, float], ...]
    n_half: int
    calibration_counts: tuple[tuple[str, int], ...]


class FederatedMatchedDiagnostics(FrozenDiagnosticsModel):
    """Matched-exceedance candidate search diagnostics."""

    kind: Literal[ThresholdDiagnosticsKind.FEDERATED_MATCHED]
    matched_coefficient: float
    target_exceedance: float
    candidate_grid_minimum: float
    candidate_grid_maximum: float
    candidate_grid_step: float
    achieved_exceedance: tuple[tuple[float, float], ...]
    tie_set: tuple[float, ...]
    tie_rule: TieBreakRule
    pooled_mean: float
    pooled_standard_deviation: float
    selected_threshold: float
    selected_deviation: float
    total_calibration_count: int


class FederatedFixedDiagnostics(FrozenDiagnosticsModel):
    """Fixed-coefficient federated diagnostics."""

    kind: Literal[ThresholdDiagnosticsKind.FEDERATED_FIXED]
    fixed_coefficient: float
    pooled_mean: float
    pooled_standard_deviation: float
    selected_threshold: float
    total_calibration_count: int


ThresholdDiagnostics = Annotated[
    ClusterDiagnostics
    | ConformalDiagnostics
    | ShrinkageDiagnostics
    | CalibrationFallbackDiagnostics
    | FederatedMatchedDiagnostics
    | FederatedFixedDiagnostics,
    Field(discriminator="kind"),
]

_diagnostics_adapter = TypeAdapter(ThresholdDiagnostics)


def get_diagnostics_adapter() -> TypeAdapter[ThresholdDiagnostics]:
    """Return the module-level TypeAdapter for ThresholdDiagnostics."""
    return _diagnostics_adapter


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdSet:
    """Complete constructed threshold set with typed diagnostics."""

    policy_id: ThresholdPolicyId
    policy_kind: ThresholdPolicyKind
    scope: ThresholdScope
    values: tuple[ThresholdRecord, ...]
    target_quantile: Probability
    diagnostics: ThresholdDiagnostics | None = None

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise ThresholdConfigurationError("Threshold set must contain at least one record")

        seen_client_ids: set[ClientId] = set()
        for rec in self.values:
            if rec.client_id in seen_client_ids:
                raise ThresholdConfigurationError(f"Duplicate client ID in threshold set: {rec.client_id}")
            seen_client_ids.add(rec.client_id)
            if rec.policy_kind is not self.policy_kind:
                raise InvalidThresholdPolicyError(
                    f"Record policy_kind {rec.policy_kind} does not match set policy_kind {self.policy_kind}"
                )
            if rec.scope is not self.scope:
                raise InvalidThresholdPolicyError(f"Record scope {rec.scope} does not match set scope {self.scope}")

        _kinds_requiring_diagnostics = {
            ThresholdPolicyKind.CLUSTER,
            ThresholdPolicyKind.CONFORMAL,
            ThresholdPolicyKind.SHRINKAGE,
            ThresholdPolicyKind.CALIBRATION_FALLBACK,
            ThresholdPolicyKind.FEDERATED_MATCHED,
            ThresholdPolicyKind.FEDERATED_FIXED,
        }
        _kinds_forbidding_diagnostics = {
            ThresholdPolicyKind.SHARED_MEAN,
            ThresholdPolicyKind.SHARED_POOLED,
            ThresholdPolicyKind.SHARED_WEIGHTED,
            ThresholdPolicyKind.LOCAL_QUANTILE,
            ThresholdPolicyKind.FAMILY_MEAN,
        }
        if self.policy_kind in _kinds_requiring_diagnostics and self.diagnostics is None:
            raise InvalidThresholdPolicyError(
                f"Policy kind {self.policy_kind} requires diagnostics but diagnostics is None"
            )
        if self.policy_kind in _kinds_forbidding_diagnostics and self.diagnostics is not None:
            raise InvalidThresholdPolicyError(f"Policy kind {self.policy_kind} must not have diagnostics")
        if self.diagnostics is not None:
            _policy_for_diag = {
                ThresholdDiagnosticsKind.CLUSTER: ThresholdPolicyKind.CLUSTER,
                ThresholdDiagnosticsKind.CONFORMAL: ThresholdPolicyKind.CONFORMAL,
                ThresholdDiagnosticsKind.SHRINKAGE: ThresholdPolicyKind.SHRINKAGE,
                ThresholdDiagnosticsKind.CALIBRATION_FALLBACK: ThresholdPolicyKind.CALIBRATION_FALLBACK,
                ThresholdDiagnosticsKind.FEDERATED_MATCHED: ThresholdPolicyKind.FEDERATED_MATCHED,
                ThresholdDiagnosticsKind.FEDERATED_FIXED: ThresholdPolicyKind.FEDERATED_FIXED,
            }
            expected_policy = _policy_for_diag.get(self.diagnostics.kind)
            if expected_policy is None:
                raise InvalidThresholdPolicyError(
                    f"Diagnostics kind {self.diagnostics.kind} is not associated with any policy kind"
                )
            if expected_policy is not self.policy_kind:
                raise InvalidThresholdPolicyError(
                    f"Diagnostics kind {self.diagnostics.kind} is not compatible with policy kind {self.policy_kind}"
                )

        sorted_values = tuple(sorted(self.values, key=lambda r: r.client_id.value))
        object.__setattr__(self, "values", sorted_values)

    def get_client_threshold(self, client_id: ClientId) -> ThresholdRecord:
        for rec in self.values:
            if rec.client_id == client_id:
                return rec
        raise KeyError(f"No threshold record for client: {client_id}")


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionRequest:
    """Fully resolved, immutable command for threshold construction."""

    policy_id: ThresholdPolicyId
    policy: (
        FixedShrinkagePolicy
        | CalibrationFallbackPolicy
        | FederatedMatchedPolicy
        | FederatedFixedPolicy
        | QuantilePolicy
        | ClusterPolicy
        | ConformalPolicy
    )
    calibration: tuple[BenignCalibrationScores, ...]
    population_id: PopulationId
    family_assignments: FamilyAssignments | None = None

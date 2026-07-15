from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from datp_core.domain.artifacts.lineage import ThresholdIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.evaluation.operating_points import EligibleClientSet
from datp_core.domain.learning.scores import CalibrationScoreArtifactSet, ThresholdAssignmentSet
from datp_core.domain.thresholding.clustering import B4ClusteringSpec, ClusterAssignmentArtifact
from datp_core.domain.thresholding.policies import (
    CoreThresholdPolicy,
    FprTarget,
    ThresholdAssignment,
    ThresholdConstructionSpec,
    ThresholdPercentile,
)

if TYPE_CHECKING:
    from datp_core.domain.thresholding.federated_statistics import ThresholdComparatorRole
    from datp_core.domain.thresholding.variants import ThresholdVariant


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdAssignmentMetadata:
    policy: CoreThresholdPolicy | ThresholdVariant | ThresholdComparatorRole
    threshold_identity: ThresholdIdentity
    fallback_fingerprint: StageFingerprint
    fpr_target: FprTarget


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructThresholdsRequest:
    calibration_scores: CalibrationScoreArtifactSet
    construction: ThresholdConstructionSpec
    eligible_clients: EligibleClientSet
    assignment_metadata: ThresholdAssignmentMetadata


@dataclass(frozen=True, slots=True, kw_only=True)
class ThresholdConstructionResult:
    assignment: ThresholdAssignment


@dataclass(frozen=True, slots=True, kw_only=True)
class AssignThresholdRequest:
    calibration_scores: CalibrationScoreArtifactSet
    construction: ThresholdConstructionSpec
    eligible_clients: EligibleClientSet
    assignment_metadata: ThresholdAssignmentMetadata


@dataclass(frozen=True, slots=True, kw_only=True)
class B4ClusteringRequest:
    calibration_scores: CalibrationScoreArtifactSet
    clustering: B4ClusteringSpec
    eligible_clients: EligibleClientSet


@dataclass(frozen=True, slots=True, kw_only=True)
class QuantileEstimateRequest:
    calibration_scores: CalibrationScoreArtifactSet
    percentile: ThresholdPercentile


@dataclass(frozen=True, slots=True, kw_only=True)
class QuantileEstimateResult:
    estimates: ThresholdAssignmentSet


class ThresholdConstructor(Protocol):
    def construct(self, request: ConstructThresholdsRequest) -> ThresholdConstructionResult: ...


class ThresholdStrategy(Protocol):
    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment: ...


class ClusteringStrategy(Protocol):
    def cluster(self, request: B4ClusteringRequest) -> ClusterAssignmentArtifact: ...


class QuantileEstimator(Protocol):
    def estimate(self, request: QuantileEstimateRequest) -> QuantileEstimateResult: ...

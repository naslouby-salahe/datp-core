"""Cross-cutting analysis contracts shared by multiple capability modules."""

from __future__ import annotations

from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import Field

from datp_core.analysis._base import ConfidenceInterval, FrozenModel
from datp_core.analysis.calibration.contracts import (
    ConformalCoverageAnalysisResult,
    QuantileEstimationAnalysisResult,
    ThresholdStabilityAnalysisResult,
)
from datp_core.analysis.clustering.contracts import (
    ClusterAblationStabilityResult,
    ClusterMembershipStabilityResult,
)
from datp_core.analysis.comparisons.contracts import (
    AbsorptionAnalysisResult,
    AnchorEquivalenceAnalysisResult,
    MetricAssociationAnalysisResult,
    PairedThresholdAnalysisResult,
    RecoveryFractionAnalysisResult,
)
from datp_core.analysis.enums import AlternativeHypothesis, AnalysisResultKind, HypothesisTestName, SweepDimensionKind
from datp_core.analysis.errors import PrerequisiteResultMissingError
from datp_core.analysis.mechanisms.contracts import (
    AlertBurdenAnalysisResult,
    DistributionMechanismRawResult,
    DistributionMechanismTradeoffResult,
    LockedClientDistributionAnalysisResult,
    ResourceCostAnalysisResult,
    TemporalRecoveryAnalysisResult,
)
from datp_core.core.identifiers import AnalysisLabel, ExperimentId, MetricId, PartitionConditionId, ThresholdPolicyId
from datp_core.core.seeding import Seed


@runtime_checkable
class QuantileThresholdPolicy(Protocol):
    quantile: float


class AnalysisCell(FrozenModel):
    dimension: SweepDimensionKind
    value: float | int | str | tuple[str, ...] | PartitionConditionId


class PairedAnalysisCell(FrozenModel):
    partition_condition: PartitionConditionId | None = None
    proximal_mu: float | None = None
    ditto_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    calibration_sample_count: int | None = None


class HypothesisTestResult(FrozenModel):
    test_name: HypothesisTestName
    statistic: float
    p_value: float
    degrees_of_freedom: float | None = None
    alternative: AlternativeHypothesis = AlternativeHypothesis.TWO_SIDED


class LinearRegressionResult(FrozenModel):
    slope: float
    intercept: float
    standard_error: float
    r_squared: float
    leverage: tuple[float, ...]
    leave_one_out_slopes: tuple[float, ...]


class PairedSeedDifferenceRecord(FrozenModel):
    metric_id: MetricId
    policy_a_id: ThresholdPolicyId
    policy_b_id: ThresholdPolicyId
    mean_difference: float
    confidence_interval: ConfidenceInterval
    resample_count: int
    analysis_seed: Seed
    hypothesis_test: HypothesisTestResult | None = None
    effect_size: float | None = None


class FederatedProximalLossObservation(FrozenModel):
    proximal_mu: float
    mean_benign_calibration_loss: float


class DittoLossObservation(FrozenModel):
    proximal_weight: float
    mean_benign_calibration_loss: float


class CheckpointSelectionArtifact(FrozenModel):
    selected_proximal_mu: float | None = None
    selected_ditto_proximal_weight: float | None = None
    locked_primary_round: int | None = None
    federated_proximal_losses: tuple[FederatedProximalLossObservation, ...] = ()
    ditto_losses: tuple[DittoLossObservation, ...] = ()


class FederatedProximalSelectionResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION] = (
        AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION
    )
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    selected_proximal_mu: float
    locked_primary_round: int | None
    calibration_losses: tuple[FederatedProximalLossObservation, ...] | None


class DittoSelectionResult(FrozenModel):
    result_kind: Literal[AnalysisResultKind.DITTO_SELECTION] = AnalysisResultKind.DITTO_SELECTION
    payload_version: Literal[1] = 1
    analysis_label: AnalysisLabel
    selected_ditto_proximal_weight: float
    locked_primary_round: int | None
    calibration_losses: tuple[DittoLossObservation, ...] | None


class CountRatioObservation(FrozenModel):
    numerator: float
    denominator: float


class PrerequisiteAnalysisReference(FrozenModel):
    experiment_id: ExperimentId
    analysis_label: AnalysisLabel
    result_kind: AnalysisResultKind


class PrerequisiteExperimentResult(FrozenModel):
    experiment_id: ExperimentId
    frozen_result_path: str
    frozen_result_checksum: str
    scientific_fingerprint: str
    statistical_results: tuple[AnalysisResult, ...]

    def paired_result(self, analysis_label: AnalysisLabel) -> PairedThresholdAnalysisResult:
        matches = tuple(
            item
            for item in self.statistical_results
            if isinstance(item, PairedThresholdAnalysisResult) and item.analysis_label == analysis_label
        )
        if len(matches) != 1:
            raise PrerequisiteResultMissingError(
                f"Prerequisite '{self.experiment_id.value}' has no unique paired result "
                f"for analysis '{analysis_label.value}'"
            )
        return matches[0]


AnalysisResult = Annotated[
    PairedThresholdAnalysisResult
    | ConformalCoverageAnalysisResult
    | QuantileEstimationAnalysisResult
    | ThresholdStabilityAnalysisResult
    | MetricAssociationAnalysisResult
    | AbsorptionAnalysisResult
    | RecoveryFractionAnalysisResult
    | ClusterAblationStabilityResult
    | ClusterMembershipStabilityResult
    | DistributionMechanismRawResult
    | DistributionMechanismTradeoffResult
    | LockedClientDistributionAnalysisResult
    | TemporalRecoveryAnalysisResult
    | AlertBurdenAnalysisResult
    | ResourceCostAnalysisResult
    | FederatedProximalSelectionResult
    | DittoSelectionResult
    | AnchorEquivalenceAnalysisResult,
    Field(discriminator="result_kind"),
]

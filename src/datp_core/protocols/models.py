"""Frozen, typed scientific declarations."""

from math import fsum, isclose
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp_core.domain.enums import (
    CentralizedModelId,
    CentralizedThresholdMethod,
    ClusterAssignmentAlgorithm,
    ClusterFeatureStandardization,
    ClusterFingerprintFeature,
    ClusterThresholdAggregation,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    KMeansInitialization,
    MetricId,
    OptimizerId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values import (
    CalibrationSize,
    ClientCount,
    ConfidenceLevel,
    CoverageTarget,
    DittoRegularization,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    LocalEpochCount,
    MetricValue,
    ProximalCoefficient,
    Quantile,
    Ratio,
    RoundNumber,
    Seed,
    ShrinkageWeight,
    SummaryCoefficient,
    TrafficRatePerDay,
)

UNIT_FRACTION_TOTAL = 1.0
FRACTION_TOTAL_ABSOLUTE_TOLERANCE = 1e-12
DATA_ROOT = Path("data")
OUTPUTS_ROOT = Path("outputs")
RESULTS_ROOT = Path("results")


def _sums_to_unit_fraction(*values: float) -> bool:
    """Compare declared fractional quantities with one shared tolerance."""
    return isclose(
        fsum(values),
        UNIT_FRACTION_TOTAL,
        rel_tol=0.0,
        abs_tol=FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
    )


class Declaration(BaseModel):
    """Common immutable Pydantic configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class SeedCohort(Declaration):
    values: tuple[Seed, ...]

    @model_validator(mode="after")
    def validate_values(self) -> "SeedCohort":
        if not self.values:
            raise ValueError("a seed cohort requires at least one seed")
        if len(set(self.values)) != len(self.values):
            raise ValueError("seed cohort values must be unique")
        return self

    @property
    def member_count(self) -> ClientCount:
        return ClientCount(len(self.values))


class FractionalSplitProtocol(Declaration):
    training: Ratio
    calibration: Ratio
    evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "FractionalSplitProtocol":
        if not _sums_to_unit_fraction(
            self.training.value,
            self.calibration.value,
            self.evaluation.value,
        ):
            raise ValueError("fractional split must sum to one")
        return self


class TemporalSplitProtocol(Declaration):
    historical_training: Ratio
    historical_calibration: Ratio
    future_recalibration: Ratio
    future_evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "TemporalSplitProtocol":
        if not _sums_to_unit_fraction(
            self.historical_training.value,
            self.historical_calibration.value,
            self.future_recalibration.value,
            self.future_evaluation.value,
        ):
            raise ValueError("temporal split must sum to one")
        return self


class CheckpointProtocol(Declaration):
    candidates: tuple[RoundNumber, ...]
    maximum_round: RoundNumber

    @model_validator(mode="after")
    def validate_candidates(self) -> "CheckpointProtocol":
        values = tuple(candidate.value for candidate in self.candidates)
        if not values or values != tuple(sorted(values)) or len(set(values)) != len(values):
            raise ValueError("checkpoint candidates must be unique and ordered")
        if values[-1] != self.maximum_round.value:
            raise ValueError("maximum round must be the final checkpoint candidate")
        return self


class AutoencoderProtocol(Declaration):
    widths: tuple[int, ...]

    @model_validator(mode="after")
    def validate_widths(self) -> "AutoencoderProtocol":
        if not self.widths or any(isinstance(width, bool) or width < 1 for width in self.widths):
            raise ValueError("autoencoder widths must be positive integers")
        return self


class OptimizerProtocol(Declaration):
    identity: OptimizerId


class FedAvgProtocol(Declaration):
    kind: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol


class FedProxProtocol(Declaration):
    kind: Literal[TrainingModelId.FEDPROX_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol
    coefficient: ProximalCoefficient


class DittoProtocol(Declaration):
    kind: Literal[TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER]
    regularization: DittoRegularization


TrainingProtocol = Annotated[FedAvgProtocol | FedProxProtocol | DittoProtocol, Field(discriminator="kind")]


class CentralizedTrainingProtocol(Declaration):
    kind: Literal[CentralizedModelId.CENTRALIZED_AUTOENCODER]
    optimizer: OptimizerProtocol


class CentralizedQuantileProtocol(Declaration):
    method: Literal[CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE]
    quantile: Quantile


class CalibrationEligibilityProtocol(Declaration):
    minimum_support: CalibrationSize


class QuantileProtocol(Declaration):
    method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    ]
    quantile: Quantile


class CalibrationSizeProtocol(Declaration):
    sizes: tuple[CalibrationSize, ...]


class FixedShrinkageProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE]
    weights: tuple[ShrinkageWeight, ...]


class SizeAwareShrinkageProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE]
    minimum_support: CalibrationSize


class ConformalProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD]
    coverage: CoverageTarget
    significance: Ratio

    @model_validator(mode="after")
    def validate_complement(self) -> "ConformalProtocol":
        if not _sums_to_unit_fraction(self.coverage.value, self.significance.value):
            raise ValueError("coverage and significance must be complements")
        return self


class FederatedStatisticsProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS]
    coefficients: tuple[SummaryCoefficient, ...]


class ClusterThresholdProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.CLUSTER_THRESHOLD]
    quantile: Quantile
    fingerprint_features: tuple[ClusterFingerprintFeature, ...]
    feature_standardization: ClusterFeatureStandardization
    assignment_algorithm: ClusterAssignmentAlgorithm
    initialization: KMeansInitialization
    initialization_count: KMeansInitializationCount
    maximum_iterations: KMeansMaximumIterationCount
    random_state: Seed
    group_count: GroupCount
    threshold_aggregation: ClusterThresholdAggregation

    @model_validator(mode="after")
    def validate_fingerprint_features(self) -> "ClusterThresholdProtocol":
        if len(set(self.fingerprint_features)) != len(self.fingerprint_features):
            raise ValueError("cluster fingerprint features must be unique")
        return self


class MetricProtocol(Declaration):
    metrics: tuple[MetricId, ...]


class StatisticalInferenceProtocol(Declaration):
    confidence_level: ConfidenceLevel
    seed_cohort: SeedCohort

    @property
    def paired_seed_count(self) -> ClientCount:
        return self.seed_cohort.member_count


class TrafficRateEvidence(Declaration):
    population: PopulationId
    rate_per_day: TrafficRatePerDay
    source_locator: str

    @model_validator(mode="after")
    def validate_source_locator(self) -> "TrafficRateEvidence":
        if not self.source_locator.strip():
            raise ValueError("traffic-rate evidence requires a source locator")
        return self


class PopulationDeclaration(Declaration):
    id: PopulationId
    dataset: DatasetId
    client_count: ClientCount
    has_attack_assignment: bool
    has_chronology: bool
    has_family_taxonomy: bool
    confirmatory_eligible: bool


class ExperimentDeclaration(Declaration):
    id: ExperimentId
    role: EvidenceRole
    population: PopulationId
    training_model: TrainingModelId
    federated_thresholds: tuple[FederatedThresholdMethod, ...]
    metrics: tuple[MetricId, ...]

    @model_validator(mode="after")
    def validate_contents(self) -> "ExperimentDeclaration":
        if not self.federated_thresholds or not self.metrics:
            raise ValueError("experiments require threshold methods and metrics")
        if len(set(self.federated_thresholds)) != len(self.federated_thresholds):
            raise ValueError("experiment threshold methods must be unique")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("experiment metrics must be unique")
        return self


class AnchorReference(Declaration):
    seed: Seed
    threshold_method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ]
    metric: MetricId
    value: MetricValue
    absolute_tolerance: MetricValue


class AnchorDecisionProtocol(Declaration):
    seed_cohort: SeedCohort
    references: tuple[AnchorReference, ...]

    @model_validator(mode="after")
    def validate_seed_coverage(self) -> "AnchorDecisionProtocol":
        reference_seeds = frozenset(reference.seed for reference in self.references)
        cohort_seeds = frozenset(self.seed_cohort.values)
        if reference_seeds != cohort_seeds:
            raise ValueError("anchor references must cover exactly the historical seed cohort")
        coordinates = tuple(
            (reference.seed, reference.threshold_method, reference.metric) for reference in self.references
        )
        if len(set(coordinates)) != len(coordinates):
            raise ValueError("anchor references must be unique by seed, threshold method, and metric")
        return self


class RuntimeProtocol(Declaration):
    data_root: Path
    outputs_root: Path
    results_root: Path
    require_cuda: bool
    worker_count: int
    overwrite_outputs: bool

    @model_validator(mode="after")
    def validate_paths(self) -> "RuntimeProtocol":
        if self.data_root.is_absolute() or self.outputs_root.is_absolute() or self.results_root.is_absolute():
            raise ValueError("runtime paths must be project-relative")
        if not self.data_root.parts or not self.outputs_root.parts:
            raise ValueError("runtime data and outputs paths must be non-empty")
        if self.data_root.parts[0] != DATA_ROOT.parts[0] or self.outputs_root.parts[0] != OUTPUTS_ROOT.parts[0]:
            raise ValueError("runtime paths must remain under data and outputs")
        if self.results_root != RESULTS_ROOT:
            raise ValueError("results root must be the dedicated project-level results directory")
        if isinstance(self.worker_count, bool) or self.worker_count < 1:
            raise ValueError("worker count must be positive")
        return self


class ResolvedProtocolGraph(Declaration):
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    suppressed_experiment_ids: tuple[ExperimentId, ...]
    temporal_split: TemporalSplitProtocol
    checkpoint: CheckpointProtocol
    calibration: CalibrationEligibilityProtocol

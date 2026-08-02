"""Frozen, typed scientific declarations."""

from math import fsum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CentralizedModelId,
    CentralizedThresholdMethod,
    ClusterAssignmentAlgorithm,
    ClusterFeatureStandardization,
    ClusterFingerprintFeature,
    ClusterThresholdAggregation,
    ConfirmatoryDeltaDirection,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    IntervalMethod,
    KMeansInitialization,
    MetricId,
    OptimizerId,
    PopulationId,
    PopulationIdentityKind,
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
    SeedCount,
    ShrinkageWeight,
    SummaryCoefficient,
    TrafficRatePerDay,
    WeightDecay,
    WorkerCount,
    floats_absolutely_close,
)

REQUIRED_CLUSTER_FINGERPRINT_FEATURES = (
    ClusterFingerprintFeature.BENIGN_ERROR_MEAN,
    ClusterFingerprintFeature.BENIGN_ERROR_STANDARD_DEVIATION,
    ClusterFingerprintFeature.BENIGN_ERROR_SKEWNESS,
    ClusterFingerprintFeature.BENIGN_ERROR_P95,
)
LOCKED_CLUSTER_INITIALIZATION_COUNT = KMeansInitializationCount(10)
LOCKED_CLUSTER_MAXIMUM_ITERATIONS = KMeansMaximumIterationCount(300)
LOCKED_CLUSTER_RANDOM_STATE = Seed(42)
LOCKED_CLUSTER_GROUP_COUNT = GroupCount(3)
CONFIRMATORY_PAIRED_SEED_COUNT = SeedCount(10)

UNIT_FRACTION_TOTAL = 1.0
FRACTION_TOTAL_ABSOLUTE_TOLERANCE = 1e-12


def _sums_to_unit_fraction(*values: Ratio | CoverageTarget) -> bool:
    """Compare declared fractional quantities with one shared tolerance."""
    return floats_absolutely_close(fsum(values), UNIT_FRACTION_TOTAL, FRACTION_TOTAL_ABSOLUTE_TOLERANCE)


class Declaration(StrictModel):
    """Common immutable protocol declaration."""


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
    def member_count(self) -> SeedCount:
        return SeedCount(len(self.values))


class FractionalSplitProtocol(Declaration):
    training: Ratio
    calibration: Ratio
    evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "FractionalSplitProtocol":
        if not _sums_to_unit_fraction(
            self.training,
            self.calibration,
            self.evaluation,
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
            self.historical_training,
            self.historical_calibration,
            self.future_recalibration,
            self.future_evaluation,
        ):
            raise ValueError("temporal split must sum to one")
        return self


class StaticReferenceSplitProtocol(Declaration):
    """Randomized counterpart to the temporal 55/15/10/20 row inventory.

    The reserve is retained and checksummed but never fitted, calibrated, scored,
    or evaluated.  This keeps the static comparison on the same row budget without
    assigning a false temporal meaning to the 10 percent allocation.
    """

    training: Ratio
    calibration: Ratio
    reserve: Ratio
    evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "StaticReferenceSplitProtocol":
        if not _sums_to_unit_fraction(
            self.training,
            self.calibration,
            self.reserve,
            self.evaluation,
        ):
            raise ValueError("static-reference split must sum to one")
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
    weight_decay: WeightDecay


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
    optimizer: OptimizerProtocol


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
        if not _sums_to_unit_fraction(self.coverage, self.significance):
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
        requirements = (
            (
                self.fingerprint_features == REQUIRED_CLUSTER_FINGERPRINT_FEATURES,
                "cluster fingerprint must contain mean, standard deviation, skewness, "
                "and p95 exactly once in locked order",
            ),
            (
                self.feature_standardization is ClusterFeatureStandardization.STANDARD_SCALER,
                "cluster fingerprint standardization must be StandardScaler",
            ),
            (self.assignment_algorithm is ClusterAssignmentAlgorithm.KMEANS, "cluster assignment must be k-means"),
            (
                self.initialization is KMeansInitialization.KMEANS_PLUS_PLUS,
                "cluster initialization must be k-means++",
            ),
            (
                self.initialization_count.value == LOCKED_CLUSTER_INITIALIZATION_COUNT.value,
                "cluster n_init must match the locked initialization count",
            ),
            (
                self.maximum_iterations.value == LOCKED_CLUSTER_MAXIMUM_ITERATIONS.value,
                "cluster max_iter must match the locked maximum iteration count",
            ),
            (
                self.random_state == LOCKED_CLUSTER_RANDOM_STATE,
                "cluster random_state must match the locked seed",
            ),
            (
                self.group_count.value == LOCKED_CLUSTER_GROUP_COUNT.value,
                "cluster group count must match the locked group count",
            ),
            (
                self.threshold_aggregation is ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
                "cluster thresholds must average eligible local thresholds",
            ),
        )
        for satisfied, message in requirements:
            if not satisfied:
                raise ValueError(message)
        return self


class StatisticalInferenceProtocol(Declaration):
    confidence_level: ConfidenceLevel
    seed_cohort: SeedCohort

    @property
    def paired_seed_count(self) -> SeedCount:
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
    identity_kind: PopulationIdentityKind
    client_count: ClientCount

    @model_validator(mode="after")
    def validate_identity_kind(self) -> "PopulationDeclaration":
        match self.identity_kind:
            case PopulationIdentityKind.PHYSICAL_DEVICES:
                if self.dataset is not DatasetId.NBAIOT:
                    raise ValueError("physical-device populations must be confirmatory N-BaIoT devices")
            case PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS:
                if self.dataset is not DatasetId.CICIOT2023:
                    raise ValueError("file-defined pseudo-clients cannot be confirmatory physical devices")
            case PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS:
                if self.dataset is not DatasetId.EDGE_IIOTSET:
                    raise ValueError("source-defined sensor groups are not physical attack-assigned devices")
            case PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS:
                if self.dataset is not DatasetId.NBAIOT:
                    raise ValueError("synthetic Dirichlet clients are not confirmatory physical devices")
            case PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS:
                if self.dataset is not DatasetId.EDGE_IIOTSET:
                    raise ValueError("verified temporal groups require Edge chronology")
        return self

    @property
    def is_confirmatory_population(self) -> bool:
        return self.identity_kind is PopulationIdentityKind.PHYSICAL_DEVICES

    @property
    def requires_family_taxonomy(self) -> bool:
        return self.identity_kind is PopulationIdentityKind.PHYSICAL_DEVICES

    @property
    def requires_verified_chronology(self) -> bool:
        return self.identity_kind is PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS

    @property
    def requires_client_attack_assignment(self) -> bool:
        return self.identity_kind in {
            PopulationIdentityKind.PHYSICAL_DEVICES,
            PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
        }


class ExperimentDeclaration(Declaration):
    id: ExperimentId
    role: EvidenceRole
    population: PopulationId
    training_model: TrainingModelId
    federated_thresholds: tuple[FederatedThresholdMethod, ...]
    metrics: tuple[MetricId, ...]
    readiness: ExperimentReadiness

    @model_validator(mode="after")
    def validate_contents(self) -> "ExperimentDeclaration":
        if not self.federated_thresholds or not self.metrics:
            raise ValueError("experiments require threshold methods and metrics")
        if len(set(self.federated_thresholds)) != len(self.federated_thresholds):
            raise ValueError("experiment threshold methods must be unique")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("experiment metrics must be unique")
        if self.readiness is ExperimentReadiness.EXECUTABLE and self.role is EvidenceRole.OPERATIONAL_TRANSLATION:
            raise ValueError("operational translation experiments cannot be marked executable without rate evidence")
        return self


class ConfirmatoryEndpoint(Declaration):
    experiment: Literal[ExperimentId.SHARED_VS_LOCAL_CONFIRMATION]
    population: Literal[PopulationId.NBAIOT_NATURAL_DEVICES]
    training_model: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    shared_threshold: Literal[FederatedThresholdMethod.SHARED_THRESHOLD]
    local_threshold: Literal[FederatedThresholdMethod.LOCAL_THRESHOLD]
    metric: Literal[MetricId.FPR_COEFFICIENT_OF_VARIATION]
    seed_cohort: SeedCohort
    positive_direction: Literal[ConfirmatoryDeltaDirection.SHARED_MINUS_LOCAL]
    interval_method: Literal[IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN]
    confidence_level: ConfidenceLevel

    @model_validator(mode="after")
    def validate_endpoint(self) -> "ConfirmatoryEndpoint":
        if self.seed_cohort.member_count != CONFIRMATORY_PAIRED_SEED_COUNT:
            raise ValueError("confirmatory endpoint requires the paired ten-seed journal cohort")
        if MetricId.AUROC is self.metric:
            raise ValueError("AUROC is a model-quality control, not the confirmatory endpoint")
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
    worker_count: WorkerCount
    overwrite_outputs: bool

    @model_validator(mode="after")
    def validate_paths(self) -> "RuntimeProtocol":
        if self.data_root.is_absolute() or self.outputs_root.is_absolute() or self.results_root.is_absolute():
            raise ValueError("runtime paths must be project-relative")
        if not self.data_root.parts or not self.outputs_root.parts:
            raise ValueError("runtime data and outputs paths must be non-empty")
        return self


class ResolvedProtocolGraph(Declaration):
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    suppressed_experiment_ids: tuple[ExperimentId, ...]
    temporal_split: TemporalSplitProtocol
    static_reference_split: StaticReferenceSplitProtocol
    non_temporal_split: FractionalSplitProtocol
    checkpoint: CheckpointProtocol
    calibration: CalibrationEligibilityProtocol
    confirmatory_endpoint: ConfirmatoryEndpoint
    confirmatory_inference: StatisticalInferenceProtocol
    anchor: AnchorDecisionProtocol
    runtime: RuntimeProtocol
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...]
    cluster_threshold: ClusterThresholdProtocol
    fedavg_training: FedAvgProtocol

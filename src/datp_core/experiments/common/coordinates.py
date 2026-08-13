from dataclasses import dataclass
from enum import StrEnum

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CalibrationSupportLevel,
    CoordinateStableKey,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TemporalState,
    ThresholdEstimator,
    TrainingModelId,
)
from datp_core.core.numeric import (
    DirichletConcentration,
    KllSketchSize,
    ModelCoefficientValue,
    Quantile,
    ReplicateIndex,
    Seed,
)
from datp_core.data.populations.contracts import ControlledPartitionKind
from datp_core.thresholds.protocols import ClusterFingerprintFeature

_MODEL_COEFFICIENT_TRAINING_MODELS = frozenset(
    (TrainingModelId.FEDPROX_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER)
)
_DITTO_TRAINING_MODELS = frozenset(
    (TrainingModelId.DITTO_GLOBAL_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER)
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionIdentityDeclaration:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_states: tuple[TemporalState | None, ...]

    def __post_init__(self) -> None:
        if not self.temporal_states:
            raise ValueError("execution identity declarations require at least one temporal state")
        if len(frozenset(self.temporal_states)) != len(self.temporal_states):
            raise ValueError("execution identity declaration temporal states must be unique")

    def matches(self, identity: "ExternalTemporalExecutionIdentity") -> bool:
        return (
            identity.experiment is self.experiment
            and identity.population is self.population
            and identity.evidence_role is self.evidence_role
            and identity.temporal_state in self.temporal_states
        )


EXECUTION_IDENTITY_DECLARATIONS = (
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        temporal_states=(None,),
    ),
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        population=PopulationId.CICIOT_FILE_CLIENTS,
        evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
        temporal_states=(None,),
    ),
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_states=(
            TemporalState.STATIC_REFERENCE,
            TemporalState.FROZEN_FUTURE,
            TemporalState.RECALIBRATED_FUTURE,
        ),
    ),
)
BOUNDED_EVIDENCE_POPULATIONS = frozenset(declaration.population for declaration in EXECUTION_IDENTITY_DECLARATIONS)


class ExternalTemporalExecutionIdentity(StrictModel):
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_state: TemporalState | None

    @model_validator(mode="after")
    def validate_declared_identity(self) -> "ExternalTemporalExecutionIdentity":
        matches = tuple(declaration for declaration in EXECUTION_IDENTITY_DECLARATIONS if declaration.matches(self))
        if len(matches) != 1:
            raise ScientificContractError(
                ErrorMessage("execution identity must be declared exactly once"),
                subject=self.experiment,
            )
        return self

    def require_population(self, population: PopulationId) -> None:
        if self.population is not population:
            raise ScientificContractError(ErrorMessage("execution identity population must match"), subject=population)

    def require_evidence_role(self, evidence_role: EvidenceRole) -> None:
        if self.evidence_role is not evidence_role:
            raise ScientificContractError(
                ErrorMessage("execution identity evidence role must match"), subject=evidence_role
            )


def require_execution_identity(
    identity: ExternalTemporalExecutionIdentity | None,
    population: PopulationId,
) -> ExternalTemporalExecutionIdentity | None:
    if population not in BOUNDED_EVIDENCE_POPULATIONS:
        if identity is not None:
            raise ScientificContractError(
                ErrorMessage("execution identity is reserved for bounded evidence"), subject=population
            )
        return None
    if identity is None:
        raise ScientificContractError(
            ErrorMessage("bounded evidence requires an execution identity"), subject=population
        )
    identity.require_population(population)
    return identity


class CoordinateIdentitySegment(StrEnum):
    ALL_METRICS = "all_metrics"
    NO_MODEL_COEFFICIENT = "no_model_coefficient"
    NON_TEMPORAL = "non_temporal"
    CANONICAL_QUANTILE = "canonical_quantile"
    NO_CONTROLLED_PARTITION = "no_controlled_partition"
    NO_CALIBRATION_SUPPORT = "no_calibration_support"


class ExecutionRoute(StrEnum):
    SINGLE_COORDINATE = "single_coordinate"
    DITTO_JOINT_PUBLICATION = "ditto_joint_publication"
    TEMPORAL_PAIRED_EXECUTION = "temporal_paired_execution"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentCoordinate:
    experiment: ExperimentId
    evidence_role: EvidenceRole
    dataset: DatasetId
    population: PopulationId
    training_model: TrainingModelId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_protocol: PreprocessingProtocolId
    model_coefficient: ModelCoefficientValue | None
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None
    threshold_quantile: Quantile | None = None
    controlled_partition_kind: ControlledPartitionKind | None = None
    dirichlet_concentration: DirichletConcentration | None = None
    kll_sketch_size: KllSketchSize | None = None
    calibration_support: CalibrationSupportLevel | None = None
    calibration_replicate: ReplicateIndex | None = None
    threshold_estimator: ThresholdEstimator = ThresholdEstimator.TYPE7_Q95
    cluster_fingerprint_omission: ClusterFingerprintFeature | None = None

    def __post_init__(self) -> None:
        requires_coefficient = self.training_model in _MODEL_COEFFICIENT_TRAINING_MODELS
        if requires_coefficient and self.model_coefficient is None:
            raise ValueError("training models with a declared coefficient grid require a model coefficient")
        if not requires_coefficient and self.model_coefficient is not None:
            raise ValueError("a model coefficient is only active for training models with a declared coefficient grid")
        if self.controlled_partition_kind is ControlledPartitionKind.DIRICHLET and self.dirichlet_concentration is None:
            raise ValueError("Dirichlet controlled partitions require a concentration")
        if self.controlled_partition_kind is ControlledPartitionKind.IID and self.dirichlet_concentration is not None:
            raise ValueError("IID controlled partitions must not carry a concentration")
        if self.controlled_partition_kind is None and self.dirichlet_concentration is not None:
            raise ValueError("a Dirichlet concentration requires a controlled partition kind")
        if self.population is PopulationId.NBAIOT_DIRICHLET_CLIENTS and self.controlled_partition_kind is None:
            raise ValueError("Dirichlet-client populations require an explicit controlled partition condition")
        is_interaction = self.experiment is ExperimentId.HETEROGENEITY_CALIBRATION_SUPPORT_INTERACTION
        if is_interaction and self.calibration_support is None:
            raise ValueError("heterogeneity-support interaction coordinates require calibration support")
        if not is_interaction and (self.calibration_support is not None or self.calibration_replicate is not None):
            raise ValueError("calibration-support coordinates are reserved for the heterogeneity-support interaction")
        if self.calibration_support is CalibrationSupportLevel.FULL:
            if self.calibration_replicate is not None:
                raise ValueError("full calibration support has no subsampling replicate")
        elif self.calibration_support is not None and self.calibration_replicate is None:
            raise ValueError("finite calibration support requires a nested-subsampling replicate")
        if (
            self.cluster_fingerprint_omission is not None
            and self.threshold_method is not FederatedThresholdMethod.CLUSTER_THRESHOLD
        ):
            raise ValueError("cluster fingerprint omission requires the cluster threshold method")

    @property
    def stable_key(self) -> CoordinateStableKey:
        return self._key_for_metric(self.metric.value)

    @property
    def execution_key(self) -> CoordinateStableKey:
        return self._key_for_metric(CoordinateIdentitySegment.ALL_METRICS.value)

    def _key_for_metric(self, metric: str) -> CoordinateStableKey:
        temporal = (
            self.temporal_state.value
            if self.temporal_state is not None
            else CoordinateIdentitySegment.NON_TEMPORAL.value
        )
        coefficient = (
            f"{self.model_coefficient.value}"
            if self.model_coefficient is not None
            else CoordinateIdentitySegment.NO_MODEL_COEFFICIENT.value
        )
        quantile = (
            f"q{self.threshold_quantile.value}"
            if self.threshold_quantile is not None
            else CoordinateIdentitySegment.CANONICAL_QUANTILE.value
        )
        kll_sketch_size = f"k{self.kll_sketch_size.value}" if self.kll_sketch_size is not None else "no_kll"
        calibration_support = (
            self.calibration_support.value
            if self.calibration_support is not None
            else CoordinateIdentitySegment.NO_CALIBRATION_SUPPORT.value
        )
        calibration_replicate = (
            str(self.calibration_replicate.value) if self.calibration_replicate is not None else "no_replicate"
        )
        cluster_fingerprint_omission = (
            self.cluster_fingerprint_omission.value
            if self.cluster_fingerprint_omission is not None
            else "no_cluster_fingerprint_omission"
        )
        if self.controlled_partition_kind is None:
            partition = CoordinateIdentitySegment.NO_CONTROLLED_PARTITION.value
        elif self.controlled_partition_kind is ControlledPartitionKind.IID:
            partition = ControlledPartitionKind.IID.value
        else:
            concentration = self.dirichlet_concentration
            if concentration is None:
                raise ValueError("Dirichlet stable keys require a concentration")
            partition = f"{ControlledPartitionKind.DIRICHLET.value}:{concentration.value}"
        return CoordinateStableKey(
            "/".join(
                (
                    self.experiment.value,
                    self.evidence_role.value,
                    self.dataset.value,
                    self.population.value,
                    self.training_model.value,
                    str(self.training_seed.value),
                    self.split_protocol.value,
                    self.preprocessing_protocol.value,
                    coefficient,
                    self.threshold_method.value,
                    metric,
                    temporal,
                    quantile,
                    partition,
                    kll_sketch_size,
                    calibration_support,
                    calibration_replicate,
                    self.threshold_estimator.value,
                    cluster_fingerprint_omission,
                )
            )
        )


def execution_route_for(coordinate: ExperimentCoordinate) -> ExecutionRoute:
    if coordinate.temporal_state is not None:
        return ExecutionRoute.TEMPORAL_PAIRED_EXECUTION
    if coordinate.training_model in _DITTO_TRAINING_MODELS:
        return ExecutionRoute.DITTO_JOINT_PUBLICATION
    return ExecutionRoute.SINGLE_COORDINATE

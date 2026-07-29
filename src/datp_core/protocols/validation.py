"""Whole-graph scientific validation."""

from dataclasses import dataclass

from datp_core.domain.enums import (
    ConfirmatoryDeltaDirection,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.errors import ProtocolValidationError, UnresolvedScientificValueError
from datp_core.domain.values import CalibrationSize, ConfidenceLevel

from .anchor import ANCHOR_DECISION_PROTOCOL
from .calibration import CLUSTER_THRESHOLD_PROTOCOL, MINIMUM_BENIGN_SUPPORT
from .experiments import EXPERIMENTS
from .models import (
    AnchorDecisionProtocol,
    CalibrationEligibilityProtocol,
    CheckpointProtocol,
    ClusterThresholdProtocol,
    ConfirmatoryEndpoint,
    ExperimentDeclaration,
    FedAvgProtocol,
    FractionalSplitProtocol,
    PopulationDeclaration,
    ResolvedProtocolGraph,
    RuntimeProtocol,
    StatisticalInferenceProtocol,
    TemporalSplitProtocol,
    TrafficRateEvidence,
)
from .populations import POPULATIONS
from .runtime import CANONICAL_RUNTIME
from .seeds import CONFIRMATORY_SEED_COHORT
from .splits import NON_TEMPORAL_SPLIT, TEMPORAL_SPLIT
from .statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from .traffic_rates import TRAFFIC_RATE_EVIDENCE
from .training import CHECKPOINT_PROTOCOL, FEDAVG_TRAINING_PROTOCOL

CONFIRMATORY_ENDPOINT = ConfirmatoryEndpoint(
    experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    shared_threshold=FederatedThresholdMethod.SHARED_THRESHOLD,
    local_threshold=FederatedThresholdMethod.LOCAL_THRESHOLD,
    metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
    seed_cohort=CONFIRMATORY_SEED_COHORT,
    positive_direction=ConfirmatoryDeltaDirection.SHARED_MINUS_LOCAL,
    interval_method=IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
    confidence_level=ConfidenceLevel(0.95),
)

_ATTACK_SENSITIVE_METRICS = (
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
    MetricId.P10_BINARY_MACRO_F1,
    MetricId.WORST_CLIENT_BALANCED_ACCURACY,
    MetricId.TPR_COEFFICIENT_OF_VARIATION,
    MetricId.MEAN_CLIENT_MACRO_F1,
    MetricId.POOLED_MACRO_F1,
    MetricId.MEAN_CLIENT_BALANCED_ACCURACY,
)


@dataclass(frozen=True, slots=True)
class ProtocolGraphInputs:
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    temporal_split: TemporalSplitProtocol
    non_temporal_split: FractionalSplitProtocol
    checkpoint: CheckpointProtocol
    minimum_support: CalibrationSize
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...]
    confirmatory_endpoint: ConfirmatoryEndpoint
    confirmatory_inference: StatisticalInferenceProtocol
    anchor: AnchorDecisionProtocol
    runtime: RuntimeProtocol
    cluster_threshold: ClusterThresholdProtocol
    fedavg_training: FedAvgProtocol


CANONICAL_PROTOCOL_GRAPH = ProtocolGraphInputs(
    populations=POPULATIONS,
    experiments=EXPERIMENTS,
    temporal_split=TEMPORAL_SPLIT,
    non_temporal_split=NON_TEMPORAL_SPLIT,
    checkpoint=CHECKPOINT_PROTOCOL,
    minimum_support=MINIMUM_BENIGN_SUPPORT,
    traffic_rate_evidence=TRAFFIC_RATE_EVIDENCE,
    confirmatory_endpoint=CONFIRMATORY_ENDPOINT,
    confirmatory_inference=CONFIRMATORY_INFERENCE_PROTOCOL,
    anchor=ANCHOR_DECISION_PROTOCOL,
    runtime=CANONICAL_RUNTIME,
    cluster_threshold=CLUSTER_THRESHOLD_PROTOCOL,
    fedavg_training=FEDAVG_TRAINING_PROTOCOL,
)


def validate_protocol_graph(inputs: ProtocolGraphInputs) -> ResolvedProtocolGraph:
    _require_unique_declaration_ids(inputs.populations, inputs.experiments)
    if inputs.runtime != CANONICAL_RUNTIME:
        raise ProtocolValidationError("runtime values must match the canonical runtime declaration")
    suppressed_experiment_ids: list[ExperimentId] = []
    _validate_confirmatory_endpoint(
        inputs.confirmatory_endpoint,
        inputs.confirmatory_inference,
        inputs.experiments,
        inputs.populations,
    )
    population_ids = tuple(population.id for population in inputs.populations)
    for experiment in inputs.experiments:
        population = _population(experiment.population, inputs.populations, population_ids)
        _validate_experiment_population_pair(experiment, population)
        _validate_experiment_thresholds(experiment, population, inputs.cluster_threshold)
        _validate_experiment_metrics(
            experiment,
            population,
            inputs.traffic_rate_evidence,
            suppressed_experiment_ids,
        )
        _validate_experiment_readiness(experiment, suppressed_experiment_ids)
    return ResolvedProtocolGraph(
        populations=inputs.populations,
        experiments=inputs.experiments,
        suppressed_experiment_ids=tuple(suppressed_experiment_ids),
        temporal_split=inputs.temporal_split,
        non_temporal_split=inputs.non_temporal_split,
        checkpoint=inputs.checkpoint,
        calibration=CalibrationEligibilityProtocol(minimum_support=inputs.minimum_support),
        confirmatory_endpoint=inputs.confirmatory_endpoint,
        confirmatory_inference=inputs.confirmatory_inference,
        anchor=inputs.anchor,
        runtime=inputs.runtime,
        traffic_rate_evidence=inputs.traffic_rate_evidence,
        cluster_threshold=inputs.cluster_threshold,
        fedavg_training=inputs.fedavg_training,
    )


def _require_unique_declaration_ids(
    populations: tuple[PopulationDeclaration, ...],
    experiments: tuple[ExperimentDeclaration, ...],
) -> None:
    population_ids = tuple(population.id for population in populations)
    experiment_ids = tuple(experiment.id for experiment in experiments)
    if len(set(population_ids)) != len(population_ids) or len(set(experiment_ids)) != len(experiment_ids):
        raise ProtocolValidationError("Protocol declaration identifiers must be unique")


def _population(
    population_id: PopulationId,
    populations: tuple[PopulationDeclaration, ...],
    population_ids: tuple[PopulationId, ...],
) -> PopulationDeclaration:
    if population_id not in population_ids:
        raise ProtocolValidationError("Experiment references an unknown population")
    return next(population for population in populations if population.id is population_id)


def _validate_confirmatory_endpoint(
    endpoint: ConfirmatoryEndpoint,
    inference: StatisticalInferenceProtocol,
    experiments: tuple[ExperimentDeclaration, ...],
    populations: tuple[PopulationDeclaration, ...],
) -> None:
    _require_endpoint_matches_inference(endpoint, inference)
    confirmatory = tuple(experiment for experiment in experiments if experiment.role is EvidenceRole.CONFIRMATORY)
    if not confirmatory:
        return
    if len(confirmatory) != 1:
        raise ProtocolValidationError("Exactly one confirmatory experiment must be declared")
    _require_endpoint_matches_experiment(endpoint, confirmatory[0])
    population = next(item for item in populations if item.id is endpoint.population)
    if not population.is_confirmatory_population:
        raise ProtocolValidationError("Confirmatory endpoint requires a confirmatory-eligible population")


def _require_endpoint_matches_inference(
    endpoint: ConfirmatoryEndpoint,
    inference: StatisticalInferenceProtocol,
) -> None:
    if endpoint.seed_cohort != inference.seed_cohort:
        raise ProtocolValidationError("Confirmatory endpoint seed cohort must match confirmatory inference")
    if endpoint.confidence_level != inference.confidence_level:
        raise ProtocolValidationError("Confirmatory endpoint confidence must match confirmatory inference")


def _require_endpoint_matches_experiment(
    endpoint: ConfirmatoryEndpoint,
    experiment: ExperimentDeclaration,
) -> None:
    if experiment.id is not endpoint.experiment:
        raise ProtocolValidationError("Confirmatory experiment identity must match the locked endpoint")
    if experiment.population is not endpoint.population:
        raise ProtocolValidationError("Confirmatory experiment requires NBAIOT_NATURAL_DEVICES")
    if experiment.training_model is not endpoint.training_model:
        raise ProtocolValidationError("Confirmatory experiment requires FEDAVG_AUTOENCODER")
    if endpoint.shared_threshold not in experiment.federated_thresholds:
        raise ProtocolValidationError("Confirmatory experiment requires SHARED_THRESHOLD")
    if endpoint.local_threshold not in experiment.federated_thresholds:
        raise ProtocolValidationError("Confirmatory experiment requires LOCAL_THRESHOLD")
    if endpoint.metric not in experiment.metrics:
        raise ProtocolValidationError("Confirmatory experiment requires FPR_COEFFICIENT_OF_VARIATION")
    if MetricId.AUROC is endpoint.metric:
        raise ProtocolValidationError("AUROC cannot be the confirmatory endpoint")


def _validate_experiment_population_pair(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
) -> None:
    if experiment.role is EvidenceRole.CONFIRMATORY and not population.is_confirmatory_population:
        raise ProtocolValidationError("Confirmatory experiments require confirmatory-eligible populations")
    if experiment.role is EvidenceRole.TEMPORAL_BOUNDARY and not population.requires_verified_chronology:
        raise ProtocolValidationError("Temporal experiments require populations with verified chronology")
    if (
        experiment.role is EvidenceRole.CONFIRMATORY
        and experiment.population is not PopulationId.NBAIOT_NATURAL_DEVICES
    ):
        raise ProtocolValidationError("Confirmatory experiments require NBAIOT_NATURAL_DEVICES")
    if (
        experiment.role is EvidenceRole.CONFIRMATORY
        and experiment.training_model is not TrainingModelId.FEDAVG_AUTOENCODER
    ):
        raise ProtocolValidationError("Confirmatory experiments require FEDAVG_AUTOENCODER")


def _validate_experiment_thresholds(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
    cluster_threshold: ClusterThresholdProtocol,
) -> None:
    if (
        FederatedThresholdMethod.FAMILY_THRESHOLD in experiment.federated_thresholds
        and not population.requires_family_taxonomy
    ):
        raise ProtocolValidationError("Family thresholding requires a family taxonomy")
    if FederatedThresholdMethod.CLUSTER_THRESHOLD in experiment.federated_thresholds:
        if cluster_threshold.group_count.value >= population.client_count.value:
            raise ProtocolValidationError("Grouped thresholding requires more eligible clients than canonical groups")


def _validate_experiment_metrics(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...],
    suppressed_experiment_ids: list[ExperimentId],
) -> None:
    uses_attack_metric = any(metric in experiment.metrics for metric in _ATTACK_SENSITIVE_METRICS)
    if uses_attack_metric and not population.requires_client_attack_assignment:
        raise ProtocolValidationError("Attack-sensitive metrics require attack assignment")
    if MetricId.ALERTS_PER_DAY not in experiment.metrics:
        return
    has_rate_evidence = any(evidence.population is experiment.population for evidence in traffic_rate_evidence)
    if has_rate_evidence:
        return
    if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
        raise UnresolvedScientificValueError(
            "Alert burden requires population-specific traffic-rate evidence",
            subject="traffic rate",
        )
    suppressed_experiment_ids.append(experiment.id)


def _validate_experiment_readiness(
    experiment: ExperimentDeclaration,
    suppressed_experiment_ids: list[ExperimentId],
) -> None:
    if experiment.id in suppressed_experiment_ids and experiment.readiness is not ExperimentReadiness.SUPPRESSED:
        raise ProtocolValidationError("Suppressed experiments must declare SUPPRESSED readiness")
    if experiment.readiness is ExperimentReadiness.EXECUTABLE:
        raise ProtocolValidationError(
            "Future experiments cannot be marked executable before their implementation phase is complete"
        )
    if experiment.readiness is ExperimentReadiness.SUPPRESSED and experiment.id not in suppressed_experiment_ids:
        if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
            raise ProtocolValidationError("Only operational-suppression experiments may declare SUPPRESSED readiness")

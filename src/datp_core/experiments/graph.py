"""Whole-graph scientific declarations, observation contracts, and validation."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.protocols import ATTACK_SENSITIVE_METRICS, SUPPRESSED_OPERATIONAL_METRICS
from datp_core.analysis.operational.traffic_rates import TRAFFIC_RATE_EVIDENCE, TrafficRateEvidence
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ProtocolValidationError,
    UnresolvedScientificValueError,
)
from datp_core.core.identifiers import (
    ContractSubject,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import CalibrationSize
from datp_core.data.populations.contracts import POPULATIONS, PopulationDeclaration
from datp_core.data.populations.protocols import (
    NON_TEMPORAL_SPLIT,
    STATIC_REFERENCE_SPLIT,
    TEMPORAL_SPLIT,
    FractionalSplitProtocol,
    StaticReferenceSplitProtocol,
    TemporalSplitProtocol,
)
from datp_core.detector.training.contracts import FedAvgProtocol
from datp_core.detector.training.protocols import FEDAVG_TRAINING_PROTOCOL
from datp_core.experiments.anchor.spec import ANCHOR_DECISION_PROTOCOL, AnchorDecisionProtocol
from datp_core.experiments.confirmatory.spec import (
    CONFIRMATORY_ENDPOINT,
    CONFIRMATORY_INFERENCE_PROTOCOL,
    ConfirmatoryEndpoint,
)
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.thresholds.protocols import (
    CLUSTER_THRESHOLD_PROTOCOL,
    MINIMUM_BENIGN_SUPPORT,
    CalibrationEligibilityProtocol,
    ClusterThresholdProtocol,
)


class ResolvedProtocolGraph(StrictModel):
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    suppressed_experiment_ids: tuple[ExperimentId, ...]
    temporal_split: TemporalSplitProtocol
    static_reference_split: StaticReferenceSplitProtocol
    non_temporal_split: FractionalSplitProtocol
    calibration: CalibrationEligibilityProtocol
    confirmatory_endpoint: ConfirmatoryEndpoint
    confirmatory_inference: PairedInferenceProtocol
    anchor: AnchorDecisionProtocol
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...]
    cluster_threshold: ClusterThresholdProtocol
    fedavg_training: FedAvgProtocol


@dataclass(frozen=True, slots=True)
class ProtocolGraphInputs:
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    temporal_split: TemporalSplitProtocol
    static_reference_split: StaticReferenceSplitProtocol
    non_temporal_split: FractionalSplitProtocol
    minimum_support: CalibrationSize
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...]
    confirmatory_endpoint: ConfirmatoryEndpoint
    confirmatory_inference: PairedInferenceProtocol
    anchor: AnchorDecisionProtocol
    cluster_threshold: ClusterThresholdProtocol
    fedavg_training: FedAvgProtocol


CANONICAL_PROTOCOL_GRAPH = ProtocolGraphInputs(
    populations=POPULATIONS,
    experiments=EXPERIMENTS,
    temporal_split=TEMPORAL_SPLIT,
    static_reference_split=STATIC_REFERENCE_SPLIT,
    non_temporal_split=NON_TEMPORAL_SPLIT,
    minimum_support=MINIMUM_BENIGN_SUPPORT,
    traffic_rate_evidence=TRAFFIC_RATE_EVIDENCE,
    confirmatory_endpoint=CONFIRMATORY_ENDPOINT,
    confirmatory_inference=CONFIRMATORY_INFERENCE_PROTOCOL,
    anchor=ANCHOR_DECISION_PROTOCOL,
    cluster_threshold=CLUSTER_THRESHOLD_PROTOCOL,
    fedavg_training=FEDAVG_TRAINING_PROTOCOL,
)


def validate_protocol_graph(inputs: ProtocolGraphInputs) -> ResolvedProtocolGraph:
    _require_unique_declaration_ids(inputs.populations, inputs.experiments)
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
        static_reference_split=inputs.static_reference_split,
        non_temporal_split=inputs.non_temporal_split,
        calibration=CalibrationEligibilityProtocol(minimum_support=inputs.minimum_support),
        confirmatory_endpoint=inputs.confirmatory_endpoint,
        confirmatory_inference=inputs.confirmatory_inference,
        anchor=inputs.anchor,
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
        raise ProtocolValidationError(ErrorMessage("Protocol declaration identifiers must be unique"))


def _population(
    population_id: PopulationId,
    populations: tuple[PopulationDeclaration, ...],
    population_ids: tuple[PopulationId, ...],
) -> PopulationDeclaration:
    if population_id not in population_ids:
        raise ProtocolValidationError(ErrorMessage("Experiment references an unknown population"))
    return next(population for population in populations if population.id is population_id)


def _validate_confirmatory_endpoint(
    endpoint: ConfirmatoryEndpoint,
    inference: PairedInferenceProtocol,
    experiments: tuple[ExperimentDeclaration, ...],
    populations: tuple[PopulationDeclaration, ...],
) -> None:
    _require_endpoint_matches_inference(endpoint, inference)
    confirmatory = tuple(experiment for experiment in experiments if experiment.role is EvidenceRole.CONFIRMATORY)
    if not confirmatory:
        return
    if len(confirmatory) != 1:
        raise ProtocolValidationError(ErrorMessage("Exactly one confirmatory experiment must be declared"))
    _require_endpoint_matches_experiment(endpoint, confirmatory[0])
    population = next(item for item in populations if item.id is endpoint.population)
    if not population.is_confirmatory_population:
        raise ProtocolValidationError(ErrorMessage("Confirmatory endpoint requires a confirmatory-eligible population"))


def _require_endpoint_matches_inference(
    endpoint: ConfirmatoryEndpoint,
    inference: PairedInferenceProtocol,
) -> None:
    if endpoint.inference_protocol != inference:
        raise ProtocolValidationError(ErrorMessage("Confirmatory endpoint inference must match confirmatory inference"))


def _require_endpoint_matches_experiment(
    endpoint: ConfirmatoryEndpoint,
    experiment: ExperimentDeclaration,
) -> None:
    if experiment.id is not endpoint.experiment:
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiment identity must match the locked endpoint"))
    if experiment.population is not endpoint.population:
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiment requires NBAIOT_NATURAL_DEVICES"))
    if experiment.training_model is not endpoint.training_model:
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiment requires FEDAVG_AUTOENCODER"))
    if endpoint.shared_threshold not in experiment.federated_thresholds:
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiment requires SHARED_THRESHOLD"))
    if endpoint.local_threshold not in experiment.federated_thresholds:
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiment requires LOCAL_THRESHOLD"))
    if endpoint.metric not in experiment.metrics:
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiment requires FPR_COEFFICIENT_OF_VARIATION"))


def _validate_experiment_population_pair(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
) -> None:
    if experiment.role is EvidenceRole.CONFIRMATORY and not population.is_confirmatory_population:
        raise ProtocolValidationError(
            ErrorMessage("Confirmatory experiments require confirmatory-eligible populations")
        )
    if experiment.role is EvidenceRole.TEMPORAL_BOUNDARY and not population.requires_verified_chronology:
        raise ProtocolValidationError(ErrorMessage("Temporal experiments require populations with verified chronology"))
    if (
        experiment.role is EvidenceRole.CONFIRMATORY
        and experiment.population is not PopulationId.NBAIOT_NATURAL_DEVICES
    ):
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiments require NBAIOT_NATURAL_DEVICES"))
    if (
        experiment.role is EvidenceRole.CONFIRMATORY
        and experiment.training_model is not TrainingModelId.FEDAVG_AUTOENCODER
    ):
        raise ProtocolValidationError(ErrorMessage("Confirmatory experiments require FEDAVG_AUTOENCODER"))


def _validate_experiment_thresholds(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
    cluster_threshold: ClusterThresholdProtocol,
) -> None:
    if (
        FederatedThresholdMethod.FAMILY_THRESHOLD in experiment.federated_thresholds
        and not population.requires_family_taxonomy
    ):
        raise ProtocolValidationError(ErrorMessage("Family thresholding requires a family taxonomy"))
    if FederatedThresholdMethod.CLUSTER_THRESHOLD in experiment.federated_thresholds:
        if not cluster_threshold.group_count.fits_within(population.client_count):
            raise ProtocolValidationError(
                ErrorMessage("Grouped thresholding requires more eligible clients than canonical groups")
            )


def _validate_experiment_metrics(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...],
    suppressed_experiment_ids: list[ExperimentId],
) -> None:
    uses_attack_metric = any(metric in experiment.metrics for metric in ATTACK_SENSITIVE_METRICS)
    if uses_attack_metric and not population.requires_client_attack_assignment:
        raise ProtocolValidationError(ErrorMessage("Attack-sensitive metrics require attack assignment"))
    if not any(metric in experiment.metrics for metric in SUPPRESSED_OPERATIONAL_METRICS):
        return
    has_rate_evidence = any(evidence.population is experiment.population for evidence in traffic_rate_evidence)
    if has_rate_evidence:
        return
    if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
        raise UnresolvedScientificValueError(
            ErrorMessage("Alert burden requires population-specific traffic-rate evidence"),
            subject=ContractSubject.TRAFFIC_RATE,
        )
    suppressed_experiment_ids.append(experiment.id)


def _validate_experiment_readiness(
    experiment: ExperimentDeclaration,
    suppressed_experiment_ids: list[ExperimentId],
) -> None:
    if experiment.id in suppressed_experiment_ids and experiment.readiness is not ExperimentReadiness.SUPPRESSED:
        raise ProtocolValidationError(ErrorMessage("Suppressed experiments must declare SUPPRESSED readiness"))
    if experiment.readiness is ExperimentReadiness.EXECUTABLE:
        raise ProtocolValidationError(
            ErrorMessage("Future experiments cannot be marked executable before their implementation is complete")
        )
    if experiment.readiness is ExperimentReadiness.SUPPRESSED and experiment.id not in suppressed_experiment_ids:
        if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
            raise ProtocolValidationError(
                ErrorMessage("Only operational-suppression experiments may declare SUPPRESSED readiness")
            )

"""Whole-graph scientific declarations, observation contracts, and validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.protocols import ATTACK_SENSITIVE_METRICS, SUPPRESSED_OPERATIONAL_METRICS
from datp_core.analysis.operational.traffic_rates import TRAFFIC_RATE_EVIDENCE, TrafficRateEvidence
from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ProtocolValidationError, UnresolvedScientificValueError
from datp_core.core.identifiers import (
    ContractSubject,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.core.numeric import CalibrationSize, Seed
from datp_core.data.populations.contracts import POPULATIONS, PopulationDeclaration
from datp_core.data.populations.protocols import (
    NON_TEMPORAL_SPLIT,
    STATIC_REFERENCE_SPLIT,
    TEMPORAL_SPLIT,
    FractionalSplitProtocol,
    StaticReferenceSplitProtocol,
    TemporalSplitProtocol,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.checkpoints.protocols import CHECKPOINT_PROTOCOL
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
    checkpoint: CheckpointProtocol
    calibration: CalibrationEligibilityProtocol
    confirmatory_endpoint: ConfirmatoryEndpoint
    confirmatory_inference: PairedInferenceProtocol
    anchor: AnchorDecisionProtocol
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...]
    cluster_threshold: ClusterThresholdProtocol
    fedavg_training: FedAvgProtocol


class GraphCoordinate(Protocol):
    """Scientific identity exposed to observation-only graph extensions."""

    @property
    def experiment(self) -> ExperimentId: ...

    @property
    def evidence_role(self) -> EvidenceRole: ...

    @property
    def dataset(self) -> DatasetId: ...

    @property
    def population(self) -> PopulationId: ...

    @property
    def training_model(self) -> TrainingModelId: ...

    @property
    def training_seed(self) -> Seed: ...

    @property
    def split_protocol(self) -> SplitProtocolId: ...

    @property
    def threshold_method(self) -> FederatedThresholdMethod: ...

    @property
    def metric(self) -> MetricId: ...

    @property
    def temporal_state(self) -> TemporalState | None: ...


class ObservationBoundary(StrEnum):
    AFTER_SCORE_GENERATION_BEFORE_CALIBRATION = "after_score_generation_before_calibration"
    AFTER_CALIBRATION_BEFORE_THRESHOLD_CONSTRUCTION = "after_calibration_before_threshold_construction"
    AFTER_THRESHOLD_CONSTRUCTION_BEFORE_EVALUATION = "after_threshold_construction_before_evaluation"
    AFTER_EVALUATION_BEFORE_ANALYSIS = "after_evaluation_before_analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationContext:
    boundary: ObservationBoundary
    coordinate: GraphCoordinate
    input_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationResult:
    boundary: ObservationBoundary
    coordinate: GraphCoordinate
    input_checksum: Checksum
    output_checksum: Checksum

    def __post_init__(self) -> None:
        if self.input_checksum != self.output_checksum:
            raise ValueError("observation hooks cannot alter scientific artifacts")


class ObservationHook(Protocol):
    def observe(self, context: ObservationContext) -> ObservationResult: ...


@dataclass(frozen=True, slots=True)
class IdentityObservationHook:
    def observe(self, context: ObservationContext) -> ObservationResult:
        return ObservationResult(
            boundary=context.boundary,
            coordinate=context.coordinate,
            input_checksum=context.input_checksum,
            output_checksum=context.input_checksum,
        )


def observe_graph_boundary(
    context: ObservationContext,
    hook: ObservationHook | None,
) -> ObservationResult:
    selected_hook = hook if hook is not None else IdentityObservationHook()
    result = selected_hook.observe(context)
    if result.boundary is not context.boundary or result.coordinate != context.coordinate:
        raise ValueError("observation hook changed its scientific boundary or coordinate")
    if result.input_checksum != context.input_checksum or result.output_checksum != context.input_checksum:
        raise ValueError("observation hook changed a scientific artifact identity")
    return result


@dataclass(frozen=True, slots=True)
class ProtocolGraphInputs:
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    temporal_split: TemporalSplitProtocol
    static_reference_split: StaticReferenceSplitProtocol
    non_temporal_split: FractionalSplitProtocol
    checkpoint: CheckpointProtocol
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
    checkpoint=CHECKPOINT_PROTOCOL,
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
        checkpoint=inputs.checkpoint,
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
    inference: PairedInferenceProtocol,
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
    inference: PairedInferenceProtocol,
) -> None:
    if endpoint.inference_protocol != inference:
        raise ProtocolValidationError("Confirmatory endpoint inference must match confirmatory inference")


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
        if not cluster_threshold.group_count.fits_within(population.client_count):
            raise ProtocolValidationError("Grouped thresholding requires more eligible clients than canonical groups")


def _validate_experiment_metrics(
    experiment: ExperimentDeclaration,
    population: PopulationDeclaration,
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...],
    suppressed_experiment_ids: list[ExperimentId],
) -> None:
    uses_attack_metric = any(metric in experiment.metrics for metric in ATTACK_SENSITIVE_METRICS)
    if uses_attack_metric and not population.requires_client_attack_assignment:
        raise ProtocolValidationError("Attack-sensitive metrics require attack assignment")
    if not any(metric in experiment.metrics for metric in SUPPRESSED_OPERATIONAL_METRICS):
        return
    has_rate_evidence = any(evidence.population is experiment.population for evidence in traffic_rate_evidence)
    if has_rate_evidence:
        return
    if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
        raise UnresolvedScientificValueError(
            "Alert burden requires population-specific traffic-rate evidence",
            subject=ContractSubject.TRAFFIC_RATE,
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
            "Future experiments cannot be marked executable before their implementation is complete"
        )
    if experiment.readiness is ExperimentReadiness.SUPPRESSED and experiment.id not in suppressed_experiment_ids:
        if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
            raise ProtocolValidationError("Only operational-suppression experiments may declare SUPPRESSED readiness")

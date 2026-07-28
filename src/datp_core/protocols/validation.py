"""Whole-graph scientific validation."""

from datp_core.domain.enums import EvidenceRole, ExperimentId, FederatedThresholdMethod, MetricId
from datp_core.domain.errors import ProtocolValidationError, UnresolvedScientificValueError

from .calibration import CLUSTER_THRESHOLD_PROTOCOL, MINIMUM_BENIGN_SUPPORT
from .experiments import EXPERIMENTS
from .models import CalibrationEligibilityProtocol, ResolvedProtocolGraph
from .populations import POPULATIONS
from .splits import TEMPORAL_SPLIT
from .traffic_rates import TRAFFIC_RATE_EVIDENCE
from .training import CHECKPOINT_PROTOCOL


def validate_protocol_graph(
    *,
    populations=POPULATIONS,
    experiments=EXPERIMENTS,
    temporal_split=TEMPORAL_SPLIT,
    checkpoint=CHECKPOINT_PROTOCOL,
    minimum_support=MINIMUM_BENIGN_SUPPORT,
    traffic_rate_evidence=TRAFFIC_RATE_EVIDENCE,
) -> ResolvedProtocolGraph:
    population_ids = tuple(population.id for population in populations)
    experiment_ids = tuple(experiment.id for experiment in experiments)
    suppressed_experiment_ids: list[ExperimentId] = []
    if len(set(population_ids)) != len(population_ids) or len(set(experiment_ids)) != len(experiment_ids):
        raise ProtocolValidationError("Protocol declaration identifiers must be unique")
    for experiment in experiments:
        if experiment.population not in population_ids:
            raise ProtocolValidationError("Experiment references an unknown population")
        population = next(population for population in populations if population.id == experiment.population)
        if experiment.role is EvidenceRole.CONFIRMATORY and not population.confirmatory_eligible:
            raise ProtocolValidationError("Confirmatory experiments require confirmatory-eligible populations")
        if (
            FederatedThresholdMethod.FAMILY_THRESHOLD in experiment.federated_thresholds
            and not population.has_family_taxonomy
        ):
            raise ProtocolValidationError("Family thresholding requires a family taxonomy")
        if FederatedThresholdMethod.CLUSTER_THRESHOLD in experiment.federated_thresholds:
            cluster_protocol = CLUSTER_THRESHOLD_PROTOCOL
            if cluster_protocol.group_count.value >= population.client_count.value:
                raise ProtocolValidationError(
                    "Grouped thresholding requires more eligible clients than canonical groups"
                )
        if (
            any(
                metric in experiment.metrics
                for metric in (
                    MetricId.TRUE_POSITIVE_RATE,
                    MetricId.BALANCED_ACCURACY,
                    MetricId.BINARY_MACRO_F1,
                    MetricId.AUROC,
                )
            )
            and not population.has_attack_assignment
        ):
            raise ProtocolValidationError("Attack-sensitive metrics require attack assignment")
        if MetricId.ALERTS_PER_DAY in experiment.metrics and not any(
            evidence.population == experiment.population for evidence in traffic_rate_evidence
        ):
            if experiment.role is not EvidenceRole.OPERATIONAL_TRANSLATION:
                raise UnresolvedScientificValueError(
                    "Alert burden requires population-specific traffic-rate evidence", subject="traffic rate"
                )
            suppressed_experiment_ids.append(experiment.id)
    return ResolvedProtocolGraph(
        populations=populations,
        experiments=experiments,
        suppressed_experiment_ids=tuple(suppressed_experiment_ids),
        temporal_split=temporal_split,
        checkpoint=checkpoint,
        calibration=CalibrationEligibilityProtocol(minimum_support=minimum_support),
    )

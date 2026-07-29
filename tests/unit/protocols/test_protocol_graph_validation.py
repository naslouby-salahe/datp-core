from dataclasses import replace

import pytest

from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.errors import ProtocolValidationError, UnresolvedScientificValueError
from datp_core.domain.values import SeedCount
from datp_core.protocols.models import ExperimentDeclaration
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.runtime import CANONICAL_RUNTIME
from datp_core.protocols.validation import (
    CANONICAL_PROTOCOL_GRAPH,
    CONFIRMATORY_ENDPOINT,
    validate_protocol_graph,
)


def test_canonical_graph_is_fully_resolved() -> None:
    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)

    assert graph.populations == POPULATIONS
    assert graph.experiments
    assert graph.suppressed_experiment_ids == (ExperimentId.ALERT_BURDEN_TRANSLATION,)
    assert graph.confirmatory_endpoint == CONFIRMATORY_ENDPOINT
    assert graph.confirmatory_inference.paired_seed_count == SeedCount(10)
    assert graph.runtime == CANONICAL_RUNTIME
    assert graph.runtime.require_cuda is True
    assert graph.runtime.worker_count == 6
    assert all(experiment.readiness is not ExperimentReadiness.EXECUTABLE for experiment in graph.experiments)


def test_confirmatory_endpoint_is_structurally_locked() -> None:
    endpoint = CONFIRMATORY_ENDPOINT
    assert endpoint.experiment is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION
    assert endpoint.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert endpoint.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert endpoint.shared_threshold is FederatedThresholdMethod.SHARED_THRESHOLD
    assert endpoint.local_threshold is FederatedThresholdMethod.LOCAL_THRESHOLD
    assert endpoint.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    assert endpoint.seed_cohort.member_count == SeedCount(10)


def test_graph_rejects_attack_metric_without_attack_assignment() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        role=EvidenceRole.EXTERNAL_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.TRUE_POSITIVE_RATE,),
        readiness=ExperimentReadiness.DECLARED,
    )
    graph = replace(CANONICAL_PROTOCOL_GRAPH, experiments=(experiment,))
    with pytest.raises(ProtocolValidationError, match="attack assignment"):
        validate_protocol_graph(graph)


def test_graph_rejects_alert_burden_without_evidence_outside_suppressed_operational_scope() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        role=EvidenceRole.EXTERNAL_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.ALERTS_PER_DAY,),
        readiness=ExperimentReadiness.DECLARED,
    )
    graph = replace(CANONICAL_PROTOCOL_GRAPH, experiments=(experiment,))
    with pytest.raises(UnresolvedScientificValueError, match="Alert burden"):
        validate_protocol_graph(graph)


def test_graph_rejects_temporal_experiment_without_verified_chronology() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        role=EvidenceRole.TEMPORAL_BOUNDARY,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.FALSE_POSITIVE_RATE,),
        readiness=ExperimentReadiness.DECLARED,
    )
    graph = replace(CANONICAL_PROTOCOL_GRAPH, experiments=(experiment,))
    with pytest.raises(ProtocolValidationError, match="verified chronology"):
        validate_protocol_graph(graph)


def test_graph_rejects_premature_executable_readiness() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        role=EvidenceRole.CONFIRMATORY,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        metrics=(MetricId.FPR_COEFFICIENT_OF_VARIATION,),
        readiness=ExperimentReadiness.EXECUTABLE,
    )
    graph = replace(CANONICAL_PROTOCOL_GRAPH, experiments=(experiment,))
    with pytest.raises(ProtocolValidationError, match="executable"):
        validate_protocol_graph(graph)

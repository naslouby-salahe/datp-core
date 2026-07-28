import pytest

from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.errors import ProtocolValidationError, UnresolvedScientificValueError
from datp_core.protocols.models import ExperimentDeclaration
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.validation import validate_protocol_graph


def test_default_graph_is_fully_resolved() -> None:
    graph = validate_protocol_graph()

    assert graph.populations == POPULATIONS
    assert graph.experiments
    assert graph.suppressed_experiment_ids == (ExperimentId.ALERT_BURDEN_TRANSLATION,)


def test_graph_rejects_attack_metric_without_attack_assignment() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        role=EvidenceRole.EXTERNAL_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.TRUE_POSITIVE_RATE,),
    )
    with pytest.raises(ProtocolValidationError, match="attack assignment"):
        validate_protocol_graph(experiments=(experiment,), populations=POPULATIONS)


def test_graph_rejects_alert_burden_without_evidence_outside_suppressed_operational_scope() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        role=EvidenceRole.EXTERNAL_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.ALERTS_PER_DAY,),
    )
    with pytest.raises(UnresolvedScientificValueError, match="Alert burden"):
        validate_protocol_graph(experiments=(experiment,), populations=POPULATIONS)


def test_graph_rejects_temporal_experiment_without_verified_chronology() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        role=EvidenceRole.TEMPORAL_BOUNDARY,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.FALSE_POSITIVE_RATE,),
    )
    with pytest.raises(ProtocolValidationError, match="verified chronology"):
        validate_protocol_graph(experiments=(experiment,), populations=POPULATIONS)

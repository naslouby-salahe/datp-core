import pytest

from datp_core.domain.enums import EvidenceRole, ExperimentId, MetricId, PopulationId, TrainingModelId
from datp_core.domain.errors import ProtocolValidationError, UnresolvedScientificValueError
from datp_core.protocols.models import ExperimentDeclaration
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.validation import validate_protocol_graph


def test_graph_rejects_unresolved_mandatory_seed_cohort() -> None:
    with pytest.raises(UnresolvedScientificValueError):
        validate_protocol_graph()


def test_graph_rejects_attack_metric_without_attack_assignment() -> None:
    experiment = ExperimentDeclaration(
        id=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        role=EvidenceRole.EXTERNAL_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        federated_thresholds=(),
        metrics=(MetricId.TRUE_POSITIVE_RATE,),
    )
    with pytest.raises(ProtocolValidationError, match="attack assignment"):
        validate_protocol_graph(experiments=(experiment,), populations=POPULATIONS)

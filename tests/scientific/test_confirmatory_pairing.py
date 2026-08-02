from datp_core.analysis.inference.bootstrap import paired_bca_interval
from datp_core.analysis.models import BcaOutcome, PairedContrast
from datp_core.domain.enums import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import MetricValue, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT, CONFIRMATORY_INFERENCE_PROTOCOL


def test_confirmatory_bca_blocks_nine_pairs_instead_of_treating_clients_as_replications() -> None:
    result = paired_bca_interval(
        tuple(_contrast(seed) for seed in range(9)),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        replicate_count=BOOTSTRAP_REPLICATE_COUNT,
        analysis_seed=Seed(17),
    )

    assert result.outcome is BcaOutcome.BLOCKED
    assert result.point_estimate is not None


def _contrast(seed: int) -> PairedContrast:
    local = MetricValue(0.02)
    shared = MetricValue(0.03 + seed / 10000)
    return PairedContrast(
        coordinate=FederatedTrainingCoordinate(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            training_seed=Seed(seed),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=None,
        ),
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=shared,
        right_value=local,
    )

from datp_core.analysis.inference.bootstrap import BcaOutcome, PairedContrast, paired_bca_interval
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
        FederatedTrainingCoordinate(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            Seed(seed),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            TrainingModelId.FEDAVG_AUTOENCODER,
            None,
        ),
        EvidenceRole.CONFIRMATORY,
        Seed(seed),
        MetricId.FPR_COEFFICIENT_OF_VARIATION,
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        shared,
        local,
        MetricValue(shared.value - local.value),
    )

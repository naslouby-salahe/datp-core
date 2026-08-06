from datp_core.analysis.contrasts import PairedContrast
from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome
from datp_core.analysis.inference.bootstrap.estimation import paired_bca_interval
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
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL


def test_confirmatory_bca_blocks_nine_pairs() -> None:
    result = paired_bca_interval(
        tuple(_contrast(seed) for seed in range(9)),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(17),
    )
    assert result.outcome is BcaOutcome.BLOCKED
    assert result.point_estimate is not None


def test_pairing_rejects_a_seed_independent_design_change() -> None:
    values = [_contrast(seed) for seed in range(10)]
    changed = values[-1]
    values[-1] = changed.model_copy(
        update={
            "coordinate": FederatedTrainingCoordinate(
                population=changed.coordinate.population,
                training_seed=changed.coordinate.training_seed,
                split_protocol=changed.coordinate.split_protocol,
                preprocessing_identity=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
                model=changed.coordinate.model,
                model_coefficient=None,
            )
        }
    )
    result = paired_bca_interval(
        tuple(values),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(17),
    )
    assert result.outcome is BcaOutcome.BLOCKED


def _contrast(seed: int) -> PairedContrast:
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
        left_value=MetricValue(0.03 + seed / 10_000),
        right_value=MetricValue(0.02),
    )

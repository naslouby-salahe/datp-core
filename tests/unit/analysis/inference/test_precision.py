import math

import pytest

from datp_core.analysis.contrasts import PairedContrast, PairedContrasts
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.inference.precision import confirmatory_precision_diagnostics
from datp_core.core.identifiers import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import MetricValue, Seed
from datp_core.detector.training.contracts import FederatedTrainingCoordinate


def test_confirmatory_precision_diagnostics_use_sample_sd_and_all_loso_means() -> None:
    contrasts = PairedContrasts(
        values=tuple(_contrast(seed, delta) for seed, delta in enumerate(range(1, 11))),
    )
    interval = BootstrapInterval.model_construct(
        lower_bound=MetricValue(-2.0),
        upper_bound=MetricValue(4.0),
    )

    diagnostics = confirmatory_precision_diagnostics(contrasts, interval)

    assert diagnostics.sample_standard_deviation.value == pytest.approx(math.sqrt(55.0 / 6.0))
    assert diagnostics.standard_error_proxy.value == pytest.approx(math.sqrt(11.0 / 12.0))
    assert diagnostics.normal_reference_half_width.value == pytest.approx(1.96 * math.sqrt(11.0 / 12.0))
    assert diagnostics.bca_width == MetricValue(6.0)
    assert diagnostics.minimum_leave_one_seed_out_mean == MetricValue(5.0)
    assert diagnostics.maximum_leave_one_seed_out_mean == MetricValue(6.0)
    assert diagnostics.maximum_leave_one_seed_out_shift == MetricValue(0.5)
    assert tuple(item.omitted_seed.value for item in diagnostics.leave_one_seed_out_means) == tuple(range(10))


def _contrast(seed: int, delta: int) -> PairedContrast:
    coordinate = FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(seed),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    return PairedContrast.model_construct(
        coordinate=coordinate,
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=MetricValue(delta),
        right_value=MetricValue(0.0),
        fixed_score=None,
    )

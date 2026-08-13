from datp_core.analysis.contrasts import PairedContrast, PairedContrasts
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
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
from datp_core.presentation.figures import confirmatory_paired_effect_figure


def test_confirmatory_paired_effect_figure_has_an_explicit_zero_reference_series() -> None:
    figure = confirmatory_paired_effect_figure(
        PairedContrasts(values=(_contrast(),)),
        BootstrapInterval.model_construct(
            point_estimate=MetricValue(0.2),
            lower_bound=None,
            upper_bound=None,
        ),
    )

    zero_reference = next(
        series for series in figure.paired_metric_series if series.label == "horizontal zero reference"
    )

    assert tuple(value.value for value in zero_reference.y_values) == (0.0,)


def _contrast() -> PairedContrast:
    coordinate = FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(0),
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
        left_value=MetricValue(0.3),
        right_value=MetricValue(0.1),
        fixed_score=None,
    )

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
from datp_core.core.numeric import MetricValue, Seed, ThresholdValue
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.presentation.figures import (
    ThresholdOverlay,
    _render_threshold_overlay,
    confirmatory_paired_effect_figure,
)


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


def test_score_geometry_overlay_renders_threshold_regions_and_operating_metrics() -> None:
    rendered = _render_threshold_overlay(
        ThresholdOverlay(
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            value=ThresholdValue(0.25),
            benign_exceedance=MetricValue(0.1),
            attack_acceptance=MetricValue(0.2),
            balanced_accuracy=MetricValue(0.85),
            macro_f1=MetricValue(0.8),
        )
    )

    assert rendered == (
        "local_threshold=0.25 (benign_exceedance=0.10000000000000001,"
        "attack_acceptance=0.20000000000000001,balanced_accuracy=0.84999999999999998,"
        "macro_f1=0.80000000000000004)"
    )


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

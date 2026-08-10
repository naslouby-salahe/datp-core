from types import SimpleNamespace
from typing import cast

from datp_core.analysis.mechanisms import (
    AssociationObservation,
    ThresholdMovementCohort,
    heterogeneity_benefit_association,
)
from datp_core.core.identifiers import ClientIdentityToken, ExperimentId, PopulationId, RegimeLabel
from datp_core.core.numeric import MetricValue, Seed
from datp_core.data.nbaiot.schema import NBaIoTDevice
from datp_core.experiments.heterogeneity import run


def _association_observations() -> tuple[AssociationObservation, ...]:
    return tuple(
        AssociationObservation(
            seed=Seed(index),
            experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            regime_label=RegimeLabel(f"alpha_{index}"),
            heterogeneity=MetricValue(0.1 + index * 0.2),
            benefit=MetricValue(0.01 + index * 0.03),
        )
        for index in range(3)
    )


def test_controlled_heterogeneity_figure_retains_each_seed_and_regime_observation() -> None:
    observations = _association_observations()

    figure = run._controlled_heterogeneity_figures(observations)[0]

    assert len(figure.paired_metric_series) == 3
    assert {series.point_labels for series in figure.paired_metric_series} == {
        ("seed_0",),
        ("seed_1",),
        ("seed_2",),
    }


def test_association_figure_carries_observed_points_and_the_locked_regression() -> None:
    result = heterogeneity_benefit_association(_association_observations())

    figure = run._association_figure(result)

    observed, regression = figure.paired_metric_series
    assert observed.x_values == tuple(item.heterogeneity for item in result.observations)
    assert observed.y_values == tuple(item.benefit for item in result.observations)
    assert regression.availability.value == "available"
    assert len(regression.x_values) == len(result.observations)


def test_threshold_movement_figures_keep_all_nine_devices_and_explicit_tpr_unavailability() -> None:
    movements = tuple(
        SimpleNamespace(
            client=SimpleNamespace(client_id=ClientIdentityToken(device.value)),
            seed=Seed(0),
            delta_threshold=MetricValue(0.01),
            delta_fpr=MetricValue(-0.02),
            delta_tpr=None,
        )
        for device in NBaIoTDevice
    )
    cohort = cast(ThresholdMovementCohort, SimpleNamespace(movements=movements))

    fpr_figure, tpr_figure = run._threshold_movement_figures((cohort,))

    assert len(fpr_figure.paired_metric_series) == len(NBaIoTDevice)
    assert len(tpr_figure.paired_metric_series) == len(NBaIoTDevice)
    assert all(series.unavailable_reason is not None for series in tpr_figure.paired_metric_series)

from datp_core.analysis.mechanisms.equity_pareto import EquityTargetAttainmentRow, EquityUtilityParetoView
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue
from datp_core.presentation.target_attainment import render_target_attainment_table


def test_target_attainment_table_renders_the_reconstructable_policy_values() -> None:
    row = EquityTargetAttainmentRow(
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        seed_mean_absolute_target_errors=(MetricValue(0.1),),
        seed_worst_absolute_target_errors=(MetricValue(0.2),),
        seed_mean_absolute_calibration_generalization_gaps=(MetricValue(0.05),),
        mean_absolute_target_error=MetricValue(0.1),
        worst_absolute_target_error=MetricValue(0.2),
        mean_absolute_calibration_generalization_gap=MetricValue(0.05),
    )
    view = EquityUtilityParetoView(utility_metric=MetricId.P10_BINARY_MACRO_F1, points=(), target_attainment=(row,))

    rendered = render_target_attainment_table(view)

    assert "`shared_threshold` | 0.1 | 0.2 | 0.05 | 1" in rendered

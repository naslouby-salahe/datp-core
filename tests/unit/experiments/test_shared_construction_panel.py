from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod
from datp_core.core.numeric import MetricValue, SeedCount
from datp_core.experiments.threshold_robustness.run import (
    MethodCvSummary,
    MethodCvSummaryReport,
    _render_shared_construction_panel,
)


def test_shared_construction_panel_compares_each_method_to_local_baseline() -> None:
    report = MethodCvSummaryReport(
        experiment=ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        rows=(
            MethodCvSummary(
                method=FederatedThresholdMethod.SHARED_THRESHOLD,
                seed_count=SeedCount(10),
                mean_cv_fpr=MetricValue(0.4),
                mean_worst_client_fpr=MetricValue(0.3),
                cv_fpr_across_seeds=MetricValue(0.1),
            ),
            MethodCvSummary(
                method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                seed_count=SeedCount(10),
                mean_cv_fpr=MetricValue(0.1),
                mean_worst_client_fpr=MetricValue(0.2),
                cv_fpr_across_seeds=MetricValue(0.2),
            ),
        ),
    )

    rendered = _render_shared_construction_panel(report)

    assert "`shared_threshold` | 10 | 0.4 | -0.3" in rendered
    assert "`local_threshold` | 10 | 0.1 | 0" in rendered

from datp_core.analysis.mechanisms.policy_surface import (
    PolicySurfacePolicyMetric,
    PolicySurfaceState,
    policy_surface_cell,
)
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import MetricValue, Seed


def test_policy_surface_reports_exact_unique_nondominated_policy() -> None:
    cell = policy_surface_cell(
        seed=Seed(1),
        alpha_label="0.1",
        calibration_size=None,
        heterogeneity=MetricValue(0.3),
        policies=(
            PolicySurfacePolicyMetric(
                policy=FederatedThresholdMethod.SHARED_THRESHOLD,
                cv_fpr=MetricValue(0.2),
                p10_macro_f1=MetricValue(0.6),
                worst_client_balanced_accuracy=MetricValue(0.4),
            ),
            PolicySurfacePolicyMetric(
                policy=FederatedThresholdMethod.LOCAL_THRESHOLD,
                cv_fpr=MetricValue(0.1),
                p10_macro_f1=MetricValue(0.7),
                worst_client_balanced_accuracy=MetricValue(0.5),
            ),
        ),
    )

    assert cell.nondominated_policies == (FederatedThresholdMethod.LOCAL_THRESHOLD,)
    assert cell.state is PolicySurfaceState.UNIQUE_LOCAL_THRESHOLD

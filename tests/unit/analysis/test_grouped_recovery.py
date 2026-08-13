from datp_core.analysis.mechanisms.clustering import grouped_cv_fpr_recovery
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import MetricValue, Seed


def test_grouped_recovery_retains_unclipped_family_fraction() -> None:
    recovery = grouped_cv_fpr_recovery(
        seed=Seed(2),
        method=FederatedThresholdMethod.FAMILY_THRESHOLD,
        shared_cv_fpr=MetricValue(0.5),
        grouped_cv_fpr=MetricValue(0.1),
        local_cv_fpr=MetricValue(0.3),
    )

    assert recovery.recovery.fraction == MetricValue(2.0)


def test_grouped_recovery_blocks_nonpositive_shared_to_local_gap() -> None:
    recovery = grouped_cv_fpr_recovery(
        seed=Seed(2),
        method=FederatedThresholdMethod.FAMILY_THRESHOLD,
        shared_cv_fpr=MetricValue(0.2),
        grouped_cv_fpr=MetricValue(0.1),
        local_cv_fpr=MetricValue(0.2),
    )

    assert recovery.recovery.fraction is None
    assert recovery.recovery.reason is not None

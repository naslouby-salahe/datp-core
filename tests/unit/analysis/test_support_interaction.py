from datp_core.analysis.mechanisms.policy_surface import PolicySurfacePolicyMetric
from datp_core.analysis.mechanisms.support_interaction import (
    SupportInteractionObservation,
    summarize_support_interaction,
)
from datp_core.core.identifiers import CalibrationSupportLevel, FederatedThresholdMethod, RegimeLabel
from datp_core.core.numeric import MetricValue, ReplicateIndex, Seed


def test_support_interaction_uses_replicate_means_and_one_seed_level_coefficient() -> None:
    seed = Seed(0)
    observations = tuple(
        SupportInteractionObservation(
            seed=seed,
            alpha_label=RegimeLabel(alpha),
            support=support,
            replicate=ReplicateIndex(replicate),
            heterogeneity=MetricValue(heterogeneity),
            policy_metrics=(
                PolicySurfacePolicyMetric(
                    policy=FederatedThresholdMethod.SHARED_THRESHOLD,
                    cv_fpr=MetricValue(heterogeneity + support_value / 1000 + replicate / 100),
                    p10_macro_f1=MetricValue(0.4),
                    worst_client_balanced_accuracy=MetricValue(0.3),
                ),
                PolicySurfacePolicyMetric(
                    policy=FederatedThresholdMethod.LOCAL_THRESHOLD,
                    cv_fpr=MetricValue(0.01),
                    p10_macro_f1=MetricValue(0.5),
                    worst_client_balanced_accuracy=MetricValue(0.4),
                ),
            ),
        )
        for alpha, heterogeneity in (("alpha_0.1", 0.1), ("alpha_1.0", 1.0), ("iid", 0.0))
        for support, support_value in (
            (CalibrationSupportLevel.M50, 50),
            (CalibrationSupportLevel.M100, 100),
            (CalibrationSupportLevel.M500, 500),
        )
        for replicate in range(10)
    )

    result = summarize_support_interaction(observations)

    assert len(result.coefficients) == 1
    assert len(result.policy_surface) == 9
    assert all(cell.state.value == "UNIQUE_LOCAL_THRESHOLD" for cell in result.policy_surface)

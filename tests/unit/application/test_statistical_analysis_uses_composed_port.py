"""Application statistics port-composition tests."""

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import StatisticalProfileId
from datp_core.domain.values import Seed


def test_statistical_analysis_uses_the_composed_port() -> None:
    result = build_application().statistical_analysis.analyze_paired_seed_differences(
        (0.11, 0.22, 0.34, 0.46, 0.59, 0.67, 0.78, 0.83, 0.95, 1.08),
        (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
        "false_positive_rate",
        "local_p95",
        "shared_mean_p95",
        statistical_profile_id=StatisticalProfileId("paired_seed_bca"),
        analysis_seed=Seed(42),
    )
    assert result.metric_id.value == "false_positive_rate"
    assert result.effect_size is not None

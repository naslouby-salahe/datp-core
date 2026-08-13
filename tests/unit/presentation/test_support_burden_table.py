from pathlib import Path

from tests.unit.thresholding.helpers import identity

from datp_core.analysis.mechanisms.support_burden import (
    CalibrationSupportBurdenCampaignSummary,
    CalibrationSupportBurdenDeviceReport,
    CalibrationSupportBurdenDeviceSummary,
    SupportCorrelationDirectionSummary,
)
from datp_core.core.numeric import MetricValue, PairedObservationCount, SeedObservationCount
from datp_core.presentation.client_impact_tables import export_support_burden_table


def test_support_burden_table_persists_mean_and_median_device_outcomes(tmp_path: Path) -> None:
    device = CalibrationSupportBurdenDeviceSummary.model_construct(
        client=identity("device_a"),
        median_source_benign_calibration_count=MetricValue(10.0),
        mean_shared_false_positive_rate=MetricValue(0.12),
        median_shared_false_positive_rate=MetricValue(0.1),
        mean_shared_target_burden=MetricValue(0.07),
        median_shared_target_burden=MetricValue(0.05),
        mean_personalization_relief=MetricValue(0.04),
        median_personalization_relief=MetricValue(0.03),
    )
    correlation = SupportCorrelationDirectionSummary.model_construct(
        valid_seed_count=SeedObservationCount(0),
        unavailable_seed_count=SeedObservationCount(0),
        median=None,
        minimum=None,
        maximum=None,
        negative_count=PairedObservationCount(0),
        zero_count=PairedObservationCount(0),
        positive_count=PairedObservationCount(0),
    )
    campaign = CalibrationSupportBurdenCampaignSummary.model_construct(
        seed_evidence=(),
        support_fpr=correlation,
        support_relief=correlation,
    )

    destination = export_support_burden_table(
        campaign,
        CalibrationSupportBurdenDeviceReport(devices=(device,)),
        tmp_path / "support.md",
    )

    rendered = destination.read_text()
    assert "Median shared FPR" in rendered
    assert "Median target burden" in rendered
    assert "Median personalization relief" in rendered
    assert "| `device_a` | 10 | 0.12 | 0.1 | 0.07 | 0.05 | 0.04 | 0.03 |" in rendered

from pathlib import Path

from datp_core.analysis.mechanisms.client_impact import ClientImpactCampaignSummary
from datp_core.analysis.mechanisms.support_burden import (
    CalibrationSupportBurdenCampaignSummary,
    CalibrationSupportBurdenDeviceReport,
)
from datp_core.analysis.mechanisms.support_strata import (
    CampaignFixedSupportStrata,
    SupportStratumCampaignSummary,
    SupportStratumOutcomeReport,
)
from datp_core.core.identifiers import FileContentText
from datp_core.core.numeric import MetricValue
from datp_core.runtime.filesystem import write_text_atomically


def export_support_burden_table(
    campaign: CalibrationSupportBurdenCampaignSummary,
    devices: CalibrationSupportBurdenDeviceReport,
    destination: Path,
) -> Path:
    lines = [
        "# Calibration support versus client burden",
        "",
        "| Association | Valid seeds | Unavailable seeds | Median Spearman | Min | Max | Negative/zero/positive |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for label, summary in (
        ("support → shared FPR", campaign.support_fpr),
        ("support → personalization relief", campaign.support_relief),
    ):
        lines.append(
            f"| {label} | {summary.valid_seed_count.value} | {summary.unavailable_seed_count.value} | "
            f"{_metric_value(summary.median)} | {_metric_value(summary.minimum)} | {_metric_value(summary.maximum)} | "
            f"{summary.negative_count.value}/{summary.zero_count.value}/{summary.positive_count.value} |"
        )
    lines.extend(
        (
            "",
            "| Device | Median support | Mean shared FPR | Mean target burden | Mean personalization relief |",
            "| --- | ---: | ---: | ---: | ---: |",
        )
    )
    lines.extend(
        f"| `{row.client.client_id.value}` | {row.median_source_benign_calibration_count.value:.12g} | "
        f"{row.mean_shared_false_positive_rate.value:.12g} | {row.mean_shared_target_burden.value:.12g} | "
        f"{row.mean_personalization_relief.value:.12g} |"
        for row in devices.devices
    )
    return write_text_atomically(destination, FileContentText("\n".join(lines) + "\n"))


def export_client_impact_strata_table(
    strata: CampaignFixedSupportStrata,
    outcomes: SupportStratumOutcomeReport,
    campaign: SupportStratumCampaignSummary,
    impact: ClientImpactCampaignSummary,
    destination: Path,
) -> Path:
    lines = ["# Natural-device helped/harmed and fixed support strata", ""]
    if strata.reason is not None or outcomes.reason is not None or campaign.reason is not None:
        reason = strata.reason or outcomes.reason or campaign.reason
        lines.append(f"UNAVAILABLE: {reason}")
        return write_text_atomically(destination, FileContentText("\n".join(lines) + "\n"))
    lines.extend(("| Device | Support score | Rank | Fixed stratum |", "| --- | ---: | ---: | --- |"))
    lines.extend(
        f"| `{entry.client.client_id.value}` | {entry.support_score.value:.12g} | "
        f"{entry.ascending_rank.value} | `{entry.stratum.value}` |"
        for entry in strata.entries
    )
    lines.extend(
        (
            "",
            "| Stratum | Mean FPR relief | FPR helped | FPR harmed | Shared MATE | Local MATE |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        )
    )
    for row in campaign.summaries:
        lines.append(
            f"| `{row.stratum.value}` | {row.mean_fpr_relief.arithmetic_mean.value:.12g} | "
            f"{row.fpr_helped_fraction.arithmetic_mean.value:.12g} | "
            f"{row.fpr_harmed_fraction.arithmetic_mean.value:.12g} | "
            f"{row.shared_mean_absolute_target_error.arithmetic_mean.value:.12g} | "
            f"{row.local_mean_absolute_target_error.arithmetic_mean.value:.12g} |"
        )
    lines.extend(
        ("", "| Campaign fraction | Arithmetic mean | Median | Min | Max |", "| --- | ---: | ---: | ---: | ---: |")
    )
    for label, summary in (
        ("FPR helped", impact.fpr_helped),
        ("FPR harmed", impact.fpr_harmed),
        ("TPR loss", impact.tpr_loss),
    ):
        lines.append(
            f"| {label} | {_metric_value(summary.arithmetic_mean)} | {_metric_value(summary.median)} | "
            f"{_metric_value(summary.minimum)} | {_metric_value(summary.maximum)} |"
        )
    return write_text_atomically(destination, FileContentText("\n".join(lines) + "\n"))


def _metric_value(metric: MetricValue | None) -> str:
    return "UNAVAILABLE" if metric is None else f"{metric.value:.12g}"

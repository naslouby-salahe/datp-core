"""Within- and across-group threshold/FPR dispersion evidence."""

import numpy as np
from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, EvidenceRole
from datp_core.core.numeric import ClusterIndex, MetricValue, PairedObservationCount, Ratio, ThresholdValue


class GroupDispersionObservation(StrictModel):
    group_index: ClusterIndex
    thresholds: tuple[ThresholdValue, ...]
    false_positive_rates: tuple[Ratio, ...]

    @model_validator(mode="after")
    def validate_observation(self) -> "GroupDispersionObservation":
        if not self.thresholds or not self.false_positive_rates:
            raise ValueError("grouped dispersion requires threshold and FPR observations")
        if len(self.thresholds) != len(self.false_positive_rates):
            raise ValueError("grouped threshold and FPR observations must cover the same clients")
        return self


class GroupDispersionSummary(StrictModel):
    group_index: ClusterIndex
    size: PairedObservationCount
    threshold_spread: MetricValue
    false_positive_rate_spread: MetricValue


class GroupedDispersionResult(StrictModel):
    evidence_role: EvidenceRole
    groups: tuple[GroupDispersionSummary, ...]
    across_group_threshold_spread: MetricValue | None
    across_group_mean_fpr_spread: MetricValue | None
    availability: AvailabilityStatus
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_result(self) -> "GroupedDispersionResult":
        if self.evidence_role is not EvidenceRole.MECHANISM:
            raise ValueError("grouped dispersion is mechanism evidence")
        expected_indexes = tuple(ClusterIndex(index) for index in range(len(self.groups)))
        if tuple(group.group_index for group in self.groups) != expected_indexes:
            raise ValueError("grouped dispersion groups must use consecutive indexes")
        if self.availability is AvailabilityStatus.AVAILABLE:
            if (
                self.reason is not None
                or self.across_group_threshold_spread is None
                or self.across_group_mean_fpr_spread is None
            ):
                raise ValueError("available grouped dispersion requires complete values and no reason")
        elif self.reason is None:
            raise ValueError("unavailable grouped dispersion requires an explicit reason")
        return self


def grouped_dispersion(
    observations: tuple[GroupDispersionObservation, ...],
) -> GroupedDispersionResult:
    if not observations:
        return GroupedDispersionResult(
            evidence_role=EvidenceRole.MECHANISM,
            groups=(),
            across_group_threshold_spread=None,
            across_group_mean_fpr_spread=None,
            availability=AvailabilityStatus.UNAVAILABLE,
            reason=AnalysisReasonText("grouped dispersion requires at least one group"),
        )
    ordered = tuple(sorted(observations, key=lambda item: item.group_index.value))
    if tuple(item.group_index.value for item in ordered) != tuple(range(len(ordered))):
        raise ValueError("group indexes must be consecutive from zero")
    threshold_means = tuple(float(np.mean([value.value for value in item.thresholds])) for item in ordered)
    fpr_means = tuple(float(np.mean([value.value for value in item.false_positive_rates])) for item in ordered)
    groups = tuple(
        GroupDispersionSummary(
            group_index=item.group_index,
            size=PairedObservationCount(len(item.thresholds)),
            threshold_spread=MetricValue(
                max(value.value for value in item.thresholds) - min(value.value for value in item.thresholds)
            ),
            false_positive_rate_spread=MetricValue(
                max(value.value for value in item.false_positive_rates)
                - min(value.value for value in item.false_positive_rates)
            ),
        )
        for item in ordered
    )
    return GroupedDispersionResult(
        evidence_role=EvidenceRole.MECHANISM,
        groups=groups,
        across_group_threshold_spread=MetricValue(max(threshold_means) - min(threshold_means)),
        across_group_mean_fpr_spread=MetricValue(max(fpr_means) - min(fpr_means)),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )

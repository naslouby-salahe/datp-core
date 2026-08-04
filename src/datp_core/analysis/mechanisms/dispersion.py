"""Within- and across-group threshold/FPR dispersion evidence."""

import numpy as np
from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import (
    ClusterIndex,
    MetricValue,
    PairedObservationCount,
    Ratio,
    ThresholdValue,
)


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


class GroupedDispersionResult(StrictModel):
    evidence_role: EvidenceRole
    group_sizes: tuple[PairedObservationCount, ...]
    within_group_threshold_spreads: tuple[MetricValue, ...]
    within_group_fpr_spreads: tuple[MetricValue, ...]
    across_group_threshold_spread: MetricValue | None
    across_group_mean_fpr_spread: MetricValue | None
    singleton_groups: tuple[ClusterIndex, ...]
    empty_groups: tuple[ClusterIndex, ...]
    availability: AvailabilityStatus
    reason: str | None

    @model_validator(mode="after")
    def validate_result(self) -> "GroupedDispersionResult":
        if self.evidence_role is not EvidenceRole.MECHANISM:
            raise ValueError("grouped dispersion is mechanism evidence")
        group_count = len(self.group_sizes)
        if len(self.within_group_threshold_spreads) != group_count or len(self.within_group_fpr_spreads) != group_count:
            raise ValueError("grouped dispersion requires one threshold and FPR spread per group")
        expected_singletons = tuple(
            ClusterIndex(index) for index, size in enumerate(self.group_sizes) if size.value == 1
        )
        expected_empty = tuple(ClusterIndex(index) for index, size in enumerate(self.group_sizes) if size.value == 0)
        if self.singleton_groups != expected_singletons or self.empty_groups != expected_empty:
            raise ValueError("group boundary indexes must be derived from group sizes")
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
            group_sizes=(),
            within_group_threshold_spreads=(),
            within_group_fpr_spreads=(),
            across_group_threshold_spread=None,
            across_group_mean_fpr_spread=None,
            singleton_groups=(),
            empty_groups=(),
            availability=AvailabilityStatus.UNAVAILABLE,
            reason="grouped dispersion requires at least one group",
        )
    ordered = tuple(sorted(observations, key=lambda item: item.group_index.value))
    if tuple(item.group_index.value for item in ordered) != tuple(range(len(ordered))):
        raise ValueError("group indexes must be consecutive from zero")
    threshold_means = tuple(float(np.mean([value.value for value in item.thresholds])) for item in ordered)
    fpr_means = tuple(float(np.mean([value.value for value in item.false_positive_rates])) for item in ordered)
    group_sizes = tuple(PairedObservationCount(len(item.thresholds)) for item in ordered)
    return GroupedDispersionResult(
        evidence_role=EvidenceRole.MECHANISM,
        group_sizes=group_sizes,
        within_group_threshold_spreads=tuple(
            MetricValue(max(value.value for value in item.thresholds) - min(value.value for value in item.thresholds))
            for item in ordered
        ),
        within_group_fpr_spreads=tuple(
            MetricValue(
                max(value.value for value in item.false_positive_rates)
                - min(value.value for value in item.false_positive_rates)
            )
            for item in ordered
        ),
        across_group_threshold_spread=MetricValue(max(threshold_means) - min(threshold_means)),
        across_group_mean_fpr_spread=MetricValue(max(fpr_means) - min(fpr_means)),
        singleton_groups=tuple(ClusterIndex(index) for index, size in enumerate(group_sizes) if size.value == 1),
        empty_groups=(),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )

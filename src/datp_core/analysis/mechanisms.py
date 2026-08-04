"""Mechanism analyses, divergence boundaries, and absorption decisions."""

from enum import StrEnum
from math import isfinite
from typing import ClassVar

import numpy as np
from pydantic import model_validator
from scipy import stats
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.models import (
    CorrelationCoefficient,
    PValue,
    ScientificDecisionResult,
    extract_named_numeric_attributes,
)
from datp_core.domain.contracts import ClientOwned, StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, ScientificDecision
from datp_core.domain.values import ClusterIndex, MetricValue, PairedObservationCount, Ratio, ThresholdValue
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import ClusterMembership

MINIMUM_ASSOCIATION_OBSERVATIONS = PairedObservationCount(3)
MINIMUM_DIVERGENCE_CLIENTS = PairedObservationCount(2)
MODEL_EFFECT_PARTIAL_RETENTION_CUTOFF = Ratio(0.25)
MODEL_EFFECT_FULL_RETENTION_CUTOFF = Ratio(0.75)


class AssociationIssue(StrEnum):
    INSUFFICIENT_OBSERVATIONS = "association requires at least three observations"
    NON_FINITE_OBSERVATION = "association observations must be finite"
    ZERO_HETEROGENEITY_VARIATION = "heterogeneity has zero variation"
    ZERO_BENEFIT_VARIATION = "benefit has zero variation"
    INVALID_STATISTICS = "statistics library returned invalid association values"

    @property
    def availability(self) -> AvailabilityStatus:
        if self in {
            AssociationIssue.ZERO_HETEROGENEITY_VARIATION,
            AssociationIssue.ZERO_BENEFIT_VARIATION,
        }:
            return AvailabilityStatus.UNDEFINED
        return AvailabilityStatus.UNAVAILABLE


class DivergenceBlocker(StrEnum):
    COMMON_SUPPORT_UNRESOLVED = "common_support_unresolved"
    BINNING_UNRESOLVED = "binning_unresolved"
    DENSITY_UNRESOLVED = "density_unresolved"
    SMOOTHING_UNRESOLVED = "smoothing_unresolved"
    ZERO_MASS_UNRESOLVED = "zero_mass_unresolved"
    AGGREGATION_UNRESOLVED = "aggregation_unresolved"

    @property
    def reason(self) -> str:
        return f"Jensen-Shannon divergence is blocked: {self.value}"


class AssociationObservation(StrictModel):
    heterogeneity: MetricValue
    benefit: MetricValue


class AssociationStatistics(StrictModel):
    spearman_rho: CorrelationCoefficient
    spearman_p_value: PValue
    regression_intercept: MetricValue
    regression_slope: MetricValue
    regression_slope_standard_error: MetricValue
    r_squared: Ratio
    leverage: tuple[Ratio, ...]


class AssociationResult(StrictModel):
    observations: tuple[AssociationObservation, ...]
    statistics: AssociationStatistics | None
    issue: AssociationIssue | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "AssociationResult":
        if (self.statistics is None) == (self.issue is None):
            raise ValueError("association result requires either statistics or one issue")
        if self.statistics is not None and len(self.statistics.leverage) != len(self.observations):
            raise ValueError("association leverage must cover every observation")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.issue is None else self.issue.availability

    @property
    def reason(self) -> str | None:
        return None if self.issue is None else self.issue.value

    @property
    def observation_count(self) -> PairedObservationCount:
        return PairedObservationCount(len(self.observations))


class ClusterPartitionSummary(StrictModel):
    group_sizes: tuple[PairedObservationCount, ...]

    @classmethod
    def from_memberships(cls, memberships: tuple[ClusterMembership, ...]) -> "ClusterPartitionSummary":
        return cls(group_sizes=tuple(PairedObservationCount(len(item.members)) for item in memberships))

    @property
    def singleton_groups(self) -> tuple[ClusterIndex, ...]:
        return tuple(ClusterIndex(index) for index, size in enumerate(self.group_sizes) if size.value == 1)

    @property
    def empty_groups(self) -> tuple[ClusterIndex, ...]:
        return tuple(ClusterIndex(index) for index, size in enumerate(self.group_sizes) if size.value == 0)


class ClusterStabilityResult(StrictModel):
    adjusted_rand_index: CorrelationCoefficient
    compared_clients: tuple[ClientIdentity, ...]
    left_partition: ClusterPartitionSummary
    right_partition: ClusterPartitionSummary
    contingency: tuple[tuple[PairedObservationCount, ...], ...]

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "ClusterStabilityResult":
        if len(self.compared_clients) < MINIMUM_DIVERGENCE_CLIENTS.value:
            raise ValueError("cluster stability requires at least two clients")
        if len(set(self.compared_clients)) != len(self.compared_clients):
            raise ValueError("cluster stability requires unique compared clients")
        if len(self.contingency) != len(self.left_partition.group_sizes):
            raise ValueError("cluster contingency row count must match the left partition")
        if any(len(row) != len(self.right_partition.group_sizes) for row in self.contingency):
            raise ValueError("cluster contingency column count must match the right partition")
        row_totals = tuple(sum(value.value for value in row) for row in self.contingency)
        if row_totals != tuple(value.value for value in self.left_partition.group_sizes):
            raise ValueError("cluster contingency row totals must match the left partition")
        column_totals = tuple(
            sum(row[column].value for row in self.contingency)
            for column in range(len(self.right_partition.group_sizes))
        )
        if column_totals != tuple(value.value for value in self.right_partition.group_sizes):
            raise ValueError("cluster contingency column totals must match the right partition")
        if sum(row_totals) != len(self.compared_clients):
            raise ValueError("cluster contingency must account for every client")
        return self


class ThresholdOperatingPoint(StrictModel):
    threshold: ThresholdValue
    fpr: Ratio
    tpr: Ratio | None


class ThresholdMovement(StrictModel):
    client: ClientIdentity
    delta_threshold: MetricValue
    delta_fpr: MetricValue
    delta_tpr: MetricValue | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @property
    def attack_availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.delta_tpr is not None else AvailabilityStatus.UNAVAILABLE

    @property
    def reason(self) -> str | None:
        return None if self.delta_tpr is not None else "attack-sensitive movement unavailable"


class DivergenceResult(StrictModel):
    clients: tuple[ClientIdentity, ...]
    pairwise_values: tuple[MetricValue, ...]
    aggregate: MetricValue | None
    blocker: DivergenceBlocker | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "DivergenceResult":
        if len(self.clients) < MINIMUM_DIVERGENCE_CLIENTS.value:
            raise ValueError("divergence analysis requires at least two clients")
        if len(set(self.clients)) != len(self.clients):
            raise ValueError("divergence analysis requires unique clients")
        available = self.blocker is None
        if available and (not self.pairwise_values or self.aggregate is None):
            raise ValueError("available divergence requires pairwise values and an aggregate")
        if not available and (self.pairwise_values or self.aggregate is not None):
            raise ValueError("blocked divergence cannot contain calculated values")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.blocker is None else AvailabilityStatus.UNAVAILABLE

    @property
    def reason(self) -> str | None:
        return None if self.blocker is None else self.blocker.reason


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
    """Within- and across-group threshold/FPR dispersion mechanism evidence."""

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
        expected_singletons = tuple(ClusterIndex(i) for i, size in enumerate(self.group_sizes) if size.value == 1)
        expected_empty = tuple(ClusterIndex(i) for i, size in enumerate(self.group_sizes) if size.value == 0)
        if self.singleton_groups != expected_singletons or self.empty_groups != expected_empty:
            raise ValueError("group boundary indexes must be derived from group sizes")
        if self.availability is AvailabilityStatus.AVAILABLE:
            if self.reason is not None or self.across_group_threshold_spread is None or self.across_group_mean_fpr_spread is None:
                raise ValueError("available grouped dispersion requires complete values and no reason")
        elif self.reason is None:
            raise ValueError("unavailable grouped dispersion requires an explicit reason")
        return self


type MechanismEvidence = (
    AssociationResult
    | ClusterStabilityResult
    | DivergenceResult
    | GroupedDispersionResult
    | ScientificDecisionResult
    | ThresholdMovement
)


def heterogeneity_benefit_association(observations: tuple[AssociationObservation, ...]) -> AssociationResult:
    if len(observations) < MINIMUM_ASSOCIATION_OBSERVATIONS.value:
        return _unavailable_association(observations, AssociationIssue.INSUFFICIENT_OBSERVATIONS)
    x_values = np.fromiter((item.heterogeneity.value for item in observations), dtype=np.float64)
    y_values = np.fromiter((item.benefit.value for item in observations), dtype=np.float64)
    if not np.isfinite(x_values).all() or not np.isfinite(y_values).all():
        return _unavailable_association(observations, AssociationIssue.NON_FINITE_OBSERVATION)
    if np.ptp(x_values) == 0.0:
        return _unavailable_association(observations, AssociationIssue.ZERO_HETEROGENEITY_VARIATION)
    if np.ptp(y_values) == 0.0:
        return _unavailable_association(observations, AssociationIssue.ZERO_BENEFIT_VARIATION)
    spearman = extract_named_numeric_attributes(
        stats.spearmanr(x_values, y_values, alternative="two-sided"),
        ("statistic", "pvalue"),
    )
    regression = extract_named_numeric_attributes(
        stats.linregress(x_values, y_values, alternative="two-sided"),
        ("intercept", "slope", "stderr", "rvalue"),
    )
    if spearman is None or regression is None:
        return _unavailable_association(observations, AssociationIssue.INVALID_STATISTICS)
    values = spearman + regression
    if not all(map(isfinite, values)):
        return _unavailable_association(observations, AssociationIssue.INVALID_STATISTICS)
    design = np.column_stack((np.ones(x_values.size), x_values))
    leverage = np.einsum("ij,ji->i", design, np.linalg.pinv(design))
    return AssociationResult(
        observations=observations,
        statistics=AssociationStatistics(
            spearman_rho=CorrelationCoefficient(values[0]),
            spearman_p_value=PValue(values[1]),
            regression_intercept=MetricValue(values[2]),
            regression_slope=MetricValue(values[3]),
            regression_slope_standard_error=MetricValue(values[4]),
            r_squared=Ratio(values[5] ** 2),
            leverage=tuple(Ratio(float(value)) for value in leverage),
        ),
        issue=None,
    )


def cluster_stability(left: tuple[ClusterMembership, ...], right: tuple[ClusterMembership, ...]) -> ClusterStabilityResult:
    left_assignments = _cluster_assignments(left)
    right_assignments = _cluster_assignments(right)
    left_clients = tuple(item.client for item in left_assignments)
    right_clients = tuple(item.client for item in right_assignments)
    if left_clients != right_clients:
        raise ValueError("cluster stability requires identical persisted client memberships")
    left_labels = tuple(item.value.value for item in left_assignments)
    right_labels = tuple(item.value.value for item in right_assignments)
    return ClusterStabilityResult(
        adjusted_rand_index=CorrelationCoefficient(float(adjusted_rand_score(left_labels, right_labels))),
        compared_clients=left_clients,
        left_partition=ClusterPartitionSummary.from_memberships(left),
        right_partition=ClusterPartitionSummary.from_memberships(right),
        contingency=_contingency(left_labels, right_labels, len(left), len(right)),
    )


def grouped_dispersion(observations: tuple[GroupDispersionObservation, ...]) -> GroupedDispersionResult:
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
        singleton_groups=tuple(ClusterIndex(i) for i, size in enumerate(group_sizes) if size.value == 1),
        empty_groups=(),
        availability=AvailabilityStatus.AVAILABLE,
        reason=None,
    )


def threshold_movement(
    *,
    client: ClientIdentity,
    shared: ThresholdOperatingPoint,
    local: ThresholdOperatingPoint,
) -> ThresholdMovement:
    if (shared.tpr is None) != (local.tpr is None):
        raise ValueError("TPR movement requires both operating points or neither")
    if shared.tpr is None:
        delta_tpr = None
    else:
        local_tpr = local.tpr
        if local_tpr is None:
            raise ValueError("TPR movement requires both operating points or neither")
        delta_tpr = MetricValue(local_tpr.value - shared.tpr.value)
    return ThresholdMovement(
        client=client,
        delta_threshold=MetricValue(local.threshold.value - shared.threshold.value),
        delta_fpr=MetricValue(local.fpr.value - shared.fpr.value),
        delta_tpr=delta_tpr,
    )


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...],
    blocker: DivergenceBlocker,
) -> DivergenceResult:
    return DivergenceResult(clients=tuple(sorted(clients)), pairwise_values=(), aggregate=None, blocker=blocker)


def decide_model_absorption(
    reference_effect: MetricValue | None,
    personalized_effect: MetricValue | None,
) -> ScientificDecisionResult:
    if reference_effect is None or personalized_effect is None or reference_effect.value <= 0.0:
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.SUPPORTIVE,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=None,
            rationale="model absorption requires a valid positive reference effect",
        )
    retention = MetricValue(personalized_effect.value / reference_effect.value)
    if retention.value >= MODEL_EFFECT_FULL_RETENTION_CUTOFF.value:
        decision, rationale = ScientificDecision.SUPPORTED, "the personalized-model effect is retained"
    elif retention.value >= MODEL_EFFECT_PARTIAL_RETENTION_CUTOFF.value:
        decision, rationale = ScientificDecision.PARTIAL_ABSORPTION, "the personalized-model effect is partially absorbed"
    else:
        decision, rationale = ScientificDecision.FULL_ABSORPTION, "the personalized-model effect is largely absorbed"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.SUPPORTIVE,
        decision=decision,
        point_estimate=retention,
        interval=None,
        rationale=rationale,
    )


def _unavailable_association(
    observations: tuple[AssociationObservation, ...],
    issue: AssociationIssue,
) -> AssociationResult:
    return AssociationResult(observations=observations, statistics=None, issue=issue)


def _cluster_assignments(
    memberships: tuple[ClusterMembership, ...],
) -> tuple[ClientOwned[ClientIdentity, ClusterIndex], ...]:
    assignments = tuple(
        ClientOwned(client=client, value=ClusterIndex(cluster_index))
        for cluster_index, membership in enumerate(memberships)
        for client in membership.members
    )
    if not assignments:
        raise ValueError("cluster stability requires at least one persisted client")
    if len({item.client for item in assignments}) != len(assignments):
        raise ValueError("each client must belong to exactly one cluster")
    return tuple(sorted(assignments, key=lambda item: item.client))


def _contingency(
    left_labels: tuple[int, ...],
    right_labels: tuple[int, ...],
    left_group_count: int,
    right_group_count: int,
) -> tuple[tuple[PairedObservationCount, ...], ...]:
    return tuple(
        tuple(
            PairedObservationCount(
                sum(
                    left_label == left_index and right_label == right_index
                    for left_label, right_label in zip(left_labels, right_labels, strict=True)
                )
            )
            for right_index in range(right_group_count)
        )
        for left_index in range(left_group_count)
    )

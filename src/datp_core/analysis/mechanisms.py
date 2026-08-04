"""Mechanism analyses, divergence boundaries, and absorption decisions."""

from enum import StrEnum
from math import isfinite
from typing import ClassVar

import numpy as np
from pydantic import model_validator
from scipy import stats
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.models import (
    PValue,
    ScientificDecisionResult,
    _extract_named_attributes,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, ScientificDecision
from datp_core.domain.values import ClusterIndex, MetricValue, Ratio, ThresholdValue
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import ClusterMembership

MINIMUM_ASSOCIATION_OBSERVATIONS = 3
MINIMUM_DIVERGENCE_CLIENTS = 2
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
    spearman_rho: MetricValue
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
    def _validate(self) -> "AssociationResult":
        if (self.statistics is None) == (self.issue is None):
            raise ValueError("association result requires either statistics or one issue")
        if self.statistics is not None and len(self.statistics.leverage) != len(self.observations):
            raise ValueError("association leverage must cover every observation")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.issue is None else self.issue.availability

    @property
    def reason(self) -> str:
        return "" if self.issue is None else self.issue.value

    @property
    def observation_count(self) -> int:
        return len(self.observations)


class ClusterPartitionSummary(StrictModel):
    group_sizes: tuple[int, ...]

    @classmethod
    def from_memberships(
        cls,
        memberships: tuple[ClusterMembership, ...],
    ) -> "ClusterPartitionSummary":
        return cls(group_sizes=tuple(len(membership.members) for membership in memberships))

    @property
    def singleton_groups(self) -> tuple[int, ...]:
        return tuple(index for index, size in enumerate(self.group_sizes) if size == 1)

    @property
    def empty_groups(self) -> tuple[int, ...]:
        return tuple(index for index, size in enumerate(self.group_sizes) if size == 0)


class ClusterAssignment(StrictModel):
    client: ClientIdentity
    cluster_index: ClusterIndex

    def __lt__(self, other: "ClusterAssignment") -> bool:
        return self.client < other.client


class ClusterStabilityResult(StrictModel):
    adjusted_rand_index: MetricValue
    compared_clients: tuple[ClientIdentity, ...]
    left_partition: ClusterPartitionSummary
    right_partition: ClusterPartitionSummary
    contingency: tuple[tuple[int, ...], ...]

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def _validate(self) -> "ClusterStabilityResult":
        if not self.compared_clients:
            raise ValueError("cluster stability requires at least one client")
        if len(self.contingency) != len(self.left_partition.group_sizes):
            raise ValueError("cluster contingency row count must match the left partition")
        if any(len(row) != len(self.right_partition.group_sizes) for row in self.contingency):
            raise ValueError("cluster contingency column count must match the right partition")
        if sum(map(sum, self.contingency)) != len(self.compared_clients):
            raise ValueError("cluster contingency must account for every client")
        return self


class ThresholdOperatingPoint(StrictModel):
    threshold: ThresholdValue
    fpr: MetricValue
    tpr: MetricValue | None


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
    def reason(self) -> str:
        return "" if self.delta_tpr is not None else "attack-sensitive movement unavailable"


class DivergenceResult(StrictModel):
    clients: tuple[ClientIdentity, ...]
    pairwise_values: tuple[MetricValue, ...]
    aggregate: MetricValue | None
    blocker: DivergenceBlocker | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def _validate(self) -> "DivergenceResult":
        if len(self.clients) < MINIMUM_DIVERGENCE_CLIENTS:
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
    def reason(self) -> str:
        return "" if self.blocker is None else self.blocker.reason


def heterogeneity_benefit_association(
    observations: tuple[AssociationObservation, ...],
) -> AssociationResult:
    if len(observations) < MINIMUM_ASSOCIATION_OBSERVATIONS:
        return _unavailable_association(observations, AssociationIssue.INSUFFICIENT_OBSERVATIONS)

    x_values = np.asarray(
        [observation.heterogeneity.value for observation in observations],
        dtype=np.float64,
    )
    y_values = np.asarray(
        [observation.benefit.value for observation in observations],
        dtype=np.float64,
    )

    if not np.isfinite(x_values).all() or not np.isfinite(y_values).all():
        return _unavailable_association(observations, AssociationIssue.NON_FINITE_OBSERVATION)
    if np.ptp(x_values) == 0.0:
        return _unavailable_association(observations, AssociationIssue.ZERO_HETEROGENEITY_VARIATION)
    if np.ptp(y_values) == 0.0:
        return _unavailable_association(observations, AssociationIssue.ZERO_BENEFIT_VARIATION)

    spearman_result = stats.spearmanr(x_values, y_values, alternative="two-sided")
    regression_result = stats.linregress(x_values, y_values, alternative="two-sided")

    spearman_values = _extract_named_attributes(spearman_result, ("statistic", "pvalue"))
    regression_values = _extract_named_attributes(regression_result, ("intercept", "slope", "stderr", "rvalue"))
    if spearman_values is None or regression_values is None:
        return _unavailable_association(observations, AssociationIssue.INVALID_STATISTICS)

    values = spearman_values + regression_values

    if not all(map(isfinite, values)):
        return _unavailable_association(observations, AssociationIssue.INVALID_STATISTICS)

    design = np.column_stack((np.ones(x_values.size), x_values))
    leverage = np.einsum("ij,ji->i", design, np.linalg.pinv(design))

    return AssociationResult(
        observations=observations,
        statistics=AssociationStatistics(
            spearman_rho=MetricValue(values[0]),
            spearman_p_value=PValue(value=values[1]),
            regression_intercept=MetricValue(values[2]),
            regression_slope=MetricValue(values[3]),
            regression_slope_standard_error=MetricValue(values[4]),
            r_squared=Ratio(values[5] ** 2),
            leverage=tuple(Ratio(float(value)) for value in leverage),
        ),
        issue=None,
    )


def cluster_stability(
    left: tuple[ClusterMembership, ...],
    right: tuple[ClusterMembership, ...],
) -> ClusterStabilityResult:
    left_assignments = _cluster_assignments(left)
    right_assignments = _cluster_assignments(right)

    left_clients = tuple(assignment.client for assignment in left_assignments)
    right_clients = tuple(assignment.client for assignment in right_assignments)
    if left_clients != right_clients:
        raise ValueError("cluster stability requires identical persisted client memberships")

    left_labels = tuple(assignment.cluster_index.value for assignment in left_assignments)
    right_labels = tuple(assignment.cluster_index.value for assignment in right_assignments)

    return ClusterStabilityResult(
        adjusted_rand_index=MetricValue(float(adjusted_rand_score(left_labels, right_labels))),
        compared_clients=left_clients,
        left_partition=ClusterPartitionSummary.from_memberships(left),
        right_partition=ClusterPartitionSummary.from_memberships(right),
        contingency=_contingency(left_labels, right_labels, len(left), len(right)),
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
        tpr_delta: MetricValue | None = None
    else:
        resolved_local_tpr = local.tpr
        if resolved_local_tpr is None:
            raise ValueError("TPR movement requires both operating points or neither")
        tpr_delta = MetricValue(resolved_local_tpr.value - shared.tpr.value)

    return ThresholdMovement(
        client=client,
        delta_threshold=MetricValue(local.threshold.value - shared.threshold.value),
        delta_fpr=MetricValue(local.fpr.value - shared.fpr.value),
        delta_tpr=tpr_delta,
    )


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...],
    blocker: DivergenceBlocker,
) -> DivergenceResult:
    return DivergenceResult(
        clients=tuple(sorted(clients)),
        pairwise_values=(),
        aggregate=None,
        blocker=blocker,
    )


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

    retention_ratio = MetricValue(personalized_effect.value / reference_effect.value)
    if retention_ratio.value >= MODEL_EFFECT_FULL_RETENTION_CUTOFF.value:
        decision = ScientificDecision.SUPPORTED
        rationale = "the personalized-model effect is retained"
    elif retention_ratio.value >= MODEL_EFFECT_PARTIAL_RETENTION_CUTOFF.value:
        decision = ScientificDecision.PARTIAL_ABSORPTION
        rationale = "the personalized-model effect is partially absorbed"
    else:
        decision = ScientificDecision.FULL_ABSORPTION
        rationale = "the personalized-model effect is largely absorbed"

    return ScientificDecisionResult(
        evidence_role=EvidenceRole.SUPPORTIVE,
        decision=decision,
        point_estimate=retention_ratio,
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
) -> tuple[ClusterAssignment, ...]:
    assignments = tuple(
        ClusterAssignment(client=client, cluster_index=ClusterIndex(cluster_index))
        for cluster_index, membership in enumerate(memberships)
        for client in membership.members
    )
    if not assignments:
        raise ValueError("cluster stability requires at least one persisted client")
    if len({assignment.client for assignment in assignments}) != len(assignments):
        raise ValueError("each client must belong to exactly one cluster")
    return tuple(sorted(assignments))


def _contingency(
    left_labels: tuple[int, ...],
    right_labels: tuple[int, ...],
    left_group_count: int,
    right_group_count: int,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(
            sum(
                left_label == left_index and right_label == right_index
                for left_label, right_label in zip(left_labels, right_labels, strict=True)
            )
            for right_index in range(right_group_count)
        )
        for left_index in range(left_group_count)
    )


class MechanismResult(StrictModel):
    """Aggregated mechanism evidence from a federated threshold evaluation."""

    evidence_role: EvidenceRole
    group_sizes: tuple[int, ...]
    within_group_threshold_spreads: tuple[MetricValue, ...]
    within_group_fpr_spreads: tuple[MetricValue, ...]
    across_group_threshold_spread: MetricValue | None
    across_group_mean_fpr_spread: MetricValue | None
    singleton_groups: tuple[int, ...]
    empty_groups: tuple[int, ...]
    recovery_fraction: MetricValue | None
    availability: AvailabilityStatus
    reason: str

    @model_validator(mode="after")
    def _validate(self) -> "MechanismResult":
        if any(size < 0 for size in self.group_sizes):
            raise ValueError("mechanism group sizes must be non-negative")
        if self.availability is AvailabilityStatus.AVAILABLE and self.reason:
            raise ValueError("available mechanism result cannot carry a reason")
        if self.availability is not AvailabilityStatus.AVAILABLE and not self.reason:
            raise ValueError("unavailable mechanism result requires an explicit reason")
        return self

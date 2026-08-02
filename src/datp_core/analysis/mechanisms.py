"""Descriptive mechanism analyses, divergence boundaries, and absorption decisions."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from numbers import Real

import numpy as np
from scipy import stats
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.models import (
    PValue,
    ScientificDecisionResult,
)
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ScientificDecision,
)
from datp_core.domain.values import (
    MetricValue,
    Ratio,
    ThresholdValue,
)
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import ClusterMembership

MINIMUM_ASSOCIATION_OBSERVATIONS = 3
MINIMUM_DIVERGENCE_CLIENTS = 2

MODEL_EFFECT_PARTIAL_RETENTION_CUTOFF = Ratio(0.25)
MODEL_EFFECT_FULL_RETENTION_CUTOFF = Ratio(0.75)


@dataclass(frozen=True, slots=True)
class AssociationResult:
    observations: tuple[tuple[float, float], ...]
    spearman_rho: float | None
    spearman_p_value: PValue | None
    intercept: float | None
    slope: float | None
    slope_standard_error: float | None
    r_squared: float | None
    leverage: tuple[float, ...]
    availability: AvailabilityStatus
    reason: str

    def __post_init__(self) -> None:
        if any(not isfinite(x) or not isfinite(y) for x, y in self.observations):
            raise ValueError("association observations must be finite")

        available = self.availability is AvailabilityStatus.AVAILABLE
        values = (
            self.spearman_rho,
            self.intercept,
            self.slope,
            self.slope_standard_error,
            self.r_squared,
        )
        if available:
            if (
                any(value is None or not isfinite(value) for value in values)
                or self.spearman_p_value is None
                or len(self.leverage) != len(self.observations)
                or any(not isfinite(value) for value in self.leverage)
                or self.reason
            ):
                raise ValueError("available association requires complete finite statistics and no reason")
        elif any(value is not None for value in values) or self.spearman_p_value is not None or self.leverage:
            raise ValueError("unavailable association cannot contain calculated statistics")
        elif not self.reason:
            raise ValueError("unavailable association requires an explicit reason")

    @property
    def evidence_role(self) -> EvidenceRole:
        return EvidenceRole.MECHANISM

    @property
    def observation_count(self) -> int:
        return len(self.observations)


@dataclass(frozen=True, slots=True)
class ClusterPartitionSummary:
    group_sizes: tuple[int, ...]

    def __post_init__(self) -> None:
        if any(size < 0 for size in self.group_sizes):
            raise ValueError("cluster group sizes must be non-negative")

    @property
    def singleton_groups(self) -> tuple[int, ...]:
        return tuple(index for index, size in enumerate(self.group_sizes) if size == 1)

    @property
    def empty_groups(self) -> tuple[int, ...]:
        return tuple(index for index, size in enumerate(self.group_sizes) if size == 0)


@dataclass(frozen=True, slots=True)
class ClusterStabilityResult:
    adjusted_rand_index: MetricValue
    compared_clients: tuple[ClientIdentity, ...]
    left_partition: ClusterPartitionSummary
    right_partition: ClusterPartitionSummary
    contingency: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if not self.compared_clients:
            raise ValueError("cluster stability requires at least one client")
        if len(self.contingency) != len(self.left_partition.group_sizes):
            raise ValueError("cluster contingency row count must match the left partition")
        if any(len(row) != len(self.right_partition.group_sizes) for row in self.contingency):
            raise ValueError("cluster contingency column count must match the right partition")
        if sum(sum(row) for row in self.contingency) != len(self.compared_clients):
            raise ValueError("cluster contingency must account for every client")

    @property
    def evidence_role(self) -> EvidenceRole:
        return EvidenceRole.MECHANISM


@dataclass(frozen=True, slots=True)
class ThresholdMovement:
    client: ClientIdentity
    delta_threshold: MetricValue
    delta_fpr: MetricValue
    delta_tpr: MetricValue | None
    reason: str

    def __post_init__(self) -> None:
        if self.delta_tpr is None and not self.reason:
            raise ValueError("unavailable attack movement requires an explicit reason")
        if self.delta_tpr is not None and self.reason:
            raise ValueError("available attack movement cannot carry an unavailable reason")

    @property
    def evidence_role(self) -> EvidenceRole:
        return EvidenceRole.MECHANISM

    @property
    def attack_availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.delta_tpr is not None else AvailabilityStatus.UNAVAILABLE


class DivergenceBlocker(StrEnum):
    COMMON_SUPPORT_UNRESOLVED = "common_support_unresolved"
    BINNING_UNRESOLVED = "binning_unresolved"
    DENSITY_UNRESOLVED = "density_unresolved"
    SMOOTHING_UNRESOLVED = "smoothing_unresolved"
    ZERO_MASS_UNRESOLVED = "zero_mass_unresolved"
    AGGREGATION_UNRESOLVED = "aggregation_unresolved"


@dataclass(frozen=True, slots=True)
class DivergenceResult:
    clients: tuple[ClientIdentity, ...]
    pairwise_values: tuple[MetricValue, ...]
    aggregate: MetricValue | None
    blocker: DivergenceBlocker | None
    reason: str

    def __post_init__(self) -> None:
        if len(self.clients) < MINIMUM_DIVERGENCE_CLIENTS:
            raise ValueError("divergence analysis requires at least two clients")
        if len(set(self.clients)) != len(self.clients):
            raise ValueError("divergence analysis requires unique clients")

        if self.blocker is None:
            if not self.pairwise_values or self.aggregate is None or self.reason:
                raise ValueError("available divergence requires values, aggregate, and no blocker")
        elif self.pairwise_values or self.aggregate is not None or not self.reason:
            raise ValueError("blocked divergence must preserve its unresolved construction")

    @property
    def evidence_role(self) -> EvidenceRole:
        return EvidenceRole.MECHANISM

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.blocker is None else AvailabilityStatus.UNAVAILABLE


def heterogeneity_benefit_association(
    observations: tuple[tuple[float, float], ...],
) -> AssociationResult:
    if len(observations) < MINIMUM_ASSOCIATION_OBSERVATIONS or any(
        not isfinite(x) or not isfinite(y) for x, y in observations
    ):
        return _unavailable_association(
            observations,
            AvailabilityStatus.UNAVAILABLE,
            "association requires at least three finite observations",
        )

    x_values = np.fromiter(
        (x for x, _ in observations),
        dtype=np.float64,
        count=len(observations),
    )
    y_values = np.fromiter(
        (y for _, y in observations),
        dtype=np.float64,
        count=len(observations),
    )
    if np.ptp(x_values) == 0.0:
        return _unavailable_association(
            observations,
            AvailabilityStatus.UNDEFINED,
            "heterogeneity has zero variation",
        )
    if np.ptp(y_values) == 0.0:
        return _unavailable_association(
            observations,
            AvailabilityStatus.UNDEFINED,
            "benefit has zero variation",
        )

    spearman = _numeric_attributes(
        stats.spearmanr(
            x_values,
            y_values,
            alternative="two-sided",
        ),
        ("statistic", "pvalue"),
    )
    regression = _numeric_attributes(
        stats.linregress(
            x_values,
            y_values,
            alternative="two-sided",
        ),
        ("intercept", "slope", "stderr", "rvalue"),
    )
    if spearman is None or regression is None:
        return _unavailable_association(
            observations,
            AvailabilityStatus.UNAVAILABLE,
            ("statistics library result is incompatible with the association contract"),
        )

    design = np.column_stack((np.ones(x_values.size), x_values))
    leverage = tuple(
        float(value)
        for value in np.einsum(
            "ij,ji->i",
            design,
            np.linalg.pinv(design),
        )
    )
    return AssociationResult(
        observations=observations,
        spearman_rho=spearman[0],
        spearman_p_value=PValue(spearman[1]),
        intercept=regression[0],
        slope=regression[1],
        slope_standard_error=regression[2],
        r_squared=regression[3] ** 2,
        leverage=leverage,
        availability=AvailabilityStatus.AVAILABLE,
        reason="",
    )


def cluster_stability(
    left: tuple[ClusterMembership, ...],
    right: tuple[ClusterMembership, ...],
) -> ClusterStabilityResult:
    left_assignments = _cluster_assignments(left)
    right_assignments = _cluster_assignments(right)
    if left_assignments.keys() != right_assignments.keys():
        raise ValueError("cluster stability requires identical persisted client memberships")

    clients = tuple(
        sorted(
            left_assignments,
            key=lambda client: client.client_id,
        )
    )
    left_labels = tuple(left_assignments[client] for client in clients)
    right_labels = tuple(right_assignments[client] for client in clients)
    contingency = tuple(
        tuple(
            sum(
                left_label == left_index and right_label == right_index
                for left_label, right_label in zip(
                    left_labels,
                    right_labels,
                    strict=True,
                )
            )
            for right_index in range(len(right))
        )
        for left_index in range(len(left))
    )
    return ClusterStabilityResult(
        adjusted_rand_index=MetricValue(
            float(
                adjusted_rand_score(
                    left_labels,
                    right_labels,
                )
            )
        ),
        compared_clients=clients,
        left_partition=ClusterPartitionSummary(tuple(len(group.members) for group in left)),
        right_partition=ClusterPartitionSummary(tuple(len(group.members) for group in right)),
        contingency=contingency,
    )


def threshold_movement(
    *,
    client: ClientIdentity,
    shared_threshold: ThresholdValue,
    local_threshold: ThresholdValue,
    shared_fpr: MetricValue,
    local_fpr: MetricValue,
    shared_tpr: MetricValue | None,
    local_tpr: MetricValue | None,
) -> ThresholdMovement:
    if (shared_tpr is None) != (local_tpr is None):
        raise ValueError("TPR movement requires both threshold methods or neither")

    return ThresholdMovement(
        client=client,
        delta_threshold=MetricValue(local_threshold.value - shared_threshold.value),
        delta_fpr=MetricValue(local_fpr.value - shared_fpr.value),
        delta_tpr=(
            None if shared_tpr is None or local_tpr is None else MetricValue(local_tpr.value - shared_tpr.value)
        ),
        reason=("" if shared_tpr is not None else "attack-sensitive movement unavailable"),
    )


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...],
    blocker: DivergenceBlocker,
) -> DivergenceResult:
    """Return a typed blocker without inventing histogram semantics."""
    return DivergenceResult(
        clients=tuple(
            sorted(
                clients,
                key=lambda client: client.client_id,
            )
        ),
        pairwise_values=(),
        aggregate=None,
        blocker=blocker,
        reason=(f"Jensen-Shannon divergence is blocked: {blocker.value}"),
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
            rationale=("model absorption requires a valid positive reference effect"),
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
    observations: tuple[tuple[float, float], ...],
    availability: AvailabilityStatus,
    reason: str,
) -> AssociationResult:
    return AssociationResult(
        observations=observations,
        spearman_rho=None,
        spearman_p_value=None,
        intercept=None,
        slope=None,
        slope_standard_error=None,
        r_squared=None,
        leverage=(),
        availability=availability,
        reason=reason,
    )


def _numeric_attributes(
    result: object,
    names: tuple[str, ...],
) -> tuple[float, ...] | None:
    values: list[float] = []
    for name in names:
        value = getattr(result, name, None)
        if not isinstance(value, Real) or isinstance(value, bool) or not isfinite(float(value)):
            return None
        values.append(float(value))
    return tuple(values)


def _cluster_assignments(
    memberships: tuple[ClusterMembership, ...],
) -> dict[ClientIdentity, int]:
    assignments: dict[ClientIdentity, int] = {}
    for group_index, membership in enumerate(memberships):
        for client in membership.members:
            if client in assignments:
                raise ValueError("each client must belong to exactly one cluster")
            assignments[client] = group_index

    if not assignments:
        raise ValueError("cluster stability requires at least one persisted client")
    return assignments

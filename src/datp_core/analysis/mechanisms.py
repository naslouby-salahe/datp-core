"""Source-authorized descriptive mechanism analyses, divergence boundary, and absorption decisions."""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

import numpy as np
from scipy import stats
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.inference.bootstrap import ScientificDecisionResult
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, ScientificDecision
from datp_core.domain.values import MetricValue, ThresholdValue
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.models import ClusterMembership


@dataclass(frozen=True, slots=True)
class AssociationResult:
    evidence_role: EvidenceRole
    observations: tuple[tuple[float, float], ...]
    spearman_rho: float | None
    spearman_p_value: float | None
    intercept: float | None
    slope: float | None
    slope_standard_error: float | None
    r_squared: float | None
    leverage: tuple[float, ...]
    availability: AvailabilityStatus
    reason: str

    @property
    def observation_count(self) -> int:
        return len(self.observations)


@dataclass(frozen=True, slots=True)
class MechanismResult:
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

    @property
    def group_count(self) -> int:
        return len(self.group_sizes)


@dataclass(frozen=True, slots=True)
class ClusterStabilityResult:
    evidence_role: EvidenceRole
    adjusted_rand_index: MetricValue
    compared_clients: tuple[ClientIdentity, ...]
    left_group_sizes: tuple[int, ...]
    right_group_sizes: tuple[int, ...]
    contingency: tuple[tuple[int, ...], ...]
    left_singleton_groups: tuple[int, ...]
    right_singleton_groups: tuple[int, ...]
    left_empty_groups: tuple[int, ...]
    right_empty_groups: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ThresholdMovement:
    evidence_role: EvidenceRole
    client: ClientIdentity
    delta_threshold: MetricValue
    delta_fpr: MetricValue
    delta_tpr: MetricValue | None
    attack_availability: AvailabilityStatus
    reason: str


def heterogeneity_benefit_association(observations: tuple[tuple[float, float], ...]) -> AssociationResult:
    if len(observations) < 3 or any(not isfinite(x) or not isfinite(y) for x, y in observations):
        return AssociationResult(
            EvidenceRole.MECHANISM,
            observations,
            None,
            None,
            None,
            None,
            None,
            None,
            (),
            AvailabilityStatus.UNAVAILABLE,
            "association requires at least three finite observations",
        )
    x_values = np.asarray(tuple(item[0] for item in observations), dtype=np.float64)
    y_values = np.asarray(tuple(item[1] for item in observations), dtype=np.float64)
    if np.all(x_values == x_values[0]):
        return AssociationResult(
            EvidenceRole.MECHANISM,
            observations,
            None,
            None,
            None,
            None,
            None,
            None,
            (),
            AvailabilityStatus.UNDEFINED,
            "heterogeneity has zero variation",
        )
    spearman = _spearman_values(stats.spearmanr(x_values, y_values, alternative="two-sided"))
    regression = _regression_values(stats.linregress(x_values, y_values, alternative="two-sided"))
    if spearman is None or regression is None:
        return AssociationResult(
            EvidenceRole.MECHANISM,
            observations,
            None,
            None,
            None,
            None,
            None,
            None,
            (),
            AvailabilityStatus.UNAVAILABLE,
            "statistics library result is incompatible with the declared association record",
        )
    design = np.column_stack((np.ones(x_values.size), x_values))
    leverage = tuple(float(value) for value in np.diag(design @ np.linalg.inv(design.T @ design) @ design.T))
    return AssociationResult(
        EvidenceRole.MECHANISM,
        observations,
        spearman[0],
        spearman[1],
        regression[0],
        regression[1],
        regression[2],
        regression[3] ** 2,
        leverage,
        AvailabilityStatus.AVAILABLE,
        "",
    )


def _spearman_values(result: object) -> tuple[float, float] | None:
    values = _numeric_attributes(result, ("statistic", "pvalue"))
    if values is None:
        return None
    return values[0], values[1]


def _regression_values(result: object) -> tuple[float, float, float, float] | None:
    values = _numeric_attributes(result, ("intercept", "slope", "stderr", "rvalue"))
    if values is None:
        return None
    return values[0], values[1], values[2], values[3]


def _numeric_attributes(result: object, names: tuple[str, ...]) -> tuple[float, ...] | None:
    values: list[float] = []
    for name in names:
        value = getattr(result, name, None)
        if not isinstance(value, int | float):
            return None
        values.append(float(value))
    return tuple(values)


def cluster_stability(
    left: tuple[ClusterMembership, ...], right: tuple[ClusterMembership, ...]
) -> ClusterStabilityResult:
    left_clients = tuple(client for group in left for client in group.members)
    right_clients = tuple(client for group in right for client in group.members)
    if frozenset(left_clients) != frozenset(right_clients):
        raise ValueError("cluster stability requires identical persisted client memberships")
    clients = tuple(sorted(left_clients, key=lambda item: item.client_id))
    left_labels = tuple(
        next(index for index, group in enumerate(left) if client in group.members) for client in clients
    )
    right_labels = tuple(
        next(index for index, group in enumerate(right) if client in group.members) for client in clients
    )
    contingency = tuple(
        tuple(
            sum(
                left_label == row and right_label == column
                for left_label, right_label in zip(left_labels, right_labels, strict=True)
            )
            for column in range(len(right))
        )
        for row in range(len(left))
    )
    return ClusterStabilityResult(
        EvidenceRole.MECHANISM,
        MetricValue(float(adjusted_rand_score(left_labels, right_labels))),
        clients,
        tuple(len(group.members) for group in left),
        tuple(len(group.members) for group in right),
        contingency,
        tuple(index for index, group in enumerate(left) if len(group.members) == 1),
        tuple(index for index, group in enumerate(right) if len(group.members) == 1),
        tuple(index for index, group in enumerate(left) if not group.members),
        tuple(index for index, group in enumerate(right) if not group.members),
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
        raise ValueError("TPR movement requires both methods or neither")
    if shared_tpr is None and local_tpr is None:
        return ThresholdMovement(
            EvidenceRole.MECHANISM,
            client,
            MetricValue(local_threshold.value - shared_threshold.value),
            MetricValue(local_fpr.value - shared_fpr.value),
            None,
            AvailabilityStatus.UNAVAILABLE,
            "attack-sensitive movement unavailable",
        )
    if shared_tpr is None or local_tpr is None:
        raise ValueError("TPR movement requires both methods or neither")
    return ThresholdMovement(
        EvidenceRole.MECHANISM,
        client,
        MetricValue(local_threshold.value - shared_threshold.value),
        MetricValue(local_fpr.value - shared_fpr.value),
        MetricValue(local_tpr.value - shared_tpr.value),
        AvailabilityStatus.AVAILABLE,
        "",
    )


class DivergenceBlocker(StrEnum):
    COMMON_SUPPORT_UNRESOLVED = "common_support_unresolved"
    BINNING_UNRESOLVED = "binning_unresolved"
    DENSITY_UNRESOLVED = "density_unresolved"
    SMOOTHING_UNRESOLVED = "smoothing_unresolved"
    ZERO_MASS_UNRESOLVED = "zero_mass_unresolved"
    AGGREGATION_UNRESOLVED = "aggregation_unresolved"


@dataclass(frozen=True, slots=True)
class DivergenceResult:
    evidence_role: EvidenceRole
    clients: tuple[ClientIdentity, ...]
    pairwise_values: tuple[MetricValue, ...]
    aggregate: MetricValue | None
    availability: AvailabilityStatus
    blocker: DivergenceBlocker | None
    reason: str

    def __post_init__(self) -> None:
        if self.availability is AvailabilityStatus.AVAILABLE:
            if self.blocker is not None or not self.pairwise_values or self.aggregate is None or self.reason:
                raise ValueError("available divergence requires values, aggregate, and no blocker")
        elif self.blocker is None or self.pairwise_values or self.aggregate is not None or not self.reason:
            raise ValueError("blocked divergence must preserve its explicit unresolved construction")


def blocked_jensen_shannon_divergence(
    clients: tuple[ClientIdentity, ...], blocker: DivergenceBlocker
) -> DivergenceResult:
    """Return the required typed blocker instead of selecting histogram semantics ad hoc."""
    if len(clients) < 2:
        raise ValueError("divergence analysis requires at least two clients")
    return DivergenceResult(
        EvidenceRole.MECHANISM,
        tuple(sorted(clients, key=lambda item: item.client_id)),
        (),
        None,
        AvailabilityStatus.UNAVAILABLE,
        blocker,
        f"Jensen-Shannon divergence is blocked: {blocker.value}",
    )


def decide_model_absorption(
    delta_fedavg: MetricValue | None, delta_ditto: MetricValue | None
) -> ScientificDecisionResult:
    if delta_fedavg is None or delta_ditto is None or delta_fedavg <= 0:
        return ScientificDecisionResult(
            EvidenceRole.SUPPORTIVE,
            ScientificDecision.BLOCKED,
            delta_ditto,
            None,
            AvailabilityStatus.UNAVAILABLE,
            "model absorption requires a valid positive FedAvg reference effect",
        )
    ratio = delta_ditto.value / delta_fedavg.value
    if ratio >= 0.75:
        decision, rationale = ScientificDecision.SUPPORTED, "the Ditto effect is retained"
    elif ratio >= 0.25:
        decision, rationale = ScientificDecision.PARTIAL_ABSORPTION, "the Ditto effect is partially absorbed"
    else:
        decision, rationale = ScientificDecision.FULL_ABSORPTION, "the Ditto effect is largely absorbed"
    return ScientificDecisionResult(
        EvidenceRole.SUPPORTIVE, decision, delta_ditto, None, AvailabilityStatus.AVAILABLE, rationale
    )

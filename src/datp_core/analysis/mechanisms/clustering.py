"""Persisted cluster-partition stability and recovery mechanism evidence."""

from enum import StrEnum
from typing import ClassVar

from pydantic import model_validator
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.inference.wilcoxon import CorrelationCoefficient
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.contracts import ClientOwned, StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole, FederatedThresholdMethod
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import ClusterIndex, PairedObservationCount, Seed
from datp_core.domain.values.ratios import MetricValue, ThresholdValue
from datp_core.thresholding.methods.cluster import ClusterFingerprint, ClusterMembership, GroupedThresholdResult

MINIMUM_STABILITY_CLIENTS = PairedObservationCount(2)


class ClusterPartitionSummary(StrictModel):
    group_sizes: tuple[PairedObservationCount, ...]
    empty_cluster_indexes: tuple[ClusterIndex, ...] = ()

    @classmethod
    def from_memberships(
        cls,
        memberships: tuple[ClusterMembership, ...],
        *,
        declared_group_count: int | None = None,
    ) -> "ClusterPartitionSummary":
        sizes = tuple(PairedObservationCount(len(item.members)) for item in memberships)
        empty: tuple[ClusterIndex, ...] = ()
        if declared_group_count is not None and declared_group_count > len(sizes):
            empty = tuple(ClusterIndex(index) for index in range(len(sizes), declared_group_count))
            sizes = sizes + tuple(PairedObservationCount(0) for _ in empty)
        return cls(group_sizes=sizes, empty_cluster_indexes=empty)

    @property
    def singleton_groups(self) -> tuple[ClusterIndex, ...]:
        return tuple(ClusterIndex(index) for index, size in enumerate(self.group_sizes) if size.value == 1)

    @property
    def empty_groups(self) -> tuple[ClusterIndex, ...]:
        derived = tuple(ClusterIndex(index) for index, size in enumerate(self.group_sizes) if size.value == 0)
        return self.empty_cluster_indexes if self.empty_cluster_indexes else derived


class ClusterEvidenceAvailability(StrEnum):
    AVAILABLE = "available"
    AVAILABLE_WITH_EMPTY_GROUP_EVIDENCE = "available_with_empty_group_evidence"
    BLOCKED = "blocked"
    FAILED = "failed"


class ClusterEvidenceRecord(StrictModel):
    """Full cluster evidence derived from a persisted grouped-threshold result."""

    seed: Seed
    method: FederatedThresholdMethod
    source_threshold_checksum: Checksum
    fingerprints: tuple[ClusterFingerprint, ...]
    memberships: tuple[ClusterMembership, ...]
    partition: ClusterPartitionSummary
    contributing_quantile_dispersion: MetricValue
    effective_threshold_dispersion: MetricValue
    threshold_dispersion_recovery_fraction: MetricValue | None
    threshold_dispersion_recovery_reason: str | None
    cv_fpr_equity_recovery_fraction: MetricValue | None
    cv_fpr_equity_recovery_reason: str | None
    evidence_availability: ClusterEvidenceAvailability = ClusterEvidenceAvailability.AVAILABLE

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_record(self) -> "ClusterEvidenceRecord":
        if self.method is not FederatedThresholdMethod.CLUSTER_THRESHOLD:
            raise ValueError("cluster evidence requires the cluster threshold method")
        if (self.threshold_dispersion_recovery_fraction is None) == (self.threshold_dispersion_recovery_reason is None):
            raise ValueError("threshold-dispersion recovery requires either a value or an explicit reason")
        if (self.cv_fpr_equity_recovery_fraction is None) == (self.cv_fpr_equity_recovery_reason is None):
            raise ValueError("CV(FPR) equity recovery requires either a value or an explicit reason")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        if self.evidence_availability in {
            ClusterEvidenceAvailability.AVAILABLE,
            ClusterEvidenceAvailability.AVAILABLE_WITH_EMPTY_GROUP_EVIDENCE,
        }:
            return AvailabilityStatus.AVAILABLE
        return AvailabilityStatus.UNAVAILABLE

    @property
    def recovery_fraction(self) -> MetricValue | None:
        """Primary recovery claim uses the CV(FPR) equity estimand when available."""
        return self.cv_fpr_equity_recovery_fraction

    @property
    def recovery_fraction_reason(self) -> str | None:
        return self.cv_fpr_equity_recovery_reason


class ClusterStabilityResult(StrictModel):
    adjusted_rand_index: CorrelationCoefficient
    compared_clients: tuple[ClientIdentity, ...]
    left_partition: ClusterPartitionSummary
    right_partition: ClusterPartitionSummary
    contingency: tuple[tuple[PairedObservationCount, ...], ...]
    left_source_checksum: Checksum | None = None
    right_source_checksum: Checksum | None = None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "ClusterStabilityResult":
        if len(self.compared_clients) < MINIMUM_STABILITY_CLIENTS.value:
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


def cluster_evidence_from_grouped_result(
    result: GroupedThresholdResult,
    *,
    source_threshold_checksum: Checksum,
    local_dispersion: MetricValue | None,
    shared_cv_fpr: MetricValue | None = None,
    local_cv_fpr: MetricValue | None = None,
    cluster_cv_fpr: MetricValue | None = None,
) -> ClusterEvidenceRecord:
    partition = ClusterPartitionSummary.from_memberships(
        result.clusters,
        declared_group_count=result.group_count.value,
    )
    contributing = tuple(
        quantile.value.value for membership in result.clusters for quantile in membership.contributing_local_quantiles
    )
    effective = tuple(membership.cluster_threshold.value for membership in result.clusters)
    contributing_dispersion = MetricValue(max(contributing) - min(contributing)) if contributing else MetricValue(0.0)
    effective_dispersion = MetricValue(max(effective) - min(effective)) if effective else MetricValue(0.0)
    if local_dispersion is None or local_dispersion.value <= 0.0:
        threshold_recovery = None
        threshold_reason = "local-threshold dispersion is unavailable or non-positive"
    else:
        threshold_recovery = MetricValue(1.0 - (effective_dispersion.value / local_dispersion.value))
        threshold_reason = None
    equity_recovery, equity_reason = _cv_fpr_equity_recovery(
        shared_cv_fpr=shared_cv_fpr,
        local_cv_fpr=local_cv_fpr,
        cluster_cv_fpr=cluster_cv_fpr,
    )
    empty = partition.empty_groups
    evidence_availability = (
        ClusterEvidenceAvailability.AVAILABLE_WITH_EMPTY_GROUP_EVIDENCE
        if empty
        else ClusterEvidenceAvailability.AVAILABLE
    )
    return ClusterEvidenceRecord(
        seed=result.coordinate.training_seed,
        method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        source_threshold_checksum=source_threshold_checksum,
        fingerprints=result.fingerprints,
        memberships=result.clusters,
        partition=partition,
        contributing_quantile_dispersion=contributing_dispersion,
        effective_threshold_dispersion=effective_dispersion,
        threshold_dispersion_recovery_fraction=threshold_recovery,
        threshold_dispersion_recovery_reason=threshold_reason,
        cv_fpr_equity_recovery_fraction=equity_recovery,
        cv_fpr_equity_recovery_reason=equity_reason,
        evidence_availability=evidence_availability,
    )


def empty_cluster_evidence_record(
    *,
    seed: Seed,
    source_threshold_checksum: Checksum,
    declared_group_count: int,
    filled_memberships: tuple[ClusterMembership, ...],
    fingerprints: tuple[ClusterFingerprint, ...] = (),
    reason: str,
) -> ClusterEvidenceRecord:
    """Preserve empty-cluster negative evidence without fabricating memberships."""
    partition = ClusterPartitionSummary.from_memberships(
        filled_memberships,
        declared_group_count=declared_group_count,
    )
    return ClusterEvidenceRecord(
        seed=seed,
        method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        source_threshold_checksum=source_threshold_checksum,
        fingerprints=fingerprints,
        memberships=filled_memberships,
        partition=partition,
        contributing_quantile_dispersion=MetricValue(0.0),
        effective_threshold_dispersion=MetricValue(0.0),
        threshold_dispersion_recovery_fraction=None,
        threshold_dispersion_recovery_reason=reason,
        cv_fpr_equity_recovery_fraction=None,
        cv_fpr_equity_recovery_reason=reason,
        evidence_availability=ClusterEvidenceAvailability.AVAILABLE_WITH_EMPTY_GROUP_EVIDENCE,
    )


def _cv_fpr_equity_recovery(
    *,
    shared_cv_fpr: MetricValue | None,
    local_cv_fpr: MetricValue | None,
    cluster_cv_fpr: MetricValue | None,
) -> tuple[MetricValue | None, str | None]:
    if shared_cv_fpr is None or local_cv_fpr is None or cluster_cv_fpr is None:
        return None, "CV(FPR) equity recovery requires shared, local, and cluster population CV(FPR)"
    gap = shared_cv_fpr.value - local_cv_fpr.value
    if gap <= 0.0:
        return None, "CV(FPR) equity recovery is undefined when the B1–B2 gap is non-positive"
    recovered = shared_cv_fpr.value - cluster_cv_fpr.value
    return MetricValue(recovered / gap), None


def cluster_stability(
    left: tuple[ClusterMembership, ...],
    right: tuple[ClusterMembership, ...],
    *,
    left_source_checksum: Checksum | None = None,
    right_source_checksum: Checksum | None = None,
    left_declared_group_count: int | None = None,
    right_declared_group_count: int | None = None,
) -> ClusterStabilityResult:
    left_assignments = _cluster_assignments(left)
    right_assignments = _cluster_assignments(right)
    left_clients = tuple(item.client for item in left_assignments)
    right_clients = tuple(item.client for item in right_assignments)
    if left_clients != right_clients:
        raise ValueError("cluster stability requires identical persisted client memberships")
    left_labels = tuple(item.value.value for item in left_assignments)
    right_labels = tuple(item.value.value for item in right_assignments)
    left_partition = ClusterPartitionSummary.from_memberships(
        left,
        declared_group_count=left_declared_group_count,
    )
    right_partition = ClusterPartitionSummary.from_memberships(
        right,
        declared_group_count=right_declared_group_count,
    )
    return ClusterStabilityResult(
        adjusted_rand_index=CorrelationCoefficient(adjusted_rand_score(left_labels, right_labels)),
        compared_clients=left_clients,
        left_partition=left_partition,
        right_partition=right_partition,
        contingency=_contingency(
            left_labels,
            right_labels,
            len(left_partition.group_sizes),
            len(right_partition.group_sizes),
        ),
        left_source_checksum=left_source_checksum,
        right_source_checksum=right_source_checksum,
    )


def local_threshold_dispersion(thresholds: tuple[ThresholdValue, ...]) -> MetricValue:
    if not thresholds:
        raise ValueError("local threshold dispersion requires at least one threshold")
    values = tuple(item.value for item in thresholds)
    return MetricValue(max(values) - min(values))


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
                    for left_label, right_label in zip(
                        left_labels,
                        right_labels,
                        strict=True,
                    )
                )
            )
            for right_index in range(right_group_count)
        )
        for left_index in range(left_group_count)
    )

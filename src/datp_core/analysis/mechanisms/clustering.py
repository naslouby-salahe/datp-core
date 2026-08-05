"""Persisted cluster-partition stability mechanism evidence."""

from typing import ClassVar

from pydantic import model_validator
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.inference.wilcoxon import CorrelationCoefficient
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.contracts import ClientOwned, StrictModel
from datp_core.domain.enums import EvidenceRole
from datp_core.domain.values import ClusterIndex, PairedObservationCount
from datp_core.thresholding.methods.cluster import ClusterMembership

MINIMUM_STABILITY_CLIENTS = PairedObservationCount(2)


class ClusterPartitionSummary(StrictModel):
    group_sizes: tuple[PairedObservationCount, ...]

    @classmethod
    def from_memberships(
        cls,
        memberships: tuple[ClusterMembership, ...],
    ) -> "ClusterPartitionSummary":
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


def cluster_stability(
    left: tuple[ClusterMembership, ...],
    right: tuple[ClusterMembership, ...],
) -> ClusterStabilityResult:
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
        contingency=_contingency(
            left_labels,
            right_labels,
            len(left),
            len(right),
        ),
    )


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

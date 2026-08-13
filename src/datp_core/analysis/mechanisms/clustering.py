from enum import StrEnum
from itertools import permutations
from math import sqrt
from typing import ClassVar

from pydantic import model_validator
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.inference.wilcoxon import CorrelationCoefficient
from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.core.contracts import ClientOwned, StrictModel
from datp_core.core.identifiers import AnalysisReasonText, AvailabilityStatus, EvidenceRole, FederatedThresholdMethod
from datp_core.core.numeric import (
    ClusterIndex,
    GroupCount,
    MatrixRowIndex,
    MetricValue,
    PairedObservationCount,
    Ratio,
    RowCount,
    Seed,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.thresholds.policies.cluster import ClusterFingerprint, ClusterMembership, GroupedThresholdResult
from datp_core.thresholds.protocols import ClusterFingerprintFeature

MINIMUM_STABILITY_CLIENTS = PairedObservationCount(2)


class ClusterPartitionSummary(StrictModel):
    group_sizes: tuple[PairedObservationCount, ...]
    empty_cluster_indexes: tuple[ClusterIndex, ...] = ()

    @classmethod
    def from_memberships(
        cls,
        memberships: tuple[ClusterMembership, ...],
        *,
        declared_group_count: GroupCount | None = None,
        observed_empty_cluster_indexes: tuple[ClusterIndex, ...] = (),
    ) -> "ClusterPartitionSummary":

        size_by_index = {item.cluster_index.value: len(item.members) for item in memberships}
        for empty_index in observed_empty_cluster_indexes:
            size_by_index.setdefault(empty_index.value, 0)
        if memberships or observed_empty_cluster_indexes or declared_group_count is not None:
            max_index = max(
                (
                    *(item.cluster_index.value for item in memberships),
                    *tuple(i.value for i in observed_empty_cluster_indexes),
                    -1 if declared_group_count is None else declared_group_count.value - 1,
                ),
                default=-1,
            )
        else:
            max_index = -1
        sizes = tuple(PairedObservationCount(size_by_index.get(index, 0)) for index in range(max_index + 1))
        empty = tuple(ClusterIndex(index) for index, size in enumerate(sizes) if size.value == 0)
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


class RecoveryAssessment(StrictModel):
    fraction: MetricValue | None
    reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_assessment(self) -> "RecoveryAssessment":
        if (self.fraction is None) == (self.reason is None):
            raise ValueError("recovery assessment requires either a fraction or an explicit reason")
        return self


class GroupedCvFprRecovery(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    shared_cv_fpr: MetricValue | None
    grouped_cv_fpr: MetricValue | None
    local_cv_fpr: MetricValue | None
    recovery: RecoveryAssessment

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_grouped_method(self) -> "GroupedCvFprRecovery":
        if self.method not in {FederatedThresholdMethod.FAMILY_THRESHOLD, FederatedThresholdMethod.CLUSTER_THRESHOLD}:
            raise ValueError("CV(FPR) recovery applies only to family or cluster threshold sharing")
        values = (self.shared_cv_fpr, self.grouped_cv_fpr, self.local_cv_fpr)
        if self.recovery.fraction is not None and any(value is None for value in values):
            raise ValueError("available CV(FPR) recovery requires all policy values")
        return self


class ClusterEvidenceRecord(StrictModel):
    seed: Seed
    method: FederatedThresholdMethod
    fingerprints: tuple[ClusterFingerprint, ...]
    memberships: tuple[ClusterMembership, ...]
    partition: ClusterPartitionSummary
    contributing_quantile_dispersion: MetricValue | None
    effective_threshold_dispersion: MetricValue | None
    threshold_dispersion_recovery: RecoveryAssessment
    cv_fpr_equity_recovery: RecoveryAssessment
    evidence_availability: ClusterEvidenceAvailability = ClusterEvidenceAvailability.AVAILABLE
    dispersion_unavailable_reason: AnalysisReasonText | None = None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_record(self) -> "ClusterEvidenceRecord":
        if self.method is not FederatedThresholdMethod.CLUSTER_THRESHOLD:
            raise ValueError("cluster evidence requires the cluster threshold method")
        if (
            self.contributing_quantile_dispersion is None or self.effective_threshold_dispersion is None
        ) and self.dispersion_unavailable_reason is None:
            raise ValueError("unavailable dispersion requires an explicit dispersion_unavailable_reason")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        if self.evidence_availability in {
            ClusterEvidenceAvailability.AVAILABLE,
            ClusterEvidenceAvailability.AVAILABLE_WITH_EMPTY_GROUP_EVIDENCE,
        }:
            return AvailabilityStatus.AVAILABLE
        return AvailabilityStatus.UNAVAILABLE


class ClusterSilhouetteObservation(StrictModel):
    client: ClientIdentity
    cluster_index: ClusterIndex
    value: MetricValue | None
    unavailable_reason: AnalysisReasonText | None

    @model_validator(mode="after")
    def validate_availability(self) -> "ClusterSilhouetteObservation":
        if (self.value is None) == (self.unavailable_reason is None):
            raise ValueError("cluster silhouette observation requires exactly one value or unavailable reason")
        return self


class ClusterSilhouetteResult(StrictModel):
    seed: Seed
    observations: tuple[ClusterSilhouetteObservation, ...]
    mean_silhouette: MetricValue | None
    unavailable_reason: AnalysisReasonText | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "ClusterSilhouetteResult":
        if not self.observations:
            raise ValueError("cluster silhouette requires at least one client observation")
        if len({item.client for item in self.observations}) != len(self.observations):
            raise ValueError("cluster silhouette observations require unique clients")
        if (self.mean_silhouette is None) != (self.unavailable_reason is not None):
            raise ValueError("cluster silhouette mean requires exactly one value or unavailable reason")
        if self.mean_silhouette is not None and any(item.value is None for item in self.observations):
            raise ValueError("available cluster silhouette mean requires every client silhouette")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.mean_silhouette is not None else AvailabilityStatus.UNAVAILABLE


class ClusterScoreDivergenceResult(StrictModel):
    seed: Seed
    within_cluster_mean: MetricValue | None
    between_cluster_mean: MetricValue | None
    within_cluster_pair_count: PairedObservationCount
    between_cluster_pair_count: PairedObservationCount
    unavailable_reason: AnalysisReasonText | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "ClusterScoreDivergenceResult":
        available = self.unavailable_reason is None
        if available != (self.within_cluster_mean is not None and self.between_cluster_mean is not None):
            raise ValueError("cluster score divergence requires both means or one unavailable reason")
        if available and (self.within_cluster_pair_count.value == 0 or self.between_cluster_pair_count.value == 0):
            raise ValueError("available cluster score divergence requires within and between pairs")
        return self


class ClusterFeatureAblationEvidence(StrictModel):
    seed: Seed
    omitted_feature: ClusterFingerprintFeature
    adjusted_rand_index: CorrelationCoefficient
    mean_silhouette: MetricValue | None
    silhouette_unavailable_reason: AnalysisReasonText | None
    cv_fpr: MetricValue
    worst_client_fpr: MetricValue

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_evidence(self) -> "ClusterFeatureAblationEvidence":
        if (self.mean_silhouette is None) != (self.silhouette_unavailable_reason is not None):
            raise ValueError("ablation silhouette requires exactly one value or unavailable reason")
        return self


class ClusterContingencyRow(StrictModel):
    left_cluster_index: ClusterIndex
    counts_by_right_cluster: tuple[PairedObservationCount, ...]


class ClusterContingencyMatrix(StrictModel):
    rows: tuple[ClusterContingencyRow, ...]

    @model_validator(mode="after")
    def validate_matrix(self) -> "ClusterContingencyMatrix":
        expected_indexes = tuple(ClusterIndex(index) for index in range(len(self.rows)))
        actual_indexes = tuple(row.left_cluster_index for row in self.rows)
        if actual_indexes != expected_indexes:
            raise ValueError("cluster contingency rows must use consecutive left-cluster indexes")
        return self

    def row_count(self) -> RowCount:
        return RowCount(len(self.rows))

    def row_at(self, index: MatrixRowIndex) -> ClusterContingencyRow:
        return self.rows[index.value]


class ClusterStabilityResult(StrictModel):
    adjusted_rand_index: CorrelationCoefficient
    compared_clients: tuple[ClientIdentity, ...]
    left_memberships: tuple[ClusterMembership, ...]
    right_memberships: tuple[ClusterMembership, ...]
    left_partition: ClusterPartitionSummary
    right_partition: ClusterPartitionSummary
    contingency: ClusterContingencyMatrix

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "ClusterStabilityResult":
        if len(self.compared_clients) < MINIMUM_STABILITY_CLIENTS.value:
            raise ValueError("cluster stability requires at least two clients")
        if len(set(self.compared_clients)) != len(self.compared_clients):
            raise ValueError("cluster stability requires unique compared clients")
        if tuple(item.client for item in _cluster_assignments(self.left_memberships)) != self.compared_clients:
            raise ValueError("left cluster memberships must cover the compared clients in order")
        if tuple(item.client for item in _cluster_assignments(self.right_memberships)) != self.compared_clients:
            raise ValueError("right cluster memberships must cover the compared clients in order")
        if self.contingency.row_count().value != len(self.left_partition.group_sizes):
            raise ValueError("cluster contingency row count must match the left partition")
        if any(
            len(row.counts_by_right_cluster) != len(self.right_partition.group_sizes) for row in self.contingency.rows
        ):
            raise ValueError("cluster contingency column count must match the right partition")
        row_totals = tuple(sum(value.value for value in row.counts_by_right_cluster) for row in self.contingency.rows)
        if row_totals != tuple(value.value for value in self.left_partition.group_sizes):
            raise ValueError("cluster contingency row totals must match the left partition")
        column_totals = tuple(
            sum(row.counts_by_right_cluster[column].value for row in self.contingency.rows)
            for column in range(len(self.right_partition.group_sizes))
        )
        if column_totals != tuple(value.value for value in self.right_partition.group_sizes):
            raise ValueError("cluster contingency column totals must match the right partition")
        if sum(row_totals) != len(self.compared_clients):
            raise ValueError("cluster contingency must account for every client")
        return self


class ClusterAssignmentSwitchFrequency(StrictModel):
    client: ClientIdentity
    switched_seed_count: PairedObservationCount
    comparison_seed_count: PairedObservationCount
    frequency: Ratio

    @model_validator(mode="after")
    def validate_frequency(self) -> "ClusterAssignmentSwitchFrequency":
        if self.comparison_seed_count.value <= 0:
            raise ValueError("cluster switch frequency requires at least one comparison seed")
        if self.switched_seed_count.value > self.comparison_seed_count.value:
            raise ValueError("cluster switch count cannot exceed comparison seed count")
        expected = self.switched_seed_count.value / self.comparison_seed_count.value
        if abs(self.frequency.value - expected) > 1e-12:
            raise ValueError("cluster switch frequency must equal switched seeds divided by comparison seeds")
        return self


class ClusterAssignmentSwitchSummary(StrictModel):
    reference_seed: Seed
    compared_seeds: tuple[Seed, ...]
    client_frequencies: tuple[ClusterAssignmentSwitchFrequency, ...]

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_summary(self) -> "ClusterAssignmentSwitchSummary":
        if not self.compared_seeds:
            raise ValueError("cluster switch reporting requires at least two seeds")
        if self.reference_seed in self.compared_seeds:
            raise ValueError("cluster switch comparisons cannot include the reference seed")
        if tuple(sorted(self.compared_seeds, key=lambda seed: seed.value)) != self.compared_seeds:
            raise ValueError("cluster switch comparison seeds must be ordered")
        if not self.client_frequencies:
            raise ValueError("cluster switch reporting requires at least one client")
        if len({item.client for item in self.client_frequencies}) != len(self.client_frequencies):
            raise ValueError("cluster switch reporting requires unique clients")
        comparisons = PairedObservationCount(len(self.compared_seeds))
        if any(item.comparison_seed_count != comparisons for item in self.client_frequencies):
            raise ValueError("cluster switch frequencies must use every comparison seed")
        return self


def cluster_evidence_from_grouped_result(
    result: GroupedThresholdResult,
    *,
    local_dispersion: MetricValue | None,
    shared_cv_fpr: MetricValue | None = None,
    local_cv_fpr: MetricValue | None = None,
    cluster_cv_fpr: MetricValue | None = None,
) -> ClusterEvidenceRecord:
    partition = ClusterPartitionSummary.from_memberships(
        result.clusters,
        declared_group_count=result.group_count,
    )
    contributing = tuple(
        quantile.value.value for membership in result.clusters for quantile in membership.contributing_local_quantiles
    )
    effective = tuple(
        membership.cluster_threshold.value for membership in result.clusters if membership.cluster_threshold is not None
    )
    contributing_dispersion = MetricValue(max(contributing) - min(contributing)) if len(contributing) >= 2 else None
    effective_dispersion = MetricValue(max(effective) - min(effective)) if len(effective) >= 2 else None
    dispersion_reason: AnalysisReasonText | None = None
    if contributing_dispersion is None or effective_dispersion is None:
        dispersion_reason = AnalysisReasonText(
            "dispersion requires at least two computed cluster quantiles or thresholds"
        )
    if local_dispersion is None or local_dispersion.value <= 0.0 or effective_dispersion is None:
        threshold_recovery = None
        threshold_reason: AnalysisReasonText | None = AnalysisReasonText(
            "local-threshold dispersion is unavailable or non-positive"
        )
    else:
        threshold_recovery = MetricValue(1.0 - (effective_dispersion.value / local_dispersion.value))
        threshold_reason = None
    equity_recovery = _cv_fpr_equity_recovery(
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
        fingerprints=result.fingerprints,
        memberships=result.clusters,
        partition=partition,
        contributing_quantile_dispersion=contributing_dispersion,
        effective_threshold_dispersion=effective_dispersion,
        threshold_dispersion_recovery=RecoveryAssessment(
            fraction=threshold_recovery,
            reason=threshold_reason,
        ),
        cv_fpr_equity_recovery=equity_recovery,
        evidence_availability=evidence_availability,
        dispersion_unavailable_reason=dispersion_reason,
    )


def cluster_silhouette_from_grouped_result(result: GroupedThresholdResult) -> ClusterSilhouetteResult:
    assignments = _assignment_by_client(result.clusters)
    fingerprints = {item.client: _fingerprint_vector(item) for item in result.fingerprints}
    if tuple(sorted(fingerprints, key=lambda client: client.client_id.value)) != tuple(
        sorted(assignments, key=lambda client: client.client_id.value)
    ):
        raise ValueError("cluster silhouette requires fingerprints for exactly the assigned clients")
    nonempty_groups = tuple(membership for membership in result.clusters if membership.members)
    if len(nonempty_groups) < 2:
        reason = AnalysisReasonText("mean silhouette is unavailable with fewer than two non-empty clusters")
        return ClusterSilhouetteResult(
            seed=result.coordinate.training_seed,
            observations=tuple(
                ClusterSilhouetteObservation(
                    client=client,
                    cluster_index=assignments[client],
                    value=None,
                    unavailable_reason=reason,
                )
                for client in sorted(assignments, key=lambda item: item.client_id.value)
            ),
            mean_silhouette=None,
            unavailable_reason=reason,
        )
    observations: list[ClusterSilhouetteObservation] = []
    for membership in result.clusters:
        for client in membership.members:
            if len(membership.members) == 1:
                value = MetricValue(0.0)
            else:
                own_distances = tuple(
                    _euclidean_distance(fingerprints[client], fingerprints[other])
                    for other in membership.members
                    if other != client
                )
                within = sum(own_distances) / len(own_distances)
                between = min(
                    sum(_euclidean_distance(fingerprints[client], fingerprints[other]) for other in other_group.members)
                    / len(other_group.members)
                    for other_group in nonempty_groups
                    if other_group.cluster_index != membership.cluster_index
                )
                denominator = max(within, between)
                value = MetricValue(0.0 if denominator == 0.0 else (between - within) / denominator)
            observations.append(
                ClusterSilhouetteObservation(
                    client=client,
                    cluster_index=membership.cluster_index,
                    value=value,
                    unavailable_reason=None,
                )
            )
    ordered = tuple(sorted(observations, key=lambda item: item.client.client_id.value))
    return ClusterSilhouetteResult(
        seed=result.coordinate.training_seed,
        observations=ordered,
        mean_silhouette=MetricValue(sum(item.value.value for item in ordered if item.value is not None) / len(ordered)),
        unavailable_reason=None,
    )


def cluster_score_divergence(
    record: ClusterEvidenceRecord,
    divergence: DivergenceResult,
) -> ClusterScoreDivergenceResult:
    assignments = _assignment_by_client(record.memberships)
    if tuple(sorted(assignments, key=lambda client: client.client_id.value)) != divergence.clients:
        raise ValueError("cluster score divergence requires the exact clustered score-vector clients")
    if divergence.blocker is not None:
        return ClusterScoreDivergenceResult(
            seed=record.seed,
            within_cluster_mean=None,
            between_cluster_mean=None,
            within_cluster_pair_count=PairedObservationCount(0),
            between_cluster_pair_count=PairedObservationCount(0),
            unavailable_reason=divergence.reason,
        )
    within = tuple(
        item.value.value
        for item in divergence.pairwise_distances
        if assignments[item.left_client] == assignments[item.right_client]
    )
    between = tuple(
        item.value.value
        for item in divergence.pairwise_distances
        if assignments[item.left_client] != assignments[item.right_client]
    )
    if not within or not between:
        return ClusterScoreDivergenceResult(
            seed=record.seed,
            within_cluster_mean=None,
            between_cluster_mean=None,
            within_cluster_pair_count=PairedObservationCount(len(within)),
            between_cluster_pair_count=PairedObservationCount(len(between)),
            unavailable_reason=AnalysisReasonText(
                "within-versus-between cluster score divergence requires at least one pair of each kind"
            ),
        )
    return ClusterScoreDivergenceResult(
        seed=record.seed,
        within_cluster_mean=MetricValue(sum(within) / len(within)),
        between_cluster_mean=MetricValue(sum(between) / len(between)),
        within_cluster_pair_count=PairedObservationCount(len(within)),
        between_cluster_pair_count=PairedObservationCount(len(between)),
        unavailable_reason=None,
    )


def cluster_feature_ablation_evidence(
    canonical: GroupedThresholdResult,
    ablation: GroupedThresholdResult,
    *,
    omitted_feature: ClusterFingerprintFeature,
    cv_fpr: MetricValue,
    worst_client_fpr: MetricValue,
) -> ClusterFeatureAblationEvidence:
    if canonical.coordinate.training_seed != ablation.coordinate.training_seed:
        raise ValueError("cluster feature ablation requires a seed-matched canonical result")
    stability = cluster_stability(
        canonical.clusters,
        ablation.clusters,
        left_declared_group_count=canonical.group_count,
        right_declared_group_count=ablation.group_count,
    )
    silhouette = cluster_silhouette_from_grouped_result(ablation)
    return ClusterFeatureAblationEvidence(
        seed=ablation.coordinate.training_seed,
        omitted_feature=omitted_feature,
        adjusted_rand_index=stability.adjusted_rand_index,
        mean_silhouette=silhouette.mean_silhouette,
        silhouette_unavailable_reason=silhouette.unavailable_reason,
        cv_fpr=cv_fpr,
        worst_client_fpr=worst_client_fpr,
    )


def _fingerprint_vector(fingerprint: ClusterFingerprint) -> tuple[float, float, float, float]:
    return (
        fingerprint.standardized.mean.value,
        fingerprint.standardized.standard_deviation.value,
        fingerprint.standardized.skewness.value,
        fingerprint.standardized.p95.value,
    )


def _euclidean_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sqrt(sum((left_value - right_value) ** 2 for left_value, right_value in zip(left, right, strict=True)))


def empty_cluster_evidence_record(
    *,
    seed: Seed,
    declared_group_count: GroupCount,
    filled_memberships: tuple[ClusterMembership, ...],
    fingerprints: tuple[ClusterFingerprint, ...] = (),
    reason: AnalysisReasonText,
    observed_empty_cluster_indexes: tuple[ClusterIndex, ...] = (),
) -> ClusterEvidenceRecord:

    partition = ClusterPartitionSummary.from_memberships(
        filled_memberships,
        declared_group_count=declared_group_count,
        observed_empty_cluster_indexes=observed_empty_cluster_indexes,
    )
    contributing = tuple(
        quantile.value.value
        for membership in filled_memberships
        for quantile in membership.contributing_local_quantiles
    )
    effective = tuple(
        membership.cluster_threshold.value
        for membership in filled_memberships
        if membership.cluster_threshold is not None
    )
    contributing_dispersion = MetricValue(max(contributing) - min(contributing)) if len(contributing) >= 2 else None
    effective_dispersion = MetricValue(max(effective) - min(effective)) if len(effective) >= 2 else None
    dispersion_reason = (
        None
        if contributing_dispersion is not None and effective_dispersion is not None
        else AnalysisReasonText("dispersion is unavailable for empty or incomplete cluster partitions")
    )
    return ClusterEvidenceRecord(
        seed=seed,
        method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
        fingerprints=fingerprints,
        memberships=filled_memberships,
        partition=partition,
        contributing_quantile_dispersion=contributing_dispersion,
        effective_threshold_dispersion=effective_dispersion,
        threshold_dispersion_recovery=RecoveryAssessment(fraction=None, reason=reason),
        cv_fpr_equity_recovery=RecoveryAssessment(fraction=None, reason=reason),
        evidence_availability=ClusterEvidenceAvailability.AVAILABLE_WITH_EMPTY_GROUP_EVIDENCE,
        dispersion_unavailable_reason=dispersion_reason,
    )


def _cv_fpr_equity_recovery(
    *,
    shared_cv_fpr: MetricValue | None,
    local_cv_fpr: MetricValue | None,
    cluster_cv_fpr: MetricValue | None,
) -> RecoveryAssessment:
    if shared_cv_fpr is None or local_cv_fpr is None or cluster_cv_fpr is None:
        return RecoveryAssessment(
            fraction=None,
            reason=AnalysisReasonText("CV(FPR) equity recovery requires shared, local, and cluster population CV(FPR)"),
        )
    gap = shared_cv_fpr.value - local_cv_fpr.value
    if gap <= 0.0:
        return RecoveryAssessment(
            fraction=None,
            reason=AnalysisReasonText(
                "CV(FPR) equity recovery is undefined when the SHARED_THRESHOLD–LOCAL_THRESHOLD gap is non-positive"
            ),
        )
    recovered = shared_cv_fpr.value - cluster_cv_fpr.value
    return RecoveryAssessment(fraction=MetricValue(recovered / gap), reason=None)


def grouped_cv_fpr_recovery(
    *,
    seed: Seed,
    method: FederatedThresholdMethod,
    shared_cv_fpr: MetricValue | None,
    grouped_cv_fpr: MetricValue | None,
    local_cv_fpr: MetricValue | None,
) -> GroupedCvFprRecovery:
    return GroupedCvFprRecovery(
        seed=seed,
        method=method,
        shared_cv_fpr=shared_cv_fpr,
        grouped_cv_fpr=grouped_cv_fpr,
        local_cv_fpr=local_cv_fpr,
        recovery=_cv_fpr_equity_recovery(
            shared_cv_fpr=shared_cv_fpr,
            local_cv_fpr=local_cv_fpr,
            cluster_cv_fpr=grouped_cv_fpr,
        ),
    )


def cluster_stability(
    left: tuple[ClusterMembership, ...],
    right: tuple[ClusterMembership, ...],
    *,
    left_declared_group_count: GroupCount | None = None,
    right_declared_group_count: GroupCount | None = None,
) -> ClusterStabilityResult:
    left_assignments = _cluster_assignments(left)
    right_assignments = _cluster_assignments(right)
    left_clients = tuple(item.client for item in left_assignments)
    right_clients = tuple(item.client for item in right_assignments)
    if left_clients != right_clients:
        raise ValueError("cluster stability requires identical persisted client memberships")
    left_labels = tuple(item.value for item in left_assignments)
    right_labels = tuple(item.value for item in right_assignments)
    left_partition = ClusterPartitionSummary.from_memberships(
        left,
        declared_group_count=left_declared_group_count,
    )
    right_partition = ClusterPartitionSummary.from_memberships(
        right,
        declared_group_count=right_declared_group_count,
    )
    return ClusterStabilityResult(
        adjusted_rand_index=CorrelationCoefficient(
            adjusted_rand_score(
                tuple(label.value for label in left_labels),
                tuple(label.value for label in right_labels),
            )
        ),
        compared_clients=left_clients,
        left_memberships=left,
        right_memberships=right,
        left_partition=left_partition,
        right_partition=right_partition,
        contingency=_contingency(
            left_labels,
            right_labels,
            GroupCount(len(left_partition.group_sizes)),
            GroupCount(len(right_partition.group_sizes)),
        ),
    )


def cluster_assignment_switch_frequencies(
    records: tuple[ClusterEvidenceRecord, ...],
) -> ClusterAssignmentSwitchSummary:
    ordered = tuple(sorted(records, key=lambda record: record.seed.value))
    if len(ordered) < 2:
        raise ValueError("cluster switch reporting requires at least two seed records")
    if len({record.seed for record in ordered}) != len(ordered):
        raise ValueError("cluster switch reporting requires unique seeds")
    reference = ordered[0]
    reference_assignments = _assignment_by_client(reference.memberships)
    reference_clients = tuple(sorted(reference_assignments, key=lambda client: client.client_id.value))
    group_count = len(reference.partition.group_sizes)
    switches = {client: 0 for client in reference_clients}
    for record in ordered[1:]:
        target_assignments = _assignment_by_client(record.memberships)
        if tuple(sorted(target_assignments, key=lambda client: client.client_id.value)) != reference_clients:
            raise ValueError("cluster switch reporting requires identical client memberships across seeds")
        if len(record.partition.group_sizes) != group_count:
            raise ValueError("cluster switch reporting requires identical declared cluster counts across seeds")
        label_mapping = _align_cluster_labels(reference_assignments, target_assignments, group_count)
        for client in reference_clients:
            if label_mapping[target_assignments[client].value] != reference_assignments[client].value:
                switches[client] += 1
    comparisons = PairedObservationCount(len(ordered) - 1)
    return ClusterAssignmentSwitchSummary(
        reference_seed=reference.seed,
        compared_seeds=tuple(record.seed for record in ordered[1:]),
        client_frequencies=tuple(
            ClusterAssignmentSwitchFrequency(
                client=client,
                switched_seed_count=PairedObservationCount(switches[client]),
                comparison_seed_count=comparisons,
                frequency=Ratio(switches[client] / comparisons.value),
            )
            for client in reference_clients
        ),
    )


def _assignment_by_client(memberships: tuple[ClusterMembership, ...]) -> dict[ClientIdentity, ClusterIndex]:
    return {item.client: item.value for item in _cluster_assignments(memberships)}


def _align_cluster_labels(
    reference: dict[ClientIdentity, ClusterIndex],
    target: dict[ClientIdentity, ClusterIndex],
    group_count: int,
) -> tuple[int, ...]:
    return max(
        permutations(range(group_count)),
        key=lambda mapping: (
            sum(mapping[target[client].value] == reference[client].value for client in reference),
            tuple(-value for value in mapping),
        ),
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
        ClientOwned(client=client, value=membership.cluster_index)
        for membership in memberships
        for client in membership.members
    )
    if not assignments:
        raise ValueError("cluster stability requires at least one persisted client")
    if len({item.client for item in assignments}) != len(assignments):
        raise ValueError("each client must belong to exactly one cluster")
    return tuple(sorted(assignments, key=lambda item: item.client))


def _contingency(
    left_labels: tuple[ClusterIndex, ...],
    right_labels: tuple[ClusterIndex, ...],
    left_group_count: GroupCount,
    right_group_count: GroupCount,
) -> ClusterContingencyMatrix:
    return ClusterContingencyMatrix(
        rows=tuple(
            ClusterContingencyRow(
                left_cluster_index=ClusterIndex(left_index),
                counts_by_right_cluster=tuple(
                    PairedObservationCount(
                        sum(
                            left_label.value == left_index and right_label.value == right_index
                            for left_label, right_label in zip(
                                left_labels,
                                right_labels,
                                strict=True,
                            )
                        )
                    )
                    for right_index in range(right_group_count.value)
                ),
            )
            for left_index in range(left_group_count.value)
        )
    )

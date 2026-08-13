from types import SimpleNamespace
from typing import cast

from tests.unit.thresholding.helpers import COORDINATE, identity

from datp_core.analysis.mechanisms.clustering import (
    ClusterEvidenceRecord,
    ClusterPartitionSummary,
    cluster_assignment_switch_frequencies,
    cluster_silhouette_from_grouped_result,
    cluster_stability,
)
from datp_core.core.identifiers import AvailabilityStatus
from datp_core.core.numeric import (
    ClusterIndex,
    DistributionSkewness,
    GroupCount,
    MetricValue,
    Quantile,
    RowCount,
    ScoreMoment,
    Seed,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.presentation.export import (
    _render_cluster_assignment_switch_summary,
    _render_cluster_silhouette_result,
    _render_cluster_stability_result,
)
from datp_core.thresholds.contracts import LocalQuantile, ThresholdDiagnostic
from datp_core.thresholds.policies.cluster import (
    ClusterFingerprint,
    ClusterMembership,
    FingerprintFeatures,
    GroupedThresholdResult,
)


def _membership(index: int, client_name: str, threshold: float) -> ClusterMembership:
    client = identity(client_name)
    quantile = LocalQuantile(
        client=client,
        coordinate=COORDINATE,
        quantile=Quantile(0.95),
        value=ThresholdValue(threshold),
        calibration_count=RowCount(10),
        diagnostic=ThresholdDiagnostic(
            quantile_interpolation=None,
            tie_count=RowCount(0),
            availability=AvailabilityStatus.AVAILABLE,
        ),
    )
    return ClusterMembership(
        cluster_index=ClusterIndex(index),
        members=(client,),
        contributing_local_quantiles=(quantile,),
        cluster_threshold=ThresholdValue(threshold),
    )


def test_cluster_stability_retains_and_renders_complete_partition_evidence() -> None:
    left = (_membership(0, "client_a", 0.1), _membership(1, "client_b", 0.2))
    right = (_membership(0, "client_b", 0.2), _membership(1, "client_a", 0.1))

    result = cluster_stability(
        left,
        right,
        left_declared_group_count=GroupCount(3),
        right_declared_group_count=GroupCount(3),
    )

    assert result.left_memberships == left
    assert result.right_memberships == right
    assert tuple(str(line) for line in _render_cluster_stability_result(result)) == (
        "ARI: 1.000",
        "Clients: 2",
        "Left cluster sizes: 1, 1, 0",
        "Right cluster sizes: 1, 1, 0",
        "Left empty groups: 2",
        "Right empty groups: 2",
        "Left singleton groups: 0, 1",
        "Right singleton groups: 0, 1",
        "Left memberships: 0:client_a; 1:client_b",
        "Right memberships: 0:client_b; 1:client_a",
    )


def test_cluster_switch_frequency_aligns_labels_to_the_smallest_seed() -> None:
    reference = (_membership(0, "client_a", 0.1), _membership(1, "client_b", 0.2))
    relabeled_same_partition = (_membership(0, "client_b", 0.2), _membership(1, "client_a", 0.1))
    changed_partition = (_membership(0, "client_a", 0.1), _membership(0, "client_b", 0.2))

    records = tuple(
        ClusterEvidenceRecord.model_construct(
            seed=Seed(seed),
            memberships=memberships,
            partition=ClusterPartitionSummary.from_memberships(
                memberships,
                declared_group_count=GroupCount(3),
            ),
        )
        for seed, memberships in ((7, relabeled_same_partition), (2, reference), (9, changed_partition))
    )

    summary = cluster_assignment_switch_frequencies(records)

    assert summary.reference_seed == Seed(2)
    assert summary.compared_seeds == (Seed(7), Seed(9))
    assert tuple(item.switched_seed_count.value for item in summary.client_frequencies) == (0, 1)
    assert tuple(item.frequency.value for item in summary.client_frequencies) == (0.0, 0.5)
    assert tuple(str(line) for line in _render_cluster_assignment_switch_summary(summary)) == (
        "Reference seed: 2",
        "Compared seeds: 7, 9",
        "Client client_a: switches=0/2; frequency=0.000",
        "Client client_b: switches=1/2; frequency=0.500",
    )


def test_cluster_silhouette_uses_standardized_fingerprints_and_singleton_zero() -> None:
    client_a, client_b, client_c = (identity(name) for name in ("client_a", "client_b", "client_c"))
    clusters = (
        ClusterMembership(
            cluster_index=ClusterIndex(0),
            members=(client_a, client_b),
            contributing_local_quantiles=(_local_quantile(client_a, 0.1), _local_quantile(client_b, 0.2)),
            cluster_threshold=ThresholdValue(0.15000000000000002),
        ),
        ClusterMembership(
            cluster_index=ClusterIndex(1),
            members=(client_c,),
            contributing_local_quantiles=(_local_quantile(client_c, 0.9),),
            cluster_threshold=ThresholdValue(0.9),
        ),
    )
    result = _cluster_result(
        clusters,
        ((client_a, 0.0), (client_b, 1.0), (client_c, 10.0)),
    )

    silhouette = cluster_silhouette_from_grouped_result(result)

    assert silhouette.mean_silhouette is not None
    by_client = {item.client.client_id.value: item.value for item in silhouette.observations}
    assert by_client["client_c"] == MetricValue(0.0)
    assert by_client["client_a"] is not None and by_client["client_a"].value > 0.8
    assert "Mean silhouette:" in str(_render_cluster_silhouette_result(silhouette)[1])


def test_cluster_silhouette_is_unavailable_with_one_nonempty_cluster() -> None:
    membership = _membership(0, "client_a", 0.1)
    result = _cluster_result((membership,), ((membership.members[0], 0.0),))

    silhouette = cluster_silhouette_from_grouped_result(result)

    assert silhouette.mean_silhouette is None
    assert silhouette.unavailable_reason is not None
    assert silhouette.observations[0].value is None


def _local_quantile(client, value: float) -> LocalQuantile:
    return LocalQuantile(
        client=client,
        coordinate=COORDINATE,
        quantile=Quantile(0.95),
        value=ThresholdValue(value),
        calibration_count=RowCount(10),
        diagnostic=ThresholdDiagnostic(
            quantile_interpolation=None,
            tie_count=RowCount(0),
            availability=AvailabilityStatus.AVAILABLE,
        ),
    )


def _cluster_result(
    clusters: tuple[ClusterMembership, ...],
    standardized_means: tuple[tuple[ClientIdentity, float], ...],
) -> GroupedThresholdResult:
    return cast(
        GroupedThresholdResult,
        SimpleNamespace(
            coordinate=COORDINATE,
            clusters=clusters,
            fingerprints=tuple(
                ClusterFingerprint(
                    client=client,
                    raw=_features(0.0),
                    standardized=_features(value),
                )
                for client, value in standardized_means
            ),
        ),
    )


def _features(value: float) -> FingerprintFeatures:
    return FingerprintFeatures(
        mean=ScoreMoment(value),
        standard_deviation=ScoreMoment(0.0),
        skewness=DistributionSkewness(0.0),
        p95=ThresholdValue(0.0),
    )

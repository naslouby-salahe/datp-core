from tests.unit.thresholding.helpers import COORDINATE, identity

from datp_core.analysis.mechanisms.clustering import cluster_stability
from datp_core.core.identifiers import AvailabilityStatus
from datp_core.core.numeric import ClusterIndex, GroupCount, Quantile, RowCount, ThresholdValue
from datp_core.presentation.export import _render_cluster_stability_result
from datp_core.thresholds.contracts import LocalQuantile, ThresholdDiagnostic
from datp_core.thresholds.policies.cluster import ClusterMembership


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

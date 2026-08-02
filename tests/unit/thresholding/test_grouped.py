import numpy as np
import pytest
from scipy.stats import skew
from tests.unit.thresholding.helpers import client_scores

from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import GroupCount, Seed
from datp_core.protocols.calibration import CLUSTER_THRESHOLD_PROTOCOL
from datp_core.protocols.models import ClusterThresholdProtocol
from datp_core.thresholding.grouped import _raw_fingerprint, construct_grouped_threshold


def _clients() -> tuple:
    generator = np.random.default_rng(0)
    return tuple(
        client_scores(f"client_{index}", tuple(float(v) for v in generator.normal(loc=index * 10, size=30)))
        for index in range(6)
    )


def test_construct_grouped_threshold_produces_the_locked_group_count() -> None:
    clients = _clients()
    result = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    assert len(result.clusters) == CLUSTER_THRESHOLD_PROTOCOL.group_count.value
    assert {member for cluster in result.clusters for member in cluster.members} == {item.client for item in clients}


def test_construct_grouped_threshold_is_deterministic_across_repeated_runs() -> None:
    clients = _clients()
    first = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    second = construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)
    first_assignment = {a.client.client_id: a.threshold.value for a in first.assignments}
    second_assignment = {a.client.client_id: a.threshold.value for a in second.assignments}
    assert first_assignment == second_assignment


def test_construct_grouped_threshold_rejects_group_count_at_or_above_eligible_population() -> None:
    clients = tuple(
        client_scores(f"client_{i}", (1.0, 2.0, 3.0)) for i in range(CLUSTER_THRESHOLD_PROTOCOL.group_count.value)
    )

    def call():
        return construct_grouped_threshold(clients, CLUSTER_THRESHOLD_PROTOCOL)

    with pytest.raises(ScientificContractError, match="more eligible clients than the declared group count"):
        call()


def test_raw_fingerprint_produces_mean_std_skew_p95_in_locked_order() -> None:
    scores = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    mean, standard_deviation, skewness, p95 = _raw_fingerprint(scores)
    assert mean == float(np.mean(scores))
    assert standard_deviation == float(np.std(scores, ddof=0))
    assert skewness == float(skew(scores, bias=True))
    assert p95 == float(np.quantile(scores, 0.95, method="linear"))


def _protocol_with_override(
    *, group_count: GroupCount | None = None, random_state: Seed | None = None
) -> ClusterThresholdProtocol:
    return ClusterThresholdProtocol(
        method=CLUSTER_THRESHOLD_PROTOCOL.method,
        quantile=CLUSTER_THRESHOLD_PROTOCOL.quantile,
        fingerprint_features=CLUSTER_THRESHOLD_PROTOCOL.fingerprint_features,
        feature_standardization=CLUSTER_THRESHOLD_PROTOCOL.feature_standardization,
        assignment_algorithm=CLUSTER_THRESHOLD_PROTOCOL.assignment_algorithm,
        initialization=CLUSTER_THRESHOLD_PROTOCOL.initialization,
        initialization_count=CLUSTER_THRESHOLD_PROTOCOL.initialization_count,
        maximum_iterations=CLUSTER_THRESHOLD_PROTOCOL.maximum_iterations,
        random_state=random_state if random_state is not None else CLUSTER_THRESHOLD_PROTOCOL.random_state,
        group_count=group_count if group_count is not None else CLUSTER_THRESHOLD_PROTOCOL.group_count,
        threshold_aggregation=CLUSTER_THRESHOLD_PROTOCOL.threshold_aggregation,
    )


def test_cluster_threshold_protocol_rejects_non_locked_group_count() -> None:
    def build() -> ClusterThresholdProtocol:
        return _protocol_with_override(group_count=GroupCount(9))

    with pytest.raises(ValueError, match="locked group count"):
        build()


def test_cluster_threshold_protocol_rejects_non_locked_random_state() -> None:
    def build() -> ClusterThresholdProtocol:
        return _protocol_with_override(random_state=Seed(7))

    with pytest.raises(ValueError, match="locked seed"):
        build()


def test_raw_fingerprint_constant_scores_produces_zero_skewness() -> None:
    scores = np.array([5.0, 5.0, 5.0, 5.0])
    mean, standard_deviation, skewness, p95 = _raw_fingerprint(scores)
    assert standard_deviation == 0.0
    assert skewness == 0.0


def test_construct_grouped_threshold_rejects_non_finite_fingerprint_matrix() -> None:
    with pytest.raises(ScientificContractError, match="finite"):
        client_scores("client_b", (float("nan"), float("nan"), float("nan")))

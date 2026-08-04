import numpy as np
from tests.unit.thresholding.helpers import client_scores

from datp_core.domain.values import Quantile
from datp_core.protocols.calibration import FEDERATED_STATISTICS_PROTOCOL
from datp_core.thresholding.federated_benign_statistics import construct_federated_benign_statistics

QUANTILE = Quantile(0.95)


def _homogeneous_clients() -> tuple:
    generator = np.random.default_rng(0)
    scores = tuple(float(v) for v in generator.normal(loc=0.0, scale=1.0, size=200))
    return (
        client_scores("client_a", scores[:100]),
        client_scores("client_b", scores[100:]),
    )


def _heterogeneous_clients() -> tuple:
    generator = np.random.default_rng(0)
    low = tuple(float(v) for v in generator.normal(loc=0.0, scale=1.0, size=100))
    high = tuple(float(v) for v in generator.normal(loc=50.0, scale=1.0, size=100))
    return (client_scores("client_a", low), client_scores("client_b", high))


def test_decomposition_between_term_is_zero_when_client_means_are_equal() -> None:
    generator = np.random.default_rng(1)
    shared_scores = tuple(float(v) for v in generator.normal(loc=5.0, scale=1.0, size=200))
    clients = (client_scores("client_a", shared_scores), client_scores("client_b", shared_scores))
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    assert abs(result.decomposition.between_client_variance) < 1e-9


def test_decomposition_between_term_is_mandatory_and_positive_for_heterogeneous_clients() -> None:
    clients = _heterogeneous_clients()
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    assert result.decomposition.between_client_variance > 0
    assert result.decomposition.full_pooled_variance == (
        result.decomposition.within_client_variance + result.decomposition.between_client_variance
    )


def test_fixed_coefficient_curve_matches_the_declared_supplementary_coefficients() -> None:
    clients = _homogeneous_clients()
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    coefficients_seen = {item.coefficient.value for item in result.fixed_coefficient_curve}
    assert coefficients_seen == {coefficient.value for coefficient in FEDERATED_STATISTICS_PROTOCOL.coefficients}


def test_fixed_coefficient_curve_is_never_the_matched_threshold() -> None:
    clients = _heterogeneous_clients()
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    fixed_values = {item.threshold.value for item in result.fixed_coefficient_curve}
    assert result.matched_threshold.value not in fixed_values


def test_client_summaries_never_carry_a_benign_exceedance_count_for_this_construction() -> None:
    clients = _homogeneous_clients()
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    assert all(summary.benign_exceedance_count is None for summary in result.client_summaries)


def test_estimated_communication_bytes_count_three_float64_scalars_per_client() -> None:
    # Each client reports exactly count, mean, and variance for this construction
    # (never a benign_exceedance_count — see the dedicated test above), so the
    # estimate is deterministic: clients * 3 scalars * 8 bytes (float64).
    clients = _homogeneous_clients()
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    assert result.estimated_communication_bytes.value == len(clients) * 3 * 8

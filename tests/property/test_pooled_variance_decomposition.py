from hypothesis import given
from hypothesis import strategies as st
from tests.unit.thresholding.helpers import client_scores

from datp_core.domain.values import Quantile
from datp_core.protocols.calibration import FEDERATED_STATISTICS_PROTOCOL
from datp_core.thresholding.methods.federated_statistics import construct_federated_benign_statistics

QUANTILE = Quantile(0.95)
_SCORE = st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False)


@given(
    scores_a=st.lists(_SCORE, min_size=2, max_size=15),
    scores_b=st.lists(_SCORE, min_size=2, max_size=15),
)
def test_full_pooled_variance_always_equals_within_plus_between(scores_a: list[float], scores_b: list[float]) -> None:
    clients = (
        client_scores("client_a", tuple(scores_a)),
        client_scores("client_b", tuple(scores_b)),
    )
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    decomposition = result.decomposition
    assert decomposition.full_pooled_variance == (
        decomposition.within_client_variance + decomposition.between_client_variance
    )
    assert decomposition.within_client_variance >= 0
    assert decomposition.between_client_variance >= 0


@given(scores=st.lists(_SCORE, min_size=2, max_size=15))
def test_between_client_variance_vanishes_when_every_client_shares_the_same_scores(scores: list[float]) -> None:
    clients = (
        client_scores("client_a", tuple(scores)),
        client_scores("client_b", tuple(scores)),
    )
    result = construct_federated_benign_statistics(clients, FEDERATED_STATISTICS_PROTOCOL, QUANTILE)
    assert abs(result.decomposition.between_client_variance) < 1e-6

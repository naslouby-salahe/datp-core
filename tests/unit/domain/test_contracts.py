from datp_core.domain.contracts import CentralizedThresholdEstimator, FederatedThresholdEstimator


class Federated:
    def estimate_federated(self, scores: tuple[object, ...]) -> object:
        return scores


class Centralized:
    def estimate_centralized(self, scores: object) -> object:
        return scores


def test_threshold_protocols_are_distinct() -> None:
    assert isinstance(Federated(), FederatedThresholdEstimator)
    assert not isinstance(Federated(), CentralizedThresholdEstimator)
    assert isinstance(Centralized(), CentralizedThresholdEstimator)

"""Flower strategy configuration tests."""

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import TrainingProfileId
from datp_core.infrastructure.federation.flower_adapter import build_flower_strategy_from_profile


def test_fedavg_strategy_uses_authored_participation_contract() -> None:
    profile = build_application().config.training_profiles.get(TrainingProfileId("federated_averaging"))
    strategy = build_flower_strategy_from_profile(profile)
    federation = profile.federation
    assert federation is not None
    assert strategy.fraction_fit == federation.fraction_fit
    assert strategy.min_available_clients == federation.minimum_available_clients.value

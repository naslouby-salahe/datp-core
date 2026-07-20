"""Flower federated learning strategy coordination adapter."""

from __future__ import annotations

import flwr as fl

from datp_core.domain.catalogue import FederationProfileRecord, TrainingProfileRecord


class DatpFedAvgStrategy(fl.server.strategy.FedAvg):
    """Custom FedAvg Flower strategy for DATP client model aggregation with explicit profile configuration."""

    def __init__(
        self,
        federation: FederationProfileRecord,
        training_profile: TrainingProfileRecord,
    ) -> None:
        super().__init__(
            fraction_fit=federation.fraction_fit,
            fraction_evaluate=federation.fraction_evaluate,
            min_fit_clients=federation.minimum_fit_clients.value,
            min_evaluate_clients=federation.minimum_evaluate_clients.value,
            min_available_clients=federation.minimum_available_clients.value,
        )
        self._training_profile = training_profile


def build_flower_strategy_from_profile(profile: TrainingProfileRecord) -> DatpFedAvgStrategy:
    """Build concrete Flower strategy from resolved DATP training profile."""
    if profile.federation is None:
        raise ValueError(f"Training profile '{profile.kind}' has no Flower federation configuration")
    return DatpFedAvgStrategy(federation=profile.federation, training_profile=profile)

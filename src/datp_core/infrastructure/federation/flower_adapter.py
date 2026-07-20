"""Flower federated learning strategy coordination adapter."""

from __future__ import annotations

from typing import Any

import flwr as fl


class DatpFedAvgStrategy(fl.server.strategy.FedAvg):
    """Custom FedAvg Flower strategy for DATP client model aggregation."""

    def __init__(self, fraction_fit: float = 1.0, min_fit_clients: int = 1, **kwargs: Any) -> None:
        super().__init__(
            fraction_fit=fraction_fit,
            min_fit_clients=min_fit_clients,
            min_available_clients=min_fit_clients,
            **kwargs,
        )

"""Result records for locked training-coefficient selection (FedProx mu, Ditto weight)."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class FederatedProximalSelectionResult:
    analysis_label: str
    selected_proximal_mu: float
    locked_primary_round: int | None
    mean_benign_calibration_loss_by_mu: Mapping[str, float] | None


@define(frozen=True, slots=True, kw_only=True)
class DittoSelectionResult:
    analysis_label: str
    selected_ditto_proximal_weight: float
    locked_primary_round: int | None
    mean_benign_calibration_loss_by_weight: Mapping[str, float] | None


__all__ = ["DittoSelectionResult", "FederatedProximalSelectionResult"]

"""Decode planner-supplied current-run training-coefficient selections."""

from __future__ import annotations

import json

from datp_core.analysis.selection.models import DittoSelectionResult, FederatedProximalSelectionResult


def federated_proximal_selection(payload_bytes: bytes) -> FederatedProximalSelectionResult:
    payload = json.loads(payload_bytes)
    if not isinstance(payload, dict) or not isinstance(payload.get("selected_proximal_mu"), (int, float)):
        raise ValueError("FedProx coefficient-selection artifact is malformed")
    locked_primary_round = payload.get("locked_primary_round")
    losses = payload.get("mean_benign_calibration_loss_by_mu")
    return FederatedProximalSelectionResult(
        analysis_label="fedprox_primary_coefficient_selection",
        selected_proximal_mu=float(payload["selected_proximal_mu"]),
        locked_primary_round=None if locked_primary_round is None else int(locked_primary_round),
        mean_benign_calibration_loss_by_mu=None if losses is None else {str(k): float(v) for k, v in losses.items()},
    )


def ditto_selection(payload_bytes: bytes) -> DittoSelectionResult:
    payload = json.loads(payload_bytes)
    selected_weight = payload.get("selected_ditto_proximal_weight") if isinstance(payload, dict) else None
    if not isinstance(selected_weight, (int, float)):
        raise ValueError("Ditto weight-selection artifact is malformed")
    locked_primary_round = payload.get("locked_primary_round")
    losses = payload.get("mean_benign_calibration_loss_by_weight")
    return DittoSelectionResult(
        analysis_label="ditto_primary_proximal_weight_selection",
        selected_ditto_proximal_weight=float(selected_weight),
        locked_primary_round=None if locked_primary_round is None else int(locked_primary_round),
        mean_benign_calibration_loss_by_weight=None
        if losses is None
        else {str(k): float(v) for k, v in losses.items()},
    )


__all__ = ["ditto_selection", "federated_proximal_selection"]

"""Training-coefficient selection from checkpoint-selection artifacts."""

from __future__ import annotations

import json

from attrs import define

from datp_core.analysis.errors import ArtifactSchemaViolationError


@define(frozen=True, slots=True, kw_only=True)
class CalibrationLossEntry:
    """One (key, loss) observation from a selection artifact."""

    configuration_key: str
    mean_benign_calibration_loss: float


@define(frozen=True, slots=True, kw_only=True)
class FederatedProximalSelectionResult:
    analysis_label: str
    selected_proximal_mu: float
    locked_primary_round: int | None
    calibration_losses: tuple[CalibrationLossEntry, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class DittoSelectionResult:
    analysis_label: str
    selected_ditto_proximal_weight: float
    locked_primary_round: int | None
    calibration_losses: tuple[CalibrationLossEntry, ...] | None


def federated_proximal_selection(payload_bytes: bytes) -> FederatedProximalSelectionResult:
    payload = json.loads(payload_bytes)
    if not isinstance(payload, dict) or not isinstance(payload.get("selected_proximal_mu"), (int, float)):
        raise ArtifactSchemaViolationError("FedProx coefficient-selection artifact is malformed")
    locked_primary_round = payload.get("locked_primary_round")
    losses = payload.get("mean_benign_calibration_loss_by_mu")
    return FederatedProximalSelectionResult(
        analysis_label="fedprox_primary_coefficient_selection",
        selected_proximal_mu=float(payload["selected_proximal_mu"]),
        locked_primary_round=None if locked_primary_round is None else int(locked_primary_round),
        calibration_losses=None
        if losses is None
        else tuple(
            CalibrationLossEntry(configuration_key=str(k), mean_benign_calibration_loss=float(v))
            for k, v in losses.items()
        ),
    )


def ditto_selection(payload_bytes: bytes) -> DittoSelectionResult:
    payload = json.loads(payload_bytes)
    selected_weight = payload.get("selected_ditto_proximal_weight") if isinstance(payload, dict) else None
    if not isinstance(selected_weight, (int, float)):
        raise ArtifactSchemaViolationError("Ditto weight-selection artifact is malformed")
    locked_primary_round = payload.get("locked_primary_round")
    losses = payload.get("mean_benign_calibration_loss_by_weight")
    return DittoSelectionResult(
        analysis_label="ditto_primary_proximal_weight_selection",
        selected_ditto_proximal_weight=float(selected_weight),
        locked_primary_round=None if locked_primary_round is None else int(locked_primary_round),
        calibration_losses=None
        if losses is None
        else tuple(
            CalibrationLossEntry(configuration_key=str(k), mean_benign_calibration_loss=float(v))
            for k, v in losses.items()
        ),
    )

"""Locked training-coefficient selection lookups: the FedProx primary mu and Ditto primary
proximal weight, each read from a previously committed selection artifact."""

from __future__ import annotations

import json

from datp_core.analysis.artifact_access.reader import read_artifact_bytes
from datp_core.analysis.selection.models import DittoSelectionResult, FederatedProximalSelectionResult
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.identity import IdentityBuilder
from datp_core.pipeline.stages.context import StageJobContext


def federated_proximal_selection(
    experiment_id: ExperimentId, *, config: ResolvedProjectConfiguration, repository: ArtifactRepository
) -> FederatedProximalSelectionResult:
    context = StageJobContext(experiment_id=experiment_id)
    payload = json.loads(
        read_artifact_bytes(
            repository,
            experiment_id,
            IdentityBuilder.federated_proximal_selection_node_key(context),
            missing_message="FedProx coefficient-selection artifact is unreadable",
        )
    )
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


def ditto_selection(
    experiment_id: ExperimentId, *, config: ResolvedProjectConfiguration, repository: ArtifactRepository
) -> DittoSelectionResult:
    source = config.primary_ditto_selection_experiment()
    context = StageJobContext(experiment_id=source.identifier)
    payload = json.loads(
        read_artifact_bytes(
            repository,
            source.identifier,
            IdentityBuilder.ditto_selection_node_key(context),
            missing_message="Ditto weight-selection artifact is unreadable",
        )
    )
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

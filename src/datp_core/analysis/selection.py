"""Training-coefficient selection from checkpoint-selection artifacts."""

from __future__ import annotations

from datp_core.analysis.contracts import (
    CheckpointSelectionArtifact,
    DittoSelectionResult,
    FederatedProximalSelectionResult,
)
from datp_core.analysis.errors import ArtifactSchemaViolationError
from datp_core.core.identifiers import AnalysisLabel


def federated_proximal_selection(artifact: CheckpointSelectionArtifact) -> FederatedProximalSelectionResult:
    """Parse checkpoint selection artifact into FederatedProximalSelectionResult."""
    if artifact.selected_proximal_mu is None:
        raise ArtifactSchemaViolationError("FedProx coefficient-selection artifact is malformed")
    return FederatedProximalSelectionResult(
        analysis_label=AnalysisLabel("fedprox_primary_coefficient_selection"),
        selected_proximal_mu=artifact.selected_proximal_mu,
        locked_primary_round=artifact.locked_primary_round,
        calibration_losses=artifact.federated_proximal_losses or None,
    )


def ditto_selection(artifact: CheckpointSelectionArtifact) -> DittoSelectionResult:
    """Parse checkpoint selection artifact into DittoSelectionResult."""
    if artifact.selected_ditto_proximal_weight is None:
        raise ArtifactSchemaViolationError("Ditto weight-selection artifact is malformed")
    return DittoSelectionResult(
        analysis_label=AnalysisLabel("ditto_primary_proximal_weight_selection"),
        selected_ditto_proximal_weight=artifact.selected_ditto_proximal_weight,
        locked_primary_round=artifact.locked_primary_round,
        calibration_losses=artifact.ditto_losses or None,
    )

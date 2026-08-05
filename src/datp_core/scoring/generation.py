"""Temporary score-service import surface pending caller migration."""

from datp_core.pipeline.scoring.service import (
    ClientScoringInput,
    FederatedScoreAssetName,
    PersistedScoreFrame,
    ScoreGenerationRequest,
    federated_scoring_is_reusable,
    generate_federated_scores,
    load_checkpoint_model,
    load_reused_federated_scores,
    rebase_federated_scores,
    score_and_persist_autoencoder_frame,
    write_federated_scores,
)

__all__ = (
    "ClientScoringInput",
    "FederatedScoreAssetName",
    "PersistedScoreFrame",
    "ScoreGenerationRequest",
    "federated_scoring_is_reusable",
    "generate_federated_scores",
    "load_checkpoint_model",
    "load_reused_federated_scores",
    "rebase_federated_scores",
    "score_and_persist_autoencoder_frame",
    "write_federated_scores",
)

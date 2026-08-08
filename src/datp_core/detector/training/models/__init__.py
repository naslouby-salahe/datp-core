"""Typed immutable contracts for federated autoencoder training."""

from datp_core.detector.training.contracts import DittoTrainingCoordinates, FederatedTrainingCoordinate
from datp_core.detector.training.models.checkpoints import (
    CheckpointCandidate,
    CheckpointDecision,
    DittoTrainingOutcome,
    FederatedTrainingExecution,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    PersonalizedCandidateSet,
)
from datp_core.detector.training.models.records import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingHistory,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
    PreparedClientProvenance,
    validate_client_preprocessing_match,
)
from datp_core.detector.training.models.snapshots import PersonalizedSnapshotSet, RoundSnapshot

__all__ = (
    "CheckpointCandidate",
    "CheckpointDecision",
    "ClientTrainingInput",
    "ClientTrainingResult",
    "ClientUpdate",
    "CommunicationRecord",
    "DittoTrainingCoordinates",
    "DittoTrainingOutcome",
    "FederatedRoundResult",
    "FederatedTrainingCoordinate",
    "FederatedTrainingExecution",
    "FederatedTrainingHistory",
    "FederatedTrainingOutcome",
    "FederatedTrainingResult",
    "GlobalModelStateReference",
    "PersonalizedCandidateSet",
    "PersonalizedModelStateReference",
    "PersonalizedSnapshotSet",
    "PreparedClientProvenance",
    "RoundSnapshot",
    "validate_client_preprocessing_match",
)

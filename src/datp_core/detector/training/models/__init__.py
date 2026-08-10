"""Typed immutable contracts for federated autoencoder training."""

from datp_core.detector.training.contracts import DittoTrainingCoordinates, FederatedTrainingCoordinate
from datp_core.detector.training.models.checkpoints import (
    DittoTrainingOutcome,
    FederatedTrainingExecution,
    FederatedTrainingResult,
    PersonalizedTerminalModel,
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
    validate_client_preprocessing_match,
)

__all__ = (
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
    "FederatedTrainingResult",
    "GlobalModelStateReference",
    "PersonalizedTerminalModel",
    "PersonalizedModelStateReference",
    "validate_client_preprocessing_match",
)

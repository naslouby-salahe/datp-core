"""Training profile contracts — pure resolved training profiles and federation contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import TrainingProfileId
from datp_core.core.numbers import PositiveInt
from datp_core.learning.contracts.enums import (
    CheckpointAuthorization,
    PersonalizationStrategy,
    TrainingParticipation,
    TrainingProfileKind,
)


class FederationProfileRecord(BaseModel):
    """Pure resolved Flower participation contract."""

    model_config = ConfigDict(frozen=True)

    fraction_fit: float
    fraction_evaluate: float
    minimum_fit_clients: PositiveInt
    minimum_evaluate_clients: PositiveInt
    minimum_available_clients: PositiveInt


class TrainingProfileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: TrainingProfileId
    kind: TrainingProfileKind
    model_architecture_id: str
    optimizer_id: str
    batching_profile_id: str
    local_epochs: PositiveInt | None
    participation: TrainingParticipation | None
    checkpoint_authorization: CheckpointAuthorization
    personalization: PersonalizationStrategy | None
    personalized_local_epochs: PositiveInt | None
    personalization_parameter_grid: tuple[float, ...] | None
    proximal_objective: str | None
    mu_grid: tuple[float, ...] | None
    mu_zero_forbidden_as_a_fedprox_condition: bool | None
    federation: FederationProfileRecord | None

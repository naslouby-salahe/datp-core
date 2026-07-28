"""Training and seed contracts with invalid states removed."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, model_validator

from datp_core.core.identifiers import SeedCohortId, TrainingProfileId
from datp_core.core.seeding import Seed
from datp_core.learning.contracts.enums import (
    CheckpointAuthorization,
    ParticipationPolicy,
    SeedAnalysisModel,
    TrainingAlgorithm,
)
from datp_core.learning.contracts.model import IdentifierText


class FullParticipationProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy: Literal[ParticipationPolicy.FULL]
    minimum_available_clients: PositiveInt


class BaseTrainingProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: TrainingProfileId
    model_architecture_id: IdentifierText
    optimizer_id: IdentifierText
    batching_profile_id: IdentifierText
    checkpoint_authorization: CheckpointAuthorization


class CentralizedTrainingProfile(BaseTrainingProfile):
    algorithm: Literal[TrainingAlgorithm.CENTRALIZED]
    local_epochs: PositiveInt


class FedAvgTrainingProfile(BaseTrainingProfile):
    algorithm: Literal[TrainingAlgorithm.FEDAVG]
    local_epochs: PositiveInt
    participation: FullParticipationProfile


class FedProxTrainingProfile(BaseTrainingProfile):
    algorithm: Literal[TrainingAlgorithm.FEDPROX]
    local_epochs: PositiveInt
    participation: FullParticipationProfile
    proximal_coefficients: tuple[PositiveFloat, ...]

    @model_validator(mode="after")
    def validate_coefficients(self) -> FedProxTrainingProfile:
        if not self.proximal_coefficients:
            raise ValueError("FedProx requires at least one strictly positive proximal coefficient")
        if len(set(self.proximal_coefficients)) != len(self.proximal_coefficients):
            raise ValueError("FedProx proximal coefficients must be unique")
        return self


class DittoTrainingProfile(BaseTrainingProfile):
    algorithm: Literal[TrainingAlgorithm.DITTO]
    global_local_epochs: PositiveInt
    personalized_local_epochs: PositiveInt
    participation: FullParticipationProfile
    personalization_weights: tuple[PositiveFloat, ...]

    @model_validator(mode="after")
    def validate_weights(self) -> DittoTrainingProfile:
        if not self.personalization_weights:
            raise ValueError("Ditto requires at least one strictly positive personalization weight")
        if len(set(self.personalization_weights)) != len(self.personalization_weights):
            raise ValueError("Ditto personalization weights must be unique")
        return self


TrainingProfile = Annotated[
    CentralizedTrainingProfile | FedAvgTrainingProfile | FedProxTrainingProfile | DittoTrainingProfile,
    Field(discriminator="algorithm"),
]


class SeedCohortProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: SeedCohortId
    paired_seed_count: PositiveInt
    training_seeds: tuple[Seed, ...]
    bootstrap_analysis_seed: Seed
    analysis_seed_model: Literal[SeedAnalysisModel.PAIRED]

    @model_validator(mode="after")
    def validate_seed_cohort(self) -> SeedCohortProfile:
        if len(self.training_seeds) != int(self.paired_seed_count):
            raise ValueError("Paired seed count must equal the number of configured training seeds")
        if len(set(self.training_seeds)) != len(self.training_seeds):
            raise ValueError("Training seeds must be unique")
        return self

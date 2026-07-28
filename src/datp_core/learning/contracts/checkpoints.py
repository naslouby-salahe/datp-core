"""Checkpoint profile and evidence contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PositiveFloat, PositiveInt, model_validator

from datp_core.core.identifiers import CheckpointProfileId
from datp_core.core.seeding import Seed
from datp_core.learning.contracts.enums import (
    CheckpointSavePolicy,
    CheckpointSelectionKind,
    CheckpointTieBreak,
    LoaderBranch,
    NoQualifyingRoundPolicy,
    TrainingAlgorithm,
)


class FirstQualifyingConvergenceSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[CheckpointSelectionKind.FIRST_QUALIFYING_CONVERGENCE]
    initial_rounds: PositiveInt
    window_rounds: PositiveInt
    relative_loss_tolerance: PositiveFloat
    tie_break: Literal[CheckpointTieBreak.EARLIEST_ROUND]
    no_qualifying_round: NoQualifyingRoundPolicy


class LowestCalibrationLossSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[CheckpointSelectionKind.LOWEST_CALIBRATION_LOSS]
    tie_break: CheckpointTieBreak


class FixedRoundSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[CheckpointSelectionKind.FIXED_ROUND]
    selected_round: PositiveInt


class AuthorizedLookupSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[CheckpointSelectionKind.AUTHORIZED_LOOKUP]
    required_algorithm: Literal[TrainingAlgorithm.FEDAVG]


CheckpointSelectionProfile = Annotated[
    FirstQualifyingConvergenceSelection
    | LowestCalibrationLossSelection
    | FixedRoundSelection
    | AuthorizedLookupSelection,
    Field(discriminator="kind"),
]


class CheckpointProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: CheckpointProfileId
    total_rounds: PositiveInt
    capture_rounds: tuple[PositiveInt, ...]
    save_policy: Literal[CheckpointSavePolicy.CONFIGURED_ROUNDS]
    selection: CheckpointSelectionProfile

    @model_validator(mode="after")
    def validate_rounds(self) -> CheckpointProfile:
        rounds = tuple(int(value) for value in self.capture_rounds)
        if not rounds:
            raise ValueError("Checkpoint profile requires at least one capture round")
        if tuple(sorted(rounds)) != rounds:
            raise ValueError("Checkpoint capture rounds must be sorted")
        if len(set(rounds)) != len(rounds):
            raise ValueError("Checkpoint capture rounds must be unique")
        if any(round_number > int(self.total_rounds) for round_number in rounds):
            raise ValueError("Checkpoint capture rounds must fall within the round budget")
        if isinstance(self.selection, FixedRoundSelection) and int(self.selection.selected_round) not in rounds:
            raise ValueError("Fixed selected round must be included in capture rounds")
        if isinstance(self.selection, FirstQualifyingConvergenceSelection):
            if int(self.total_rounds) not in rounds:
                raise ValueError("Convergence selection requires the final round to be captured")
        return self


class RoundMetricEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    round_number: PositiveInt
    global_calibration_loss: NonNegativeFloat
    personalized_calibration_loss: NonNegativeFloat | None


class LoaderSeedEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    round_number: PositiveInt
    client_id: str
    local_epoch_index: int
    branch: LoaderBranch
    shuffle_seed: Seed
    worker_seed: Seed


class CentralizedAlgorithmEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: Literal[TrainingAlgorithm.CENTRALIZED]


class FedAvgAlgorithmEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: Literal[TrainingAlgorithm.FEDAVG]


class FedProxAlgorithmEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: Literal[TrainingAlgorithm.FEDPROX]
    proximal_coefficient: PositiveFloat


class DittoAlgorithmEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    algorithm: Literal[TrainingAlgorithm.DITTO]
    personalization_weight: PositiveFloat


AlgorithmEvidence = Annotated[
    CentralizedAlgorithmEvidence | FedAvgAlgorithmEvidence | FedProxAlgorithmEvidence | DittoAlgorithmEvidence,
    Field(discriminator="algorithm"),
]


class CheckpointSelectionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    selected_round: PositiveInt
    captured_rounds: tuple[PositiveInt, ...]
    round_metrics: tuple[RoundMetricEvidence, ...]
    algorithm: AlgorithmEvidence
    model_initialization_seed: Seed
    loader_seeds: tuple[LoaderSeedEvidence, ...]

    @model_validator(mode="after")
    def validate_evidence(self) -> CheckpointSelectionEvidence:
        captured = tuple(int(value) for value in self.captured_rounds)
        if int(self.selected_round) not in captured:
            raise ValueError("Selected checkpoint round was not captured")
        if tuple(sorted(captured)) != captured or len(set(captured)) != len(captured):
            raise ValueError("Captured checkpoint rounds must be sorted and unique")
        metric_rounds = tuple(int(metric.round_number) for metric in self.round_metrics)
        if metric_rounds != tuple(range(1, len(metric_rounds) + 1)):
            raise ValueError("Round metric evidence must be complete and contiguous")
        return self

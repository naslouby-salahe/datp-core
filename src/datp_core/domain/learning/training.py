from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Final, assert_never

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.checkpoints import ANCHOR_CHECKPOINT_ROUNDS_MAX, SCHEDULED_CHECKPOINT_ROUNDS
from datp_core.domain.learning.models import (
    FIXED_ENCODER_ACTIVATION,
    FIXED_ENCODER_BOTTLENECK_DIM,
    FIXED_ENCODER_HIDDEN_DIMS,
    AutoencoderSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, GradientAccumulationSteps
from datp_core.domain.runtime.seeds import Seed

# FedProx is a Tier-4 stress-test-only profile (architecture doc section 27.1); no experiment
# currently exercises it, so no configs/scientific/*.yaml grid exists yet — this stays the sole
# code-owned source until a FedProx experiment profile is implemented.
FEDPROX_MU_GRID = (0.001, 0.01, 0.1)
LOCKED_ROUNDS_MAX_VALUES = (ANCHOR_CHECKPOINT_ROUNDS_MAX, SCHEDULED_CHECKPOINT_ROUNDS[-1])


class AggregationStrategy(StrEnum):
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"


class ModelPersonalizationStrategy(StrEnum):
    NONE = "none"
    DITTO = "ditto"
    FEDREP_AE = "fedrep_ae"
    FEDPER_AE = "fedper_ae"


class ParticipationStrategy(StrEnum):
    FULL = "full"

    def required_participation_fraction(self) -> float:
        match self:
            case ParticipationStrategy.FULL:
                return 1.0
            case _:
                assert_never(self)

    def permits_round_failures(self) -> bool:
        match self:
            case ParticipationStrategy.FULL:
                return False
            case _:
                assert_never(self)


class OptimizerType(StrEnum):
    ADAM = "adam"
    ADAMW = "adamw"
    SGD = "sgd"
    RMSPROP = "rmsprop"


class LrSchedulerType(StrEnum):
    NONE = "none"
    STEP = "step"
    COSINE = "cosine"
    PLATEAU = "plateau"


# Locked core-training optimizer/batch profile (architecture doc section 27.1): Adam, lr=0.001,
# no weight decay, no LR scheduler, micro-batch 256. Domain-owned so config mapping can validate
# against it (config -> domain is the only allowed direction; infrastructure imports it back).
ANCHOR_OPTIMIZER: Final = OptimizerType.ADAM
ANCHOR_LEARNING_RATE: Final = 0.001
ANCHOR_WEIGHT_DECAY: Final = 0.0
ANCHOR_SCHEDULER: Final = LrSchedulerType.NONE
ANCHOR_BATCH_SIZE: Final = 256


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelTrainingProfileSpec:
    autoencoder: AutoencoderSpec
    optimizer: OptimizerType
    learning_rate: float
    weight_decay: float
    scheduler: LrSchedulerType
    micro_batch_size: BatchSize
    local_epochs: int
    participation: ParticipationStrategy
    rounds_max: int

    def __post_init__(self) -> None:
        if not _is_locked_model_training_profile(self):
            raise DomainValidationError(
                detail="model training profile must match the locked core-training architecture and optimizer",
                value=repr(self),
                constraint=(
                    "hidden_dims=(80, 40); bottleneck_dim=20; activation=RELU; optimizer=ADAM; "
                    "learning_rate=0.001; weight_decay=0.0; scheduler=NONE; micro_batch_size=256; "
                    "local_epochs=1; participation=FULL; rounds_max in LOCKED_ROUNDS_MAX_VALUES"
                ),
            )


def _is_locked_model_training_profile(profile: ModelTrainingProfileSpec) -> bool:
    return all(
        (
            profile.autoencoder.hidden_dims == FIXED_ENCODER_HIDDEN_DIMS,
            profile.autoencoder.bottleneck_dim == FIXED_ENCODER_BOTTLENECK_DIM,
            profile.autoencoder.activation is FIXED_ENCODER_ACTIVATION,
            profile.optimizer is ANCHOR_OPTIMIZER,
            profile.learning_rate == ANCHOR_LEARNING_RATE,
            profile.weight_decay == ANCHOR_WEIGHT_DECAY,
            profile.scheduler is ANCHOR_SCHEDULER,
            profile.micro_batch_size.value == ANCHOR_BATCH_SIZE,
            profile.local_epochs == 1,
            profile.participation is ParticipationStrategy.FULL,
            profile.rounds_max in LOCKED_ROUNDS_MAX_VALUES,
        )
    )


class PrecisionMode(StrEnum):
    FP32 = "fp32"
    TF32 = "tf32"
    MIXED_FP16 = "mixed_fp16"
    MIXED_BF16 = "mixed_bf16"


class DeterminismLevel(StrEnum):
    STRICT = "strict"
    RELAXED = "relaxed"


class ClientBatchPartitioning(StrEnum):
    WHOLE_CLIENT = "whole_client"


class OptimizerStepSemantics(StrEnum):
    AFTER_GRADIENT_ACCUMULATION = "after_gradient_accumulation"


@dataclass(frozen=True, slots=True, kw_only=True)
class FederationSpec:
    aggregation: AggregationStrategy
    local_epochs: int
    participation: ParticipationStrategy
    rounds_max: int
    fedprox_mu: float | None

    def __post_init__(self) -> None:
        _validate_aggregation(self.aggregation)
        _validate_local_epochs(self.local_epochs)
        _validate_participation(self.participation)
        _validate_rounds_max(self.rounds_max)
        _validate_fedprox_coefficient(self)


def _validate_aggregation(aggregation: AggregationStrategy) -> None:
    if type(aggregation) is not AggregationStrategy:
        raise DomainValidationError(
            detail="federation aggregation must be an AggregationStrategy member",
            value=repr(aggregation),
            constraint="AggregationStrategy",
        )


def _validate_local_epochs(local_epochs: int) -> None:
    if type(local_epochs) is not int or local_epochs != 1:
        raise DomainValidationError(
            detail="federation local epochs are locked to one",
            value=repr(local_epochs),
            constraint="local_epochs == 1",
        )


def _validate_participation(participation: ParticipationStrategy) -> None:
    if participation is not ParticipationStrategy.FULL:
        raise DomainValidationError(
            detail="core-ladder federation requires full participation",
            value=repr(participation),
            constraint="participation == FULL",
        )


def _validate_rounds_max(rounds_max: int) -> None:
    if type(rounds_max) is not int or rounds_max not in LOCKED_ROUNDS_MAX_VALUES:
        raise DomainValidationError(
            detail="federation round budget must equal a locked recovered value",
            value=repr(rounds_max),
            constraint=repr(LOCKED_ROUNDS_MAX_VALUES),
        )


def _validate_fedprox_coefficient(specification: FederationSpec) -> None:
    if specification.aggregation is AggregationStrategy.FEDAVG and specification.fedprox_mu is not None:
        raise DomainValidationError(
            detail="FedAvg must not carry a FedProx coefficient",
            value=repr(specification.fedprox_mu),
            constraint="fedprox_mu is None for FEDAVG",
        )
    if specification.aggregation is AggregationStrategy.FEDPROX and not _is_valid_fedprox_mu(specification.fedprox_mu):
        raise DomainValidationError(
            detail="FedProx coefficient must be a frozen grid member",
            value=repr(specification.fedprox_mu),
            constraint="0.001, 0.01, or 0.1",
        )


def _is_valid_fedprox_mu(fedprox_mu: float | None) -> bool:
    return type(fedprox_mu) is float and fedprox_mu in FEDPROX_MU_GRID


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingBatchSpec:
    micro_batch_size: BatchSize
    gradient_accumulation_steps: GradientAccumulationSteps
    effective_batch_size: BatchSize
    dataloader_batch_size: BatchSize
    client_batch_partitioning: ClientBatchPartitioning
    optimizer_step_semantics: OptimizerStepSemantics

    def __post_init__(self) -> None:
        expected_batch_size = self.micro_batch_size.value * self.gradient_accumulation_steps.value
        if self.effective_batch_size.value != expected_batch_size:
            raise DomainValidationError(
                detail="effective batch size must equal micro batch size times accumulation steps",
                value=str(self.effective_batch_size.value),
                constraint=str(expected_batch_size),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingSpec:
    seed: Seed
    autoencoder: AutoencoderSpec
    federation: FederationSpec
    optimizer: OptimizerType
    lr: float
    scheduler: LrSchedulerType
    training_batch: TrainingBatchSpec
    precision: PrecisionMode
    determinism: DeterminismLevel
    personalization: ModelPersonalizationStrategy

    def __post_init__(self) -> None:
        _validate_training_seed(self.seed)
        _validate_learning_rate(self.lr)
        _validate_personalization(self.personalization)


def _validate_training_seed(seed: Seed) -> None:
    if type(seed) is not Seed:
        raise DomainValidationError(
            detail="training seed must be a validated Seed value object",
            value=repr(seed),
            constraint="Seed",
        )


def _validate_learning_rate(learning_rate: float) -> None:
    if not _is_positive_finite_float(learning_rate):
        raise DomainValidationError(
            detail="training learning rate must be strictly positive", value=str(learning_rate), constraint="lr > 0"
        )


def _is_positive_finite_float(value: float) -> bool:
    return type(value) is float and isfinite(value) and value > 0.0


def _validate_personalization(personalization: ModelPersonalizationStrategy) -> None:
    if type(personalization) is not ModelPersonalizationStrategy:
        raise DomainValidationError(
            detail="training personalization must be a ModelPersonalizationStrategy member",
            value=repr(personalization),
            constraint="ModelPersonalizationStrategy",
        )
    if personalization is not ModelPersonalizationStrategy.NONE:
        raise DomainValidationError(
            detail="core-ladder training does not permit personalization",
            value=personalization.value,
            constraint="personalization == NONE",
        )

"""Executable model, optimizer, batching, and materialization contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    StringConstraints,
    model_validator,
)

from datp_core.data.contracts.enums import SplitMembership
from datp_core.learning.contracts.enums import (
    AccumulationRemainderPolicy,
    ActivationKind,
    BiasInitializationKind,
    GradientClippingKind,
    IncompleteBatchPolicy,
    LossReduction,
    ModelArchitectureKind,
    NormalizationKind,
    OptimizerKind,
    OptimizerStateLifecycle,
    OutputActivationKind,
    PrecisionKind,
    ReconstructionObjective,
    SchedulerKind,
    ShufflePolicy,
    SplitProfileKind,
    WeightInitializationKind,
)

IdentifierText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
FeatureName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Probability = Annotated[float, Field(gt=0.0, lt=1.0)]


class DenseAutoencoderProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: IdentifierText
    kind: Literal[ModelArchitectureKind.DENSE_AUTOENCODER]
    hidden_dimensions: tuple[PositiveInt, ...]
    activation: ActivationKind
    output_activation: OutputActivationKind
    normalization: NormalizationKind
    use_bias: bool
    objective: ReconstructionObjective
    reduction: LossReduction
    precision: PrecisionKind
    weight_initialization: WeightInitializationKind
    bias_initialization: BiasInitializationKind

    @model_validator(mode="after")
    def validate_hidden_dimensions(self) -> DenseAutoencoderProfile:
        if not self.hidden_dimensions:
            raise ValueError("Dense autoencoder requires at least one hidden dimension")
        return self

    @property
    def bottleneck_dimension(self) -> int:
        return int(self.hidden_dimensions[-1])


class NoSchedulerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[SchedulerKind.NONE]


class StepSchedulerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[SchedulerKind.STEP]
    step_size_epochs: PositiveInt
    gamma: Probability


SchedulerProfile = Annotated[NoSchedulerProfile | StepSchedulerProfile, Field(discriminator="kind")]


class NoGradientClippingProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[GradientClippingKind.NONE]


class GlobalNormGradientClippingProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[GradientClippingKind.GLOBAL_NORM]
    maximum_norm: PositiveFloat


GradientClippingProfile = Annotated[
    NoGradientClippingProfile | GlobalNormGradientClippingProfile,
    Field(discriminator="kind"),
]


class AdamOptimizerProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: IdentifierText
    kind: Literal[OptimizerKind.ADAM]
    learning_rate: PositiveFloat
    beta_1: Probability
    beta_2: Probability
    epsilon: PositiveFloat
    weight_decay: NonNegativeFloat
    amsgrad: bool
    scheduler: SchedulerProfile
    gradient_clipping: GradientClippingProfile
    state_lifecycle: Literal[OptimizerStateLifecycle.RESET_EACH_LOCAL_TRAINING]


class BatchingProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: IdentifierText
    micro_batch_size: PositiveInt
    gradient_accumulation_steps: PositiveInt
    shuffle_policy: ShufflePolicy
    incomplete_batch_policy: IncompleteBatchPolicy
    accumulation_remainder_policy: AccumulationRemainderPolicy
    worker_count: NonNegativeInt
    pin_memory: bool
    persistent_workers: bool

    @model_validator(mode="after")
    def validate_workers(self) -> BatchingProfile:
        if self.worker_count == 0 and self.persistent_workers:
            raise ValueError("Persistent workers require a positive worker count")
        return self

    @property
    def effective_batch_size(self) -> int:
        return int(self.micro_batch_size) * int(self.gradient_accumulation_steps)


class StandardSplitProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[SplitProfileKind.STANDARD]
    training: Literal[SplitMembership.TRAIN]
    calibration: Literal[SplitMembership.CALIBRATION]
    test: Literal[SplitMembership.TEST]


class TemporalSplitProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[SplitProfileKind.TEMPORAL]
    training: Literal[SplitMembership.HISTORICAL_TRAINING]
    calibration: Literal[SplitMembership.HISTORICAL_CALIBRATION]
    future_recalibration: Literal[SplitMembership.FUTURE_RECALIBRATION]
    test: Literal[SplitMembership.FUTURE_EVALUATION]


SplitProfile = Annotated[StandardSplitProfile | TemporalSplitProfile, Field(discriminator="kind")]


class LearningDataSchema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: IdentifierText
    feature_columns: tuple[FeatureName, ...]
    split_profile: SplitProfile

    @model_validator(mode="after")
    def validate_features(self) -> LearningDataSchema:
        if not self.feature_columns:
            raise ValueError("Learning data schema requires explicit model feature columns")
        if len(set(self.feature_columns)) != len(self.feature_columns):
            raise ValueError("Learning data schema feature columns must be unique")
        return self

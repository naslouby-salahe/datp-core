import torch

from datp_core.domain.errors import TrainingError
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import (
    AggregationStrategy,
    ClientBatchPartitioning,
    DeterminismLevel,
    FederationSpec,
    LrSchedulerType,
    ModelPersonalizationStrategy,
    OptimizerStepSemantics,
    OptimizerType,
    ParticipationStrategy,
    PrecisionMode,
    TrainingBatchSpec,
    TrainingSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, GradientAccumulationSteps
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.learning.models.autoencoder import FixedAutoencoder

ANCHOR_AUTOENCODER_SPECIFICATION = AutoencoderSpec(
    input_dim=115,
    hidden_dims=(80, 40),
    bottleneck_dim=20,
    activation=ActivationFunction.RELU,
)

_ANCHOR_OPTIMIZER = OptimizerType.ADAM
_ANCHOR_LEARNING_RATE = 0.001
_ANCHOR_WEIGHT_DECAY = 0.0
_ANCHOR_SCHEDULER = LrSchedulerType.NONE
_ANCHOR_BATCH_SIZE = 256


def is_authorized_anchor_training_policy(
    *, optimizer: OptimizerType, scheduler: LrSchedulerType, lr: float, autoencoder: AutoencoderSpec
) -> bool:
    return (
        optimizer is _ANCHOR_OPTIMIZER
        and scheduler is _ANCHOR_SCHEDULER
        and lr == _ANCHOR_LEARNING_RATE
        and autoencoder == ANCHOR_AUTOENCODER_SPECIFICATION
    )


def _unauthorized_anchor_training_error(detail: str, *, seed: Seed) -> TrainingError:
    return TrainingError(detail=detail, seed=seed.value, round_number=0)


def anchor_training_spec(*, seed: Seed) -> TrainingSpec:
    training_batch = TrainingBatchSpec(
        micro_batch_size=BatchSize(value=_ANCHOR_BATCH_SIZE),
        gradient_accumulation_steps=GradientAccumulationSteps(value=1),
        effective_batch_size=BatchSize(value=_ANCHOR_BATCH_SIZE),
        dataloader_batch_size=BatchSize(value=_ANCHOR_BATCH_SIZE),
        client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
        optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
    )
    federation = FederationSpec(
        aggregation=AggregationStrategy.FEDAVG,
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        rounds_max=200,
        fedprox_mu=None,
    )
    return TrainingSpec(
        seed=seed,
        autoencoder=ANCHOR_AUTOENCODER_SPECIFICATION,
        federation=federation,
        optimizer=_ANCHOR_OPTIMIZER,
        lr=_ANCHOR_LEARNING_RATE,
        scheduler=_ANCHOR_SCHEDULER,
        training_batch=training_batch,
        precision=PrecisionMode.FP32,
        determinism=DeterminismLevel.STRICT,
        personalization=ModelPersonalizationStrategy.NONE,
    )


def build_anchor_optimizer(*, model: FixedAutoencoder, training: TrainingSpec) -> torch.optim.Optimizer:
    if not is_authorized_anchor_training_policy(
        optimizer=training.optimizer, scheduler=training.scheduler, lr=training.lr, autoencoder=training.autoencoder
    ):
        raise _unauthorized_anchor_training_error(
            "anchor optimizer construction requires the recovered Adam/lr=0.001/no-scheduler/fixed-AE policy",
            seed=training.seed,
        )
    return torch.optim.Adam(model.parameters(), lr=training.lr, weight_decay=_ANCHOR_WEIGHT_DECAY)


def anchor_scheduler(*, training: TrainingSpec) -> None:
    if training.scheduler is not _ANCHOR_SCHEDULER:
        raise _unauthorized_anchor_training_error(
            "the recovered anchor protocol has no learning-rate scheduler", seed=training.seed
        )
    return None

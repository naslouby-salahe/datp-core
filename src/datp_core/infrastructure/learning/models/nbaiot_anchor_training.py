import torch

from datp_core.domain.errors import TrainingError
from datp_core.domain.learning.checkpoints import ANCHOR_CHECKPOINT_ROUNDS_MAX
from datp_core.domain.learning.models import (
    FIXED_ENCODER_ACTIVATION,
    FIXED_ENCODER_BOTTLENECK_DIM,
    FIXED_ENCODER_HIDDEN_DIMS,
    AutoencoderSpec,
)
from datp_core.domain.learning.training import (
    ANCHOR_BATCH_SIZE,
    ANCHOR_LEARNING_RATE,
    ANCHOR_OPTIMIZER,
    ANCHOR_SCHEDULER,
    ANCHOR_WEIGHT_DECAY,
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

# N-BaIoT's feature count (115) is dataset-intrinsic, not a model-profile parameter; it has no
# configs/scientific/*.yaml representation by design (see infrastructure/data/nbaiot_inspection.py
# and nbaiot_source.py for the equivalent dataset-adapter-local-constant precedent).
ANCHOR_AUTOENCODER_SPECIFICATION = AutoencoderSpec(
    input_dim=115,
    hidden_dims=FIXED_ENCODER_HIDDEN_DIMS,
    bottleneck_dim=FIXED_ENCODER_BOTTLENECK_DIM,
    activation=FIXED_ENCODER_ACTIVATION,
)


def is_authorized_anchor_training_policy(
    *, optimizer: OptimizerType, scheduler: LrSchedulerType, lr: float, autoencoder: AutoencoderSpec
) -> bool:
    return (
        optimizer is ANCHOR_OPTIMIZER
        and scheduler is ANCHOR_SCHEDULER
        and lr == ANCHOR_LEARNING_RATE
        and autoencoder == ANCHOR_AUTOENCODER_SPECIFICATION
    )


def _unauthorized_anchor_training_error(detail: str, *, seed: Seed) -> TrainingError:
    return TrainingError(detail=detail, seed=seed.value, round_number=0)


def anchor_training_spec(*, seed: Seed) -> TrainingSpec:
    training_batch = TrainingBatchSpec(
        micro_batch_size=BatchSize(value=ANCHOR_BATCH_SIZE),
        gradient_accumulation_steps=GradientAccumulationSteps(value=1),
        effective_batch_size=BatchSize(value=ANCHOR_BATCH_SIZE),
        dataloader_batch_size=BatchSize(value=ANCHOR_BATCH_SIZE),
        client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
        optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
    )
    federation = FederationSpec(
        aggregation=AggregationStrategy.FEDAVG,
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        rounds_max=ANCHOR_CHECKPOINT_ROUNDS_MAX,
        fedprox_mu=None,
    )
    return TrainingSpec(
        seed=seed,
        autoencoder=ANCHOR_AUTOENCODER_SPECIFICATION,
        federation=federation,
        optimizer=ANCHOR_OPTIMIZER,
        lr=ANCHOR_LEARNING_RATE,
        scheduler=ANCHOR_SCHEDULER,
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
    return torch.optim.Adam(model.parameters(), lr=training.lr, weight_decay=ANCHOR_WEIGHT_DECAY)


def anchor_scheduler(*, training: TrainingSpec) -> None:
    if training.scheduler is not ANCHOR_SCHEDULER:
        raise _unauthorized_anchor_training_error(
            "the recovered anchor protocol has no learning-rate scheduler", seed=training.seed
        )
    return None

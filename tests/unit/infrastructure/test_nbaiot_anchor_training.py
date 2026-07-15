import pytest
import torch
from torch import nn

from datp_core.domain.errors import TrainingError
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import LrSchedulerType, OptimizerType, TrainingSpec
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.learning.models.autoencoder import FixedAutoencoder, build_fixed_autoencoder
from datp_core.infrastructure.learning.models.nbaiot_anchor_training import (
    ANCHOR_AUTOENCODER_SPECIFICATION,
    anchor_scheduler,
    anchor_training_spec,
    build_anchor_optimizer,
    is_authorized_anchor_training_policy,
)

_BATCH_NORMALIZATION_TYPES = (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d, nn.SyncBatchNorm)


@pytest.fixture
def fixed_anchor_model() -> FixedAutoencoder:
    return build_fixed_autoencoder(specification=ANCHOR_AUTOENCODER_SPECIFICATION, initialization_seed=Seed(value=1))


def test_anchor_specification_matches_the_recovered_architecture_and_has_no_batch_normalization(
    fixed_anchor_model: FixedAutoencoder,
) -> None:
    assert ANCHOR_AUTOENCODER_SPECIFICATION == AutoencoderSpec(
        input_dim=115, hidden_dims=(80, 40), bottleneck_dim=20, activation=ActivationFunction.RELU
    )

    assert not any(isinstance(module, _BATCH_NORMALIZATION_TYPES) for module in fixed_anchor_model.modules())


def test_anchor_training_spec_carries_the_recovered_optimizer_and_absent_scheduler() -> None:
    training = anchor_training_spec(seed=Seed(value=1))

    assert training.optimizer is OptimizerType.ADAM
    assert training.lr == 0.001
    assert training.scheduler is LrSchedulerType.NONE
    assert training.federation.local_epochs == 1
    assert anchor_scheduler(training=training) is None


def test_authorization_policy_accepts_only_the_recovered_anchor_combination() -> None:
    assert is_authorized_anchor_training_policy(
        optimizer=OptimizerType.ADAM,
        scheduler=LrSchedulerType.NONE,
        lr=0.001,
        autoencoder=ANCHOR_AUTOENCODER_SPECIFICATION,
    )
    assert not is_authorized_anchor_training_policy(
        optimizer=OptimizerType.SGD,
        scheduler=LrSchedulerType.NONE,
        lr=0.001,
        autoencoder=ANCHOR_AUTOENCODER_SPECIFICATION,
    )
    assert not is_authorized_anchor_training_policy(
        optimizer=OptimizerType.ADAM,
        scheduler=LrSchedulerType.COSINE,
        lr=0.001,
        autoencoder=ANCHOR_AUTOENCODER_SPECIFICATION,
    )


def _unauthorized_training_spec() -> TrainingSpec:
    training = anchor_training_spec(seed=Seed(value=1))
    return TrainingSpec(
        seed=training.seed,
        autoencoder=training.autoencoder,
        federation=training.federation,
        optimizer=OptimizerType.SGD,
        lr=training.lr,
        scheduler=training.scheduler,
        training_batch=training.training_batch,
        precision=training.precision,
        determinism=training.determinism,
        personalization=training.personalization,
    )


def test_build_anchor_optimizer_rejects_an_unauthorized_optimizer_choice(fixed_anchor_model: FixedAutoencoder) -> None:
    with pytest.raises(TrainingError):
        build_anchor_optimizer(model=fixed_anchor_model, training=_unauthorized_training_spec())


def test_build_anchor_optimizer_returns_an_adam_optimizer_over_the_model_parameters(
    fixed_anchor_model: FixedAutoencoder,
) -> None:
    training = anchor_training_spec(seed=Seed(value=1))

    optimizer = build_anchor_optimizer(model=fixed_anchor_model, training=training)

    assert isinstance(optimizer, torch.optim.Adam)
    assert optimizer.param_groups[0]["lr"] == 0.001
    assert optimizer.param_groups[0]["weight_decay"] == 0.0

from decimal import Decimal

import pytest

from datp_core.config.mapping.catalog import map_model_training_profile_config
from datp_core.config.schemas.catalog import ModelProfileConfig
from datp_core.domain.errors import ConfigurationError
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
    ModelTrainingProfileSpec,
    ParticipationStrategy,
)
from datp_core.domain.runtime.admissibility import BatchSize


def _locked_profile_config(
    *, profile_id: str, maximum_rounds: int, checkpoint_rounds: tuple[int, ...]
) -> ModelProfileConfig:
    return ModelProfileConfig(
        profile_id=profile_id,
        hidden_dimensions=(80, 40),
        bottleneck_dimension=20,
        activation="relu",
        optimizer="adam",
        learning_rate=Decimal("0.001"),
        weight_decay=Decimal("0.0"),
        micro_batch_size=256,
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        maximum_rounds=maximum_rounds,
        checkpoint_rounds=checkpoint_rounds,
    )


def test_anchor_model_profile_mapping_produces_the_locked_training_profile() -> None:
    configuration = _locked_profile_config(profile_id="anchor_nbaiot", maximum_rounds=150, checkpoint_rounds=(40, 150))

    mapped = map_model_training_profile_config(configuration, input_dim=115)

    assert mapped == ModelTrainingProfileSpec(
        autoencoder=AutoencoderSpec(
            input_dim=115,
            hidden_dims=FIXED_ENCODER_HIDDEN_DIMS,
            bottleneck_dim=FIXED_ENCODER_BOTTLENECK_DIM,
            activation=FIXED_ENCODER_ACTIVATION,
        ),
        optimizer=ANCHOR_OPTIMIZER,
        learning_rate=ANCHOR_LEARNING_RATE,
        weight_decay=ANCHOR_WEIGHT_DECAY,
        scheduler=ANCHOR_SCHEDULER,
        micro_batch_size=BatchSize(value=ANCHOR_BATCH_SIZE),
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        rounds_max=150,
    )


def test_journal_model_profile_mapping_produces_the_locked_training_profile() -> None:
    configuration = _locked_profile_config(
        profile_id="journal_fedavg",
        maximum_rounds=200,
        checkpoint_rounds=(25, 50, 75, 100, 125, 150, 200),
    )

    mapped = map_model_training_profile_config(configuration, input_dim=115)

    assert mapped.rounds_max == 200
    assert mapped.autoencoder.hidden_dims == FIXED_ENCODER_HIDDEN_DIMS


def test_model_profile_mapping_rejects_a_non_locked_learning_rate() -> None:
    configuration = _locked_profile_config(
        profile_id="anchor_nbaiot", maximum_rounds=150, checkpoint_rounds=(40, 150)
    ).model_copy(update={"learning_rate": Decimal("0.01")})

    with pytest.raises(ConfigurationError):
        map_model_training_profile_config(configuration, input_dim=115)


def test_model_profile_mapping_rejects_a_non_locked_round_budget() -> None:
    configuration = _locked_profile_config(profile_id="anchor_nbaiot", maximum_rounds=999, checkpoint_rounds=(40, 999))

    with pytest.raises(ConfigurationError):
        map_model_training_profile_config(configuration, input_dim=115)

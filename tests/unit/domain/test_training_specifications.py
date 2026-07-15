from collections.abc import Callable
from dataclasses import fields

import pytest

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import (
    FEDPROX_MU_GRID,
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


def test_autoencoder_specification_has_no_batch_norm_surface() -> None:
    assert {entry.name for entry in fields(AutoencoderSpec)} == {
        "input_dim",
        "hidden_dims",
        "bottleneck_dim",
        "activation",
    }


def _federation(*, aggregation: AggregationStrategy, fedprox_mu: float | None) -> FederationSpec:
    return FederationSpec(
        aggregation=aggregation,
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        rounds_max=200,
        fedprox_mu=fedprox_mu,
    )


def _federation_with_unsupported_aggregation() -> FederationSpec:
    return _construct_federation_with_unsupported_aggregation(FederationSpec)


def _construct_federation_with_unsupported_aggregation(constructor: Callable[..., FederationSpec]) -> FederationSpec:
    return constructor(
        aggregation="fedavg",
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        rounds_max=200,
        fedprox_mu=0.1,
    )


def test_federation_enforces_the_fedavg_and_fedprox_coefficient_rules() -> None:
    with pytest.raises(DomainValidationError):
        _federation(aggregation=AggregationStrategy.FEDAVG, fedprox_mu=0.1)
    with pytest.raises(DomainValidationError):
        _federation(aggregation=AggregationStrategy.FEDPROX, fedprox_mu=None)
    with pytest.raises(DomainValidationError):
        _federation(aggregation=AggregationStrategy.FEDPROX, fedprox_mu=0.2)
    with pytest.raises(DomainValidationError):
        _federation_with_unsupported_aggregation()

    specification = _federation(aggregation=AggregationStrategy.FEDPROX, fedprox_mu=FEDPROX_MU_GRID[0])

    assert specification.fedprox_mu == 0.001


def test_training_batch_rejects_non_exact_effective_batch_size() -> None:
    micro_batch_size = BatchSize(value=8)
    gradient_accumulation_steps = GradientAccumulationSteps(value=2)
    effective_batch_size = BatchSize(value=15)
    dataloader_batch_size = BatchSize(value=8)

    with pytest.raises(DomainValidationError):
        TrainingBatchSpec(
            micro_batch_size=micro_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            effective_batch_size=effective_batch_size,
            dataloader_batch_size=dataloader_batch_size,
            client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
            optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
        )


def test_core_training_rejects_personalization() -> None:
    seed = Seed(value=17)
    autoencoder = AutoencoderSpec(
        input_dim=115,
        hidden_dims=(80, 40),
        bottleneck_dim=20,
        activation=ActivationFunction.RELU,
    )
    federation = _federation(aggregation=AggregationStrategy.FEDAVG, fedprox_mu=None)
    training_batch = TrainingBatchSpec(
        micro_batch_size=BatchSize(value=256),
        gradient_accumulation_steps=GradientAccumulationSteps(value=1),
        effective_batch_size=BatchSize(value=256),
        dataloader_batch_size=BatchSize(value=256),
        client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
        optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
    )

    with pytest.raises(DomainValidationError):
        TrainingSpec(
            seed=seed,
            autoencoder=autoencoder,
            federation=federation,
            optimizer=OptimizerType.ADAM,
            lr=0.001,
            scheduler=LrSchedulerType.NONE,
            training_batch=training_batch,
            precision=PrecisionMode.FP32,
            determinism=DeterminismLevel.STRICT,
            personalization=ModelPersonalizationStrategy.DITTO,
        )

"""Typed structured logging without scientific-record payloads."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    StageOperationId,
    TrainingModelId,
)
from datp_core.domain.values import ClientPathToken, Seed


@dataclass(frozen=True, slots=True, kw_only=True)
class PipelineLogContext:
    experiment: ExperimentId
    population: PopulationId
    training_seed: Seed
    training_model: TrainingModelId
    stage: StageOperationId
    threshold_method: FederatedThresholdMethod | None = None
    client: ClientPathToken | None = None


def bind_pipeline_logger(context: PipelineLogContext) -> structlog.stdlib.BoundLogger:
    """Bind only stable scientific identities suitable for operational logs."""
    logger = structlog.get_logger("datp_core.pipeline").bind(
        experiment=context.experiment.value,
        population=context.population.value,
        training_seed=context.training_seed.value,
        training_model=context.training_model.value,
        stage=context.stage.value,
    )
    if context.threshold_method is not None:
        logger = logger.bind(threshold_method=context.threshold_method.value)
    if context.client is not None:
        logger = logger.bind(client=context.client.value)
    return logger

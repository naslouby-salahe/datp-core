from dataclasses import FrozenInstanceError

import pytest
from structlog.testing import capture_logs

from datp_core.domain.enums import (
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    StageOperationId,
    TrainingModelId,
)
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.paths import ClientPathToken
from datp_core.runtime.logging import PipelineLogContext, bind_pipeline_logger


def test_pipeline_logger_binds_only_stable_scientific_context() -> None:
    threshold_method = FederatedThresholdMethod.LOCAL_THRESHOLD
    context = PipelineLogContext(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(0),
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        stage=StageOperationId.ANALYZE,
        threshold_method=threshold_method,
        client=ClientPathToken("device_1"),
    )
    with capture_logs() as captured:
        bind_pipeline_logger(context).info("stage_complete")
    event = captured[0]
    assert event["event"] == "stage_complete"
    assert event["experiment"] == context.experiment.value
    assert event["population"] == context.population.value
    assert event["training_seed"] == 0
    assert event["threshold_method"] == threshold_method.value
    assert event["client"] == "device_1"


def test_pipeline_log_context_is_immutable() -> None:
    context = PipelineLogContext(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(0),
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        stage=StageOperationId.ANALYZE,
    )
    with pytest.raises(FrozenInstanceError):
        context.__setattr__("training_seed", Seed(1))

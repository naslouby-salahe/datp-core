from dataclasses import FrozenInstanceError

import pytest

from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values import Checksum, Seed
from datp_core.orchestration.hooks import (
    NoOpObservationHook,
    ObservationBoundary,
    ObservationContext,
    ObservationResult,
    apply_observation_hook,
)
from datp_core.pipeline.planning import ExperimentCoordinate


def coordinate() -> ExperimentCoordinate:
    return ExperimentCoordinate(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        evidence_role=EvidenceRole.CONFIRMATORY,
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        training_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model_coefficient=None,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        temporal_state=None,
    )


def context() -> ObservationContext:
    return ObservationContext(
        boundary=ObservationBoundary.BEFORE_CALIBRATION,
        coordinate=coordinate(),
        input_checksum=Checksum("a" * 64),
    )


def test_noop_hook_preserves_coordinate_and_checksum() -> None:
    result = apply_observation_hook(context(), NoOpObservationHook())
    assert result.input_checksum == result.output_checksum
    assert result.coordinate == coordinate()


def test_absent_hook_has_identical_noop_behavior() -> None:
    assert apply_observation_hook(context(), None) == apply_observation_hook(context(), NoOpObservationHook())


def test_hook_context_is_immutable() -> None:
    value = context()
    with pytest.raises(FrozenInstanceError):
        value.input_checksum = Checksum("b" * 64)  # type: ignore[misc]


def test_observation_result_rejects_changed_checksum() -> None:
    with pytest.raises(ValueError, match="cannot alter"):
        ObservationResult(
            boundary=ObservationBoundary.BEFORE_CALIBRATION,
            coordinate=coordinate(),
            input_checksum=Checksum("a" * 64),
            output_checksum=Checksum("b" * 64),
        )

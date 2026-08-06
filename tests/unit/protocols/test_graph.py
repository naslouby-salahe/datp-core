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
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.protocols.graph import (
    IdentityObservationHook,
    ObservationBoundary,
    ObservationContext,
    ObservationResult,
    observe_graph_boundary,
)


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
        boundary=ObservationBoundary.AFTER_SCORE_GENERATION_BEFORE_CALIBRATION,
        coordinate=coordinate(),
        input_checksum=Checksum("a" * 64),
    )


def test_identity_hook_preserves_coordinate_and_checksum() -> None:
    result = observe_graph_boundary(context(), IdentityObservationHook())
    assert result.input_checksum == result.output_checksum
    assert result.coordinate == coordinate()


def test_absent_hook_has_identical_identity_behavior() -> None:
    assert observe_graph_boundary(context(), None) == observe_graph_boundary(context(), IdentityObservationHook())


def test_hook_context_is_immutable() -> None:
    value = context()
    with pytest.raises(FrozenInstanceError):
        value.input_checksum = Checksum("b" * 64)  # type: ignore[misc]


def test_observation_result_rejects_changed_checksum() -> None:
    with pytest.raises(ValueError, match="cannot alter"):
        ObservationResult(
            boundary=ObservationBoundary.AFTER_SCORE_GENERATION_BEFORE_CALIBRATION,
            coordinate=coordinate(),
            input_checksum=Checksum("a" * 64),
            output_checksum=Checksum("b" * 64),
        )

from dataclasses import dataclass

import pytest

from datp_core.domain.enums import (
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Quantile, Seed, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.common import (
    FederatedThresholdResult,
    ThresholdAssignmentSet,
    ThresholdConstructionContext,
)
from datp_core.thresholding.models import ThresholdAssignment


COORDINATE = FederatedTrainingCoordinate(
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_seed=Seed(0),
    split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    model=TrainingModelId.FEDAVG_AUTOENCODER,
    model_coefficient=None,
)


def _client(identity: str) -> ClientIdentity:
    return ClientIdentity(
        PopulationId.NBAIOT_NATURAL_DEVICES,
        identity,
        PopulationIdentityKind.PHYSICAL_DEVICES,
    )


@dataclass(frozen=True, slots=True)
class _Result:
    coordinate: FederatedTrainingCoordinate
    assignments: tuple[ThresholdAssignment, ...]
    method = FederatedThresholdMethod.LOCAL_THRESHOLD


def test_threshold_assignment_set_enforces_unique_client_coverage() -> None:
    assignment = ThresholdAssignment(_client("client-a"), ThresholdValue(0.5))
    with pytest.raises(ScientificContractError, match="unique"):
        ThresholdAssignmentSet(assignments=(assignment, assignment))


def test_existing_result_shape_satisfies_shared_protocol() -> None:
    assignment = ThresholdAssignment(_client("client-a"), ThresholdValue(0.5))
    result = _Result(COORDINATE, (assignment,))
    assert isinstance(result, FederatedThresholdResult)
    assert ThresholdAssignmentSet(assignments=result.assignments).clients == (assignment.client,)


def test_threshold_context_binds_coordinate_scores_and_quantile() -> None:
    context = ThresholdConstructionContext(
        coordinate=COORDINATE,
        calibration_manifest_checksum=Checksum("a" * 64),
        score_set_checksum=Checksum("b" * 64),
        quantile=Quantile(0.95),
    )
    assert context.coordinate == COORDINATE

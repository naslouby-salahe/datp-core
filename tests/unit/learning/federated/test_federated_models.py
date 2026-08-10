from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    CHECKPOINT,
    client_identity,
    ditto_coordinates,
    fedavg_coordinate,
    fedprox_coordinate,
)

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import CheckpointStatus, CommunicationEstimationMethod, CudaDeviceName, TrainingModelId
from datp_core.core.numeric import (
    BatchSize,
    ByteCount,
    LogicalElementCount,
    MetricValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.training.models import (
    CheckpointCandidate,
    CheckpointDecision,
    ClientTrainingResult,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
)

SEED = Seed(0)


def _communication(round_number: RoundNumber) -> CommunicationRecord:
    return CommunicationRecord(
        round_number=round_number,
        estimated_upload_bytes=ByteCount(100),
        estimated_download_bytes=ByteCount(100),
        estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        state_bytes=ByteCount(100),
        logical_element_count=LogicalElementCount(5),
    )


def _round_result(coordinate, round_number: RoundNumber) -> FederatedRoundResult:
    return FederatedRoundResult(
        round_number=round_number,
        client_results=(
            ClientTrainingResult(
                client=client_identity("client_a"), sample_count=RowCount(8), local_loss=MetricValue(0.1)
            ),
        ),
        aggregate_loss=MetricValue(0.1),
        communication=_communication(round_number),
        global_state_reference=GlobalModelStateReference(
            coordinate=coordinate, round_number=round_number, state_checksum=Checksum("a" * 64), tensor_path=None
        ),
        personalized_state_references=(),
    )


def test_coordinate_rejects_coefficient_for_fedavg() -> None:
    from datp_core.detector.training.contracts import FederatedTrainingCoordinate

    coordinate = fedavg_coordinate(SEED)
    coefficient = ProximalCoefficient(0.1)
    with pytest.raises(ScientificContractError, match="no model coefficient"):
        FederatedTrainingCoordinate(
            population=coordinate.population,
            training_seed=SEED,
            split_protocol=coordinate.split_protocol,
            preprocessing_identity=coordinate.preprocessing_identity,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=coefficient,
        )


def test_coordinate_requires_coefficient_for_fedprox() -> None:
    with pytest.raises(ScientificContractError, match="proximal coefficient"):
        fedprox_coordinate(SEED, None)  # type: ignore[arg-type]


def test_ditto_global_and_personalized_coordinates_are_structurally_distinct() -> None:
    coordinates, _regularization = ditto_coordinates(SEED)
    assert coordinates.global_coordinate.model is TrainingModelId.DITTO_GLOBAL_AUTOENCODER
    assert coordinates.personalized_coordinate.model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER
    assert coordinates.global_coordinate != coordinates.personalized_coordinate


def test_ditto_training_coordinates_create_shares_regularization() -> None:
    coordinates, regularization = ditto_coordinates(SEED)
    assert coordinates.global_coordinate.model_coefficient == regularization
    assert coordinates.personalized_coordinate.model_coefficient == regularization
    assert coordinates.global_coordinate.matches_ditto_peer(coordinates.personalized_coordinate)


def test_global_state_reference_rejects_personalized_coordinate() -> None:
    coordinates, _regularization = ditto_coordinates(SEED)
    number = RoundNumber(1)
    state_checksum = Checksum("a" * 64)
    with pytest.raises(ScientificContractError, match="global federated model coordinate"):
        GlobalModelStateReference(
            coordinate=coordinates.personalized_coordinate,
            round_number=number,
            state_checksum=state_checksum,
            tensor_path=None,
        )


def test_personalized_state_reference_requires_personalized_coordinate() -> None:
    coordinate = fedavg_coordinate(SEED)
    client = client_identity("client_a")
    number = RoundNumber(1)
    local_loss = MetricValue(0.1)
    state_checksum = Checksum("a" * 64)
    with pytest.raises(ScientificContractError, match="Ditto personalized coordinate"):
        PersonalizedModelStateReference(
            coordinate=coordinate,
            client=client,
            round_number=number,
            local_loss=local_loss,
            state_checksum=state_checksum,
            tensor_path=None,
        )


def test_communication_record_requires_serialized_message_size_basis() -> None:
    number = RoundNumber(1)
    one_byte = ByteCount(1)
    element_count = LogicalElementCount(1)
    with pytest.raises(ScientificContractError, match="serialized-message-size estimate"):
        CommunicationRecord(
            round_number=number,
            estimated_upload_bytes=one_byte,
            estimated_download_bytes=one_byte,
            estimation_basis=CommunicationEstimationMethod.MEASURED_NETWORK_TRAFFIC,
            state_bytes=one_byte,
            logical_element_count=element_count,
        )


def test_round_result_rejects_duplicate_client_results() -> None:
    coordinate = fedavg_coordinate(SEED)
    number = RoundNumber(1)
    duplicate_client_result = ClientTrainingResult(
        client=client_identity("client_a"), sample_count=RowCount(8), local_loss=MetricValue(0.1)
    )
    aggregate_loss = MetricValue(0.1)
    communication = _communication(number)
    global_state_reference = GlobalModelStateReference(
        coordinate=coordinate, round_number=number, state_checksum=Checksum("a" * 64), tensor_path=None
    )
    with pytest.raises(ScientificContractError, match="duplicate client results"):
        FederatedRoundResult(
            round_number=number,
            client_results=(duplicate_client_result, duplicate_client_result),
            aggregate_loss=aggregate_loss,
            communication=communication,
            global_state_reference=global_state_reference,
            personalized_state_references=(),
        )


def test_history_requires_consecutive_rounds_starting_at_one() -> None:
    coordinate = fedavg_coordinate(SEED)
    rounds = (_round_result(coordinate, RoundNumber(2)),)
    with pytest.raises(ScientificContractError, match="rounds must be consecutive from one"):
        FederatedTrainingHistory(coordinate=coordinate, rounds=rounds)


def test_history_accepts_consecutive_rounds() -> None:
    coordinate = fedavg_coordinate(SEED)
    history = FederatedTrainingHistory(
        coordinate=coordinate,
        rounds=(_round_result(coordinate, RoundNumber(1)), _round_result(coordinate, RoundNumber(2))),
    )
    assert len(history.rounds) == 2


def test_checkpoint_candidate_requires_client_only_for_ditto_personalized() -> None:
    coordinate = fedavg_coordinate(SEED)
    number = RoundNumber(1)
    client = client_identity("client_a")
    tensor_path = Path("model.safetensors")
    tensor_checksum = Checksum("a" * 64)
    mean_training_loss = MetricValue(0.1)
    preprocessing_state_set_checksum = Checksum("b" * 64)
    split_manifest_checksum = Checksum("c" * 64)
    with pytest.raises(ScientificContractError, match="global checkpoints cannot carry a client identity"):
        CheckpointCandidate(
            coordinate=coordinate,
            round_number=number,
            client=client,
            tensor_path=tensor_path,
            tensor_checksum=tensor_checksum,
            mean_training_loss=mean_training_loss,
            status=CheckpointStatus.CANDIDATE,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
        )


def test_checkpoint_decision_requires_candidates_to_match_realized_rounds() -> None:
    coordinate = fedavg_coordinate(SEED)
    candidate_one = CheckpointCandidate(
        coordinate=coordinate,
        round_number=RoundNumber(1),
        client=None,
        tensor_path=Path("round_1.safetensors"),
        tensor_checksum=Checksum("a" * 64),
        mean_training_loss=MetricValue(0.1),
        status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        preprocessing_state_set_checksum=Checksum("b" * 64),
        split_manifest_checksum=Checksum("c" * 64),
    )
    candidate_two = CheckpointCandidate(
        coordinate=coordinate,
        round_number=RoundNumber(2),
        client=None,
        tensor_path=Path("round_2.safetensors"),
        tensor_checksum=Checksum("d" * 64),
        mean_training_loss=MetricValue(0.1),
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_set_checksum=Checksum("b" * 64),
        split_manifest_checksum=Checksum("c" * 64),
    )
    checkpoint_protocol = CheckpointProtocol(candidates=(RoundNumber(1), RoundNumber(2)), maximum_round=RoundNumber(2))
    with pytest.raises(
        ScientificContractError, match="checkpoint decision candidates must equal the realized ordered rounds"
    ):
        # A decision whose selected round (1) stops the run at round 1 realizes only
        # (1,), so retaining candidate round 2 must be rejected.
        CheckpointDecision(
            coordinate=coordinate,
            client=None,
            selected=candidate_one,
            candidates=(candidate_one, candidate_two),
            checkpoint_protocol=checkpoint_protocol,
            status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        )


def test_training_result_requires_matching_history_coordinate() -> None:
    coordinate = fedavg_coordinate(SEED)
    other_coordinate = fedavg_coordinate(Seed(SEED.value + 1))
    history = FederatedTrainingHistory(
        coordinate=other_coordinate, rounds=(_round_result(other_coordinate, RoundNumber(1)),)
    )
    preprocessing_state_set_checksum = Checksum("a" * 64)
    split_manifest_checksum = Checksum("b" * 64)
    device_name = CudaDeviceName("cuda")
    batch_size_used = BatchSize(4)
    with pytest.raises(ScientificContractError, match="training result coordinate must match its history"):
        FederatedTrainingResult(
            coordinate=coordinate,
            autoencoder=AUTOENCODER,
            checkpoint_protocol=CHECKPOINT,
            history=history,
            preprocessing_state_set_checksum=preprocessing_state_set_checksum,
            split_manifest_checksum=split_manifest_checksum,
            device_name=device_name,
            batch_size_used=batch_size_used,
        )

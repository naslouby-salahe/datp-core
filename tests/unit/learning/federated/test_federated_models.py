from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    CHECKPOINT,
    client_identity,
    ditto_coordinates,
    fedavg_coordinate,
    fedprox_coordinate,
)

from datp_core.domain.enums import CheckpointStatus, TrainingModelId, WarningCode
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    ByteCount,
    Checksum,
    MetricValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
)
from datp_core.learning.federated.models import (
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
from datp_core.protocols.models import CheckpointProtocol

SEED = 0


def _communication(round_number: RoundNumber) -> CommunicationRecord:
    return CommunicationRecord(
        round_number=round_number,
        estimated_upload_bytes=ByteCount(100),
        estimated_download_bytes=ByteCount(100),
        estimation_basis=WarningCode.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
    )


def _round_result(coordinate, round_number: int) -> FederatedRoundResult:
    number = RoundNumber(round_number)
    return FederatedRoundResult(
        round_number=number,
        client_results=(
            ClientTrainingResult(
                client=client_identity("client_a"), sample_count=RowCount(8), local_loss=MetricValue(0.1)
            ),
        ),
        aggregate_loss=MetricValue(0.1),
        communication=_communication(number),
        global_state_reference=GlobalModelStateReference(
            coordinate=coordinate, round_number=number, state_checksum=Checksum("a" * 64), tensor_path=None
        ),
        personalized_state_references=(),
    )


def test_coordinate_rejects_coefficient_for_fedavg() -> None:
    from datp_core.domain.values import Seed
    from datp_core.learning.federated.models import FederatedTrainingCoordinate

    with pytest.raises(ScientificContractError, match="no model coefficient"):
        FederatedTrainingCoordinate(
            population=fedavg_coordinate(Seed(SEED)).population,
            training_seed=Seed(SEED),
            split_protocol=fedavg_coordinate(Seed(SEED)).split_protocol,
            preprocessing_identity=fedavg_coordinate(Seed(SEED)).preprocessing_identity,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=ProximalCoefficient(0.1),
        )


def test_coordinate_requires_coefficient_for_fedprox() -> None:
    from datp_core.domain.values import Seed

    with pytest.raises(ScientificContractError, match="proximal coefficient"):
        fedprox_coordinate(Seed(SEED), None)  # type: ignore[arg-type]


def test_ditto_global_and_personalized_coordinates_are_structurally_distinct() -> None:
    from datp_core.domain.values import Seed

    global_coordinate, personalized_coordinate, _regularization = ditto_coordinates(Seed(SEED))
    assert global_coordinate.model is TrainingModelId.DITTO_GLOBAL_AUTOENCODER
    assert personalized_coordinate.model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER
    assert global_coordinate != personalized_coordinate


def test_global_state_reference_rejects_personalized_coordinate() -> None:
    from datp_core.domain.values import Seed

    _global, personalized, _regularization = ditto_coordinates(Seed(SEED))
    with pytest.raises(ScientificContractError, match="personalized-model coordinate"):
        GlobalModelStateReference(
            coordinate=personalized, round_number=RoundNumber(1), state_checksum=Checksum("a" * 64), tensor_path=None
        )


def test_personalized_state_reference_requires_personalized_coordinate() -> None:
    from datp_core.domain.values import Seed

    with pytest.raises(ScientificContractError, match="Ditto personalized coordinate"):
        PersonalizedModelStateReference(
            coordinate=fedavg_coordinate(Seed(SEED)),
            client=client_identity("client_a"),
            round_number=RoundNumber(1),
            state_checksum=Checksum("a" * 64),
            tensor_path=None,
        )


def test_communication_record_requires_serialized_message_size_basis() -> None:
    with pytest.raises(ScientificContractError, match="serialized-message-size estimate"):
        CommunicationRecord(
            round_number=RoundNumber(1),
            estimated_upload_bytes=ByteCount(1),
            estimated_download_bytes=ByteCount(1),
            estimation_basis=WarningCode.NEAR_ZERO_MEAN_FPR,
        )


def test_round_result_rejects_duplicate_client_results() -> None:
    from datp_core.domain.values import Seed

    coordinate = fedavg_coordinate(Seed(SEED))
    number = RoundNumber(1)
    duplicate_client_result = ClientTrainingResult(
        client=client_identity("client_a"), sample_count=RowCount(8), local_loss=MetricValue(0.1)
    )
    with pytest.raises(ScientificContractError, match="duplicate client results"):
        FederatedRoundResult(
            round_number=number,
            client_results=(duplicate_client_result, duplicate_client_result),
            aggregate_loss=MetricValue(0.1),
            communication=_communication(number),
            global_state_reference=GlobalModelStateReference(
                coordinate=coordinate, round_number=number, state_checksum=Checksum("a" * 64), tensor_path=None
            ),
            personalized_state_references=(),
        )


def test_history_requires_consecutive_rounds_starting_at_one() -> None:
    from datp_core.domain.values import Seed

    coordinate = fedavg_coordinate(Seed(SEED))
    with pytest.raises(ScientificContractError, match="consecutive rounds"):
        FederatedTrainingHistory(coordinate=coordinate, rounds=(_round_result(coordinate, 2),))


def test_history_accepts_consecutive_rounds() -> None:
    from datp_core.domain.values import Seed

    coordinate = fedavg_coordinate(Seed(SEED))
    history = FederatedTrainingHistory(
        coordinate=coordinate, rounds=(_round_result(coordinate, 1), _round_result(coordinate, 2))
    )
    assert len(history.rounds) == 2


def test_checkpoint_candidate_requires_client_only_for_ditto_personalized() -> None:
    from datp_core.domain.values import Seed

    coordinate = fedavg_coordinate(Seed(SEED))
    with pytest.raises(ScientificContractError, match="only Ditto personalized checkpoints"):
        CheckpointCandidate(
            coordinate=coordinate,
            round_number=RoundNumber(1),
            client=client_identity("client_a"),
            tensor_path=Path("model.safetensors"),
            tensor_checksum=Checksum("a" * 64),
            mean_training_loss=MetricValue(0.1),
            status=CheckpointStatus.CANDIDATE,
            preprocessing_state_set_checksum=Checksum("b" * 64),
            split_manifest_checksum=Checksum("c" * 64),
        )


def test_checkpoint_decision_requires_selected_round_equal_maximum_round() -> None:
    from datp_core.domain.values import Seed

    coordinate = fedavg_coordinate(Seed(SEED))
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
    with pytest.raises(ScientificContractError, match="declared maximum round"):
        CheckpointDecision(
            coordinate=coordinate,
            client=None,
            selected=candidate_one,
            candidates=(candidate_one,),
            checkpoint_protocol=CheckpointProtocol(
                candidates=(RoundNumber(1), RoundNumber(2)), maximum_round=RoundNumber(2)
            ),
            status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        )


def test_training_result_requires_matching_history_coordinate() -> None:
    from datp_core.domain.values import Seed

    coordinate = fedavg_coordinate(Seed(SEED))
    other_coordinate = fedavg_coordinate(Seed(SEED + 1))
    history = FederatedTrainingHistory(coordinate=other_coordinate, rounds=(_round_result(other_coordinate, 1),))
    with pytest.raises(ScientificContractError, match="own history coordinate"):
        FederatedTrainingResult(
            coordinate=coordinate,
            autoencoder_widths=(4, 3, 2, 3, 4),
            checkpoint_protocol=CHECKPOINT,
            history=history,
            preprocessing_state_set_checksum=Checksum("a" * 64),
            split_manifest_checksum=Checksum("b" * 64),
            device_name="cuda",
            batch_size_used=BatchSize(4),
        )

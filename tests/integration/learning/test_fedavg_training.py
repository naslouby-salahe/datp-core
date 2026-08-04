from pathlib import Path

from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEATURE_NAMES,
    FEDAVG_PROTOCOL,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    benign_frame,
    build_all_client_inputs,
    fedavg_coordinate,
)

from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values import Checksum, RowCount, Seed
from datp_core.learning.federated.checkpoints.selection import select_checkpoint
from datp_core.learning.federated.fedavg import train_fedavg
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.orchestration.stages.train_federated import TrainFederatedRequest, train_federated_stage
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import ClientScoringInput, ScoreGenerationRequest, generate_federated_scores


def _training_request(tmp_path: Path) -> FederatedTrainingRequest:
    return FederatedTrainingRequest(
        coordinate=fedavg_coordinate(Seed(0)),
        clients=build_all_client_inputs(tmp_path),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "training",
    )


def test_fedavg_end_to_end_train_select_and_score(tmp_path: Path) -> None:
    request = _training_request(tmp_path)
    outcome = train_fedavg(request)
    assert outcome.training_result.history.rounds[-1].round_number == CHECKPOINT.maximum_round

    decision = select_checkpoint(
        outcome.candidates,
        CHECKPOINT,
        coordinate=request.coordinate,
        client=None,
        selection_rule=CHECKPOINT_SELECTION_RULE,
        preprocessing_state_set_checksum=outcome.candidates[0].preprocessing_state_set_checksum,
        split_manifest_checksum=outcome.candidates[0].split_manifest_checksum,
    )
    assert decision.selected.round_number == CHECKPOINT.maximum_round

    device = resolve_cuda_device()
    scoring_clients = tuple(
        ClientScoringInput(
            client=client_dataset.client,
            calibration_features=benign_frame(RowCount(8), seed=Seed(index)),
            evaluation_features=benign_frame(RowCount(8), seed=Seed(index + 50)),
        )
        for index, client_dataset in enumerate(request.clients)
    )
    result = generate_federated_scores(
        ScoreGenerationRequest(
            checkpoint=decision.selected,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            clients=scoring_clients,
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_set_checksum=decision.selected.preprocessing_state_set_checksum,
            split_manifest_checksum=decision.selected.split_manifest_checksum,
        ),
        device,
    )
    assert len(result.manifest.calibration_records) == len(request.clients)
    assert len(result.manifest.evaluation_records) == len(request.clients)
    assert result.invariant.model_checksum == decision.selected.tensor_checksum


def test_fedavg_reruns_identical_coordinate_and_reuses_published_training(tmp_path: Path) -> None:
    request = TrainFederatedRequest(request=_training_request(tmp_path), overwrite=False)

    first = train_federated_stage(request)
    second = train_federated_stage(request)

    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert tuple(candidate.tensor_checksum for candidate in first.candidates) == tuple(
        candidate.tensor_checksum for candidate in second.candidates
    )

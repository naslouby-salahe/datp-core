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

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import PublicationStatus
from datp_core.core.numeric import RowCount, Seed
from datp_core.detector.checkpoints.protocols import CHECKPOINT_SELECTION_RULE
from datp_core.detector.checkpoints.selection import select_checkpoint
from datp_core.detector.scoring.federated import publish_federated_scores
from datp_core.detector.scoring.models import ClientScoringInput, GenerateFederatedScoresRequest
from datp_core.detector.training.common import federated_training_is_reusable
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated import train_global_federated
from datp_core.detector.training.federated_publication import TrainFederatedDetectorRequest, train_federated_detector


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
    outcome = train_global_federated(request)
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

    scoring_clients = tuple(
        ClientScoringInput(
            client=client_dataset.client,
            calibration_features=benign_frame(RowCount(8), seed=Seed(index)),
            evaluation_features=benign_frame(RowCount(8), seed=Seed(index + 50)),
        )
        for index, client_dataset in enumerate(request.clients)
    )
    result = publish_federated_scores(
        GenerateFederatedScoresRequest(
            checkpoint=decision.selected,
            scored_split_protocol=decision.selected.coordinate.split_protocol,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            clients=scoring_clients,
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_set_checksum=decision.selected.preprocessing_state_set_checksum,
            split_manifest_checksum=decision.selected.split_manifest_checksum,
            overwrite=False,
        )
    )
    assert len(result.manifest.calibration_records) == len(request.clients)
    assert len(result.manifest.evaluation_records) == len(request.clients)
    assert result.invariant.model_checksum == decision.selected.tensor_checksum


def test_fedavg_reruns_identical_coordinate_and_reuses_published_training(tmp_path: Path) -> None:
    request = TrainFederatedDetectorRequest(request=_training_request(tmp_path), overwrite=False)

    first = train_federated_detector(request)
    second = train_federated_detector(request)

    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert tuple(candidate.tensor_checksum for candidate in first.candidates) == tuple(
        candidate.tensor_checksum for candidate in second.candidates
    )


def test_fedavg_marker_without_valid_artifacts_is_not_reusable(tmp_path: Path) -> None:
    request = _training_request(tmp_path)
    request.output_directory.mkdir(parents=True)
    (request.output_directory / "COMPLETE").write_text("stale completion marker", encoding="utf-8")

    assert federated_training_is_reusable(request, request.output_directory) is False

    rebuilt = train_federated_detector(TrainFederatedDetectorRequest(request=request, overwrite=False))
    assert rebuilt.publication_status is PublicationStatus.PUBLISHED

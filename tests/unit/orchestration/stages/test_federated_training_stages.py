from pathlib import Path

import polars as pl
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    CLIENT_IDS,
    FEATURE_NAMES,
    FEDAVG_PROTOCOL,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    benign_frame,
    client_identity,
    feature_protocol,
    fedavg_coordinate,
)

from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values import Checksum, ClientPathToken, RowCount, Seed
from datp_core.learning.federated.models import ClientTrainingInput
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.orchestration.stages.score_federated import ScoreFederatedRequest, score_federated_stage
from datp_core.orchestration.stages.select_federated_checkpoint import (
    SelectFederatedCheckpointRequest,
    select_federated_checkpoint_stage,
)
from datp_core.orchestration.stages.train_federated import TrainFederatedRequest, train_federated_stage
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    FederatedFittedPreprocessingState,
    PreprocessedPartitionPaths,
)
from datp_core.scoring.generation import ClientScoringInput


def _client_publication(client_id: str, directory: Path) -> ClientPreprocessingResult:
    directory.mkdir(parents=True, exist_ok=True)
    train_path = directory / "train.parquet"
    calibration_path = directory / "calibration.parquet"
    evaluation_path = directory / "evaluation.parquet"
    benign_frame(RowCount(16), seed=Seed(hash(client_id) % 1000)).write_parquet(train_path)
    benign_frame(RowCount(8), seed=Seed((hash(client_id) + 1) % 1000)).write_parquet(calibration_path)
    benign_frame(RowCount(8), seed=Seed((hash(client_id) + 2) % 1000)).write_parquet(evaluation_path)
    estimator_path = directory / "state.skops"
    estimator_path.write_bytes(b"placeholder")
    fitted_state = FederatedFittedPreprocessingState(
        protocol=feature_protocol(),
        client_identity=ClientPathToken(client_id),
        estimator_path=estimator_path,
        estimator_checksum=Checksum(f"{client_id[-1]}" * 64),
        fit_row_count=RowCount(16),
    )
    return ClientPreprocessingResult(
        client_identity=ClientPathToken(client_id),
        paths=PreprocessedPartitionPaths(
            train=train_path,
            calibration=calibration_path,
            evaluation=evaluation_path,
            future_recalibration=None,
            static_reference_reserve=None,
        ),
        fitted_state=fitted_state,
        publication_status=PublicationStatus.PUBLISHED,
        train_row_count=RowCount(16),
        calibration_row_count=RowCount(8),
        evaluation_row_count=RowCount(8),
        future_recalibration_row_count=RowCount(0),
        static_reference_reserve_row_count=RowCount(0),
    )


def _training_request(
    publications: tuple[ClientPreprocessingResult, ...], output_directory: Path
) -> TrainFederatedRequest:
    coordinate = fedavg_coordinate(Seed(0))
    clients = tuple(
        ClientTrainingInput(
            client=client_identity(publication.client_identity.value),
            training_features=pl.read_parquet(publication.paths.train),
            feature_names=FEATURE_NAMES,
            preprocessing_state=publication.fitted_state,
        )
        for publication in publications
    )
    return TrainFederatedRequest(
        request=FederatedTrainingRequest(
            coordinate=coordinate,
            clients=clients,
            population_client_count=POPULATION_CLIENT_COUNT,
            autoencoder=AUTOENCODER,
            training_protocol=FEDAVG_PROTOCOL,
            checkpoint_protocol=CHECKPOINT,
            training_seed=Seed(0),
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            split_manifest_checksum=Checksum("a" * 64),
            output_directory=output_directory,
        ),
        overwrite=False,
    )


def test_train_federated_stage_publishes_then_reuses(tmp_path: Path) -> None:
    publications = tuple(
        _client_publication(client_id, tmp_path / "preprocessed" / client_id) for client_id in CLIENT_IDS
    )
    request = _training_request(publications, tmp_path / "training")

    first = train_federated_stage(request)
    second = train_federated_stage(request)

    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert tuple(candidate.tensor_checksum for candidate in first.candidates) == tuple(
        candidate.tensor_checksum for candidate in second.candidates
    )


def test_select_and_score_federated_stages(tmp_path: Path) -> None:
    publications = tuple(
        _client_publication(client_id, tmp_path / "preprocessed" / client_id) for client_id in CLIENT_IDS
    )
    coordinate = fedavg_coordinate(Seed(0))
    training = train_federated_stage(_training_request(publications, tmp_path / "training"))

    selection = select_federated_checkpoint_stage(
        SelectFederatedCheckpointRequest(
            coordinate=coordinate,
            client=None,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT,
            preprocessing_state_set_checksum=training.candidates[0].preprocessing_state_set_checksum,
            split_manifest_checksum=training.candidates[0].split_manifest_checksum,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    )
    assert selection.decision.selected.round_number == CHECKPOINT.maximum_round

    clients = tuple(
        ClientScoringInput(
            client=client_identity(publication.client_identity.value),
            calibration_features=pl.read_parquet(publication.paths.calibration),
            evaluation_features=pl.read_parquet(publication.paths.evaluation),
        )
        for publication in publications
    )
    score_request = ScoreFederatedRequest(
        checkpoint=selection.decision.selected,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        clients=clients,
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_set_checksum=selection.decision.selected.preprocessing_state_set_checksum,
        split_manifest_checksum=selection.decision.selected.split_manifest_checksum,
        overwrite=False,
    )
    first_scoring = score_federated_stage(score_request)
    second_scoring = score_federated_stage(score_request)

    assert first_scoring.publication_status is PublicationStatus.PUBLISHED
    assert second_scoring.publication_status is PublicationStatus.REUSED
    assert first_scoring.result.invariant == second_scoring.result.invariant

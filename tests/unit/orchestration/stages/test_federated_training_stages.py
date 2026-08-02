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
from datp_core.domain.values import Checksum, RowCount, Seed
from datp_core.domain.values import ClientPathToken as PreprocessingClientPathToken
from datp_core.orchestration.stages.score_federated import ScoreFederatedRequest, score_federated_stage
from datp_core.orchestration.stages.select_federated_checkpoint import (
    SelectFederatedCheckpointRequest,
    select_federated_checkpoint_stage,
)
from datp_core.orchestration.stages.train_federated import TrainFedAvgRequest, train_fedavg_stage
from datp_core.preprocessing.models import ClientPreprocessingResult, ClientPreprocessPublication
from datp_core.scoring.generation import ClientScoringInput


def _client_publication(client_id: str, directory: Path) -> ClientPreprocessPublication:
    directory.mkdir(parents=True, exist_ok=True)
    train_path = directory / "train.parquet"
    calibration_path = directory / "calibration.parquet"
    evaluation_path = directory / "evaluation.parquet"
    benign_frame(RowCount(16), seed=Seed(hash(client_id) % 1000)).write_parquet(train_path)
    benign_frame(RowCount(8), seed=Seed((hash(client_id) + 1) % 1000)).write_parquet(calibration_path)
    benign_frame(RowCount(8), seed=Seed((hash(client_id) + 2) % 1000)).write_parquet(evaluation_path)
    estimator_path = directory / "state.skops"
    estimator_path.write_bytes(b"placeholder")
    protocol = feature_protocol()
    from datp_core.domain.enums import PartitionRole, ProcessedDataBranch
    from datp_core.preprocessing.models import FittedPreprocessingState

    fitted_state = FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.FEDERATED,
        client_identity=PreprocessingClientPathToken(client_id),
        estimator_path=estimator_path,
        estimator_checksum=Checksum(f"{client_id[-1]}" * 64),
        transformed_schema=protocol.transformed_schema,
        fit_row_count=RowCount(16),
        fit_partition=PartitionRole.TRAIN,
    )
    result = ClientPreprocessingResult(
        client_identity=PreprocessingClientPathToken(client_id),
        train_path=train_path,
        calibration_path=calibration_path,
        evaluation_path=evaluation_path,
        fitted_state=fitted_state,
        transformed_schema=protocol.transformed_schema,
        publication_status=PublicationStatus.PUBLISHED,
    )
    return ClientPreprocessPublication(
        client_identity=PreprocessingClientPathToken(client_id),
        result=result,
        publication_status=PublicationStatus.PUBLISHED,
        train_row_count=RowCount(16),
        calibration_row_count=RowCount(8),
        evaluation_row_count=RowCount(8),
    )


def test_train_fedavg_stage_publishes_then_reuses(tmp_path: Path) -> None:
    publications = tuple(
        _client_publication(client_id, tmp_path / "preprocessed" / client_id) for client_id in CLIENT_IDS
    )
    request = TrainFedAvgRequest(
        coordinate=fedavg_coordinate(Seed(0)),
        client_publications=publications,
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "training",
        overwrite=False,
    )
    first = train_fedavg_stage(request)
    assert first.publication_status is PublicationStatus.PUBLISHED
    second = train_fedavg_stage(request)
    assert second.publication_status is PublicationStatus.REUSED
    first_checksums = tuple(candidate.tensor_checksum for candidate in first.candidates)
    second_checksums = tuple(candidate.tensor_checksum for candidate in second.candidates)
    assert first_checksums == second_checksums


def test_select_and_score_federated_stages(tmp_path: Path) -> None:
    publications = tuple(
        _client_publication(client_id, tmp_path / "preprocessed" / client_id) for client_id in CLIENT_IDS
    )
    coordinate = fedavg_coordinate(Seed(0))
    training_request = TrainFedAvgRequest(
        coordinate=coordinate,
        client_publications=publications,
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "training",
        overwrite=False,
    )
    training = train_fedavg_stage(training_request)

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
            calibration_features=pl.read_parquet(publication.result.calibration_path),
            evaluation_features=pl.read_parquet(publication.result.evaluation_path),
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
    assert first_scoring.publication_status is PublicationStatus.PUBLISHED
    second_scoring = score_federated_stage(score_request)
    assert second_scoring.publication_status is PublicationStatus.REUSED
    assert first_scoring.result.invariant == second_scoring.result.invariant

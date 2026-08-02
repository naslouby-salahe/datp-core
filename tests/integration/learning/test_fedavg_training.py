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
    build_all_client_datasets,
    fedavg_coordinate,
)

from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values import Checksum, RowCount, Seed
from datp_core.learning.federated.checkpointing import select_checkpoint
from datp_core.learning.federated.fedavg import FedAvgTrainingRequest, train_fedavg
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import ClientScoringInput, ScoreGenerationRequest, generate_federated_scores


def test_fedavg_end_to_end_train_select_and_score(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    clients = build_all_client_datasets(tmp_path)
    outcome = train_fedavg(
        FedAvgTrainingRequest(
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
            output_directory=tmp_path / "training",
        )
    )
    assert outcome.training_result.history.rounds[-1].round_number == CHECKPOINT.maximum_round

    decision = select_checkpoint(
        outcome.candidates,
        CHECKPOINT,
        coordinate=coordinate,
        client=None,
        selection_rule=CHECKPOINT_SELECTION_RULE,
    )
    assert decision.selected.round_number == CHECKPOINT.maximum_round

    device = resolve_cuda_device()
    scoring_clients = tuple(
        ClientScoringInput(
            client=client_dataset.training_input.client,
            calibration_features=benign_frame(RowCount(8), seed=Seed(index)),
            evaluation_features=benign_frame(RowCount(8), seed=Seed(index + 50)),
        )
        for index, client_dataset in enumerate(clients)
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
    assert len(result.manifest.calibration_records) == len(clients)
    assert len(result.manifest.evaluation_records) == len(clients)
    assert result.invariant.model_checksum == decision.selected.tensor_checksum


def test_fedavg_reruns_the_identical_coordinate_and_reuses_the_published_training(tmp_path: Path) -> None:
    from tests.unit.learning.federated.helpers import CLIENT_IDS, feature_protocol

    from datp_core.domain.values import ClientPathToken as PreprocessingClientPathToken
    from datp_core.orchestration.stages.train_federated import TrainFedAvgRequest, train_fedavg_stage
    from datp_core.preprocessing.models import ClientPreprocessingResult, ClientPreprocessPublication

    def publication(client_id: str, directory: Path) -> ClientPreprocessPublication:
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

    publications = tuple(publication(client_id, tmp_path / "preprocessed" / client_id) for client_id in CLIENT_IDS)
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
    second = train_fedavg_stage(request)
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED

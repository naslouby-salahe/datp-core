from pathlib import Path

from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEATURE_NAMES,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    benign_frame,
    build_all_client_inputs,
    fedprox_coordinate,
    fedprox_protocol,
)

from datp_core.artifacts.provenance import Checksum
from datp_core.core.numeric import RowCount, Seed
from datp_core.detector.checkpoints.protocols import CHECKPOINT_SELECTION_RULE
from datp_core.detector.checkpoints.selection import select_checkpoint
from datp_core.detector.scoring.federated import publish_federated_scores
from datp_core.detector.scoring.models import ClientScoringInput, GenerateFederatedScoresRequest
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated import train_global_federated
from datp_core.detector.training.protocols import FEDPROX_COEFFICIENTS


def test_fedprox_end_to_end_train_select_and_score_for_one_declared_coefficient(tmp_path: Path) -> None:
    coefficient = FEDPROX_COEFFICIENTS[0]
    coordinate = fedprox_coordinate(Seed(0), coefficient)
    clients = build_all_client_inputs(tmp_path)
    outcome = train_global_federated(
        FederatedTrainingRequest(
            coordinate=coordinate,
            clients=clients,
            population_client_count=POPULATION_CLIENT_COUNT,
            autoencoder=AUTOENCODER,
            training_protocol=fedprox_protocol(coefficient),
            checkpoint_protocol=CHECKPOINT,
            training_seed=Seed(0),
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            split_manifest_checksum=Checksum("a" * 64),
            output_directory=tmp_path / "training",
        )
    )
    decision = select_checkpoint(
        outcome.candidates,
        CHECKPOINT,
        coordinate=coordinate,
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
        for index, client_dataset in enumerate(clients)
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
    assert result.invariant.model_checksum == decision.selected.tensor_checksum


def test_fedprox_grid_produces_independent_checksums_per_coefficient(tmp_path: Path) -> None:
    checksums = []
    for index, coefficient in enumerate(FEDPROX_COEFFICIENTS):
        directory = tmp_path / f"coefficient_{index}"
        directory.mkdir()
        clients = build_all_client_inputs(directory)
        outcome = train_global_federated(
            FederatedTrainingRequest(
                coordinate=fedprox_coordinate(Seed(0), coefficient),
                clients=clients,
                population_client_count=POPULATION_CLIENT_COUNT,
                autoencoder=AUTOENCODER,
                training_protocol=fedprox_protocol(coefficient),
                checkpoint_protocol=CHECKPOINT,
                training_seed=Seed(0),
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=Checksum("a" * 64),
                output_directory=directory / "training",
            )
        )
        terminal = next(
            candidate for candidate in outcome.candidates if candidate.round_number == CHECKPOINT.maximum_round
        )
        checksums.append(terminal.tensor_checksum)
    assert len(set(checksums)) == len(FEDPROX_COEFFICIENTS)

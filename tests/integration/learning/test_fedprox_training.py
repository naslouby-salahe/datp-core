from pathlib import Path

from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEATURE_NAMES,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    benign_frame,
    build_all_client_datasets,
    fedprox_coordinate,
    fedprox_protocol,
)

from datp_core.domain.values import Checksum, Seed
from datp_core.learning.federated.checkpointing import select_checkpoint
from datp_core.learning.federated.fedprox import FedProxTrainingRequest, train_fedprox
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE, FEDPROX_COEFFICIENTS
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import ClientScoringInput, ScoreGenerationRequest, generate_federated_scores


def test_fedprox_end_to_end_train_select_and_score_for_one_declared_coefficient(tmp_path: Path) -> None:
    coefficient = FEDPROX_COEFFICIENTS[0]
    coordinate = fedprox_coordinate(Seed(0), coefficient)
    clients = build_all_client_datasets(tmp_path)
    outcome = train_fedprox(
        FedProxTrainingRequest(
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
    )
    assert decision.selected.round_number == CHECKPOINT.maximum_round

    device = resolve_cuda_device()
    scoring_clients = tuple(
        ClientScoringInput(
            client=client_dataset.training_input.client,
            calibration_features=benign_frame(8, seed=index),
            evaluation_features=benign_frame(8, seed=index + 50),
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
    assert result.invariant.model_checksum == decision.selected.tensor_checksum


def test_fedprox_grid_produces_independent_checksums_per_coefficient(tmp_path: Path) -> None:
    checksums = []
    for index, coefficient in enumerate(FEDPROX_COEFFICIENTS):
        directory = tmp_path / f"coefficient_{index}"
        directory.mkdir()
        clients = build_all_client_datasets(directory)
        outcome = train_fedprox(
            FedProxTrainingRequest(
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
        terminal = next(c for c in outcome.candidates if c.round_number == CHECKPOINT.maximum_round)
        checksums.append(terminal.tensor_checksum)
    assert len(set(checksums)) == len(FEDPROX_COEFFICIENTS)

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
    ditto_coordinates,
    ditto_protocol,
)

from datp_core.domain.values import Checksum, RowCount, Seed
from datp_core.learning.federated.checkpointing import select_checkpoint
from datp_core.learning.federated.ditto import DittoTrainingRequest, train_ditto
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import ClientScoringInput, ScoreGenerationRequest, generate_federated_scores


def test_ditto_end_to_end_train_select_and_score_global_and_personalized(tmp_path: Path) -> None:
    global_coordinate, personalized_coordinate, regularization = ditto_coordinates(Seed(0))
    clients = build_all_client_inputs(tmp_path)
    outcome = train_ditto(
        DittoTrainingRequest(
            global_coordinate=global_coordinate,
            personalized_coordinate=personalized_coordinate,
            clients=clients,
            population_client_count=POPULATION_CLIENT_COUNT,
            autoencoder=AUTOENCODER,
            training_protocol=ditto_protocol(regularization),
            checkpoint_protocol=CHECKPOINT,
            training_seed=Seed(0),
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            split_manifest_checksum=Checksum("a" * 64),
            global_output_directory=tmp_path / "global",
            personalized_output_directory=tmp_path / "personalized",
        )
    )

    global_decision = select_checkpoint(
        outcome.global_candidates,
        CHECKPOINT,
        coordinate=global_coordinate,
        client=None,
        selection_rule=CHECKPOINT_SELECTION_RULE,
        preprocessing_state_set_checksum=outcome.global_candidates[0].preprocessing_state_set_checksum,
        split_manifest_checksum=outcome.global_candidates[0].split_manifest_checksum,
    )
    assert global_decision.selected.round_number == CHECKPOINT.maximum_round

    device = resolve_cuda_device()
    scoring_clients = tuple(
        ClientScoringInput(
            client=client_dataset.client,
            calibration_features=benign_frame(RowCount(8), seed=Seed(index)),
            evaluation_features=benign_frame(RowCount(8), seed=Seed(index + 50)),
        )
        for index, client_dataset in enumerate(clients)
    )
    global_scores = generate_federated_scores(
        ScoreGenerationRequest(
            checkpoint=global_decision.selected,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            clients=scoring_clients,
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores" / "global",
            preprocessing_state_set_checksum=global_decision.selected.preprocessing_state_set_checksum,
            split_manifest_checksum=global_decision.selected.split_manifest_checksum,
        ),
        device,
    )

    personalized_score_checksums = []
    for pcs in outcome.personalized_candidates:
        client = pcs.client
        decision = select_checkpoint(
            pcs.candidates,
            CHECKPOINT,
            coordinate=personalized_coordinate,
            client=client,
            selection_rule=CHECKPOINT_SELECTION_RULE,
            preprocessing_state_set_checksum=pcs.candidates[0].preprocessing_state_set_checksum,
            split_manifest_checksum=pcs.candidates[0].split_manifest_checksum,
        )
        personalized_scores = generate_federated_scores(
            ScoreGenerationRequest(
                checkpoint=decision.selected,
                autoencoder=AUTOENCODER,
                feature_names=FEATURE_NAMES,
                clients=(
                    ClientScoringInput(
                        client=client,
                        calibration_features=benign_frame(RowCount(8), seed=Seed(1)),
                        evaluation_features=benign_frame(RowCount(8), seed=Seed(2)),
                    ),
                ),
                batch_size=BATCH_SIZE,
                output_directory=tmp_path / "scores" / "personalized" / client.client_id,
                preprocessing_state_set_checksum=decision.selected.preprocessing_state_set_checksum,
                split_manifest_checksum=decision.selected.split_manifest_checksum,
            ),
            device,
        )
        personalized_score_checksums.append(personalized_scores.invariant.model_checksum)

    assert global_scores.invariant.model_checksum not in personalized_score_checksums
    assert len(set(personalized_score_checksums)) == len(clients)

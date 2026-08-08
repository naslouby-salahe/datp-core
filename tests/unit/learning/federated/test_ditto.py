from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    build_all_client_inputs,
    ditto_coordinates,
    ditto_protocol,
)

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.numeric import Seed
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.detector.training.ditto import DittoTrainingRequest, train_ditto
from datp_core.detector.training.models import DittoTrainingCoordinates


def _request(tmp_path: Path) -> DittoTrainingRequest:
    coordinates, regularization = ditto_coordinates(Seed(0))
    return DittoTrainingRequest(
        coordinates=coordinates,
        clients=build_all_client_inputs(tmp_path),
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


def test_train_ditto_produces_distinct_global_and_personalized_checkpoints(tmp_path: Path) -> None:
    outcome = train_ditto(_request(tmp_path))
    assert len(outcome.global_candidates) == len(CHECKPOINT.candidates)
    assert len(outcome.personalized_candidates) == 2
    for pcs in outcome.personalized_candidates:
        assert pcs.client.client_id in {"client_a", "client_b"}
        assert len(pcs.candidates) == len(CHECKPOINT.candidates)
        for candidate in pcs.candidates:
            assert candidate.client is not None
            assert candidate.client == pcs.client


def test_train_ditto_never_aggregates_personalized_states_into_global(tmp_path: Path) -> None:
    outcome = train_ditto(_request(tmp_path))
    global_checksums = {candidate.tensor_checksum for candidate in outcome.global_candidates}
    personalized_checksums = {
        candidate.tensor_checksum for pcs in outcome.personalized_candidates for candidate in pcs.candidates
    }
    assert global_checksums.isdisjoint(personalized_checksums)


def test_train_ditto_personalized_states_differ_by_client(tmp_path: Path) -> None:
    outcome = train_ditto(_request(tmp_path))
    terminal_round = CHECKPOINT.maximum_round
    terminal_checksums = {
        pcs.client: next(
            candidate.tensor_checksum for candidate in pcs.candidates if candidate.round_number == terminal_round
        )
        for pcs in outcome.personalized_candidates
    }
    assert len(set(terminal_checksums.values())) == len(terminal_checksums)


def test_train_ditto_personalized_states_persist_across_rounds(tmp_path: Path) -> None:
    outcome = train_ditto(_request(tmp_path))
    for pcs in outcome.personalized_candidates:
        checksums = tuple(candidate.tensor_checksum for candidate in pcs.candidates)
        assert len(set(checksums)) >= 1


def test_train_ditto_records_personalized_state_references_every_round(tmp_path: Path) -> None:
    outcome = train_ditto(_request(tmp_path))
    for round_result in outcome.global_training_result.history.rounds:
        client_ids = {reference.client.client_id for reference in round_result.personalized_state_references}
        assert client_ids == {"client_a", "client_b"}


def test_train_ditto_rejects_partial_participation(tmp_path: Path) -> None:
    request = _request(tmp_path)
    single_client_request = DittoTrainingRequest(
        coordinates=request.coordinates,
        clients=(request.clients[0],),
        population_client_count=request.population_client_count,
        autoencoder=request.autoencoder,
        training_protocol=request.training_protocol,
        checkpoint_protocol=request.checkpoint_protocol,
        training_seed=request.training_seed,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
        split_manifest_checksum=request.split_manifest_checksum,
        global_output_directory=request.global_output_directory,
        personalized_output_directory=request.personalized_output_directory,
    )
    with pytest.raises(ScientificContractError, match="does not match the declared population count"):
        train_ditto(single_client_request)


def test_ditto_training_coordinates_reject_mismatched_regularization(tmp_path: Path) -> None:
    del tmp_path
    from datp_core.protocols.training import DITTO_REGULARIZATION_GRID

    coordinates, _ = ditto_coordinates(Seed(0))

    mismatched_personalized = FederatedTrainingCoordinate(
        population=coordinates.personalized_coordinate.population,
        training_seed=coordinates.personalized_coordinate.training_seed,
        split_protocol=coordinates.personalized_coordinate.split_protocol,
        preprocessing_identity=coordinates.personalized_coordinate.preprocessing_identity,
        model=coordinates.personalized_coordinate.model,
        model_coefficient=DITTO_REGULARIZATION_GRID[0],
    )
    with pytest.raises(ScientificContractError, match="must share one experiment identity"):
        DittoTrainingCoordinates(
            global_coordinate=coordinates.global_coordinate,
            personalized_coordinate=mismatched_personalized,
        )

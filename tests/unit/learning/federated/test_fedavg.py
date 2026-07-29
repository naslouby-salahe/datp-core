from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEDAVG_PROTOCOL,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    build_all_client_datasets,
    fedavg_coordinate,
)

from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed
from datp_core.learning.federated.fedavg import FedAvgTrainingRequest, train_fedavg


def _request(tmp_path: Path, seed: Seed | None = None) -> FedAvgTrainingRequest:
    resolved_seed = Seed(0) if seed is None else seed
    return FedAvgTrainingRequest(
        coordinate=fedavg_coordinate(resolved_seed),
        clients=build_all_client_datasets(tmp_path),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        checkpoint_protocol=CHECKPOINT,
        training_seed=resolved_seed,
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "output",
    )


def test_train_fedavg_produces_history_with_full_participation_every_round(tmp_path: Path) -> None:
    outcome = train_fedavg(_request(tmp_path))
    for round_result in outcome.training_result.history.rounds:
        assert len(round_result.client_results) == POPULATION_CLIENT_COUNT.value
    assert len(outcome.training_result.history.rounds) == CHECKPOINT.maximum_round.value


def test_train_fedavg_produces_one_checkpoint_candidate_per_declared_round(tmp_path: Path) -> None:
    outcome = train_fedavg(_request(tmp_path))
    observed_rounds = tuple(candidate.round_number for candidate in outcome.candidates)
    expected_rounds = tuple(CHECKPOINT.candidates)
    assert observed_rounds == expected_rounds
    for candidate in outcome.candidates:
        assert candidate.client is None
        assert candidate.tensor_path.is_file()


def test_train_fedavg_is_deterministic_given_the_same_seed(tmp_path: Path) -> None:
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    first_directory.mkdir()
    second_directory.mkdir()
    first = train_fedavg(_request(first_directory))
    second = train_fedavg(_request(second_directory))
    first_checksums = tuple(candidate.tensor_checksum for candidate in first.candidates)
    second_checksums = tuple(candidate.tensor_checksum for candidate in second.candidates)
    assert first_checksums == second_checksums


def test_train_fedavg_rejects_partial_client_participation(tmp_path: Path) -> None:
    clients = build_all_client_datasets(tmp_path)
    request = FedAvgTrainingRequest(
        coordinate=fedavg_coordinate(Seed(0)),
        clients=(clients[0],),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "output",
    )
    with pytest.raises(ScientificContractError, match="declared population client count"):
        train_fedavg(request)


def test_train_fedavg_rejects_a_fedprox_coordinate(tmp_path: Path) -> None:
    from tests.unit.learning.federated.helpers import fedprox_coordinate

    from datp_core.domain.values import ProximalCoefficient

    request = _request(tmp_path)
    wrong_coordinate = fedprox_coordinate(Seed(0), ProximalCoefficient(0.1))
    with pytest.raises(ScientificContractError, match="FEDAVG_AUTOENCODER coordinate"):
        train_fedavg(
            FedAvgTrainingRequest(
                coordinate=wrong_coordinate,
                clients=request.clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=request.output_directory,
            )
        )


def test_train_fedavg_never_trains_on_attack_labelled_rows(tmp_path: Path) -> None:
    from tests.unit.learning.federated.helpers import FEATURE_NAMES, benign_frame, build_client_dataset, client_identity

    from datp_core.learning.federated.models import ClientTrainingInput
    from datp_core.populations.models import PopulationOutcomeLabel

    clients = list(build_all_client_datasets(tmp_path))
    attack_frame = benign_frame(16, seed=99, label=PopulationOutcomeLabel.ATTACK.value)
    poisoned = build_client_dataset("client_a", tmp_path, row_count=16)
    poisoned = poisoned.__class__(
        training_input=ClientTrainingInput(
            client=client_identity("client_a"), training_features=attack_frame, feature_names=FEATURE_NAMES
        ),
        preprocessing_state=poisoned.preprocessing_state,
    )
    clients[0] = poisoned
    request = FedAvgTrainingRequest(
        coordinate=fedavg_coordinate(Seed(0)),
        clients=tuple(clients),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "output",
    )
    from datp_core.domain.errors import LeakageError

    with pytest.raises(LeakageError, match="attack-labelled rows"):
        train_fedavg(request)

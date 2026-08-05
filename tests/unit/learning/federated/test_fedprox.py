from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    build_all_client_inputs,
    fedprox_coordinate,
    fedprox_protocol,
)

from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, ProximalCoefficient, Seed
from datp_core.learning.federated.global_training import train_global_federated
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.protocols.training import FEDPROX_COEFFICIENTS


def _request(tmp_path: Path, coefficient: ProximalCoefficient) -> FederatedTrainingRequest:
    return FederatedTrainingRequest(
        coordinate=fedprox_coordinate(Seed(0), coefficient),
        clients=build_all_client_inputs(tmp_path),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=fedprox_protocol(coefficient),
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "output",
    )


def test_fedprox_zero_coefficient_is_structurally_impossible() -> None:
    with pytest.raises(ValueError, match="proximal coefficient"):
        ProximalCoefficient(0.0)


def test_declared_fedprox_grid_excludes_zero() -> None:
    assert all(coefficient.value > 0 for coefficient in FEDPROX_COEFFICIENTS)


def test_train_fedprox_produces_independent_model_per_coefficient(tmp_path: Path) -> None:
    first_directory = tmp_path / "coefficient_a"
    second_directory = tmp_path / "coefficient_b"
    first_directory.mkdir()
    second_directory.mkdir()
    first = train_global_federated(_request(first_directory, FEDPROX_COEFFICIENTS[0]))
    second = train_global_federated(_request(second_directory, FEDPROX_COEFFICIENTS[-1]))
    first_checksums = {candidate.tensor_checksum for candidate in first.candidates}
    second_checksums = {candidate.tensor_checksum for candidate in second.candidates}
    assert first_checksums.isdisjoint(second_checksums)


def test_train_fedprox_rejects_partial_participation(tmp_path: Path) -> None:
    coefficient = FEDPROX_COEFFICIENTS[0]
    clients = build_all_client_inputs(tmp_path)
    request = FederatedTrainingRequest(
        coordinate=fedprox_coordinate(Seed(0), coefficient),
        clients=(clients[0],),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=fedprox_protocol(coefficient),
        checkpoint_protocol=CHECKPOINT,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        split_manifest_checksum=Checksum("a" * 64),
        output_directory=tmp_path / "output",
    )
    with pytest.raises(ScientificContractError, match="does not match the declared population count"):
        train_global_federated(request)


def test_train_fedprox_rejects_mismatched_coordinate_and_protocol_coefficient(tmp_path: Path) -> None:
    request = _request(tmp_path, FEDPROX_COEFFICIENTS[0])
    mismatched = FederatedTrainingRequest(
        coordinate=fedprox_coordinate(Seed(0), FEDPROX_COEFFICIENTS[1]),
        clients=request.clients,
        population_client_count=request.population_client_count,
        autoencoder=request.autoencoder,
        training_protocol=fedprox_protocol(FEDPROX_COEFFICIENTS[0]),
        checkpoint_protocol=request.checkpoint_protocol,
        training_seed=request.training_seed,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
        split_manifest_checksum=request.split_manifest_checksum,
        output_directory=request.output_directory,
    )
    with pytest.raises(ScientificContractError, match="coefficient must match"):
        train_global_federated(mismatched)


def test_global_training_module_owns_fedavg_and_fedprox_dispatch() -> None:
    import datp_core.learning.federated.global_training as global_training

    source = Path(global_training.__file__).read_text(encoding="utf-8")
    assert "FedAvgProtocol" in source
    assert "FedProxProtocol" in source
    assert "learning.federated.fedavg" not in source
    assert "learning.federated.fedprox" not in source

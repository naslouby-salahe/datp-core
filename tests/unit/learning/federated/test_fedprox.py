from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    build_all_client_datasets,
    fedprox_coordinate,
    fedprox_protocol,
)

from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, ProximalCoefficient, Seed
from datp_core.learning.federated.fedprox import (
    FedProxPrimarySelectionStatus,
    FedProxTrainingRequest,
    fedprox_primary_selection_outcome,
    train_fedprox,
)
from datp_core.protocols.training import FEDPROX_COEFFICIENTS


def _request(tmp_path: Path, coefficient: ProximalCoefficient) -> FedProxTrainingRequest:
    return FedProxTrainingRequest(
        coordinate=fedprox_coordinate(Seed(0), coefficient),
        clients=build_all_client_datasets(tmp_path),
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
    first = train_fedprox(_request(first_directory, FEDPROX_COEFFICIENTS[0]))
    second = train_fedprox(_request(second_directory, FEDPROX_COEFFICIENTS[-1]))
    first_checksums = {candidate.tensor_checksum for candidate in first.candidates}
    second_checksums = {candidate.tensor_checksum for candidate in second.candidates}
    assert first_checksums.isdisjoint(second_checksums)


def test_train_fedprox_rejects_partial_participation(tmp_path: Path) -> None:
    coefficient = FEDPROX_COEFFICIENTS[0]
    clients = build_all_client_datasets(tmp_path)
    request = FedProxTrainingRequest(
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
    with pytest.raises(ScientificContractError, match="declared population client count"):
        train_fedprox(request)


def test_train_fedprox_rejects_mismatched_coordinate_and_protocol_coefficient(tmp_path: Path) -> None:
    request = _request(tmp_path, FEDPROX_COEFFICIENTS[0])
    mismatched = FedProxTrainingRequest(
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
        train_fedprox(mismatched)


def test_fedprox_primary_selection_outcome_is_unresolved_not_invented() -> None:
    outcome = fedprox_primary_selection_outcome(FEDPROX_COEFFICIENTS)
    assert outcome.status is FedProxPrimarySelectionStatus.UNRESOLVED_NO_SOURCE_BACKED_RULE
    assert outcome.declared_coefficients == FEDPROX_COEFFICIENTS
    assert "not declared" in outcome.detail

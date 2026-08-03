"""Stage: dispatch federated training across FedAvg, FedProx, and genuine Ditto."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl
from filelock import FileLock

from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientCount,
    FeatureNameSequence,
    LearningRate,
    Seed,
)
from datp_core.learning.federated.checkpointing import (
    CheckpointCandidate,
    FederatedHistoryAssetName,
    ReusedDittoTrainingRequest,
    ReusedFederatedTrainingRequest,
    load_reused_ditto_training,
    load_reused_federated_training,
    rebase_checkpoint_candidates,
)
from datp_core.learning.federated.ditto import DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import train_fedavg
from datp_core.learning.federated.fedprox import train_fedprox
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedTrainingCoordinate,
    FederatedTrainingResult,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import (
    FederatedTrainingRequest,
    preprocessing_state_set_checksum,
)
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import ClientPreprocessPublication
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CheckpointProtocol,
    DittoProtocol,
    FedAvgProtocol,
    FedProxProtocol,
)


def _training_is_reusable(directory: Path) -> bool:
    complete = directory / FederatedHistoryAssetName.COMPLETE.value
    return complete.is_file()


def _remove_stale_temporary_directories(target: Path) -> None:
    parent = target.parent
    if not parent.is_dir():
        return
    prefix = f".{target.name}."
    for candidate in sorted(parent.iterdir()):
        if candidate.is_dir() and candidate.name.startswith(prefix):
            rmtree(candidate, ignore_errors=True)


def _prepare_and_publish(
    target: Path,
    overwrite: bool,
    train: Callable[[Path], None],
) -> bool:
    with FileLock(f"{target}.lock"):
        _remove_stale_temporary_directories(target)
        if not overwrite and _training_is_reusable(target):
            return True
        if target.exists():
            rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        train(target)
    return False


@dataclass(frozen=True, slots=True)
class TrainFedAvgRequest:
    coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedAvgProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFedProxRequest:
    coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedProxProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainDittoRequest:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate
    client_publications: tuple[ClientPreprocessPublication, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: DittoProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    global_output_directory: Path
    personalized_output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainFederatedStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainDittoStageResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates_by_client: dict[ClientIdentity, tuple[CheckpointCandidate, ...]]


def train_fedavg_stage(request: TrainFedAvgRequest) -> TrainFederatedStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_inputs(request.coordinate, request.client_publications)
    preprocessing_checksum = _compute_checksum(clients)

    def train(target: Path) -> None:
        train_fedavg(
            FederatedTrainingRequest(
                coordinate=request.coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=target,
            )
        )

    identity_kind = resolve_population(request.coordinate.population).declaration.identity_kind
    reused = _prepare_and_publish(request.output_directory, request.overwrite, train)
    return _finalize_global(
        coordinate=request.coordinate,
        directory=request.output_directory,
        clients=clients,
        identity_kind=identity_kind,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        reused=reused,
    )


def train_fedprox_stage(request: TrainFedProxRequest) -> TrainFederatedStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_inputs(request.coordinate, request.client_publications)
    preprocessing_checksum = _compute_checksum(clients)

    def train(target: Path) -> None:
        train_fedprox(
            FederatedTrainingRequest(
                coordinate=request.coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=target,
            )
        )

    identity_kind = resolve_population(request.coordinate.population).declaration.identity_kind
    reused = _prepare_and_publish(request.output_directory, request.overwrite, train)
    return _finalize_global(
        coordinate=request.coordinate,
        directory=request.output_directory,
        clients=clients,
        identity_kind=identity_kind,
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
        preprocessing_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        reused=reused,
    )


def train_ditto_stage(request: TrainDittoRequest) -> TrainDittoStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_inputs(request.global_coordinate, request.client_publications)
    preprocessing_checksum = _compute_checksum(clients)
    identity_kind = resolve_population(request.global_coordinate.population).declaration.identity_kind

    def train(target: Path) -> None:
        train_ditto(
            DittoTrainingRequest(
                global_coordinate=request.global_coordinate,
                personalized_coordinate=request.personalized_coordinate,
                clients=clients,
                population_client_count=request.population_client_count,
                autoencoder=request.autoencoder,
                training_protocol=request.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                training_seed=request.training_seed,
                batch_size=request.batch_size,
                learning_rate=request.learning_rate,
                split_manifest_checksum=request.split_manifest_checksum,
                global_output_directory=target,
                personalized_output_directory=request.personalized_output_directory,
            )
        )

    reused = _prepare_and_publish(request.global_output_directory, request.overwrite, train)
    if reused:
        return _finalize_reused_ditto(
            request=request,
            clients=clients,
            preprocessing_checksum=preprocessing_checksum,
            identity_kind=identity_kind,
        )

    outcome = load_reused_ditto_training(
        ReusedDittoTrainingRequest(
            global_coordinate=request.global_coordinate,
            personalized_coordinate=request.personalized_coordinate,
            global_directory=request.global_output_directory,
            personalized_directory=request.personalized_output_directory,
            clients=tuple(client.client for client in clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    global_candidates = rebase_checkpoint_candidates(
        outcome.global_candidates,
        request.global_output_directory,
    )
    personalized_candidates = {
        pcs.client: rebase_checkpoint_candidates(pcs.candidates, request.personalized_output_directory)
        for pcs in outcome.personalized_candidates
    }
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=PublicationStatus.PUBLISHED,
        global_training=outcome.global_training_result,
        global_candidates=global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _finalize_reused_ditto(
    *,
    request: TrainDittoRequest,
    clients: tuple[ClientTrainingInput, ...],
    preprocessing_checksum: Checksum,
    identity_kind,
) -> TrainDittoStageResult:
    outcome = load_reused_ditto_training(
        ReusedDittoTrainingRequest(
            global_coordinate=request.global_coordinate,
            personalized_coordinate=request.personalized_coordinate,
            global_directory=request.global_output_directory,
            personalized_directory=request.personalized_output_directory,
            clients=tuple(client.client for client in clients),
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder=request.autoencoder,
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    personalized_candidates = {pcs.client: pcs.candidates for pcs in outcome.personalized_candidates}
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=PublicationStatus.REUSED,
        global_training=outcome.global_training_result,
        global_candidates=outcome.global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _finalize_global(
    *,
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    clients: tuple[ClientTrainingInput, ...],
    identity_kind,
    checkpoint_protocol: CheckpointProtocol,
    autoencoder: AutoencoderProtocol,
    batch_size: BatchSize,
    preprocessing_checksum: Checksum,
    split_manifest_checksum: Checksum,
    reused: bool,
) -> TrainFederatedStageResult:
    reload_request = ReusedFederatedTrainingRequest(
        coordinate=coordinate,
        directory=directory,
        clients=tuple(client.client for client in clients),
        checkpoint_protocol=checkpoint_protocol,
        identity_kind=identity_kind,
        autoencoder=autoencoder,
        batch_size=batch_size,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=split_manifest_checksum,
    )
    outcome = load_reused_federated_training(reload_request)
    status = PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED
    candidates = rebase_checkpoint_candidates(outcome.candidates, directory)
    return TrainFederatedStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=status,
        training=outcome.training_result,
        candidates=candidates,
    )


def _compute_checksum(clients: tuple[ClientTrainingInput, ...]) -> Checksum:
    return preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client.client,
                preprocessing_checksum=client.preprocessing_state.estimator_checksum,
            )
            for client in clients
        )
    )


def _client_inputs(
    coordinate: FederatedTrainingCoordinate,
    client_publications: tuple[ClientPreprocessPublication, ...],
) -> tuple[ClientTrainingInput, ...]:
    identity_kind = resolve_population(coordinate.population).declaration.identity_kind
    inputs: list[ClientTrainingInput] = []
    for publication in client_publications:
        client = ClientIdentity(coordinate.population, publication.client_identity.value, identity_kind)
        frame = pl.read_parquet(publication.result.train_path)
        training_input = ClientTrainingInput(
            client=client,
            training_features=frame,
            feature_names=FeatureNameSequence(publication.result.transformed_schema.feature_names),
            preprocessing_state=publication.result.fitted_state,
        )
        inputs.append(training_input)
    return tuple(inputs)


def _require_autoencoder_matches_preprocessing(
    autoencoder: AutoencoderProtocol,
    client_publications: tuple[ClientPreprocessPublication, ...],
) -> None:
    """Fail before training when a declared model cannot reconstruct its published feature space."""
    if not client_publications:
        raise ScientificContractError(
            "federated training requires published client preprocessing", subject=ContractSubject.TRAINING
        )
    expected_names = client_publications[0].result.transformed_schema.feature_names
    expected_width = len(expected_names)
    if autoencoder.widths[0] != expected_width or autoencoder.widths[-1] != expected_width:
        raise ScientificContractError(
            "autoencoder input and reconstruction widths must match the published transformed schema",
            subject=ContractSubject.WIDTHS,
        )
    if any(
        publication.result.transformed_schema.feature_names != expected_names for publication in client_publications
    ):
        raise ScientificContractError(
            "federated clients must publish one identical transformed feature schema",
            subject=ContractSubject.SCHEMA,
        )

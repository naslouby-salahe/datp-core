"""Stage: dispatch federated training across FedAvg, FedProx, and genuine Ditto."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientCount,
    FeatureNameSequence,
    LearningRate,
    Seed,
)
from datp_core.learning.federated.checkpointing import CheckpointCandidate
from datp_core.learning.federated.ditto import DittoTrainingOutcome, DittoTrainingRequest, train_ditto
from datp_core.learning.federated.fedavg import (
    FedAvgClientDataset,
    FedAvgTrainingOutcome,
    FedAvgTrainingRequest,
    train_fedavg,
)
from datp_core.learning.federated.fedprox import FedProxTrainingRequest, train_fedprox
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedHistoryAssetName,
    FederatedTrainingCoordinate,
    FederatedTrainingResult,
    ReusedFederatedTrainingRequest,
    ReusedPersonalizedCandidatesRequest,
    federated_training_directory_is_reusable,
    load_reused_federated_training,
    load_reused_personalized_candidates,
    persist_federated_training_history,
    rebase_checkpoint_candidates,
    training_complete_digest,
)
from datp_core.learning.federated.training import preprocessing_state_set_checksum
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


@dataclass
class _OutcomeBox[OutcomeT]:
    """A single-slot mutable box for an `AtomicPublication.write` closure to populate."""

    outcome: OutcomeT | None = None


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
    personalized_candidates_by_client: dict[str, tuple[CheckpointCandidate, ...]]


def train_fedavg_stage(request: TrainFedAvgRequest) -> TrainFederatedStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_datasets(request.coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in clients)
    )
    box: _OutcomeBox[FedAvgTrainingOutcome] = _OutcomeBox()

    def write(temporary: Path) -> None:
        outcome = train_fedavg(
            FedAvgTrainingRequest(
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
                output_directory=temporary,
            )
        )
        _publish_training_artifacts(temporary, outcome.training_result, outcome.candidates)
        box.outcome = outcome

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: federated_training_directory_is_reusable(
                directory, request.checkpoint_protocol.candidates
            ),
            write=write,
            remove_target=rmtree,
        )
    )
    return _finalize_global_training_stage(
        reload=ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=request.output_directory,
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=resolve_population(request.coordinate.population).declaration.identity_kind,
            autoencoder_widths=tuple(request.autoencoder.widths),
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        ),
        outcome=box.outcome,
        reused=reused,
    )


def train_fedprox_stage(request: TrainFedProxRequest) -> TrainFederatedStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_datasets(request.coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in clients)
    )
    box: _OutcomeBox[FedAvgTrainingOutcome] = _OutcomeBox()

    def write(temporary: Path) -> None:
        outcome = train_fedprox(
            FedProxTrainingRequest(
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
                output_directory=temporary,
            )
        )
        _publish_training_artifacts(temporary, outcome.training_result, outcome.candidates)
        box.outcome = outcome

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: federated_training_directory_is_reusable(
                directory, request.checkpoint_protocol.candidates
            ),
            write=write,
            remove_target=rmtree,
        )
    )
    return _finalize_global_training_stage(
        reload=ReusedFederatedTrainingRequest(
            coordinate=request.coordinate,
            directory=request.output_directory,
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=resolve_population(request.coordinate.population).declaration.identity_kind,
            autoencoder_widths=tuple(request.autoencoder.widths),
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        ),
        outcome=box.outcome,
        reused=reused,
    )


def train_ditto_stage(request: TrainDittoRequest) -> TrainDittoStageResult:
    _require_autoencoder_matches_preprocessing(request.autoencoder, request.client_publications)
    clients = _client_datasets(request.global_coordinate, request.client_publications)
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple(client.preprocessing_state.estimator_checksum for client in clients)
    )
    box: _OutcomeBox[DittoTrainingOutcome] = _OutcomeBox()

    def write_global(temporary: Path) -> None:
        if box.outcome is None:
            box.outcome = train_ditto(
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
                    global_output_directory=temporary,
                    personalized_output_directory=request.personalized_output_directory,
                )
            )
        _publish_training_artifacts(
            temporary,
            box.outcome.global_training_result,
            box.outcome.global_candidates,
        )

    reused = publish_atomically(
        AtomicPublication(
            target=request.global_output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: federated_training_directory_is_reusable(
                directory, request.checkpoint_protocol.candidates
            ),
            write=write_global,
            remove_target=rmtree,
        )
    )
    if reused:
        return _finalize_reused_ditto_stage(request, clients, preprocessing_checksum)
    if box.outcome is None:
        raise ArtifactIntegrityError(
            "Ditto training write did not populate an outcome", subject=ContractSubject.TRAINING
        )
    global_candidates = rebase_checkpoint_candidates(
        box.outcome.global_candidates, request.global_output_directory, client=None
    )
    personalized_candidates = {
        client_id: rebase_checkpoint_candidates(
            candidates,
            request.personalized_output_directory,
            client=_client_by_id(clients, client_id),
        )
        for client_id, candidates in box.outcome.personalized_candidates_by_client.items()
    }
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=PublicationStatus.PUBLISHED,
        global_training=box.outcome.global_training_result,
        global_candidates=global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _finalize_reused_ditto_stage(
    request: TrainDittoRequest,
    clients: tuple[FedAvgClientDataset, ...],
    preprocessing_checksum: Checksum,
) -> TrainDittoStageResult:
    identity_kind = resolve_population(request.global_coordinate.population).declaration.identity_kind
    global_training, global_candidates = load_reused_federated_training(
        ReusedFederatedTrainingRequest(
            coordinate=request.global_coordinate,
            directory=request.global_output_directory,
            checkpoint_protocol=request.checkpoint_protocol,
            identity_kind=identity_kind,
            autoencoder_widths=tuple(request.autoencoder.widths),
            batch_size=request.batch_size,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    personalized_candidates = load_reused_personalized_candidates(
        ReusedPersonalizedCandidatesRequest(
            personalized_coordinate=request.personalized_coordinate,
            personalized_output_directory=request.personalized_output_directory,
            global_history_directory=request.global_output_directory,
            clients=tuple(client.training_input.client for client in clients),
            checkpoint_protocol=request.checkpoint_protocol,
            preprocessing_state_set_checksum=preprocessing_checksum,
            split_manifest_checksum=request.split_manifest_checksum,
        )
    )
    return TrainDittoStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=PublicationStatus.REUSED,
        global_training=global_training,
        global_candidates=global_candidates,
        personalized_candidates_by_client=personalized_candidates,
    )


def _publish_training_artifacts(
    directory: Path,
    training_result: FederatedTrainingResult,
    candidates: tuple[CheckpointCandidate, ...],
) -> None:
    persist_federated_training_history(
        training_result.history,
        directory,
        device_name=training_result.device_name,
    )
    digest = training_complete_digest(candidates)
    (directory / FederatedHistoryAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")


def _finalize_global_training_stage(
    *,
    reload: ReusedFederatedTrainingRequest,
    outcome: FedAvgTrainingOutcome | None,
    reused: bool,
) -> TrainFederatedStageResult:
    if reused:
        training, candidates = load_reused_federated_training(reload)
        status = PublicationStatus.REUSED
    else:
        if outcome is None:
            raise ArtifactIntegrityError(
                "federated training write did not populate an outcome", subject=ContractSubject.TRAINING
            )
        training = outcome.training_result
        candidates = rebase_checkpoint_candidates(outcome.candidates, reload.directory, client=None)
        status = PublicationStatus.PUBLISHED
    return TrainFederatedStageResult(
        stage=StageOperationId.TRAIN_FEDERATED,
        publication_status=status,
        training=training,
        candidates=candidates,
    )


def _client_by_id(clients: tuple[FedAvgClientDataset, ...], client_id: str) -> ClientIdentity:
    for client in clients:
        if client.training_input.client.client_id == client_id:
            return client.training_input.client
    raise ScientificContractError(
        f"no client dataset found for personalized checkpoint client {client_id}",
        subject=ContractSubject.CLIENT_IDENTITY,
    )


def _client_datasets(
    coordinate: FederatedTrainingCoordinate,
    client_publications: tuple[ClientPreprocessPublication, ...],
) -> tuple[FedAvgClientDataset, ...]:
    identity_kind = resolve_population(coordinate.population).declaration.identity_kind
    datasets: list[FedAvgClientDataset] = []
    for publication in client_publications:
        client = ClientIdentity(coordinate.population, publication.client_identity.value, identity_kind)
        frame = pl.read_parquet(publication.result.train_path)
        training_input = ClientTrainingInput(
            client=client,
            training_features=frame,
            feature_names=FeatureNameSequence(publication.result.transformed_schema.feature_names),
        )
        datasets.append(
            FedAvgClientDataset(training_input=training_input, preprocessing_state=publication.result.fitted_state)
        )
    return tuple(datasets)


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
